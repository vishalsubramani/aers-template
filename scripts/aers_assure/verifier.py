"""External verifier reference: immutable candidate handoff, DSSE-style
attestation signed with ASYMMETRIC (Ed25519) keys, and fail-closed verification.

WHY ASYMMETRIC (this is the core of the trust model).
The verifier signs with a PRIVATE key that never enters this repository. The
repository and relying parties hold only PUBLIC verification keys. Because
producing a signature requires the private key, no repository-local code can
forge a signature that verifies under a legitimate production public key — even
if it can see or supply the public key. This is strictly stronger than a shared
(HMAC) secret, where holding the verification key would let you sign.

Two independent barriers make `production_valid` unreachable from inside the repo:
  1. No production PRIVATE key exists here (only a published demo keypair whose
     public key is marked non-production).
  2. `verify_attestation` will not honor caller-supplied production trust roots
     unless an explicit test-only flag is set; by default production public keys
     come only from an out-of-band store OUTSIDE the repository.

The pure-Python Ed25519 in `_ed25519.py` is a self-contained reference whose
VERIFICATION path is RFC-8032 correct (it accepts genuine Ed25519 signatures and
rejects forgeries — see tests). Production deployments swap in an audited signing
library on the verifier side; this module verifies those signatures unchanged.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aers.git import read_file_at_ref, rev_parse, run_git
from aers.util import canonical_json, find_repo_root, load_json, sha256_bytes, sha256_text, utc_now
from . import _ed25519 as ed

# ---------------------------------------------------------------------------
# Demo keypair. The SEED is intentionally published — it exists only so the
# protocol can be exercised offline. Its public key is registered as a DEMO key,
# never a production key, so anything it signs is demo-scoped by construction.
# ---------------------------------------------------------------------------
DEMO_KEY_ID = "aers-offline-demo-ed25519-v1"
_DEMO_SEED = hashlib.sha256(b"AERS-OFFLINE-DEMO-SEED-NOT-FOR-PRODUCTION").digest()  # 32 bytes
DEMO_PUBLIC_KEY = ed.publickey(_DEMO_SEED)
DEMO_PUBLIC_HEX = DEMO_PUBLIC_KEY.hex()

PAYLOAD_TYPE = "application/vnd.aers.verification+json"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://aers.dev/attestation/verification/v1"
VALID_VERDICTS = {"VERIFIED", "REJECTED", "INFRASTRUCTURE_ERROR"}

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
# DSSE primitives (Ed25519 signatures).
# ---------------------------------------------------------------------------
def _pae(payload_type: str, payload: bytes) -> bytes:
    return b"DSSEv1 %d %s %d %s" % (len(payload_type), payload_type.encode("utf-8"), len(payload), payload)


def sign_ed25519(statement: dict[str, Any], seed: bytes, keyid: str) -> dict[str, Any]:
    payload = canonical_json(statement).encode("utf-8")
    pub = ed.publickey(seed)
    sig = ed.signature(_pae(PAYLOAD_TYPE, payload), seed, pub)
    return {
        "payloadType": PAYLOAD_TYPE,
        "payload": base64.standard_b64encode(payload).decode("ascii"),
        "signatures": [{"keyid": keyid, "sig": sig.hex()}],
    }


def sign_demo(statement: dict[str, Any]) -> dict[str, Any]:
    """Sign with the published demo key. Cannot be production-valid: DEMO_KEY_ID
    is never a production key, and no other private key exists in the repo."""
    return sign_ed25519(statement, _DEMO_SEED, DEMO_KEY_ID)


def default_trust_store() -> dict[str, Any]:
    """Verification trust store. `production_keys`/`isolation_keys` are populated
    ONLY from AERS_EXTERNAL_TRUST_STORE and ONLY when that path resolves OUTSIDE
    this repository — a "trusted" file inside a writable repo is not a boundary.
    With no external store, there are no production keys, so nothing this repo can
    sign is production-valid."""
    store: dict[str, Any] = {"demo_keys": {DEMO_KEY_ID: DEMO_PUBLIC_HEX}, "production_keys": {}, "isolation_keys": {}}
    external = os.environ.get("AERS_EXTERNAL_TRUST_STORE")
    if external:
        path = Path(external).resolve()
        try:
            repo = find_repo_root().resolve()
            inside = str(path).startswith(str(repo) + os.sep)
        except Exception:
            inside = False
        if path.exists() and not inside:
            data = load_json(path)
            for group in ("production_keys", "isolation_keys"):
                for keyid, keyhex in (data.get(group) or {}).items():
                    store[group][str(keyid)] = str(keyhex)
    return store


# ---------------------------------------------------------------------------
# Immutable candidate handoff (unchanged shape; digests bind the attestation).
# ---------------------------------------------------------------------------
def _policy_digest(repo: Path, ref: str) -> str:
    materials: dict[str, str | None] = {}
    for rel in POLICY_FILES:
        try:
            materials[rel] = sha256_bytes(read_file_at_ref(repo, ref, rel))
        except ValueError:
            materials[rel] = None
    return sha256_text(canonical_json(materials))


def _repo_identity(repo: Path) -> str:
    result = run_git(repo, ["remote", "get-url", "origin"], check=False)
    return result.stdout.strip() or repo.resolve().name


def build_handoff(repo: Path, feature_id: str, task_id: str, candidate_ref: str,
                  author_report_path: Path, profile: str, contract_ref: str | None = None) -> dict[str, Any]:
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
# Attestation.
# ---------------------------------------------------------------------------
def make_attestation(handoff: dict[str, Any], verdict: str, reason_codes: list[str],
                     verifier_identity: str, trust_domain: str = "offline-demo",
                     ttl_seconds: int = 3600, nonce: str | None = None,
                     signer_seed: bytes | None = None, keyid: str | None = None) -> dict[str, Any]:
    """Build and sign an attestation. Defaults to the demo signer. A production
    verifier passes its own private seed/keyid (held in its trust domain)."""
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
            "nonce": nonce or hashlib.sha256(canonical_json(handoff).encode() + now.isoformat().encode()).hexdigest()[:16],
        },
    }
    if signer_seed is not None:
        return sign_ed25519(statement, signer_seed, keyid or "external-production-key")
    return sign_demo(statement)


def _now_dt(now_iso: str | None) -> datetime:
    if now_iso:
        return datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def verify_attestation(envelope: dict[str, Any], handoff: dict[str, Any],
                       trust_store: dict[str, Any] | None = None, now_iso: str | None = None,
                       allow_untrusted_production_roots: bool = False) -> dict[str, Any]:
    """Verify a DSSE/Ed25519 attestation against the immutable handoff. Fail-closed.

    `production_valid` is True ONLY when: the Ed25519 signature verifies under a
    PRODUCTION public key that came from a trusted (non-caller, out-of-repo)
    store, AND every digest binding holds, AND it has not expired, AND the verdict
    is VERIFIED. A caller-supplied trust store is treated as untrusted: its
    production keys are ignored unless `allow_untrusted_production_roots=True`
    (explicit test-only escape hatch)."""
    caller_supplied = trust_store is not None
    store = trust_store if caller_supplied else default_trust_store()
    reasons: list[str] = []
    result: dict[str, Any] = {"valid": False, "production_valid": False, "verdict": None, "keyid": None,
                              "trust_domain": None, "reasons": reasons}

    try:
        payload = base64.standard_b64decode(envelope["payload"])
        sig_entry = envelope["signatures"][0]
        keyid = sig_entry["keyid"]
        presented_sig = bytes.fromhex(sig_entry["sig"])
    except (KeyError, IndexError, ValueError):
        reasons.append("MALFORMED_ENVELOPE")
        return result
    result["keyid"] = keyid

    demo_keys = dict(store.get("demo_keys", {}))
    production_keys = dict(store.get("production_keys", {}))
    all_keys = {**demo_keys, **production_keys}
    key_hex = all_keys.get(keyid)
    if key_hex is None:
        reasons.append("UNKNOWN_SIGNING_KEY")
        return result

    if not ed.checkvalid(presented_sig, _pae(envelope.get("payloadType", PAYLOAD_TYPE), payload), bytes.fromhex(key_hex)):
        reasons.append("SIGNATURE_MISMATCH")
        return result

    statement = json.loads(payload)
    predicate = statement.get("predicate", {})
    result["verdict"] = predicate.get("verdict")
    result["trust_domain"] = predicate.get("trust_domain")

    # A production key only counts if it was NOT injected by an untrusted caller
    # (unless the explicit test-only escape hatch is set). This is what makes
    # local code unable to manufacture production_valid by choosing its own root.
    key_is_production = keyid in production_keys
    if key_is_production and caller_supplied and not allow_untrusted_production_roots:
        reasons.append("UNTRUSTED_CALLER_ROOT")
        key_is_production = False

    bindings = {
        "candidate_digest": handoff["candidate_sha"],
        "policy_digest": handoff["policy_digest"],
        "evidence_digest": handoff["author_evidence_digest"],
        "handoff_digest": handoff["handoff_digest"],
        "source_tree_digest": handoff["source_tree_digest"],
    }
    binding_ok = True
    for field, expected in bindings.items():
        if predicate.get(field) != expected:
            reasons.append(f"BINDING_MISMATCH:{field}")
            binding_ok = False

    fresh = True
    try:
        if _now_dt(now_iso) > datetime.fromisoformat(predicate["expires_at"].replace("Z", "+00:00")):
            reasons.append("ATTESTATION_EXPIRED")
            fresh = False
    except (KeyError, ValueError):
        reasons.append("MISSING_EXPIRY")
        fresh = False

    verdict_ok = predicate.get("verdict") == "VERIFIED"
    if not verdict_ok:
        reasons.append(f"VERDICT_{predicate.get('verdict')}")

    all_ok = binding_ok and fresh and verdict_ok and "UNTRUSTED_CALLER_ROOT" not in reasons
    result["valid"] = all_ok
    result["production_valid"] = all_ok and key_is_production
    if all_ok and not key_is_production and "UNTRUSTED_CALLER_ROOT" not in reasons:
        reasons.append("DEMO_TRUST_DOMAIN_ONLY")
    return result
