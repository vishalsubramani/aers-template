"""Evidence-linked assurance case for AERS itself.

Each material trust claim maps to implementation locations, an enforcing control,
tests, adversarial benchmark cases, and a pinned evidence digest. `assurance`
reports each claim as SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / STALE /
BROKEN:

- BROKEN      — a referenced file/symbol/test/benchmark case does not exist.
- UNSUPPORTED — no implementation or no test/benchmark evidence at all.
- STALE       — referenced implementation or tests changed since the evidence
                digest was last refreshed (the mapping no longer reflects reality).
- SUPPORTED   — implementation + at least one test + fresh digest.

`--refresh` recomputes and rewrites the pinned digests after an intentional change.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aers.util import atomic_write_json, canonical_json, load_json, sha256_text

SUPPORTED, PARTIAL, UNSUPPORTED, STALE, BROKEN = (
    "SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "STALE", "BROKEN")

CASE_PATH = "assurance/assurance-case/assurance-case.json"
BENCH_PATH = "assurance/benchmark/cases.jsonl"


def _file_symbol(ref: str) -> tuple[str, str | None]:
    if "::" in ref:
        path, symbol = ref.split("::", 1)
        return path, symbol
    return ref, None


def _evidence_digest(repo: Path, refs: list[str]) -> str:
    """Digest over the content of every referenced implementation + test file,
    order-independent. Changing any of them changes this digest (→ STALE)."""
    materials: dict[str, str | None] = {}
    for ref in sorted(set(refs)):
        path, _sym = _file_symbol(ref)
        p = repo / path
        materials[path] = sha256_text(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else None
    return sha256_text(canonical_json(materials))


def _benchmark_ids(repo: Path) -> set[str]:
    path = repo / BENCH_PATH
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            ids.add(load_json_line(line))
    return ids


def load_json_line(line: str) -> str:
    import json
    return json.loads(line)["id"]


def _check_refs(repo: Path, refs: list[str]) -> list[str]:
    """Return a list of broken references (missing file or missing symbol)."""
    broken = []
    for ref in refs:
        path, symbol = _file_symbol(ref)
        p = repo / path
        if not p.exists():
            broken.append(f"missing:{ref}")
            continue
        if symbol and symbol not in p.read_text(encoding="utf-8", errors="replace"):
            broken.append(f"missing_symbol:{ref}")
    return broken


def evaluate_claim(repo: Path, claim: dict[str, Any], bench_ids: set[str]) -> dict[str, Any]:
    impl = claim.get("implementation", [])
    tests = claim.get("tests", [])
    benches = claim.get("benchmark_cases", [])
    broken = _check_refs(repo, impl) + _check_refs(repo, tests)
    broken += [f"missing_benchmark:{b}" for b in benches if b not in bench_ids]

    if broken:
        status = BROKEN
    elif not impl:
        status = UNSUPPORTED
    elif not tests and not benches:
        status = PARTIAL
    else:
        current = _evidence_digest(repo, impl + tests)
        status = SUPPORTED if current == claim.get("evidence_digest") else STALE
    return {
        "claim_id": claim["id"],
        "text": claim["text"],
        "enforcing_control": claim.get("enforcing_control"),
        "status": status,
        "broken_refs": broken,
        "implementation": impl,
        "tests": tests,
        "benchmark_cases": benches,
        "residual_limitations": claim.get("residual_limitations", ""),
    }


def run_assurance(repo: Path, case_path: Path | None = None) -> dict[str, Any]:
    path = case_path or (repo / CASE_PATH)
    case = load_json(path)
    bench_ids = _benchmark_ids(repo)
    results = [evaluate_claim(repo, claim, bench_ids) for claim in case["claims"]]
    broken = [r for r in results if r["status"] == BROKEN]
    unsupported = [r for r in results if r["status"] == UNSUPPORTED]
    stale = [r for r in results if r["status"] == STALE]
    ok = not broken and not unsupported
    return {
        "schema_version": 1,
        "case_version": case.get("version"),
        "total_claims": len(results),
        "supported": sum(1 for r in results if r["status"] == SUPPORTED),
        "partial": sum(1 for r in results if r["status"] == PARTIAL),
        "stale": len(stale),
        "unsupported": len(unsupported),
        "broken": len(broken),
        "passed": ok,
        "results": results,
        "statement": "Broken or unsupported claims fail the assurance case; stale claims warn that a mapping "
                     "needs review after an implementation or test change.",
    }


def refresh(repo: Path) -> Path:
    """Recompute and rewrite every claim's evidence_digest from current file
    content. Run this deliberately after an intentional implementation change."""
    path = repo / CASE_PATH
    case = load_json(path)
    for claim in case["claims"]:
        refs = claim.get("implementation", []) + claim.get("tests", [])
        broken = _check_refs(repo, refs)
        claim["evidence_digest"] = None if broken else _evidence_digest(repo, refs)
    atomic_write_json(path, case)
    return path


def render_human(report: dict[str, Any]) -> str:
    lines = [f"AERS assurance case (v{report['case_version']}) — {report['total_claims']} claims",
             f"supported {report['supported']}  partial {report['partial']}  stale {report['stale']}  "
             f"unsupported {report['unsupported']}  broken {report['broken']}", ""]
    for r in report["results"]:
        lines.append(f"[{r['status']:<18}] {r['claim_id']}: {r['text']}")
        if r["broken_refs"]:
            lines.append(f"    broken: {r['broken_refs']}")
    return "\n".join(lines)
