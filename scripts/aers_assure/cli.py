"""Command surface for the AERS assurance layer (`python3 scripts/assure.py --help`).

Additive to the control plane: verifier protocol, adversarial benchmark,
compliance assessment, assurance case, isolation truth model, structured threat
model, evaluator health, evidence manifest, and migration planning. Nothing here
issues VERIFIED or mutates the control plane.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aers.util import atomic_write_json, atomic_write_text, find_repo_root, load_json
from . import assess as assess_mod
from . import assurance as assurance_mod
from . import baseline as baseline_mod
from . import benchmark as benchmark_mod
from . import evidence as evidence_mod
from . import health as health_mod
from . import isolation as isolation_mod
from . import migrate as migrate_mod
from . import profiles as profiles_mod
from . import threats as threats_mod
from . import verifier as verifier_mod


def _json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aers-assure", description="AERS assurance layer")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("assess", help="compliance/maturity assessment against a profile")
    a.add_argument("--profile", default="standard", choices=profiles_mod.PROFILE_IDS)
    a.add_argument("--json", action="store_true"); a.add_argument("--output")

    sub.add_parser("profiles", help="list assurance profiles")

    b = sub.add_parser("benchmark", help="run the adversarial benchmark")
    b.add_argument("--json", action="store_true"); b.add_argument("--output")

    asu = sub.add_parser("assurance", help="evaluate the AERS assurance case")
    asu.add_argument("--json", action="store_true"); asu.add_argument("--refresh", action="store_true")
    asu.add_argument("--case", help="path to an alternate assurance-case.json (for testing)")

    tm = sub.add_parser("threat-model", help="validate/render the structured threat model")
    tm.add_argument("--render", action="store_true"); tm.add_argument("--output")

    eh = sub.add_parser("evaluator-health", help="run the evaluator-health suite")
    eh.add_argument("--json", action="store_true")

    iso = sub.add_parser("isolation", help="classify current isolation state")
    iso.add_argument("--risk", default="R2", choices=["R0", "R1", "R2", "R3"])

    hs = sub.add_parser("handoff", help="build an immutable candidate handoff")
    hs.add_argument("--feature", required=True); hs.add_argument("--task", required=True)
    hs.add_argument("--candidate", default="HEAD"); hs.add_argument("--contract-ref")
    hs.add_argument("--author-report", required=True); hs.add_argument("--profile", default="high-assurance")
    hs.add_argument("--output")

    ad = sub.add_parser("attest-demo", help="OFFLINE DEMO: produce a demo-scoped attestation (never production-valid)")
    ad.add_argument("--handoff", required=True); ad.add_argument("--verdict", default="VERIFIED")
    ad.add_argument("--reason", action="append", default=["ALL_CHECKS_PASS"])
    ad.add_argument("--identity", default="aers-offline-demo-verifier"); ad.add_argument("--output")

    va = sub.add_parser("verify-attestation", help="verify an attestation against a handoff (fail-closed)")
    va.add_argument("--attestation", required=True); va.add_argument("--handoff", required=True)

    em = sub.add_parser("evidence-manifest", help="aggregate all author-side assurance evidence")
    em.add_argument("--profile", default="high-assurance", choices=profiles_mod.PROFILE_IDS)
    em.add_argument("--output"); em.add_argument("--release-readiness")

    mig = sub.add_parser("migrate", help="plan a non-destructive AERS adoption for a target repo")
    mig.add_argument("--assess", required=True, help="path to the target repository")
    mig.add_argument("--template", help="template root (defaults to this repo)")
    mig.add_argument("--json", action="store_true")

    bl = sub.add_parser("baseline", help="compare workflow modes (derived containment + simulated cost)")
    bl.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = find_repo_root()
    try:
        if args.command == "assess":
            report = assess_mod.assess(repo, args.profile)
            if args.output:
                atomic_write_json(Path(args.output), report)
            print(json.dumps(report, indent=2) if args.json else assess_mod.render_human(report))
            return 0 if report["overall"] != "FAIL" else 1

        if args.command == "profiles":
            out = {}
            for pid in profiles_mod.PROFILE_IDS:
                prof = profiles_mod.load_profile(repo, pid)
                req = sum(1 for v in prof["controls"].values() if v == "REQUIRED")
                out[pid] = {"name": prof["name"], "version": prof["version"], "required_controls": req}
            _json(out); return 0

        if args.command == "benchmark":
            output = Path(args.output) if args.output else None
            report = benchmark_mod.run_benchmark(repo, output)
            print(json.dumps(report, indent=2) if args.json else benchmark_mod.render_human(report))
            return 0 if report["all_passed"] else 1

        if args.command == "assurance":
            if args.refresh:
                path = assurance_mod.refresh(repo); _json({"refreshed": str(path)}); return 0
            case_path = Path(args.case) if args.case else None
            report = assurance_mod.run_assurance(repo, case_path)
            print(json.dumps(report, indent=2) if args.json else assurance_mod.render_human(report))
            return 0 if report["passed"] else 1

        if args.command == "threat-model":
            if args.render:
                text = threats_mod.render_markdown(repo)
                if args.output:
                    atomic_write_text(Path(args.output), text); _json({"rendered": args.output})
                else:
                    print(text)
                return 0
            report = threats_mod.validate(repo); _json(report); return 0 if report["passed"] else 1

        if args.command == "evaluator-health":
            report = health_mod.run_health(repo)
            print(json.dumps(report, indent=2) if args.json else health_mod.render_human(report))
            return 0 if report["passed"] else 1

        if args.command == "isolation":
            decision = isolation_mod.gate_author_ready(args.risk)
            _json(decision); return 0 if decision["allowed"] else 1

        if args.command == "handoff":
            handoff = verifier_mod.build_handoff(repo, args.feature, args.task, args.candidate,
                                                 Path(args.author_report), args.profile, args.contract_ref)
            if args.output:
                atomic_write_json(Path(args.output), handoff)
            _json(handoff); return 0

        if args.command == "attest-demo":
            handoff = load_json(Path(args.handoff))
            envelope = verifier_mod.make_attestation(handoff, args.verdict, args.reason, args.identity)
            if args.output:
                atomic_write_json(Path(args.output), envelope)
            _json({"envelope": envelope,
                   "note": "OFFLINE DEMO attestation. Signed with the published demo key; it is NOT "
                           "production-valid and cannot be, from inside this repository."})
            return 0

        if args.command == "verify-attestation":
            envelope = load_json(Path(args.attestation))
            handoff = load_json(Path(args.handoff))
            result = verifier_mod.verify_attestation(envelope, handoff)
            _json(result)
            return 0 if result["valid"] else 1

        if args.command == "evidence-manifest":
            manifest = evidence_mod.build_manifest(repo, args.profile)
            if args.output:
                atomic_write_json(Path(args.output), manifest)
            if args.release_readiness:
                atomic_write_text(Path(args.release_readiness), evidence_mod.render_release_readiness(manifest))
            _json(manifest)
            return 0 if manifest["author_side_all_green"] else 1

        if args.command == "migrate":
            template = Path(args.template) if args.template else repo
            report = migrate_mod.assess_target(template, Path(args.assess))
            print(json.dumps(report, indent=2) if args.json else migrate_mod.render_human(report))
            return 0

        if args.command == "baseline":
            report = baseline_mod.run_baseline(repo)
            print(json.dumps(report, indent=2) if args.json else baseline_mod.render_human(report))
            return 0

        raise ValueError(f"Unhandled command: {args.command}")
    except Exception as exc:  # surface as structured error, exit 2
        _json({"error": type(exc).__name__, "message": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
