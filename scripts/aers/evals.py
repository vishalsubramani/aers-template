from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import audit_text_for_eval
from .scope import classify_path, matches
from .util import load_json


def _eval_scope(case: dict[str, Any], policy: dict[str, Any]) -> str:
    role = case["role"]
    allowed = case["write_scope"]
    for path in case["changed"]:
        kinds = classify_path(path, policy)
        if not matches(path, allowed):
            return "fail"
        if "protected" in kinds:
            return "fail"
        if role == "implementer" and "test" in kinds:
            return "fail"
        if role in {"explorer", "reviewer", "security", "sre"}:
            return "fail"
    return "pass"


def run_public(repo: Path) -> dict[str, Any]:
    policy = load_json(repo / ".agents/policies/protected-paths.json")
    results = []
    path = repo / "evals/public-cases.jsonl"
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        if case["type"] == "scope":
            actual = _eval_scope(case, policy)
        elif case["type"] == "audit_text":
            actual = audit_text_for_eval(case["text"])
        else:
            actual = "unknown"
        passed = actual == case["expected"]
        results.append({"id":case["id"],"expected":case["expected"],"actual":actual,"passed":passed})
    return {"passed":all(x["passed"] for x in results),"total":len(results),"passed_count":sum(x["passed"] for x in results),"results":results}
