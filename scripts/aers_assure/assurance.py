"""Evidence-linked assurance case for AERS itself.

Each material trust claim maps to implementation, tests, an enforcing control,
and adversarial benchmark cases. `assurance` now goes beyond "the references
exist": it

  - runs the referenced benchmark cases and requires them to be CONTAINED,
  - folds the benchmark case DEFINITIONS (not just their IDs) into the pinned
    evidence digest, so editing a benchmark's content makes the claim STALE,
  - requires the enforcing control to exist in the control catalog,
  - binds the report to the exact candidate SHA,
  - FAILS the case on any BROKEN, UNSUPPORTED, STALE, or FAILED_EVIDENCE claim.

Statuses: SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / STALE / BROKEN /
FAILED_EVIDENCE. `--refresh` recomputes the pinned digests after an intentional
change.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aers.git import head_sha
from aers.util import atomic_write_json, canonical_json, load_json, sha256_text
from . import benchmark as benchmark_mod
from .profiles import load_controls

SUPPORTED, PARTIAL, UNSUPPORTED, STALE, BROKEN, FAILED = (
    "SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "STALE", "BROKEN", "FAILED_EVIDENCE")

CASE_PATH = "assurance/assurance-case/assurance-case.json"


def _file_symbol(ref: str) -> tuple[str, str | None]:
    if "::" in ref:
        path, symbol = ref.split("::", 1)
        return path, symbol
    return ref, None


def _benchmark_defs(repo: Path) -> dict[str, str]:
    """Map benchmark id -> canonical digest of its full definition."""
    defs: dict[str, str] = {}
    for case in benchmark_mod.load_cases(repo):
        defs[case["id"]] = sha256_text(canonical_json(case))
    return defs


def _evidence_digest(repo: Path, refs: list[str], bench_ids: list[str], bench_defs: dict[str, str]) -> str:
    """Digest over referenced implementation + test file content AND the
    definitions of the referenced benchmark cases. Changing any of them changes
    this digest (-> STALE)."""
    materials: dict[str, str | None] = {}
    for ref in sorted(set(refs)):
        path, _sym = _file_symbol(ref)
        p = repo / path
        materials[path] = sha256_text(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else None
    for bid in sorted(set(bench_ids)):
        materials[f"bench::{bid}"] = bench_defs.get(bid)
    return sha256_text(canonical_json(materials))


def _check_refs(repo: Path, refs: list[str]) -> list[str]:
    broken = []
    for ref in refs:
        path, symbol = _file_symbol(ref)
        p = repo / path
        if not p.exists():
            broken.append(f"missing:{ref}")
        elif symbol and symbol not in p.read_text(encoding="utf-8", errors="replace"):
            broken.append(f"missing_symbol:{ref}")
    return broken


def _makefile_targets(repo: Path) -> set[str]:
    text = (repo / "Makefile").read_text(encoding="utf-8", errors="replace") if (repo / "Makefile").exists() else ""
    return {line.split(":", 1)[0].strip() for line in text.splitlines() if line and not line[0].isspace() and ":" in line}


def evaluate_claim(repo: Path, claim: dict[str, Any], bench_defs: dict[str, str],
                   bench_results: dict[str, bool], controls: dict[str, Any], make_targets: set[str]) -> dict[str, Any]:
    impl = claim.get("implementation", [])
    tests = claim.get("tests", [])
    benches = claim.get("benchmark_cases", [])
    broken = _check_refs(repo, impl) + _check_refs(repo, tests)
    broken += [f"missing_benchmark:{b}" for b in benches if b not in bench_defs]
    if claim.get("enforcing_control") and claim["enforcing_control"] not in controls:
        broken.append(f"unknown_control:{claim['enforcing_control']}")

    status = None
    if broken:
        status = BROKEN
    elif not impl:
        status = UNSUPPORTED
    else:
        # Referenced benchmark cases must actually be contained.
        failed_bench = [b for b in benches if not bench_results.get(b, False)]
        if failed_bench:
            status = FAILED
            broken.extend(f"benchmark_not_contained:{b}" for b in failed_bench)
        elif not tests and not benches:
            status = PARTIAL
        else:
            current = _evidence_digest(repo, impl + tests, benches, bench_defs)
            status = SUPPORTED if current == claim.get("evidence_digest") else STALE

    # ci_evidence sanity: any make target it names should be a real target.
    named = [w for w in claim.get("ci_evidence", "").replace("+", " ").split() if w not in {"make", ""}]
    known_targets = {"verify", "test", "benchmark", "assurance", "assess", "threat-model", "evaluator-health"}
    ci_missing = [w for w in named if w in known_targets and w not in make_targets]
    return {
        "claim_id": claim["id"],
        "text": claim["text"],
        "enforcing_control": claim.get("enforcing_control"),
        "status": status,
        "broken_refs": broken,
        "ci_evidence_targets_missing": ci_missing,
        "implementation": impl,
        "tests": tests,
        "benchmark_cases": benches,
        "residual_limitations": claim.get("residual_limitations", ""),
    }


def run_assurance(repo: Path, case_path: Path | None = None,
                  bench_results: dict[str, bool] | None = None) -> dict[str, Any]:
    path = case_path or (repo / CASE_PATH)
    case = load_json(path)
    bench_defs = _benchmark_defs(repo)
    if bench_results is None:
        report = benchmark_mod.run_benchmark(repo)
        bench_results = {r["id"]: r["passed"] for r in report["results"]}
    controls = load_controls(repo)
    make_targets = _makefile_targets(repo)
    results = [evaluate_claim(repo, c, bench_defs, bench_results, controls, make_targets) for c in case["claims"]]

    def count(*statuses):
        return sum(1 for r in results if r["status"] in statuses)

    broken, unsupported, stale, failed = count(BROKEN), count(UNSUPPORTED), count(STALE), count(FAILED)
    ok = not (broken or unsupported or stale or failed)
    try:
        candidate = head_sha(repo)
    except Exception:
        candidate = None
    return {
        "schema_version": 1,
        "candidate_sha": candidate,
        "case_version": case.get("version"),
        "total_claims": len(results),
        "supported": count(SUPPORTED),
        "partial": count(PARTIAL),
        "stale": stale,
        "unsupported": unsupported,
        "failed_evidence": failed,
        "broken": broken,
        "passed": ok,
        "results": results,
        "statement": "A claim is SUPPORTED only when its implementation and tests exist, its referenced benchmark "
                     "cases are actually contained, and its pinned digest (over code, tests, AND benchmark "
                     "definitions) is fresh. BROKEN, UNSUPPORTED, STALE, or FAILED_EVIDENCE claims fail the case.",
    }


def refresh(repo: Path) -> Path:
    path = repo / CASE_PATH
    case = load_json(path)
    bench_defs = _benchmark_defs(repo)
    for claim in case["claims"]:
        refs = claim.get("implementation", []) + claim.get("tests", [])
        benches = claim.get("benchmark_cases", [])
        broken = _check_refs(repo, refs) or [b for b in benches if b not in bench_defs]
        claim["evidence_digest"] = None if broken else _evidence_digest(repo, refs, benches, bench_defs)
    atomic_write_json(path, case)
    return path


def render_human(report: dict[str, Any]) -> str:
    lines = [f"AERS assurance case (v{report['case_version']}) — {report['total_claims']} claims @ "
             f"{(report.get('candidate_sha') or '?')[:12]}",
             f"supported {report['supported']}  partial {report['partial']}  stale {report['stale']}  "
             f"failed-evidence {report['failed_evidence']}  unsupported {report['unsupported']}  broken {report['broken']}", ""]
    for r in report["results"]:
        lines.append(f"[{r['status']:<18}] {r['claim_id']}: {r['text']}")
        if r["broken_refs"]:
            lines.append(f"    issues: {r['broken_refs']}")
    return "\n".join(lines)
