"""Compliance and maturity assessment.

`assess --profile <id>` inspects the repository for *detectable implementation*
of each control the profile requires and emits PASS / FAIL / PARTIAL /
NOT_APPLICABLE / UNVERIFIABLE. A control is never PASS merely because a document
claims it — detection reads real files, schemas, config, and command wiring.
Controls that depend on an external trust domain (a deployed verifier, private
holdouts, production signing) are honestly reported PARTIAL/UNVERIFIABLE from
inside the repository, never PASS.
"""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Callable

from aers.util import load_json
from .profiles import load_controls, load_profile

PASS, FAIL, PARTIAL, NOT_APPLICABLE, UNVERIFIABLE = "PASS", "FAIL", "PARTIAL", "NOT_APPLICABLE", "UNVERIFIABLE"


class _Ctx:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        try:
            self.toml = tomllib.loads((repo / "aers.toml").read_text(encoding="utf-8"))
        except Exception:
            self.toml = {}

    def exists(self, rel: str) -> bool:
        return (self.repo / rel).exists()

    def text(self, rel: str) -> str:
        try:
            return (self.repo / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def json(self, rel: str) -> Any:
        try:
            return load_json(self.repo / rel)
        except Exception:
            return None


Detector = Callable[[_Ctx], tuple]


def _d_stable_commands(c: _Ctx) -> tuple:
    text = c.text("Makefile")
    needed = ["bootstrap", "check", "test", "security", "evals", "verify"]
    missing = [t for t in needed if f"{t}:" not in text]
    if not missing:
        return PASS, ["Makefile"], "All six stable targets present."
    return FAIL, ["Makefile"], f"Missing Make targets: {missing}"


def _d_scope(c: _Ctx) -> tuple:
    if c.exists("scripts/aers/scope.py") and "def evaluate_scope" in c.text("scripts/aers/scope.py"):
        return PASS, ["scripts/aers/scope.py"], "evaluate_scope diff gate present."
    return FAIL, ["scripts/aers/scope.py"], "Scope gate missing."


def _d_protected_paths(c: _Ctx) -> tuple:
    data = c.json(".agents/policies/protected-paths.json")
    if data and data.get("always_protected") and data.get("test_patterns"):
        return PASS, [".agents/policies/protected-paths.json"], "Protected-path policy populated."
    return FAIL, [".agents/policies/protected-paths.json"], "Protected-path policy missing or empty."


def _d_static_checks(c: _Ctx) -> tuple:
    text = c.text("Makefile")
    if "aers.py lint" in text or "aers lint" in text:
        return PASS, ["Makefile", "scripts/aers/lint.py"], "check target runs aers lint."
    return FAIL, ["Makefile"], "check target does not run aers lint."


def _d_test_suite(c: _Ctx) -> tuple:
    tests = list((c.repo / "tests").rglob("test_*.py")) if c.exists("tests") else []
    if tests:
        return PASS, ["tests/"], f"{len(tests)} test module(s) discoverable."
    return FAIL, ["tests/"], "No test_*.py modules found."


def _d_audit(c: _Ctx) -> tuple:
    if c.exists("scripts/aers/audit.py") and "def audit_candidate" in c.text("scripts/aers/audit.py"):
        return PASS, ["scripts/aers/audit.py"], "Deterministic audit present."
    return FAIL, ["scripts/aers/audit.py"], "Deterministic audit missing."


def _d_contract_integrity(c: _Ctx) -> tuple:
    if c.exists(".agents/schemas/feature-contract.schema.json") and c.exists("scripts/aers/contracts.py"):
        return PASS, [".agents/schemas/feature-contract.schema.json", "scripts/aers/contracts.py"], "Typed contracts + loader present."
    return FAIL, [".agents/schemas/feature-contract.schema.json"], "Contract schema or loader missing."


def _d_differential(c: _Ctx) -> tuple:
    if "DIFFERENTIAL_TEST_PASSES_ON_BASE" in c.text("scripts/aers/verify.py"):
        return PASS, ["scripts/aers/verify.py"], "Differential (fails-on-base) gate present."
    return FAIL, ["scripts/aers/verify.py"], "Differential gate missing."


def _d_reviewer_independence(c: _Ctx) -> tuple:
    loop = c.text("scripts/loop.py")
    schema = c.json(".agents/schemas/reviewer-report.schema.json")
    binds = bool(schema and "candidate_sha" in schema.get("required", []))
    if "validate_reviewer" in loop and binds:
        return PASS, ["scripts/loop.py", ".agents/schemas/reviewer-report.schema.json"], "Reviewer stage binds candidate_sha."
    return FAIL, ["scripts/loop.py"], "Independent reviewer stage or candidate binding missing."


def _d_second_reviewer(c: _Ctx) -> tuple:
    verification = c.toml.get("verification", {})
    if "require_second_reviewer_r2" not in verification:
        return FAIL, ["aers.toml"], "require_second_reviewer_r2 not configured."
    if verification.get("require_second_reviewer_r2") is True:
        return PASS, ["aers.toml", "scripts/loop.py"], "Second R2 reviewer required by default."
    return PARTIAL, ["aers.toml"], "Mechanism present but require_second_reviewer_r2 defaults to false; set true for Standard+/High Assurance."


def _d_isolation(c: _Ctx) -> tuple:
    if c.exists("scripts/aers_assure/isolation.py") and "ASSERTED_ISOLATED" in c.text("scripts/aers_assure/isolation.py"):
        return PASS, ["scripts/aers_assure/isolation.py"], "Isolation truth model present (states, not booleans)."
    return FAIL, ["scripts/aers_assure/isolation.py"], "Isolation truth model missing."


def _d_external_verifier(c: _Ctx) -> tuple:
    ref = c.exists("scripts/aers_assure/verifier.py")
    wf = c.exists(".github/workflows/TRUSTED-VERIFIER.reference.yml.disabled")
    if ref and wf:
        return PARTIAL, ["scripts/aers_assure/verifier.py", ".github/workflows/TRUSTED-VERIFIER.reference.yml.disabled"], (
            "Verifier protocol + reference workflow present; production VERIFIED requires deploying the verifier "
            "in a separate protected trust domain (external, not repo-verifiable).")
    return FAIL, ["scripts/aers_assure/verifier.py"], "External verifier reference missing."


def _d_private_oracle(c: _Ctx) -> tuple:
    if c.exists(".agents/trusted/private-eval-contract.json"):
        return PARTIAL, [".agents/trusted/private-eval-contract.json"], (
            "Private-oracle contract present; actual holdouts must live outside this repo (cannot be verified from here).")
    return FAIL, [".agents/trusted/private-eval-contract.json"], "Private-oracle contract missing."


def _d_attestation(c: _Ctx) -> tuple:
    text = c.text("scripts/aers_assure/verifier.py")
    if "def verify_attestation" in text and "BINDING_MISMATCH" in text:
        return PASS, ["scripts/aers_assure/verifier.py"], "Attestation binds candidate/policy/evidence with tamper checks."
    return FAIL, ["scripts/aers_assure/verifier.py"], "Attestation binding/verification missing."


def _d_signed_provenance(c: _Ctx) -> tuple:
    rel = c.json(".agents/policies/release-policy.json")
    if rel and "build_provenance" in rel.get("requires", []) and "signed_artifact" in rel.get("requires", []):
        return PARTIAL, [".agents/policies/release-policy.json"], (
            "Release policy requires signed provenance; production signing key lives in the release trust domain "
            "(not repo-verifiable).")
    return FAIL, [".agents/policies/release-policy.json"], "Release policy does not require signed provenance."


def _d_memory(c: _Ctx) -> tuple:
    pol = c.json(".agents/policies/memory-policy.json")
    mem = c.text("scripts/aers/memory.py")
    if pol and pol.get("proposer_may_approve") is False and "AERS_CURATOR_ID" in mem:
        return PASS, [".agents/policies/memory-policy.json", "scripts/aers/memory.py"], "Quarantine + curator-only promotion enforced."
    return FAIL, [".agents/policies/memory-policy.json"], "Memory governance (no self-promotion) not enforced."


def _d_dependency(c: _Ctx) -> tuple:
    lock = c.json(".agents/skills/skills.lock.json")
    if lock is not None and all("sha256" in s for s in lock.get("skills", [])):
        return PASS, [".agents/skills/skills.lock.json"], "Skills pinned with sha256."
    if lock is not None:
        return PARTIAL, [".agents/skills/skills.lock.json"], "Skills lock present but not all entries hash-pinned."
    return FAIL, [".agents/skills/skills.lock.json"], "No skills lock."


def _d_rollback(c: _Ctx) -> tuple:
    schema = c.text(".agents/schemas/feature-contract.schema.json")
    if '"rollback"' in schema or "rollback" in schema:
        return PASS, [".agents/schemas/feature-contract.schema.json", "scripts/aers/contracts.py"], "Rollout/rollback required in feature contract."
    return FAIL, [".agents/schemas/feature-contract.schema.json"], "Rollback not required."


def _d_observability(c: _Ctx) -> tuple:
    tel = c.toml.get("telemetry", {})
    if c.exists(".agents/schemas/trajectory-event.schema.json") and tel:
        return PASS, [".agents/schemas/trajectory-event.schema.json", "aers.toml"], "Trajectory schema + telemetry config present."
    return FAIL, ["aers.toml"], "Observability/telemetry not configured."


def _d_release_segregation(c: _Ctx) -> tuple:
    rel = c.json(".agents/policies/release-policy.json")
    forbidden = rel.get("forbidden", []) if rel else []
    if "release_from_worktree" in forbidden and "agent_direct_production_shell" in forbidden:
        return PASS, [".agents/policies/release-policy.json"], "Release segregation forbidden-list enforced."
    return FAIL, [".agents/policies/release-policy.json"], "Release segregation not enforced."


def _d_evidence_retention(c: _Ctx) -> tuple:
    if c.exists("scripts/aers_assure/evidence.py"):
        return PASS, ["scripts/aers_assure/evidence.py"], "Evidence manifest generator present."
    return FAIL, ["scripts/aers_assure/evidence.py"], "No evidence manifest generator."


def _d_evaluator_health(c: _Ctx) -> tuple:
    if c.exists("scripts/aers_assure/health.py") and c.exists("assurance/health/health-cases.jsonl"):
        return PASS, ["scripts/aers_assure/health.py", "assurance/health/health-cases.jsonl"], "Evaluator-health suite present."
    return FAIL, ["scripts/aers_assure/health.py"], "Evaluator-health suite missing."


def _d_segregation_duties(c: _Ctx) -> tuple:
    if c.exists("CODEOWNERS"):
        return PARTIAL, ["CODEOWNERS", ".agents/roles/"], "Roles + CODEOWNERS present; identity separation enforced operationally (partly external)."
    return FAIL, ["CODEOWNERS"], "No CODEOWNERS / duty separation."


def _d_approval_records(c: _Ctx) -> tuple:
    return PARTIAL, [".agents/schemas/ledger-event.schema.json"], "Ledger records events; external approval records live in the verifier/release domain."


def _d_policy_pinning(c: _Ctx) -> tuple:
    if "policy_digest" in c.text("scripts/aers_assure/verifier.py"):
        return PASS, ["scripts/aers_assure/verifier.py"], "Handoff/attestation pin policy_digest."
    return FAIL, ["scripts/aers_assure/verifier.py"], "Policy version not pinned in attestation."


def _d_exception_handling(c: _Ctx) -> tuple:
    if c.exists("docs/RESIDUAL-RISK.md"):
        return PARTIAL, ["docs/RESIDUAL-RISK.md"], "Residual-risk register present; per-run waiver records are operational."
    return FAIL, ["docs/RESIDUAL-RISK.md"], "No residual-risk / exception register."


def _d_assurance_layer_protected(c: _Ctx) -> tuple:
    data = c.json(".agents/policies/protected-paths.json")
    prot = data.get("always_protected", []) if data else []
    needed = ["scripts/aers_assure/**", "scripts/assure.py", "assurance/**"]
    missing = [n for n in needed if n not in prot]
    if not missing:
        return PASS, [".agents/policies/protected-paths.json", "CODEOWNERS"], "Assurance layer is protected."
    return FAIL, [".agents/policies/protected-paths.json"], (
        f"Assurance layer NOT protected ({missing}); a task could modify the verifier/assessor and rely on it "
        "in the same run. Apply docs/proposed-control-plane-change/.")


def _d_retention_redaction(c: _Ctx) -> tuple:
    tel = c.toml.get("telemetry", {})
    if tel.get("redact_by_default") is True and tel.get("capture_content") is False:
        return PASS, ["aers.toml", "scripts/aers/util.py"], "Redaction on by default; content capture off."
    return FAIL, ["aers.toml"], "Redaction/retention defaults not safe."


DETECTORS: dict[str, Detector] = {
    "CTRL-STABLE-COMMANDS": _d_stable_commands,
    "CTRL-SCOPE-ENFORCEMENT": _d_scope,
    "CTRL-PROTECTED-PATHS": _d_protected_paths,
    "CTRL-STATIC-CHECKS": _d_static_checks,
    "CTRL-TEST-SUITE": _d_test_suite,
    "CTRL-DETERMINISTIC-AUDIT": _d_audit,
    "CTRL-CONTRACT-INTEGRITY": _d_contract_integrity,
    "CTRL-DIFFERENTIAL-TEST": _d_differential,
    "CTRL-REVIEWER-INDEPENDENCE": _d_reviewer_independence,
    "CTRL-SECOND-REVIEWER-R2": _d_second_reviewer,
    "CTRL-ISOLATION": _d_isolation,
    "CTRL-EXTERNAL-VERIFIER": _d_external_verifier,
    "CTRL-PRIVATE-ORACLE": _d_private_oracle,
    "CTRL-ATTESTATION": _d_attestation,
    "CTRL-SIGNED-PROVENANCE": _d_signed_provenance,
    "CTRL-MEMORY-GOVERNANCE": _d_memory,
    "CTRL-DEPENDENCY-GOVERNANCE": _d_dependency,
    "CTRL-ROLLBACK": _d_rollback,
    "CTRL-OBSERVABILITY": _d_observability,
    "CTRL-RELEASE-SEGREGATION": _d_release_segregation,
    "CTRL-EVIDENCE-RETENTION": _d_evidence_retention,
    "CTRL-EVALUATOR-HEALTH": _d_evaluator_health,
    "CTRL-SEGREGATION-OF-DUTIES": _d_segregation_duties,
    "CTRL-APPROVAL-RECORDS": _d_approval_records,
    "CTRL-POLICY-VERSION-PINNING": _d_policy_pinning,
    "CTRL-EXCEPTION-HANDLING": _d_exception_handling,
    "CTRL-RETENTION-REDACTION": _d_retention_redaction,
    "CTRL-ASSURANCE-LAYER-PROTECTED": _d_assurance_layer_protected,
}


def assess(repo: Path, profile_id: str) -> dict[str, Any]:
    profile = load_profile(repo, profile_id)
    catalog = load_controls(repo)
    ctx = _Ctx(repo)
    results: list[dict[str, Any]] = []
    for control_id, level in sorted(profile["controls"].items()):
        meta = catalog.get(control_id, {})
        if level == "NOT_APPLICABLE":
            status, files, reason = NOT_APPLICABLE, [], "Not applicable to this profile."
        else:
            detector = DETECTORS.get(control_id)
            if detector is None:
                status, files, reason = UNVERIFIABLE, [], "No detector implemented for this control."
            else:
                status, files, reason = detector(ctx)
        results.append({
            "control_id": control_id,
            "requirement": level,
            "category": meta.get("category", "unknown"),
            "description": meta.get("description", ""),
            "status": status,
            "evidence_source": meta.get("evidence_source", ""),
            "affected_files": files,
            "reason": reason,
            "remediation": meta.get("remediation", ""),
            "blocks": meta.get("blocks", "AUTHOR_READY"),
        })

    required = [r for r in results if r["requirement"] == "REQUIRED"]
    failing_required = [r for r in required if r["status"] == FAIL]
    partial_required = [r for r in required if r["status"] in {PARTIAL, UNVERIFIABLE}]
    recommended_fail = [r for r in results if r["requirement"] == "RECOMMENDED" and r["status"] == FAIL]

    if failing_required:
        overall = FAIL
    elif partial_required:
        overall = PARTIAL
    else:
        overall = PASS
    return {
        "schema_version": 1,
        "profile": profile_id,
        "profile_version": profile.get("version"),
        "overall": overall,
        "summary": {
            "required_total": len(required),
            "required_pass": sum(1 for r in required if r["status"] == PASS),
            "required_partial": len(partial_required),
            "required_fail": len(failing_required),
            "recommended_fail": len(recommended_fail),
        },
        "results": results,
        "statement": "PASS reflects detectable implementation only; controls that depend on an external trust "
                     "domain are reported PARTIAL/UNVERIFIABLE from inside the repository, never PASS.",
    }


def render_human(report: dict[str, Any]) -> str:
    icons = {PASS: "PASS", FAIL: "FAIL", PARTIAL: "PART", NOT_APPLICABLE: "N/A ", UNVERIFIABLE: "UNVF"}
    lines = [f"AERS assessment — profile '{report['profile']}' (v{report['profile_version']})",
             f"Overall: {report['overall']}   "
             f"required {report['summary']['required_pass']}/{report['summary']['required_total']} pass, "
             f"{report['summary']['required_partial']} partial, {report['summary']['required_fail']} fail", ""]
    for r in report["results"]:
        lines.append(f"[{icons.get(r['status'], r['status'])}] {r['control_id']:<28} ({r['requirement']}) {r['reason']}")
    return "\n".join(lines)
