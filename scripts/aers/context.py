from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import load_bundle
from .git import rev_parse, run_git
from .util import atomic_write_text, sha256_bytes, utc_now


def build_context_packet(repo: Path, feature_id: str, task_id: str, base_ref: str, output: Path) -> dict[str, Any]:
    base_sha = rev_parse(repo, base_ref)
    bundle = load_bundle(repo, feature_id, task_id, ref=base_sha)
    tracked = run_git(repo, ["ls-tree", "-r", "--name-only", base_sha]).stdout.splitlines()
    scopes = bundle.task["write_scope"]
    likely = []
    from .scope import matches
    for path in tracked:
        if matches(path, scopes) or matches(path, ["AGENTS.md", ".agents/context/**", "docs/adr/**", "docs/runbooks/**", "tests/**", "**/*_test.*", "**/*.test.*", "**/*.spec.*"]):
            likely.append(path)
    likely = likely[:500]
    lines = [
        f"# Context Packet — {feature_id}/{task_id}", "", f"Generated: {utc_now()}", f"Base SHA: `{base_sha}`",
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
    lines += ["", "## Mandatory stop conditions", "- Missing/conflicting evidence or contract", "- Scope, risk, permission, network, secret, destructive-operation, nondeterminism, or budget violation", "- Repeated failure without a materially new hypothesis", "", "This packet is navigational. Read primary files directly and record their hashes when load-bearing."]
    text = "\n".join(lines) + "\n"
    atomic_write_text(output, text)
    return {"path": str(output), "sha256": sha256_bytes(text.encode()), "base_sha": base_sha, "paths_indexed": len(likely)}
