"""Machine-readable evidence manifest and release-readiness aggregation.

`evidence-manifest` runs every assurance gate from the exact candidate commit and
records their outcomes and content digests in one immutable manifest. It never
issues VERIFIED — it aggregates AUTHOR-side evidence a separate verifier can bind
against. `release-readiness` renders the same data as a human report.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aers.git import head_sha, is_clean
from aers.util import atomic_write_json, hash_object, utc_now
from . import assess as assess_mod
from . import assurance as assurance_mod
from . import benchmark as benchmark_mod
from . import health as health_mod
from . import threats as threats_mod


def build_manifest(repo: Path, profile: str = "high-assurance") -> dict[str, Any]:
    candidate = head_sha(repo)
    assessment = assess_mod.assess(repo, profile)
    bench = benchmark_mod.run_benchmark(repo)
    assurance = assurance_mod.run_assurance(repo)
    threat = threats_mod.validate(repo)
    hlth = health_mod.run_health(repo)

    gates = {
        "assessment": {"profile": profile, "overall": assessment["overall"],
                       "required_pass": assessment["summary"]["required_pass"],
                       "required_total": assessment["summary"]["required_total"],
                       "digest": hash_object(assessment)},
        "adversarial_benchmark": {"passed": bench["all_passed"], "cases": bench["total"],
                                  "contained": bench["passed"], "digest": hash_object(bench)},
        "assurance_case": {"passed": assurance["passed"], "claims": assurance["total_claims"],
                           "broken": assurance["broken"], "stale": assurance["stale"],
                           "digest": hash_object(assurance)},
        "threat_model": {"passed": threat["passed"], "threats": threat["total_threats"],
                         "digest": hash_object(threat)},
        "evaluator_health": {"passed": hlth["passed"],
                             "detection_rate": hlth["seeded_defect_detection_rate"],
                             "digest": hash_object(hlth)},
    }
    author_ready_gates = [g["passed"] if "passed" in g else (g["overall"] != "FAIL")
                          for g in gates.values()]
    manifest = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "candidate_sha": candidate,
        "clean_worktree": is_clean(repo),
        "requested_profile": profile,
        "gates": gates,
        "author_side_all_green": all(author_ready_gates),
        "verified": False,
        "statement": "This is AUTHOR-side evidence only. VERIFIED can only be issued by a separate, protected "
                     "verification trust domain that re-runs these gates and binds this manifest's digests.",
    }
    manifest["manifest_digest"] = hash_object({k: v for k, v in manifest.items() if k != "manifest_digest"})
    return manifest


def render_release_readiness(manifest: dict[str, Any]) -> str:
    lines = [
        "# AERS Release-Readiness Report",
        "",
        f"Candidate: `{manifest['candidate_sha']}`   clean worktree: {manifest['clean_worktree']}",
        f"Generated: {manifest['generated_at']}",
        f"Manifest digest: `{manifest['manifest_digest']}`",
        "",
        "| Gate | Result | Detail |",
        "|------|--------|--------|",
    ]
    g = manifest["gates"]
    lines.append(f"| Compliance ({g['assessment']['profile']}) | {g['assessment']['overall']} | "
                 f"{g['assessment']['required_pass']}/{g['assessment']['required_total']} required controls |")
    lines.append(f"| Adversarial benchmark | {'PASS' if g['adversarial_benchmark']['passed'] else 'FAIL'} | "
                 f"{g['adversarial_benchmark']['contained']}/{g['adversarial_benchmark']['cases']} contained |")
    lines.append(f"| Assurance case | {'PASS' if g['assurance_case']['passed'] else 'FAIL'} | "
                 f"{g['assurance_case']['claims']} claims, {g['assurance_case']['broken']} broken, "
                 f"{g['assurance_case']['stale']} stale |")
    lines.append(f"| Threat model | {'PASS' if g['threat_model']['passed'] else 'FAIL'} | "
                 f"{g['threat_model']['threats']} threats mapped |")
    lines.append(f"| Evaluator health | {'PASS' if g['evaluator_health']['passed'] else 'FAIL'} | "
                 f"detection {g['evaluator_health']['detection_rate']:.2f} |")
    lines += [
        "",
        f"**Author-side gates green:** {manifest['author_side_all_green']}",
        "",
        "> VERIFIED is NOT asserted here. A separate protected verifier must re-run these gates against the "
        "immutable candidate and issue the production attestation.",
        "",
    ]
    return "\n".join(lines)
