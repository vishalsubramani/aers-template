"""Machine-readable evidence manifest and release-readiness aggregation.

`evidence-manifest` generates AUTHOR-side evidence from a CLEAN EXPORT of the
exact candidate commit (via `git archive HEAD`), so the results reflect the
committed candidate and nothing from a dirty working tree. It:

  - records the exact candidate SHA and requires a clean worktree for a green
    result (a dirty tree means uncommitted changes the evidence would ignore),
  - runs assess / benchmark / assurance / threat-model / evaluator-health against
    the export,
  - treats a required PARTIAL / UNVERIFIABLE / STALE result as NOT green.

It never issues VERIFIED. It is a POST-COMMIT artifact and must not be committed
back into the candidate it describes (that would change the candidate SHA); the
Makefile target writes it under the gitignored evidence dir.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from aers.git import export_commit, head_sha, is_clean
from aers.util import hash_object, utc_now
from . import assess as assess_mod
from . import assurance as assurance_mod
from . import benchmark as benchmark_mod
from . import health as health_mod
from . import threats as threats_mod


def build_manifest(repo: Path, profile: str = "standard") -> dict[str, Any]:
    candidate = head_sha(repo)
    clean = is_clean(repo)
    with tempfile.TemporaryDirectory(prefix="aers-evidence-") as td:
        export_root = Path(td) / "candidate"
        export_commit(repo, candidate, export_root)  # archives the COMMIT, not the worktree

        assessment = assess_mod.assess(export_root, profile)
        bench = benchmark_mod.run_benchmark(export_root)
        bench_results = {r["id"]: r["passed"] for r in bench["results"]}
        assurance = assurance_mod.run_assurance(export_root, bench_results=bench_results)
        threat = threats_mod.validate(export_root)
        hlth = health_mod.run_health(export_root)

    gates = {
        "assessment": {"profile": profile, "overall": assessment["overall"],
                       "required_pass": assessment["summary"]["required_pass"],
                       "required_total": assessment["summary"]["required_total"],
                       "required_partial": assessment["summary"]["required_partial"],
                       "green": assessment["overall"] == "PASS", "digest": hash_object(assessment)},
        "adversarial_benchmark": {"passed": bench["all_passed"], "cases": bench["total"],
                                  "contained": bench["passed"], "green": bench["all_passed"],
                                  "digest": hash_object(bench)},
        "assurance_case": {"passed": assurance["passed"], "claims": assurance["total_claims"],
                           "broken": assurance["broken"], "stale": assurance["stale"],
                           "failed_evidence": assurance["failed_evidence"],
                           "green": assurance["passed"], "digest": hash_object(assurance)},
        "threat_model": {"passed": threat["passed"], "threats": threat["total_threats"],
                         "green": threat["passed"], "digest": hash_object(threat)},
        "evaluator_health": {"passed": hlth["passed"], "detection_rate": hlth["seeded_defect_detection_rate"],
                             "green": hlth["passed"], "digest": hash_object(hlth)},
    }
    all_green = clean and all(g["green"] for g in gates.values())
    reasons = []
    if not clean:
        reasons.append("WORKTREE_DIRTY: evidence must be generated from a clean candidate")
    for name, g in gates.items():
        if not g["green"]:
            reasons.append(f"{name}_not_green")

    manifest = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "candidate_sha": candidate,
        "clean_worktree": clean,
        "generated_from": "clean git-archive export of candidate_sha",
        "requested_profile": profile,
        "gates": gates,
        "author_side_all_green": all_green,
        "not_green_reasons": reasons,
        "verified": False,
        "statement": "AUTHOR-side evidence from a clean export of the exact candidate. A required PARTIAL, "
                     "UNVERIFIABLE, or STALE result is NOT green. VERIFIED can only be issued by a separate, "
                     "protected verification trust domain that re-runs these gates and binds these digests.",
    }
    manifest["manifest_digest"] = hash_object({k: v for k, v in manifest.items() if k != "manifest_digest"})
    return manifest


def render_release_readiness(manifest: dict[str, Any]) -> str:
    g = manifest["gates"]
    def mark(x): return "PASS" if x else "NOT GREEN"
    lines = [
        "# AERS Release-Readiness Report",
        "",
        "> POST-COMMIT artifact generated from a clean export of the candidate. Not committed into the candidate.",
        "",
        f"Candidate: `{manifest['candidate_sha']}`   clean worktree: {manifest['clean_worktree']}",
        f"Generated: {manifest['generated_at']}   profile: {manifest['requested_profile']}",
        f"Manifest digest: `{manifest['manifest_digest']}`",
        "",
        "| Gate | Result | Detail |",
        "|------|--------|--------|",
        f"| Compliance ({g['assessment']['profile']}) | {mark(g['assessment']['green'])} | "
        f"{g['assessment']['required_pass']}/{g['assessment']['required_total']} required, "
        f"{g['assessment']['required_partial']} partial |",
        f"| Adversarial benchmark | {mark(g['adversarial_benchmark']['green'])} | "
        f"{g['adversarial_benchmark']['contained']}/{g['adversarial_benchmark']['cases']} contained |",
        f"| Assurance case | {mark(g['assurance_case']['green'])} | "
        f"{g['assurance_case']['claims']} claims, {g['assurance_case']['broken']} broken, "
        f"{g['assurance_case']['stale']} stale, {g['assurance_case']['failed_evidence']} failed-evidence |",
        f"| Threat model | {mark(g['threat_model']['green'])} | {g['threat_model']['threats']} threats mapped |",
        f"| Evaluator health | {mark(g['evaluator_health']['green'])} | detection {g['evaluator_health']['detection_rate']:.2f} |",
        "",
        f"**Author-side all green:** {manifest['author_side_all_green']}",
    ]
    if manifest["not_green_reasons"]:
        lines.append(f"**Not-green reasons:** {manifest['not_green_reasons']}")
    lines += ["", "> VERIFIED is NOT asserted here. A separate protected verifier must re-run these gates against "
              "the immutable candidate and issue the production attestation.", ""]
    return "\n".join(lines)
