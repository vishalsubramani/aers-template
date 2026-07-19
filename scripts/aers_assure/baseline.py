"""Baseline comparison across workflow modes.

Compares an unconstrained agent, AGENTS.md-only guidance, spec-driven execution
without enforcement, and AERS Lite/Standard/High-Assurance on the same seeded
adversarial scenarios. The *containment* metrics (false-pass, scope/protected
violation caught) are DERIVED from which gates each mode actually enables — they
are a real consequence of configuration, not hardcoded answers. The *cost*
metrics (tool calls, elapsed, retries, reviewer disagreement, human
intervention) are SIMULATED deterministic estimates, clearly labeled, so the
comparison runs offline without a live model. Swap in an empirical adapter to
replace the simulated columns with real model-run numbers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import benchmark as benchmark_mod

# Which gate kinds each mode actually enforces at runtime.
MODES: dict[str, set[str]] = {
    "unconstrained": set(),
    "agents_md_only": set(),                         # guidance in prose; no runtime gate
    "spec_driven_no_enforcement": {"contract"},      # typed specs, but nothing checks the diff
    "aers_lite": {"scope", "audit", "contract"},
    "aers_standard": {"scope", "audit", "contract", "differential", "reviewer"},
    "aers_high_assurance": {"scope", "audit", "contract", "differential", "reviewer",
                            "attestation", "isolation", "memory"},
}

# Simulated cost profile per mode (labeled SIMULATED). More gates cost more per
# task but let fewer defects through. Values are illustrative, not measured.
_SIM_COST = {
    "unconstrained":               {"tool_calls": 8,  "elapsed_s": 40,  "retries": 0, "reviewer_disagreement": 0.0, "human_intervention": 0.0},
    "agents_md_only":              {"tool_calls": 10, "elapsed_s": 55,  "retries": 0, "reviewer_disagreement": 0.0, "human_intervention": 0.05},
    "spec_driven_no_enforcement":  {"tool_calls": 14, "elapsed_s": 80,  "retries": 1, "reviewer_disagreement": 0.0, "human_intervention": 0.10},
    "aers_lite":                   {"tool_calls": 18, "elapsed_s": 110, "retries": 1, "reviewer_disagreement": 0.0, "human_intervention": 0.10},
    "aers_standard":               {"tool_calls": 26, "elapsed_s": 170, "retries": 2, "reviewer_disagreement": 0.12, "human_intervention": 0.15},
    "aers_high_assurance":         {"tool_calls": 34, "elapsed_s": 240, "retries": 2, "reviewer_disagreement": 0.15, "human_intervention": 0.20},
}


def run_baseline(repo: Path) -> dict[str, Any]:
    cases = benchmark_mod.load_cases(repo)
    attacks = [c for c in cases if c.get("expected_verdict") in {"blocked", "detected"}]
    scope_attacks = [c for c in attacks if c["kind"] == "scope"]
    protected = [c for c in attacks if c.get("expected_reason") == "PROTECTED_PATH"]
    rows: list[dict[str, Any]] = []
    for mode, gates in MODES.items():
        caught = [c for c in attacks if c["kind"] in gates]
        missed = [c for c in attacks if c["kind"] not in gates]
        scope_caught = [c for c in scope_attacks if c["kind"] in gates]
        prot_caught = [c for c in protected if c["kind"] in gates]
        n = len(attacks)
        cost = _SIM_COST[mode]
        rows.append({
            "mode": mode,
            "derived": {
                "attacks": n,
                "contained": len(caught),
                "false_pass_rate": round(len(missed) / n, 3) if n else 0.0,
                "false_reject_rate": 0.0,
                "scope_violation_caught": f"{len(scope_caught)}/{len(scope_attacks)}",
                "protected_path_violation_caught": f"{len(prot_caught)}/{len(protected)}",
                "unsupported_completion_blocked": ("differential" in gates or "audit" in gates),
                "task_success_rate": 1.0,
            },
            "simulated_cost": cost,
        })
    return {
        "schema_version": 1,
        "attacks_evaluated": len(attacks),
        "note": "Containment metrics are DERIVED from enabled gates (real). Cost metrics are SIMULATED "
                "deterministic estimates; replace with an empirical adapter for live-model numbers.",
        "rows": rows,
    }


def render_human(report: dict[str, Any]) -> str:
    lines = [f"AERS baseline comparison — {report['attacks_evaluated']} seeded attacks",
             "(containment DERIVED from gates; cost SIMULATED)", "",
             f"{'mode':<28}{'false_pass':>11}{'contained':>11}{'sim_tool_calls':>16}{'human_interv':>14}"]
    for r in report["rows"]:
        d, c = r["derived"], r["simulated_cost"]
        lines.append(f"{r['mode']:<28}{d['false_pass_rate']:>11}{d['contained']:>11}"
                     f"{c['tool_calls']:>16}{c['human_intervention']:>14}")
    return "\n".join(lines)
