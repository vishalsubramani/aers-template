from __future__ import annotations

import json
from pathlib import Path

from .git import head_sha
from .util import atomic_write_json, atomic_write_text


def init_feature(repo: Path, feature_id: str, title: str, mode: str, risk: str) -> Path:
    if mode not in {"S0","S1","S2"} or risk not in {"R0","R1","R2","R3"}:
        raise ValueError("Invalid spec mode or risk tier")
    if not feature_id.startswith("FEAT-"):
        raise ValueError("Feature IDs must begin with FEAT-")
    directory = repo / ".specify/specs" / feature_id
    if directory.exists() and any(directory.iterdir()):
        raise ValueError(f"Feature directory already exists and is non-empty: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    try:
        base = head_sha(repo)
    except Exception:
        base = "REPLACE_WITH_APPROVED_BASE_SHA"
    feature = {"schema_version":1,"feature_id":feature_id,"title":title,"spec_mode":mode,"risk_tier":risk,
               "status":"draft","base_ref":base,"owner":"REPLACE_WITH_OWNER","non_goals":[],
               "acceptance_criteria":[{"id":"AC-001","statement":"Replace with objective observable behavior","evidence":["public:replace","private:replace"]}],
               "contracts":[],"quality":{"security":[],"reliability":[],"observability":[],"performance":[]},
               "rollout":{"strategy":"Replace rollout strategy","rollback":"Replace rollback procedure","health_gates":[]}}
    tasks = {"schema_version":1,"feature_id":feature_id,"tasks":[{"id":"T-001","title":"Implement one bounded behavior","role":"implementer","depends_on":[],
              "write_scope":["src/example/**"],"acceptance":["AC-001"],
              "commands":[{"name":"control-plane lint","argv":["python3","scripts/aers.py","lint"],"timeout_seconds":120,"network":"deny"}],
              "budget":{"max_attempts":3,"max_files":10,"max_lines":600,"max_seconds":1800},"notes":""}]}
    atomic_write_json(directory / "feature.contract.json", feature)
    atomic_write_json(directory / "tasks.json", tasks)
    templates = {
      "spec.md":".specify/templates/spec-template.md","plan.md":".specify/templates/plan-template.md",
      "tasks.md":".specify/templates/tasks-template.md","acceptance.md":".specify/templates/acceptance-template.md",
      "validation.md":".specify/templates/validation-template.md","decision-log.md":".specify/templates/decision-log-template.md"}
    for target, source in templates.items():
        text = (repo / source).read_text(encoding="utf-8").replace("FEAT-NNN", feature_id).replace("Replace title", title)
        atomic_write_text(directory / target, text)
    if mode == "S2":
        atomic_write_text(directory / "threat-model.md", "# Feature Threat Model\n\n## Assets\n## Trust boundaries\n## Abuse cases\n## Controls\n## Residual risk\n")
        atomic_write_text(directory / "migration.md", "# Migration Plan\n\n## Compatibility\n## Backfill\n## Dry run\n## Rollback\n## Verification\n")
        atomic_write_text(directory / "runbook.md", "# Operational Runbook\n\n## Detection\n## Diagnosis\n## Mitigation\n## Rollback\n## Recovery validation\n")
    return directory
