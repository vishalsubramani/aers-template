"""Structured threat model — a machine-readable control matrix.

The human-readable threat table is *generated* from this structured source so the
two never drift. Each threat binds to preventive/detective/recovery controls, a
verification method, and the adversarial benchmark cases that exercise it, plus
an explicit residual-risk statement. `threat-model` validates the matrix (every
critical threat must map to at least one control and one executable benchmark
case) and can render Markdown.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aers.util import load_json

MODEL_PATH = "assurance/threats/threat-model.json"
BENCH_PATH = "assurance/benchmark/cases.jsonl"

REQUIRED_FIELDS = [
    "id", "protected_asset", "attacker_capability", "entry_vector", "trust_boundary",
    "preconditions", "preventive_controls", "detective_controls", "recovery_controls",
    "residual_risk", "verification_method", "benchmark_cases", "owner", "review_cadence", "severity",
]


def _benchmark_ids(repo: Path) -> set[str]:
    import json
    path = repo / BENCH_PATH
    if not path.exists():
        return set()
    return {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def validate(repo: Path, model: dict[str, Any] | None = None) -> dict[str, Any]:
    model = model or load_json(repo / MODEL_PATH)
    bench_ids = _benchmark_ids(repo)
    findings: list[dict[str, str]] = []
    seen: set[str] = set()
    for threat in model.get("threats", []):
        tid = threat.get("id", "<no-id>")
        for field in REQUIRED_FIELDS:
            if field not in threat:
                findings.append({"threat": tid, "code": "MISSING_FIELD", "detail": field})
        if tid in seen:
            findings.append({"threat": tid, "code": "DUPLICATE_ID", "detail": tid})
        seen.add(tid)
        has_control = bool(threat.get("preventive_controls") or threat.get("detective_controls"))
        if not has_control:
            findings.append({"threat": tid, "code": "NO_CONTROL", "detail": "no preventive or detective control"})
        # Every critical threat must have an executable benchmark case that exists.
        cases = threat.get("benchmark_cases", [])
        missing = [c for c in cases if c not in bench_ids]
        if missing:
            findings.append({"threat": tid, "code": "MISSING_BENCHMARK", "detail": str(missing)})
        if threat.get("severity") == "critical" and not cases:
            findings.append({"threat": tid, "code": "CRITICAL_WITHOUT_BENCHMARK", "detail": tid})
        if not threat.get("residual_risk"):
            findings.append({"threat": tid, "code": "NO_RESIDUAL_RISK", "detail": tid})
    return {
        "schema_version": 1,
        "total_threats": len(model.get("threats", [])),
        "passed": not findings,
        "findings": findings,
        "statement": "Every critical threat maps to at least one containment control, one executable benchmark "
                     "case, and an explicit residual-risk statement.",
    }


def render_markdown(repo: Path, model: dict[str, Any] | None = None) -> str:
    model = model or load_json(repo / MODEL_PATH)
    lines = [
        "# AERS Threat Model (generated)",
        "",
        "> Generated from `assurance/threats/threat-model.json` by `python3 scripts/assure.py threat-model --render`.",
        "> Do not edit by hand; edit the structured source and regenerate.",
        "",
        f"Protected assets, {model.get('total_threats', len(model.get('threats', [])))} threats.",
        "",
        "| ID | Severity | Protected asset | Entry vector | Preventive | Detective | Recovery | Benchmark | Residual risk |",
        "|----|----------|-----------------|--------------|------------|-----------|----------|-----------|----------------|",
    ]
    for t in model.get("threats", []):
        lines.append("| {id} | {sev} | {asset} | {vector} | {prev} | {det} | {rec} | {bench} | {res} |".format(
            id=t["id"], sev=t.get("severity", ""), asset=t["protected_asset"], vector=t["entry_vector"],
            prev="; ".join(t["preventive_controls"]) or "—", det="; ".join(t["detective_controls"]) or "—",
            rec="; ".join(t["recovery_controls"]) or "—", bench=", ".join(t.get("benchmark_cases", [])) or "—",
            res=t["residual_risk"]))
    lines.append("")
    return "\n".join(lines)
