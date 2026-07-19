#!/usr/bin/env python3
"""Outer AERS runner: drive scripts/loop.py across all ready tasks of a feature.

Honors the ledger's dependency graph, per-task attempt budgets, and a STOP file
(.aers-runtime/STOP). Like loop.py it only produces AUTHOR_READY candidates on
branches; it never pushes, merges, or issues VERIFIED. Run inside a sandbox.

Usage:
  python3 scripts/run_ready.py --feature FEAT-001 [--max-runs 10] [--contract-ref HEAD]
Env:
  AERS_AGENT_CMD_JSON / AERS_REVIEWER_CMD_JSON (required by loop.py)
  AERS_AUDITOR_CMD_JSON (optional LLM audit stage)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aers.config import load_config
from aers.ledger import Ledger

READY_SATISFIED = {"author_ready", "verified", "merged", "released"}
RUNNABLE = {"pending", "failed"}
TERMINAL = {"safe_stopped", "rejected", "blocked", "author_ready", "verified", "merged", "released"}


def ready_tasks(ledger: Ledger, feature_id: str) -> list[dict]:
    view = ledger.view(feature_id)
    by_id = {t["task_id"]: t for t in view["tasks"]}
    out = []
    for task in view["tasks"]:
        if task["status"] not in RUNNABLE:
            continue
        definition = json.loads(ledger.task(feature_id, task["task_id"])["definition_json"]) \
            if "definition_json" in ledger.task(feature_id, task["task_id"]) else ledger.task(feature_id, task["task_id"])["definition"]
        if task["attempts"] >= definition["budget"]["max_attempts"]:
            continue
        deps = definition.get("depends_on", [])
        if all(by_id.get(d, {}).get("status") in READY_SATISFIED for d in deps):
            out.append({"task_id": task["task_id"], "attempts": task["attempts"], "definition": definition})
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--max-runs", type=int, default=12)
    parser.add_argument("--contract-ref", default="HEAD")
    args = parser.parse_args(argv)
    cfg = load_config()
    mission = cfg.repo / "MISSION.md"
    if mission.exists() and "<!-- PLACEHOLDER" in mission.read_text(encoding="utf-8", errors="replace"):
        print("SAFE_STOP: MISSION.md is still the unfilled placeholder; a human must state the repository's mission before autonomous work", file=sys.stderr)
        return 2
    ledger = Ledger(cfg.state_dir / "ledger.sqlite3")
    stop_file = cfg.state_dir / "STOP"
    runs = 0
    results: list[dict] = []
    while runs < args.max_runs:
        if stop_file.exists():
            print("STOP file present — halting.", file=sys.stderr)
            break
        candidates = ready_tasks(ledger, args.feature)
        if not candidates:
            break
        task_id = sorted(candidates, key=lambda t: t["task_id"])[0]["task_id"]
        runs += 1
        print(f"=== run {runs}: {args.feature}/{task_id} ===", file=sys.stderr)
        proc = subprocess.run([sys.executable, "scripts/loop.py", "--feature", args.feature,
                               "--task", task_id, "--contract-ref", args.contract_ref],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # child output goes to stderr so this runner's stdout stays pure JSON
        sys.stderr.write(proc.stdout or "")
        status = ledger.task(args.feature, task_id)["status"]
        results.append({"run": runs, "task_id": task_id, "loop_exit": proc.returncode, "status": status})
        if status == "safe_stopped":
            print(f"SAFE_STOP recorded for {task_id}; stopping the outer runner for human review.", file=sys.stderr)
            break
    view = ledger.view(args.feature)
    stale = ledger.stale_stacks(args.feature)
    for item in stale:
        print(f"STALE STACK: {item['task_id']} was verified against {item['dependency']}@"
              f"{(item['integrated_candidate'] or '')[:12]} but that dependency's candidate is now "
              f"{(item['current_candidate'] or 'gone')[:12]} — requeue before external verification: "
              f"python3 scripts/aers.py requeue --feature {args.feature} --task {item['task_id']} --reason 'stale stack'",
              file=sys.stderr)
    summary = {"feature_id": args.feature, "runs": results,
               "tasks": [{"task_id": t["task_id"], "status": t["status"], "attempts": t["attempts"],
                          "candidate_sha": t["candidate_sha"]} for t in view["tasks"]],
               "stale_stacks": stale,
               "statement": "AUTHOR_READY candidates only; external verifier attestation is still required."}
    print(json.dumps(summary, indent=2))
    incomplete = [t for t in view["tasks"] if t["status"] not in READY_SATISFIED]
    return 0 if not incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
