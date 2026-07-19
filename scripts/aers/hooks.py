"""Claude Code hook guards: early denial of dangerous commands and protected-path writes (defense in depth, not the boundary)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import load_config
from .contracts import load_bundle
from .scope import classify_path, matches
from .util import load_json

DANGEROUS = [r"git\s+push\s+.*--force", r"git\s+reset\s+--hard", r"git\s+clean\s+-fdx", r"rm\s+-rf\s+/", r"curl[^\n|]*\|\s*(?:sh|bash)", r"wget[^\n|]*\|\s*(?:sh|bash)", r"/proc/self/environ", r"\bprintenv\b"]


def _bash_write_targets(command: str) -> list[str]:
    """Best-effort extraction of paths a shell command would write or remove.

    Shell cannot be parsed reliably without executing it; this catches the
    common forms (redirection, tee, sed -i, rm/mv) so protected-path writes
    are denied early. The scope gate on the actual git diff is the boundary.
    """
    targets: list[str] = []
    for match in re.finditer(r"(?<![<>0-9])>{1,2}\s*([^\s;|&<>]+)", command):
        targets.append(match.group(1))
    for match in re.finditer(r"\btee\b((?:\s+-\S+)*)((?:\s+[^\s;|&-]\S*)+)", command):
        targets.extend(match.group(2).split())
    for pattern in (r"\bsed\b[^|;&]*\s-i\S*\s+(.+)$", r"\b(?:rm|mv)\b((?:\s+-\S+)*)((?:\s+[^\s;|&-]\S*)+)"):
        for match in re.finditer(pattern, command, flags=re.MULTILINE):
            targets.extend(t for t in match.group(match.lastindex).split() if not t.startswith("-"))
    return targets


def _deny(reason: str) -> int:
    print(json.dumps({"decision":"block","reason":reason}))
    return 2


def pre_tool_guard(payload: dict[str, Any]) -> int:
    cfg = load_config()
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command", ""))
    for pattern in DANGEROUS:
        if re.search(pattern, command):
            return _deny(f"AERS blocked dangerous command pattern: {pattern}")
    if command:
        policy = load_json(cfg.repo / ".agents/policies/protected-paths.json")
        for raw_target in _bash_write_targets(command):
            try:
                rel = Path(raw_target).resolve(strict=False).relative_to(cfg.repo.resolve()).as_posix()
            except ValueError:
                continue  # outside the repo (e.g. /dev/null, temp files) — not ours to police
            if "protected" in classify_path(rel, policy):
                return _deny(f"Shell command writes to protected path: {rel}")
    feature_id, task_id, base = os.environ.get("AERS_FEATURE_ID"), os.environ.get("AERS_TASK_ID"), os.environ.get("AERS_BASE_SHA")
    if tool in {"Write","Edit","MultiEdit","NotebookEdit"}:
        raw_path = tool_input.get("file_path") or tool_input.get("path") or ""
        if not raw_path:
            return _deny("Write-like tool did not expose a path")
        path = Path(raw_path)
        try:
            rel = path.resolve(strict=False).relative_to(cfg.repo.resolve()).as_posix()
        except ValueError:
            return _deny("Write path escapes repository")
        policy = load_json(cfg.repo / ".agents/policies/protected-paths.json")
        if "protected" in classify_path(rel, policy):
            return _deny(f"Protected path: {rel}")
        if feature_id and task_id and base:
            try:
                bundle = load_bundle(cfg.repo, feature_id, task_id, ref=base)
                if not matches(rel, bundle.task["write_scope"]):
                    return _deny(f"Outside immutable task write scope: {rel}")
                if bundle.task["role"] == "implementer" and "test" in classify_path(rel, policy):
                    return _deny(f"Implementer may not edit tests: {rel}")
            except Exception as exc:
                return _deny(f"Could not load immutable task authority: {exc}")
        # No task identity means an interactive session (e.g. /kickoff drafting a
        # feature pack): protected paths stay denied above; other writes are the
        # human's responsibility. The scope gate, not this hook, is the boundary.
    print(json.dumps({"decision":"allow"}))
    return 0


def task_completed_gate() -> int:
    feature_id, task_id, base = os.environ.get("AERS_FEATURE_ID"), os.environ.get("AERS_TASK_ID"), os.environ.get("AERS_BASE_SHA")
    if not all([feature_id,task_id,base]):
        return _deny("TaskCompleted missing immutable AERS task identity")
    proc = subprocess.run([sys.executable,"scripts/aers.py","scope-check","--feature",feature_id,"--task",task_id,"--base",base], text=True)
    if proc.returncode != 0:
        return _deny("Scope gate failed; task completion blocked")
    print(json.dumps({"decision":"allow","reason":"Early scope gate passed; external author verification still required"}))
    return 0
