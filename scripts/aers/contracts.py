"""Load and validate immutable feature/task contracts against their JSON schemas at a fixed git ref."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .git import read_file_at_ref
from .util import hash_object, load_json

VALID_MODES = {"S0", "S1", "S2"}
VALID_RISKS = {"R0", "R1", "R2", "R3"}
VALID_ROLES = {"explorer", "architect", "implementer", "test_author", "reviewer", "security", "sre", "documentation"}


@dataclass(frozen=True)
class ContractBundle:
    feature: dict[str, Any]
    tasks_doc: dict[str, Any]
    task: dict[str, Any]
    feature_hash: str
    tasks_hash: str


def feature_paths(feature_id: str) -> tuple[str, str]:
    root = f".specify/specs/{feature_id}"
    return f"{root}/feature.contract.json", f"{root}/tasks.json"


def _parse_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid immutable JSON contract {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Contract must be a JSON object: {label}")
    return value


def load_bundle(repo: Path, feature_id: str, task_id: str, ref: str | None = None) -> ContractBundle:
    feature_path, tasks_path = feature_paths(feature_id)
    if ref:
        feature = _parse_json_bytes(read_file_at_ref(repo, ref, feature_path), f"{ref}:{feature_path}")
        tasks_doc = _parse_json_bytes(read_file_at_ref(repo, ref, tasks_path), f"{ref}:{tasks_path}")
    else:
        feature = load_json(repo / feature_path)
        tasks_doc = load_json(repo / tasks_path)
    validate_feature(feature)
    validate_tasks(tasks_doc, feature)
    match = [t for t in tasks_doc["tasks"] if t["id"] == task_id]
    if len(match) != 1:
        raise ValueError(f"Task {task_id} not found exactly once in feature {feature_id}")
    return ContractBundle(feature, tasks_doc, match[0], hash_object(feature), hash_object(tasks_doc))


def validate_feature(value: dict[str, Any]) -> None:
    required = ["schema_version", "feature_id", "title", "spec_mode", "risk_tier", "status", "base_ref", "acceptance_criteria", "contracts", "quality", "rollout"]
    missing = [key for key in required if key not in value]
    if missing:
        raise ValueError(f"Feature contract missing fields: {', '.join(missing)}")
    if value["schema_version"] != 1:
        raise ValueError("Feature contract schema_version must be 1")
    if value["spec_mode"] not in VALID_MODES or value["risk_tier"] not in VALID_RISKS:
        raise ValueError("Invalid spec_mode or risk_tier")
    criteria = value["acceptance_criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("Feature contract needs at least one acceptance criterion")
    ids = [c.get("id") for c in criteria if isinstance(c, dict)]
    if len(ids) != len(criteria) or len(set(ids)) != len(ids):
        raise ValueError("Acceptance criteria need unique IDs")
    for criterion in criteria:
        if not criterion.get("statement") or not criterion.get("evidence"):
            raise ValueError(f"Acceptance criterion is incomplete: {criterion}")
    rollout = value.get("rollout")
    if not isinstance(rollout, dict) or not rollout.get("strategy") or not rollout.get("rollback"):
        raise ValueError("Rollout strategy and rollback are required")


def validate_tasks(value: dict[str, Any], feature: dict[str, Any]) -> None:
    if value.get("schema_version") != 1 or value.get("feature_id") != feature.get("feature_id"):
        raise ValueError("Task graph schema/version or feature ID mismatch")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Task graph needs at least one task")
    ids = [t.get("id") for t in tasks if isinstance(t, dict)]
    if len(ids) != len(tasks) or len(set(ids)) != len(ids):
        raise ValueError("Tasks need unique IDs")
    accepted = {c["id"] for c in feature["acceptance_criteria"]}
    graph: dict[str, list[str]] = {}
    for task in tasks:
        for key in ["id", "title", "role", "depends_on", "write_scope", "acceptance", "commands", "budget"]:
            if key not in task:
                raise ValueError(f"Task {task.get('id')} missing {key}")
        if task["role"] not in VALID_ROLES:
            raise ValueError(f"Task {task['id']} has invalid role {task['role']}")
        if task["role"] in {"implementer", "test_author", "architect", "documentation"} and not task["write_scope"]:
            raise ValueError(f"Writable task {task['id']} requires write_scope")
        unknown_acceptance = set(task["acceptance"]) - accepted
        if unknown_acceptance:
            raise ValueError(f"Task {task['id']} references unknown acceptance: {sorted(unknown_acceptance)}")
        graph[task["id"]] = list(task["depends_on"])
        budget = task["budget"]
        for key in ["max_attempts", "max_files", "max_lines", "max_seconds"]:
            if not isinstance(budget.get(key), int) or budget[key] < 0:
                raise ValueError(f"Task {task['id']} has invalid budget {key}")
        diff_spec = task.get("differential")
        if diff_spec is not None:
            template = diff_spec.get("argv_template") if isinstance(diff_spec, dict) else None
            if (not isinstance(template, list) or not template
                    or not all(isinstance(x, str) and x for x in template)
                    or not any("{file}" in x for x in template)):
                raise ValueError(f"Task {task['id']} differential.argv_template must be a string array containing {{file}}")
            timeout = diff_spec.get("timeout_seconds", 120)
            if not isinstance(timeout, int) or timeout < 1:
                raise ValueError(f"Task {task['id']} differential.timeout_seconds must be a positive integer")
        for command in task["commands"]:
            if not isinstance(command.get("argv"), list) or not command["argv"] or not all(isinstance(x, str) for x in command["argv"]):
                raise ValueError(f"Task {task['id']} command argv must be a non-empty string array")
            if command.get("network", "deny") not in {"deny", "allowlisted"}:
                raise ValueError(f"Task {task['id']} command has invalid network mode")
    task_ids = set(ids)
    for task_id, deps in graph.items():
        unknown = set(deps) - task_ids
        if unknown:
            raise ValueError(f"Task {task_id} has unknown dependencies: {sorted(unknown)}")
    _assert_acyclic(graph)


def _assert_acyclic(graph: dict[str, list[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"Task dependency cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dep in graph[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)
