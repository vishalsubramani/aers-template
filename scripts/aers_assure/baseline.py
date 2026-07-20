"""Baseline comparison across workflow modes.

This is a CAPABILITY comparison, not a live-model experiment. It is honest about
which parts are measured and which are not:

  - Containment is OBSERVED: the adversarial benchmark is actually executed once,
    and a mode "contains" a seeded attack only if (a) the mode enables the gate
    that attack targets AND (b) that gate was observed to contain it in the real
    benchmark run. A mode lacking the relevant gate does not run it, so the
    attack escapes. These false-pass numbers are therefore executed results, not
    assumptions.
  - Task success rate and false-reject rate are NOT measured here — they require
    live-model trajectories. They are reported as null with a note, never as
    1.0/0.0 by construction.
  - Cost/latency/retry/human-intervention columns are SIMULATED deterministic
    estimates, clearly labeled, so the comparison runs offline.

Replace the simulated columns with an empirical adapter to get live-model numbers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import benchmark as benchmark_mod

# Which gate kinds each mode actually enforces at runtime.
MODES: dict[str, set[str]] = {
    "unconstrained": set(),
    "agents_md_only": set(),
    "spec_driven_no_enforcement": {"contract"},
    "aers_lite": {"scope", "audit", "contract"},
    "aers_standard": {"scope", "audit", "contract", "differential", "reviewer"},
    "aers_high_assurance": {"scope", "audit", "contract", "differential", "reviewer",
                            "attestation", "isolation", "memory"},
}

# SIMULATED cost profile per mode (labeled). More gates cost more but let fewer
# defects through. Illustrative, not measured.
_SIM_COST = {
    "unconstrained":               {"tool_calls": 8,  "elapsed_s": 40,  "retries": 0, "human_intervention": 0.0},
    "agents_md_only":              {"tool_calls": 10, "elapsed_s": 55,  "retries": 0, "human_intervention": 0.05},
    "spec_driven_no_enforcement":  {"tool_calls": 14, "elapsed_s": 80,  "retries": 1, "human_intervention": 0.10},
    "aers_lite":                   {"tool_calls": 18, "elapsed_s": 110, "retries": 1, "human_intervention": 0.10},
    "aers_standard":               {"tool_calls": 26, "elapsed_s": 170, "retries": 2, "human_intervention": 0.15},
    "aers_high_assurance":         {"tool_calls": 34, "elapsed_s": 240, "retries": 2, "human_intervention": 0.20},
}


def run_baseline(repo: Path, bench_report: dict[str, Any] | None = None) -> dict[str, Any]:
    if bench_report is None:
        bench_report = benchmark_mod.run_benchmark(repo)
    # Observed containment per case (kind + whether the real gate contained it).
    observed = {r["id"]: {"kind": r["kind"], "contained": r["passed"]} for r in bench_report["results"]}
    attacks = list(observed.values())
    n = len(attacks)
    rows: list[dict[str, Any]] = []
    for mode, gates in MODES.items():
        contained = [a for a in attacks if a["kind"] in gates and a["contained"]]
        escaped = [a for a in attacks if not (a["kind"] in gates and a["contained"])]
        cost = _SIM_COST[mode]
        rows.append({
            "mode": mode,
            "measured": {
                "attacks": n,
                "contained_observed": len(contained),
                "false_pass_rate_observed": round(len(escaped) / n, 3) if n else 0.0,
            },
            "not_measured": {
                "task_success_rate": None,
                "false_reject_rate": None,
                "reviewer_disagreement": None,
                "note": "requires live-model trajectories; use an empirical adapter",
            },
            "simulated_cost": cost,
        })
    return {
        "schema_version": 1,
        "attacks_evaluated": n,
        "containment": "OBSERVED (benchmark executed once; a mode contains an attack only if it enables the "
                       "relevant gate AND that gate was observed to contain it)",
        "cost": "SIMULATED deterministic estimates (labeled); not empirical",
        "rows": rows,
    }


def render_human(report: dict[str, Any]) -> str:
    lines = [f"AERS baseline comparison — {report['attacks_evaluated']} seeded attacks",
             "containment: OBSERVED | cost: SIMULATED | task-success/false-reject: NOT MEASURED", "",
             f"{'mode':<28}{'false_pass(obs)':>16}{'contained':>11}{'sim_tool_calls':>16}"]
    for r in report["rows"]:
        m, c = r["measured"], r["simulated_cost"]
        lines.append(f"{r['mode']:<28}{m['false_pass_rate_observed']:>16}{m['contained_observed']:>11}{c['tool_calls']:>16}")
    return "\n".join(lines)
