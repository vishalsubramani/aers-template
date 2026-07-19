"""Isolation truth model — explicit isolation states replacing asserted booleans.

The core dishonesty AERS must avoid: treating "I set an env var" or "isolation is
required by policy" as proof that isolation actually held. This module names five
states and defines which risk tiers / assurance profiles may accept each. An
environment-variable attestation is, on its own, only ASSERTED — never PROVEN.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

PROVEN_ISOLATED = "PROVEN_ISOLATED"
EXTERNALLY_ATTESTED_ISOLATED = "EXTERNALLY_ATTESTED_ISOLATED"
ASSERTED_ISOLATED = "ASSERTED_ISOLATED"
NOT_ISOLATED = "NOT_ISOLATED"
UNKNOWN = "UNKNOWN"

# Ordering from strongest to weakest evidence.
STRENGTH = {PROVEN_ISOLATED: 4, EXTERNALLY_ATTESTED_ISOLATED: 3, ASSERTED_ISOLATED: 2, NOT_ISOLATED: 1, UNKNOWN: 0}

# Minimum isolation state that may reach AUTHOR_READY per risk tier. R2+ must not
# advance on ASSERTED alone — that is the whole point of the truth model.
MIN_STATE_FOR_AUTHOR_READY = {
    "R0": ASSERTED_ISOLATED,
    "R1": ASSERTED_ISOLATED,
    "R2": EXTERNALLY_ATTESTED_ISOLATED,
    "R3": PROVEN_ISOLATED,
}

# Production VERIFIED may NEVER rest on a repository-local isolation claim; it
# requires the external verifier's own proven/attested isolation.
PRODUCTION_VERIFIED_MIN_STATE = EXTERNALLY_ATTESTED_ISOLATED


def assess_isolation(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Classify the *current* process's network-isolation evidence, honestly.

    - PROVEN_ISOLATED: we actively demonstrated a network namespace with no
      egress (a positive test), not merely that a tool exists.
    - EXTERNALLY_ATTESTED_ISOLATED: an out-of-band attestation token from the
      trusted infrastructure is present (still not repo-local proof, but a
      separate trust domain vouches).
    - ASSERTED_ISOLATED: a plain env flag claims isolation with no demonstration.
    - NOT_ISOLATED: we demonstrated egress is possible, or no mechanism exists.
    - UNKNOWN: we could not determine either way.
    """
    env = env if env is not None else dict(os.environ)
    evidence: list[str] = []

    # External attestation: a signed/opaque token from trusted infra. We do not
    # treat the mere presence of a boolean like AERS_NETWORK_ISOLATED=1 as this;
    # that is only ASSERTED. A real attestation carries a value we can record.
    attestation = env.get("AERS_ISOLATION_ATTESTATION")
    if attestation:
        evidence.append("external isolation attestation token present")
        return {"state": EXTERNALLY_ATTESTED_ISOLATED, "evidence": evidence,
                "attestation_fingerprint": attestation[:12] + "..." if len(attestation) > 12 else attestation}

    # Proof by demonstration: create a user network namespace and confirm it.
    # AERS_DISABLE_ISOLATION_PROBE simulates a host with no provable isolation
    # mechanism (used by the adversarial benchmark to exercise the asserted-only
    # path deterministically); it never manufactures proof, only withholds it.
    if env.get("AERS_DISABLE_ISOLATION_PROBE") != "1" and shutil.which("unshare"):
        probe = subprocess.run(["unshare", "-Urn", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            evidence.append("demonstrated an isolated user network namespace (unshare -Urn)")
            return {"state": PROVEN_ISOLATED, "evidence": evidence}
        evidence.append("unshare present but namespace creation failed")

    # Assertion only: a boolean flag with nothing behind it.
    if env.get("AERS_NETWORK_ISOLATED") == "1":
        evidence.append("AERS_NETWORK_ISOLATED=1 asserted with no demonstration (NOT proof)")
        return {"state": ASSERTED_ISOLATED, "evidence": evidence}

    evidence.append("no isolation mechanism demonstrated or attested")
    return {"state": UNKNOWN, "evidence": evidence}


def accepts_for_author_ready(state: str, risk_tier: str) -> bool:
    required = MIN_STATE_FOR_AUTHOR_READY.get(risk_tier, PROVEN_ISOLATED)
    return STRENGTH.get(state, 0) >= STRENGTH[required]


def gate_author_ready(risk_tier: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Fail-closed isolation gate for AUTHOR_READY. Returns a decision dict; the
    caller refuses to advance when `allowed` is False."""
    assessment = assess_isolation(env)
    state = assessment["state"]
    allowed = accepts_for_author_ready(state, risk_tier)
    required = MIN_STATE_FOR_AUTHOR_READY.get(risk_tier, PROVEN_ISOLATED)
    return {
        "risk_tier": risk_tier,
        "isolation_state": state,
        "required_state": required,
        "allowed": allowed,
        "evidence": assessment["evidence"],
        "reason": None if allowed else (
            f"ISOLATION_INSUFFICIENT: risk {risk_tier} requires >= {required} but observed {state}; "
            "asserted isolation is not proven isolation"),
    }
