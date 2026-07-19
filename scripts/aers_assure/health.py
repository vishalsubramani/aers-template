"""Evaluator and verifier health.

The systems that do the judging must themselves be tested. This suite feeds the
deterministic audit evaluator a set of seeded cases — defects it MUST reject and
clean canaries it MUST accept — and measures seeded-defect detection, false
acceptance, false rejection, and reproducibility. Results are tied to the exact
evaluator configuration digest so a reviewer/evaluator change that regresses
detection is caught and can block promotion of that evaluator.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aers.audit import audit_text_for_eval
from aers.util import canonical_json, load_json, sha256_text

CASES_PATH = "assurance/health/health-cases.jsonl"


def _evaluator_config_digest(repo: Path) -> str:
    """Digest over the audit evaluator's implementation. Any change to the
    tamper/secret detection logic changes this digest, tying health results to
    the exact evaluator configuration."""
    audit = (repo / "scripts/aers/audit.py").read_text(encoding="utf-8", errors="replace")
    util = (repo / "scripts/aers/util.py").read_text(encoding="utf-8", errors="replace")
    return sha256_text(canonical_json({"audit": sha256_text(audit), "util": sha256_text(util)}))


def load_cases(repo: Path) -> list[dict[str, Any]]:
    path = repo / CASES_PATH
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_health(repo: Path, thresholds: dict[str, float] | None = None, trials: int = 3) -> dict[str, Any]:
    thresholds = thresholds or {"min_detection_rate": 1.0, "max_false_acceptance": 0.0, "max_false_rejection": 0.0}
    cases = load_cases(repo)
    results: list[dict[str, Any]] = []
    # Reproducibility: run each case `trials` times; a stable evaluator returns
    # the same verdict every time (the deterministic audit is expected to).
    for case in cases:
        verdicts = {audit_text_for_eval(case["text"]) for _ in range(trials)}
        actual = next(iter(verdicts)) if len(verdicts) == 1 else "NONDETERMINISTIC"
        detected = actual in {"fail", "needs_review"}
        expected_defect = case["class"] == "defect"
        results.append({
            "id": case["id"], "class": case["class"], "expected": case["expected"],
            "actual": actual, "reproducible": len(verdicts) == 1,
            "correct": actual == case["expected"],
            "seeded_defect_detected": expected_defect and detected,
            "false_acceptance": expected_defect and not detected,
            "false_rejection": (case["class"] == "canary") and detected,
        })
    defects = [r for r in results if r["class"] == "defect"]
    canaries = [r for r in results if r["class"] == "canary"]
    detection_rate = (sum(r["seeded_defect_detected"] for r in defects) / len(defects)) if defects else 1.0
    false_acceptance = (sum(r["false_acceptance"] for r in defects) / len(defects)) if defects else 0.0
    false_rejection = (sum(r["false_rejection"] for r in canaries) / len(canaries)) if canaries else 0.0
    nondeterministic = sum(0 if r["reproducible"] else 1 for r in results)

    regressions = []
    if detection_rate < thresholds["min_detection_rate"]:
        regressions.append(f"detection_rate {detection_rate:.2f} < {thresholds['min_detection_rate']}")
    if false_acceptance > thresholds["max_false_acceptance"]:
        regressions.append(f"false_acceptance {false_acceptance:.2f} > {thresholds['max_false_acceptance']}")
    if false_rejection > thresholds["max_false_rejection"]:
        regressions.append(f"false_rejection {false_rejection:.2f} > {thresholds['max_false_rejection']}")
    if nondeterministic:
        regressions.append(f"{nondeterministic} nondeterministic verdict(s)")

    return {
        "schema_version": 1,
        "evaluator_config_digest": _evaluator_config_digest(repo),
        "trials_per_case": trials,
        "total_cases": len(results),
        "seeded_defect_detection_rate": round(detection_rate, 4),
        "false_acceptance_rate": round(false_acceptance, 4),
        "false_rejection_rate": round(false_rejection, 4),
        "nondeterministic_verdicts": nondeterministic,
        "passed": not regressions,
        "regressions": regressions,
        "results": results,
        "statement": "Health results bind to evaluator_config_digest; a change that regresses detection beyond "
                     "thresholds must block promotion of the evaluator.",
    }


def render_human(report: dict[str, Any]) -> str:
    lines = [
        f"AERS evaluator health — evaluator {report['evaluator_config_digest'][:12]}",
        f"detection {report['seeded_defect_detection_rate']:.2f}  "
        f"false-accept {report['false_acceptance_rate']:.2f}  "
        f"false-reject {report['false_rejection_rate']:.2f}  "
        f"nondeterministic {report['nondeterministic_verdicts']}",
        f"result: {'PASS' if report['passed'] else 'REGRESSED: ' + '; '.join(report['regressions'])}",
    ]
    return "\n".join(lines)
