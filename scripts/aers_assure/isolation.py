"""Isolation truth model — explicit isolation states, with CRYPTOGRAPHICALLY
verified external attestations.

The core dishonesty AERS must avoid: treating an assertion as proof. This module
names five states and enforces a per-risk-tier minimum. Two things are true here
that were not before:

  1. A bare `AERS_NETWORK_ISOLATED=1` is only `ASSERTED_ISOLATED`.
  2. `AERS_ISOLATION_ATTESTATION` is honored as `EXTERNALLY_ATTESTED_ISOLATED`
     ONLY when it is a valid Ed25519-signed token from an issuer key in the
     external (out-of-repo) trust store, is unexpired, and — when provided —
     binds the mechanism, candidate, and policy. A forged or unsigned token is
     rejected and downgraded.

Production `VERIFIED` never rests on a repository-local isolation claim. The gate
fails closed. Integrating this gate into `scripts/aers/verify.py` (a protected
file) is staged in `docs/proposed-control-plane-change/`.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aers.util import canonical_json
from . import _ed25519 as ed
from .verifier import default_trust_store

PROVEN_ISOLATED = "PROVEN_ISOLATED"
EXTERNALLY_ATTESTED_ISOLATED = "EXTERNALLY_ATTESTED_ISOLATED"
ASSERTED_ISOLATED = "ASSERTED_ISOLATED"
NOT_ISOLATED = "NOT_ISOLATED"
UNKNOWN = "UNKNOWN"

STRENGTH = {PROVEN_ISOLATED: 4, EXTERNALLY_ATTESTED_ISOLATED: 3, ASSERTED_ISOLATED: 2, NOT_ISOLATED: 1, UNKNOWN: 0}

MIN_STATE_FOR_AUTHOR_READY = {
    "R0": ASSERTED_ISOLATED,
    "R1": ASSERTED_ISOLATED,
    "R2": EXTERNALLY_ATTESTED_ISOLATED,
    "R3": PROVEN_ISOLATED,
}
PRODUCTION_VERIFIED_MIN_STATE = EXTERNALLY_ATTESTED_ISOLATED


def make_isolation_token(payload: dict[str, Any], seed: bytes, keyid: str) -> str:
    """Build a signed isolation attestation token (used by trusted infra / tests)."""
    body = canonical_json(payload).encode("utf-8")
    sig = ed.signature(body, seed, ed.publickey(seed))
    envelope = {"payload": base64.standard_b64encode(body).decode("ascii"), "keyid": keyid, "sig": sig.hex()}
    return base64.standard_b64encode(canonical_json(envelope).encode("utf-8")).decode("ascii")


def verify_isolation_attestation(token: str, trust_store: dict[str, Any] | None = None,
                                 now_iso: str | None = None, bindings: dict[str, str] | None = None) -> dict[str, Any]:
    """Verify a signed isolation token. Returns {ok, reasons, payload}. Fail-closed:
    any decode/signature/expiry/binding problem yields ok=False."""
    store = trust_store or default_trust_store()
    reasons: list[str] = []
    try:
        envelope = json.loads(base64.standard_b64decode(token))
        body = base64.standard_b64decode(envelope["payload"])
        keyid = envelope["keyid"]
        sig = bytes.fromhex(envelope["sig"])
    except Exception:
        return {"ok": False, "reasons": ["MALFORMED_ISOLATION_TOKEN"], "payload": None}
    key_hex = dict(store.get("isolation_keys", {})).get(keyid)
    if key_hex is None:
        return {"ok": False, "reasons": ["UNKNOWN_ISOLATION_ISSUER"], "payload": None}
    if not ed.checkvalid(sig, body, bytes.fromhex(key_hex)):
        return {"ok": False, "reasons": ["ISOLATION_SIGNATURE_MISMATCH"], "payload": None}
    payload = json.loads(body)
    now = datetime.fromisoformat(now_iso.replace("Z", "+00:00")) if now_iso else datetime.now(timezone.utc)
    try:
        if now > datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00")):
            reasons.append("ISOLATION_ATTESTATION_EXPIRED")
    except (KeyError, ValueError):
        reasons.append("ISOLATION_MISSING_EXPIRY")
    for field, expected in (bindings or {}).items():
        if payload.get(field) != expected:
            reasons.append(f"ISOLATION_BINDING_MISMATCH:{field}")
    return {"ok": not reasons, "reasons": reasons, "payload": payload}


def assess_isolation(env: dict[str, str] | None = None, trust_store: dict[str, Any] | None = None,
                     now_iso: str | None = None, bindings: dict[str, str] | None = None) -> dict[str, Any]:
    """Classify the current process's network-isolation evidence, honestly."""
    env = env if env is not None else dict(os.environ)
    evidence: list[str] = []

    token = env.get("AERS_ISOLATION_ATTESTATION")
    if token:
        result = verify_isolation_attestation(token, trust_store, now_iso, bindings)
        if result["ok"]:
            evidence.append("verified external isolation attestation (Ed25519, unexpired, bound)")
            return {"state": EXTERNALLY_ATTESTED_ISOLATED, "evidence": evidence,
                    "issuer": (result["payload"] or {}).get("issuer")}
        # A present-but-invalid token must NOT be trusted; record why and fall through.
        evidence.append(f"isolation attestation present but REJECTED: {result['reasons']}")

    if env.get("AERS_DISABLE_ISOLATION_PROBE") != "1" and shutil.which("unshare"):
        probe = subprocess.run(["unshare", "-Urn", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            evidence.append("demonstrated an isolated user network namespace (unshare -Urn)")
            return {"state": PROVEN_ISOLATED, "evidence": evidence}
        evidence.append("unshare present but namespace creation failed")

    if env.get("AERS_NETWORK_ISOLATED") == "1":
        evidence.append("AERS_NETWORK_ISOLATED=1 asserted with no demonstration (NOT proof)")
        return {"state": ASSERTED_ISOLATED, "evidence": evidence}

    evidence.append("no isolation mechanism demonstrated or attested")
    return {"state": UNKNOWN, "evidence": evidence}


def accepts_for_author_ready(state: str, risk_tier: str) -> bool:
    required = MIN_STATE_FOR_AUTHOR_READY.get(risk_tier, PROVEN_ISOLATED)
    return STRENGTH.get(state, 0) >= STRENGTH[required]


def gate_author_ready(risk_tier: str, env: dict[str, str] | None = None,
                      trust_store: dict[str, Any] | None = None, now_iso: str | None = None,
                      bindings: dict[str, str] | None = None) -> dict[str, Any]:
    """Fail-closed isolation gate for AUTHOR_READY."""
    assessment = assess_isolation(env, trust_store, now_iso, bindings)
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
            "asserted or unverifiable isolation is not proven isolation"),
    }
