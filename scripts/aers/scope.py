"""Exact diff-vs-authority scope gate: write scopes, roles, budgets, protected paths, symlinks."""
from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .contracts import ContractBundle, load_bundle
from .git import changed_paths, diff_numstat, rev_parse
from .util import load_json


@dataclass
class ScopeFinding:
    severity: str
    code: str
    path: str
    message: str


@dataclass
class ScopeReport:
    passed: bool
    base_sha: str
    feature_id: str
    task_id: str
    role: str
    changed_paths: list[str]
    changed_files: int
    changed_lines: int
    allowed_scope: list[str]
    findings: list[dict[str, str]]
    contract_hashes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace(os.sep, "/").lstrip("./")
    return any(fnmatch.fnmatchcase(normalized, pattern.lstrip("./")) for pattern in patterns)


def classify_path(path: str, policy: dict[str, Any]) -> set[str]:
    kinds: set[str] = set()
    for key, label in [("always_protected", "protected"), ("test_patterns", "test"), ("generated_patterns", "generated"), ("sensitive_patterns", "sensitive")]:
        if matches(path, policy.get(key, [])):
            kinds.add(label)
    return kinds


def _symlink_escape(repo: Path, relpath: str) -> str | None:
    current = repo.resolve()
    for part in Path(relpath).parts:
        current = current / part
        try:
            if current.is_symlink():
                target = current.resolve(strict=False)
                try:
                    target.relative_to(repo.resolve())
                except ValueError:
                    return f"symlink escapes repository: {current} -> {target}"
                return f"changed path traverses symlink: {current} -> {target}"
        except OSError:
            return f"could not inspect path for symlink safety: {current}"
    return None


def evaluate_scope(repo: Path, feature_id: str, task_id: str, base_ref: str, contract_ref: str | None = None) -> ScopeReport:
    base_sha = rev_parse(repo, base_ref)
    bundle: ContractBundle = load_bundle(repo, feature_id, task_id, ref=contract_ref or base_sha)
    task = bundle.task
    role = task["role"]
    changed = changed_paths(repo, base_sha)
    total_lines, _ = diff_numstat(repo, base_sha)
    policy = load_json(repo / ".agents/policies/protected-paths.json")
    findings: list[ScopeFinding] = []

    if len(changed) > task["budget"]["max_files"]:
        findings.append(ScopeFinding("high", "DIFF_FILE_BUDGET", "", f"{len(changed)} files exceeds budget {task['budget']['max_files']}"))
    if total_lines > task["budget"]["max_lines"]:
        findings.append(ScopeFinding("high", "DIFF_LINE_BUDGET", "", f"{total_lines} lines exceeds budget {task['budget']['max_lines']}"))

    read_only_roles = {"explorer", "reviewer", "security", "sre"}
    for path in changed:
        kinds = classify_path(path, policy)
        if role in read_only_roles:
            findings.append(ScopeFinding("critical", "READ_ONLY_ROLE_WROTE", path, f"Role {role} is read-only"))
        if not matches(path, task["write_scope"]):
            findings.append(ScopeFinding("high", "OUTSIDE_WRITE_SCOPE", path, "Path is outside immutable task write scope"))
        if "protected" in kinds:
            findings.append(ScopeFinding("critical", "PROTECTED_PATH", path, "Control-plane or verifier path is protected"))
        if role == "implementer" and "test" in kinds:
            findings.append(ScopeFinding("critical", "IMPLEMENTER_EDITED_TEST", path, "Implementer cannot write tests"))
        if role == "test_author" and "test" not in kinds and not matches(path, ["testdata/**", "fixtures/**", "**/fixtures/**"]):
            findings.append(ScopeFinding("high", "TEST_AUTHOR_EDITED_NONTEST", path, "Test author may only write tests/fixtures"))
        if role == "architect" and not matches(path, [f".specify/specs/{feature_id}/**", "docs/adr/**", "docs/architecture/**"]):
            findings.append(ScopeFinding("high", "ARCHITECT_EDITED_IMPLEMENTATION", path, "Architect role is limited to design artifacts"))
        if role == "documentation" and not matches(path, ["docs/**", "README.md", "**/*.md"]):
            findings.append(ScopeFinding("high", "DOC_ROLE_EDITED_CODE", path, "Documentation role is limited to documentation"))
        if "generated" in kinds:
            findings.append(ScopeFinding("medium", "GENERATED_PATH", path, "Generated/vendor surface changed; require canonical generator evidence"))
        escape = _symlink_escape(repo, path)
        if escape:
            findings.append(ScopeFinding("critical", "SYMLINK_PATH", path, escape))

    passed = not any(f.severity in {"high", "critical"} for f in findings)
    return ScopeReport(
        passed=passed, base_sha=base_sha, feature_id=feature_id, task_id=task_id, role=role,
        changed_paths=changed, changed_files=len(changed), changed_lines=total_lines,
        allowed_scope=task["write_scope"], findings=[asdict(f) for f in findings],
        contract_hashes={"feature": bundle.feature_hash, "tasks": bundle.tasks_hash},
    )
