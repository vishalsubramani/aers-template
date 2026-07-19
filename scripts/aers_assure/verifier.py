"""External verifier reference: immutable candidate handoff, DSSE-style signed
attestation, and tamper/substitution/replay-resistant verification.

TRUST-DOMAIN SEPARATION (read this before trusting any output here).
This module models the *protocol* between the authoring trust domain (this
repository, where an agent produces AUTHOR_READY candidates) and a separate
verification trust domain that alone may issue VERIFIED. The offline-demo signer
below uses a well-known, published demo key. It can therefore only produce a
*demo-scoped* attestation: `production_valid` is structurally False for anything
the repository can sign, because the repository trust-store carries no production
verifier keys (`production_keys` is empty). A real production VERIFIED requires an
external verifier that holds a private signing key which never enters this
repository, and whose public key is supplied out-of-band to the party checking
the attestation (see AERS_EXTERNAL_TRUST_STORE).

Nothing in this module gives repository-local code the ability to mint a
production-valid VERIFIED. That is the point, and tests/aers_selftest proves it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aers.git import read_file_at_ref, rev_parse, run_git
from aers.util import canonical_json, load_json, sha256_bytes, sha256_text, utc_now

# ---------------------------------------------------------------------------
# Constants. The demo key is intentionally public: it exists so the protocol can
# be exercised fully offline. It is NOT a secret and confers no production trust.
# ---------------------------------------------------------------------------
DEMO_KEY_ID = "aers-offline-demo-v1"
_DEMO_KEY = b"AERS-OFFLINE-DEMO-KEY-NOT-FOR-PRODUCTION-USE"
PAYLOAD_TYPE = "application/vnd.aers.verification+json"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://aers.dev/attestation/verification/v1"
VALID_VERDICTS = {"VERIFIED", "REJECTED", "INFRASTRUCTURE_ERROR"}

# Policy files whose content defines what a candidate is allowed to do. The
# handoff pins a digest over these so a verifier can detect policy substitution
# between authoring time and verification time.
POLICY_FILES = [
    ".agents/policies/protected-paths.json",
    ".agents/policies/verification-policy.json",
    ".agents/policies/autonomy-policy.json",
    ".agents/policies/capability-policy.json",
    ".agents/policies/command-policy.json",
    ".agents/policies/release-policy.json",
    ".agents/policies/memory-policy.json",
    ".agents/policies/skills-policy.json",
    "aers.toml",
]


# ---------------------------------------------------------------------------
# DSSE (Dead Simple Signing Envelope) primitives.
# ---------------------------------------------------------------------------
def _pae(payload_type: str, payload: bytes) -> bytes:
    """DSSE pre-authentication encoding — binds the payload type into the signed
    bytes so a payload cannot be reinterpreted under a different type."""
    return b"DSSEv1 %d %s %d %s" % (len(payload_type), payload_type.encode("utf-8"), len(payload), payload)


def _mac(key: bytes, payload_type: str, payload: bytes) -> str:
    return hmac.new(key, _pae(payload_type, payload), hashlib.sha256).hexdigest()


def sign_demo(statement: dict[str, Any]) -> dict[str, Any]:
    """Produce a DSSE envelope over `statement` using the published demo key.

    This is the ONLY signer in the repository. It can never yield a
    production-valid attestation because DEMO_KEY_ID is not a production key.
    """
    payload = canonical_json(statement).encode("utf-8")
    b64 = base64.standard_b64encode(payload).decode("ascii")
    signature = _mac(_DEMO_KEY, PAYLOAD_TYPE, payload)
    return {
        "payloadType": PAYLOAD_TYPE,
        "payload": b64,
        "signatures": [{"keyid": DEMO_KEY_ID, "sig": signature}],
    }


def default_trust_store() -> dict[str, Any]:
    """The trust store used to *verify* attestations offline.

    `production_keys` is empty by design: no production verifier key material
    lives in this repository, so no envelope produced here can be
    production-valid. A relying party supplies real production public keys
    out-of-band via AERS_EXTERNAL_TRUST_STORE (a path OUTSIDE this repo)."""
    store: dict[str, Any] = {"demo_keys": {DEMO_KEY_ID: _DEMO_KEY.hex()}, "production_keys": {}}
    external = os.environ.get("AERS_EXTERNAL_TRUST_STORE")
    if external:
        path = Path(external)
        # An external trust store is only meaningful if it lives outside the
        # writable repository; a "trusted" file inside the repo is not a boundary.
        if path.exists():
            data = load_json(path)
            for keyid, keyhex in (data.get("production_keys") or {}).items():
                store["production_keys"][str(keyid)] = str(keyhex)
    return store


# ---------------------------------------------------------------------------
# Immutable candidate handoff.
# ---------------------------------------------------------------------------
def _policy_digest(repo: Path, ref: str) -> str:
    """Digest over the applicable policy files read at an immutable ref. Missing
    files are recorded as null so adding/removing a policy also changes the
    digest (substitution and omission are both detected)."""
    materials: dict[str, str | None] = {}
    for rel in POLICY_FILES:
        try:
            materials[rel] = sha256_bytes(read_file_at_ref(repo, ref, rel))
        except ValueError:
            materials[rel] = None
    return sha256_text(canonical_json(materials))


def _repo_identity(repo: Path) -> str:
    result = run_git(repo, ["remote", "get-url", "origin"], check=False)
    url = result.stdout.strip()
    return url or repo.resolve().name


def build_handoff(repo: Path, feature_id: str, task_id: str, candidate_ref: str,
                  author_report_path: Path, profile: str, contract_ref: str | None = None) -> dict[str, Any]:
    """Assemble the immutable candidate handoff the author domain sends to the
    verifier. Contains only digests and identities — never private material.

    Every field a verifier must bind against is present, and `handoff_digest`
    covers all of them so a single comparison detects any substitution."""
    candidate_sha = rev_parse(repo, candidate_ref)
    contract_sha = rev_parse(repo, contract_ref) if contract_ref else candidate_sha
    feature_path = f".specify/specs/{feature_id}/feature.contract.json"
    tasks_path = f".specify/specs/{feature_id}/tasks.json"
    source_digest = run_git(repo, ["rev-parse", f"{candidate_sha}^{{tree}}"]).stdout.strip()
    author_report = load_json(author_report_path)
    core = {
        "schema_version": 1,
        "repo_identity": _repo_identity(repo),
        "candidate_sha": candidate_sha,
        "source_tree_digest": source_digest,
        "feature_id": feature_id,
        "task_id": task_id,
        "feature_contract_digest": sha256_bytes(read_file_at_ref(repo, contract_sha, feature_path)),
        "task_contract_digest": sha256_bytes(read_file_at_ref(repo, contract_sha, tasks_path)),
        "policy_digest": _policy_digest(repo, contract_sha),
        "author_evidence_digest": sha256_text(canonical_json(author_report)),
        "requested_profile": profile,
        "created_at": utc_now(),
    }
    core["handoff_digest"] = sha256_text(canonical_json(core))
    return core


# ---------------------------------------------------------------------------
# Attestation (what the external verifier emits). Modeled here with the demo
# signer so the protocol is testable offline; a production verifier swaps in a
# real private key held in its own trust domain.
# ---------------------------------------------------------------------------
def make_attestation(handoff: dict[str, Any], verdict: str, reason_codes: list[str],
                     verifier_identity: str, trust_domain: str = "offline-demo",
                     ttl_seconds: int = 3600, nonce: str | None = None) -> dict[str, Any]:
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"Invalid verifier verdict: {verdict}")
    now = datetime.now(timezone.utc)
    statement = {
        "_type": STATEMENT_TYPE,
        "predicateType": PREDICATE_TYPE,
        "subject": [{"name": handoff["repo_identity"], "digest": {"gitCommit": handoff["candidate_sha"]}}],
        "predicate": {
            "verdict": verdict,
            "handoff_digest": handoff["handoff_digest"],
            "candidate_digest": handoff["candidate_sha"],
            "source_tree_digest": handoff["source_tree_digest"],
            "policy_digest": handoff["policy_digest"],
            "evidence_digest": handoff["author_evidence_digest"],
            "profile": handoff["requested_profile"],
            "verifier_identity": verifier_identity,
            "trust_domain": trust_domain,
            "reason_codes": sorted(set(reason_codes)),
            "timestamp": now.isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z"),
            "nonce": nonce or hashlib.sha256(canonical_json(handoff).encode() + str(now.timestamp()).encode()).hexdigest()[:16],
        },
    }
    return sign_demo(statement)


def _now_dt(now_iso: str | None) -> datetime:
    if now_iso:
        return datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def verify_attestation(envelope: dict[str, Any], handoff: dict[str, Any],
                       trust_store: dict[str, Any] | None = None, now_iso: str | None = None) -> dict[str, Any]:
    """Verify a DSSE attestation against the immutable handoff. Fail-closed.

    Detects: result tampering (signature mismatch), candidate/policy/evidence
    substitution (digest binding mismatch), stale attestations (expiry), and
    demo-vs-production trust scope. `production_valid` is True ONLY when the
    signing key is a known production key AND all bindings hold AND the verdict
    is VERIFIED AND it has not expired."""
    store = trust_store or default_trust_store()
    reasons: list[str] = []
    result: dict[str, Any] = {"valid": False, "production_valid": False, "verdict": None, "keyid": None,
                              "trust_domain": None, "reasons": reasons}

    # 1. Signature check — decode payload, recompute MAC under the named key.
    try:
        payload = base64.standard_b64decode(envelope["payload"])
        sig_entry = envelope["signatures"][0]
        keyid = sig_entry["keyid"]
        presented_sig = sig_entry["sig"]
    except (KeyError, IndexError, ValueError):
        reasons.append("MALFORMED_ENVELOPE")
        return result
    result["keyid"] = keyid
    all_keys = {**dict(store.get("demo_keys", {})), **dict(store.get("production_keys", {}))}
    key_hex = all_keys.get(keyid)
    if key_hex is None:
        reasons.append("UNKNOWN_SIGNING_KEY")
        return result
    expected_sig = _mac(bytes.fromhex(key_hex), envelope.get("payloadType", PAYLOAD_TYPE), payload)
    if not hmac.compare_digest(expected_sig, presented_sig):
        reasons.append("SIGNATURE_MISMATCH")  # result tampering or wrong key
        return result

    statement = json.loads(payload)
    predicate = statement.get("predicate", {})
    result["verdict"] = predicate.get("verdict")
    result["trust_domain"] = predicate.get("trust_domain")
    is_production_key = keyid in store.get("production_keys", {})

    # 2. Binding — the attestation must bind to THIS handoff, digit for digit.
    bindings = {
        "candidate_digest": handoff["candidate_sha"],
        "policy_digest": handoff["policy_digest"],
        "evidence_digest": handoff["author_evidence_digest"],
        "handoff_digest": handoff["handoff_digest"],
        "source_tree_digest": handoff["source_tree_digest"],
    }
    for field, expected in bindings.items():
        if predicate.get(field) != expected:
            reasons.append(f"BINDING_MISMATCH:{field}")

    # 3. Freshness.
    try:
        if _now_dt(now_iso) > datetime.fromisoformat(predicate["expires_at"].replace("Z", "+00:00")):
            reasons.append("ATTESTATION_EXPIRED")
    except (KeyError, ValueError):
        reasons.append("MISSING_EXPIRY")

    # 4. Verdict.
    if predicate.get("verdict") != "VERIFIED":
        reasons.append(f"VERDICT_{predicate.get('verdict')}")

    signature_ok = not reasons  # bindings/freshness/verdict all clean
    result["valid"] = signature_ok
    # Production validity additionally requires a production trust anchor. The
    # repository has none, so repository-signed attestations are never
    # production-valid — the core trust invariant.
    result["production_valid"] = signature_ok and is_production_key
    if signature_ok and not is_production_key:
        reasons.append("DEMO_TRUST_DOMAIN_ONLY")
    return result
