"""External SQLite runtime ledger: registered contracts, task state machine, and hash-chained append-only events."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .contracts import validate_feature, validate_tasks
from .util import canonical_json, hash_object, utc_now

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS features (
  feature_id TEXT PRIMARY KEY,
  base_sha TEXT NOT NULL,
  feature_hash TEXT NOT NULL,
  tasks_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  registered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  feature_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  role TEXT NOT NULL,
  definition_json TEXT NOT NULL,
  definition_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  lease_owner TEXT,
  lease_expires_at TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  candidate_sha TEXT,
  PRIMARY KEY(feature_id, task_id),
  FOREIGN KEY(feature_id) REFERENCES features(feature_id)
);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  feature_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  failure_fingerprint TEXT,
  evidence_path TEXT,
  FOREIGN KEY(feature_id, task_id) REFERENCES tasks(feature_id, task_id)
);
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  UNIQUE(run_id, sequence),
  FOREIGN KEY(run_id) REFERENCES runs(run_id)
);
"""

ALLOWED_TASK_TRANSITIONS = {
    "pending": {"leased", "blocked", "safe_stopped"},
    "leased": {"implementing", "pending", "failed", "safe_stopped"},
    "implementing": {"scope_passed", "failed", "safe_stopped"},
    "scope_passed": {"candidate_committed", "failed"},
    "candidate_committed": {"author_verifying", "failed"},
    "author_verifying": {"auditing", "failed", "safe_stopped"},
    "auditing": {"reviewing", "failed", "safe_stopped"},
    "reviewing": {"author_ready", "failed", "safe_stopped"},
    # author_ready -> pending exists only for explicit human requeue (stale
    # stack or withdrawn candidate); the runners never take it themselves.
    "author_ready": {"verified", "rejected", "pending"},
    "verified": {"merged", "released"},
    "failed": {"pending", "safe_stopped"},
    "blocked": {"pending", "safe_stopped"},
    "safe_stopped": set(), "rejected": set(), "merged": set(), "released": set(),
}


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def register(self, feature: dict[str, Any], tasks_doc: dict[str, Any], base_sha: str) -> None:
        validate_feature(feature)
        validate_tasks(tasks_doc, feature)
        if feature.get("status") != "approved":
            raise ValueError(f"Feature contract status is '{feature.get('status')}'; a human must set it to 'approved' before registration")
        if feature.get("owner") == "REPLACE_WITH_OWNER":
            raise ValueError("Feature contract owner is still the REPLACE_WITH_OWNER scaffold value; assign a real owner")
        feature_hash, tasks_hash = hash_object(feature), hash_object(tasks_doc)
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM features WHERE feature_id=?", (feature["feature_id"],)).fetchone()
            if existing:
                if existing["feature_hash"] != feature_hash or existing["tasks_hash"] != tasks_hash or existing["base_sha"] != base_sha:
                    raise ValueError("Registered immutable feature/task definition differs from ledger; create a new approved version")
                return
            conn.execute("INSERT INTO features VALUES (?,?,?,?,?,?)", (feature["feature_id"], base_sha, feature_hash, tasks_hash, "registered", utc_now()))
            for task in tasks_doc["tasks"]:
                payload = canonical_json(task)
                conn.execute("INSERT INTO tasks(feature_id,task_id,role,definition_json,definition_hash,status) VALUES (?,?,?,?,?,?)",
                             (feature["feature_id"], task["id"], task["role"], payload, hash_object(task), "pending"))

    def task(self, feature_id: str, task_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE feature_id=? AND task_id=?", (feature_id, task_id)).fetchone()
            if not row:
                raise ValueError(f"Task not registered: {feature_id}/{task_id}")
            result = dict(row)
            result["definition"] = json.loads(result.pop("definition_json"))
            return result

    def start_run(self, feature_id: str, task_id: str, owner: str) -> str:
        run_id = f"RUN-{uuid.uuid4().hex[:16]}"
        with self.connect() as conn:
            # Atomic compare-and-set lease: two concurrent runners cannot both
            # win — the losing UPDATE matches zero rows.
            cursor = conn.execute(
                "UPDATE tasks SET status='leased', lease_owner=?, attempts=attempts+1 "
                "WHERE feature_id=? AND task_id=? AND status IN ('pending','failed')",
                (owner, feature_id, task_id))
            if cursor.rowcount != 1:
                row = conn.execute("SELECT status FROM tasks WHERE feature_id=? AND task_id=?", (feature_id, task_id)).fetchone()
                raise ValueError(f"Task cannot be leased from state: {row['status'] if row else 'missing'}")
            conn.execute("INSERT INTO runs(run_id,feature_id,task_id,status,started_at) VALUES (?,?,?,?,?)", (run_id, feature_id, task_id, "running", utc_now()))
        self.append_event(run_id, "run_started", {"owner": owner, "feature_id": feature_id, "task_id": task_id})
        return run_id

    def transition(self, feature_id: str, task_id: str, new_status: str, run_id: str, payload: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT status FROM tasks WHERE feature_id=? AND task_id=?", (feature_id, task_id)).fetchone()
            if not row:
                raise ValueError("Task not registered")
            current = row["status"]
            if new_status not in ALLOWED_TASK_TRANSITIONS.get(current, set()):
                raise ValueError(f"Invalid task transition {current} -> {new_status}")
            # Compare-and-set on the observed state so a concurrent transition
            # loses loudly instead of silently overwriting.
            cursor = conn.execute("UPDATE tasks SET status=? WHERE feature_id=? AND task_id=? AND status=?",
                                  (new_status, feature_id, task_id, current))
            if cursor.rowcount != 1:
                raise ValueError(f"Concurrent transition lost: task left state {current} during {current} -> {new_status}")
        self.append_event(run_id, "state_transition", {"from": current, "to": new_status, **(payload or {})})

    def set_candidate(self, feature_id: str, task_id: str, candidate_sha: str, run_id: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE tasks SET candidate_sha=? WHERE feature_id=? AND task_id=?", (candidate_sha, feature_id, task_id))
        self.append_event(run_id, "candidate_bound", {"candidate_sha": candidate_sha})

    def finish_run(self, run_id: str, status: str, evidence_path: str | None = None, failure_fingerprint: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE runs SET status=?,finished_at=?,evidence_path=?,failure_fingerprint=? WHERE run_id=?",
                         (status, utc_now(), evidence_path, failure_fingerprint, run_id))
        self.append_event(run_id, "run_finished", {"status": status, "evidence_path": evidence_path, "failure_fingerprint": failure_fingerprint})

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT sequence,event_hash FROM events WHERE run_id=? ORDER BY sequence DESC LIMIT 1", (run_id,)).fetchone()
            sequence = 1 if not row else row["sequence"] + 1
            prev_hash = "0" * 64 if not row else row["event_hash"]
            event = {"event_id": str(uuid.uuid4()), "run_id": run_id, "sequence": sequence, "event_type": event_type,
                     "timestamp": utc_now(), "payload": payload, "prev_hash": prev_hash}
            event_hash = hash_object(event)
            conn.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)",
                         (event["event_id"], run_id, sequence, event_type, event["timestamp"], canonical_json(payload), prev_hash, event_hash))
            event["event_hash"] = event_hash
            return event

    def verify_chain(self, run_id: str) -> bool:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
        prev = "0" * 64
        expected_seq = 1
        for row in rows:
            if row["sequence"] != expected_seq or row["prev_hash"] != prev:
                return False
            event = {"event_id": row["event_id"], "run_id": row["run_id"], "sequence": row["sequence"],
                     "event_type": row["event_type"], "timestamp": row["timestamp"],
                     "payload": json.loads(row["payload_json"]), "prev_hash": row["prev_hash"]}
            if hash_object(event) != row["event_hash"]:
                return False
            prev, expected_seq = row["event_hash"], expected_seq + 1
        return True

    def view(self, feature_id: str | None = None) -> dict[str, Any]:
        with self.connect() as conn:
            if feature_id:
                features = [dict(r) for r in conn.execute("SELECT * FROM features WHERE feature_id=?", (feature_id,))]
                tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE feature_id=? ORDER BY task_id", (feature_id,))]
                runs = [dict(r) for r in conn.execute("SELECT * FROM runs WHERE feature_id=? ORDER BY started_at", (feature_id,))]
            else:
                features = [dict(r) for r in conn.execute("SELECT * FROM features ORDER BY registered_at")]
                tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY feature_id,task_id")]
                runs = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY started_at")]
        for task in tasks:
            task.pop("definition_json", None)
        return {"features": features, "tasks": tasks, "runs": runs}

    def stale_stacks(self, feature_id: str) -> list[dict[str, Any]]:
        """Finished stacked tasks whose dependency candidates have since changed.

        Such a task's evidence was produced against an integration start that
        no longer reflects its dependencies; it needs human requeue before
        external verification can trust it.
        """
        view = self.view(feature_id)
        candidates = {t["task_id"]: t["candidate_sha"] for t in view["tasks"]}
        stale: list[dict[str, Any]] = []
        with self.connect() as conn:
            for task in view["tasks"]:
                if task["status"] not in {"author_ready", "verified"}:
                    continue
                requeuable = task["status"] == "author_ready"
                rows = conn.execute(
                    "SELECT e.payload_json FROM events e JOIN runs r ON e.run_id=r.run_id "
                    "WHERE r.feature_id=? AND r.task_id=? AND e.event_type='state_transition' "
                    "ORDER BY e.rowid DESC", (feature_id, task["task_id"])).fetchall()
                for row in rows:
                    payload = json.loads(row["payload_json"])
                    if payload.get("to") != "author_ready":
                        continue
                    for entry in payload.get("integrated", []):
                        dep, sha = entry.split(":", 1)
                        if candidates.get(dep) != sha:
                            stale.append({"task_id": task["task_id"], "status": task["status"],
                                          "dependency": dep, "integrated_candidate": sha,
                                          "current_candidate": candidates.get(dep),
                                          "remediation": "requeue" if requeuable else "external_reverify"})
                    break
        return stale

    INTERMEDIATE_STATES = {"leased", "implementing", "scope_passed", "candidate_committed",
                           "author_verifying", "auditing", "reviewing"}
    FORCE_RECOVERABLE = INTERMEDIATE_STATES | {"safe_stopped", "rejected"}

    def requeue(self, feature_id: str, task_id: str, reason: str, force: bool = False) -> None:
        """Explicit human re-queue back to `pending`, clearing the candidate
        binding and RESETTING the attempt counter (a human requeue is a fresh
        authorization to attempt). Always journaled, never called by a runner:
        - normal: a finished-but-stale/withdrawn candidate (author_ready -> pending);
        - `force=True`: recover a task stuck with no live process — an orphaned
          in-flight run (crash/SIGKILL) OR a `safe_stopped`/`rejected` task a
          human has decided to return to service. Force bypasses the normal
          transition table but is still journaled with the reason.
        """
        if not reason.strip():
            raise ValueError("Requeue requires a human-stated reason")
        with self.connect() as conn:
            row = conn.execute("SELECT run_id FROM runs WHERE feature_id=? AND task_id=? ORDER BY started_at DESC LIMIT 1",
                               (feature_id, task_id)).fetchone()
            status_row = conn.execute("SELECT status FROM tasks WHERE feature_id=? AND task_id=?", (feature_id, task_id)).fetchone()
        if not row or not status_row:
            raise ValueError("No prior run recorded; nothing to requeue")
        current = status_row["status"]
        if not force and current != "author_ready":
            raise ValueError(f"Invalid requeue from {current}; use --force to recover a stuck/parked task")
        if force and current not in self.FORCE_RECOVERABLE:
            raise ValueError(f"--force cannot recover a terminal state: {current}")
        # Single compare-and-set: the status flip AND the candidate/lease/attempt
        # clear are one atomic UPDATE guarded on the observed state, so a crash
        # or a concurrent lease cannot leave a half-requeued row.
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET status='pending', candidate_sha=NULL, lease_owner=NULL, attempts=0 "
                "WHERE feature_id=? AND task_id=? AND status=?", (feature_id, task_id, current))
            if cursor.rowcount != 1:
                raise ValueError(f"Requeue lost a race: task left state {current}")
        self.append_event(row["run_id"], "state_transition",
                          {"from": current, "to": "pending", "requeue": True, "forced": force, "reason": reason.strip()})
