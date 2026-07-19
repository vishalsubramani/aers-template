"""Build per-task context packets: hashed file excerpts, contract text, curated
lessons recalled by scope association, and navigation for a fresh agent."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import load_bundle
from .git import rev_parse, run_git
from .util import atomic_write_text, load_json, sha256_bytes, utc_now

MAX_LESSONS = 8


def _glob_prefix(pattern: str) -> str:
    return pattern.split("*", 1)[0].rstrip("/")


def _globs_overlap(a: str, b: str) -> bool:
    """Conservative pattern-level intersection: one glob's literal prefix is a
    path-component prefix of the other's. Covers scopes over paths that do not
    exist yet (creation tasks), e.g. `src/newmod/**` vs `src/**`."""
    pa, pb = _glob_prefix(a), _glob_prefix(b)
    if not pa or not pb:
        return False
    return (pa + "/").startswith(pb + "/") or (pb + "/").startswith(pa + "/")


def select_active_lessons(repo: Path, write_scope: list[str], tracked_paths: list[str]) -> list[dict[str, Any]]:
    """Deterministic associative recall from curated active memory.

    A lesson is directly relevant when its `scope` globs intersect the task's
    write scope — via a tracked path both match, or at the pattern level so
    creation tasks recall lessons for files that do not exist yet — or when
    its scope is global (empty / `**`). Records reachable one hop through
    `links` from a relevant record are included too, so related lessons
    surface together. Selection is glob intersection, not similarity —
    auditable, reproducible, and stdlib-only by design.

    Integrity fail-closed: only records under `.agents/memory/active/` with
    status `active`, an index-matching sha256, and a recomputed content hash
    are eligible. Quarantined or tampered records are never loaded.
    """
    from .scope import matches
    from .util import hash_object
    index_path = repo / ".agents/memory/index.json"
    if not index_path.exists():
        return []
    active_root = (repo / ".agents/memory/active").resolve()
    records: dict[str, dict[str, Any]] = {}
    for item in load_json(index_path).get("active_records", []):
        record_path = (repo / item["path"]).resolve()
        try:
            record_path.relative_to(active_root)
        except ValueError:
            continue  # index points outside the active store — never load
        if not record_path.exists():
            continue
        record = load_json(record_path)
        if record.get("status") != "active":
            continue
        if record.get("sha256") != item.get("sha256"):
            continue  # index/record disagreement — treat as tampered
        if hash_object({k: v for k, v in record.items() if k != "sha256"}) != record.get("sha256"):
            continue  # content does not match its own hash — tampered
        records[record["id"]] = record
    scoped_paths = [p for p in tracked_paths if matches(p, write_scope)]

    def tier(record: dict[str, Any]) -> int:
        """Lower is more relevant. 0: a tracked path in scope matches the
        lesson's globs (direct hit). 1: pattern-level scope overlap (creation
        tasks). 2: global lesson. 3: reached only via a link. Ranking before
        truncation keeps recall sharp as memory grows — specific beats broad."""
        globs = record.get("scope") or []
        if any(matches(p, globs) for p in scoped_paths):
            return 0
        if any(_globs_overlap(g, w) for g in globs for w in write_scope):
            return 1
        if not globs or "**" in globs:
            return 2
        return 3

    tiers = {r["id"]: tier(r) for r in records.values()}
    selected: dict[str, int] = {rid: t for rid, t in tiers.items() if t <= 2}
    for rid in list(selected):
        for linked_id in records[rid].get("links", []):
            if linked_id in records:
                selected.setdefault(linked_id, 3)  # link-reached, lowest priority
    # Sort by (tier asc, id desc) — most relevant first, newest breaking ties.
    ordered = sorted(selected, key=lambda rid: (selected[rid], _neg_id(rid)))
    return [records[rid] for rid in ordered[:MAX_LESSONS]]


def _neg_id(record_id: str) -> tuple:
    # Sort helper: newer IDs (lexicographically larger) come first within a tier.
    return tuple(-ord(c) for c in record_id)


def build_context_packet(repo: Path, feature_id: str, task_id: str, base_ref: str, output: Path,
                         contract_ref: str | None = None) -> dict[str, Any]:
    # base_ref: where files are listed (integration start for stacked tasks).
    # contract_ref: where immutable contracts are read; defaults to base_ref.
    base_sha = rev_parse(repo, base_ref)
    contract_sha = rev_parse(repo, contract_ref) if contract_ref else base_sha
    bundle = load_bundle(repo, feature_id, task_id, ref=contract_sha)
    tracked = run_git(repo, ["ls-tree", "-r", "--name-only", base_sha]).stdout.splitlines()
    scopes = bundle.task["write_scope"]
    likely = []
    from .scope import matches
    for path in tracked:
        if matches(path, scopes) or matches(path, ["AGENTS.md", ".agents/context/**", ".agents/doctrine/**", "docs/adr/**", "docs/runbooks/**", "tests/**", "**/*_test.*", "**/*.test.*", "**/*.spec.*"]):
            likely.append(path)
    likely = likely[:500]
    lines = [
        f"# Context Packet — {feature_id}/{task_id}", "", f"Generated: {utc_now()}", f"Base SHA: `{base_sha}`",
        f"Contract SHA: `{contract_sha}`",
        f"Feature contract SHA-256: `{bundle.feature_hash}`", f"Task graph SHA-256: `{bundle.tasks_hash}`", "",
        "## Task", f"- Title: {bundle.task['title']}", f"- Role: `{bundle.task['role']}`",
        f"- Exact write scope: {', '.join(f'`{x}`' for x in bundle.task['write_scope']) or 'none'}",
        f"- Acceptance IDs: {', '.join(bundle.task['acceptance'])}", "", "## Acceptance criteria"
    ]
    criteria = {c["id"]: c for c in bundle.feature["acceptance_criteria"]}
    for cid in bundle.task["acceptance"]:
        c = criteria[cid]
        lines.append(f"- **{cid}:** {c['statement']} — evidence: {', '.join(c['evidence'])}")
    lines += ["", "## Commands"]
    for command in bundle.task["commands"]:
        lines.append(f"- `{command['name']}`: `{command['argv']}`; timeout {command['timeout_seconds']}s; network {command.get('network','deny')}")
    lines += ["", "## Relevant repository paths at base"]
    lines.extend(f"- `{p}`" for p in likely)
    lessons = select_active_lessons(repo, scopes, tracked)
    lines += ["", "## Curated lessons (active memory)"]
    if lessons:
        for record in lessons:
            provenance = ", ".join(record.get("provenance", [])[:3])
            lines.append(f"- **{record['id']}** ({provenance}): {record['statement']}")
        lines.append("These are curator-promoted, hash-verified lessons recalled by scope association. Quarantined memory is never loaded.")
    else:
        lines.append("None active for this scope.")
    lines += ["", "## Mandatory stop conditions", "- Missing/conflicting evidence or contract", "- Scope, risk, permission, network, secret, destructive-operation, nondeterminism, or budget violation", "- Repeated failure without a materially new hypothesis", "", "This packet is navigational. Read primary files directly and record their hashes when load-bearing."]
    text = "\n".join(lines) + "\n"
    atomic_write_text(output, text)
    return {"path": str(output), "sha256": sha256_bytes(text.encode()), "base_sha": base_sha, "paths_indexed": len(likely)}
