"""External verifier reference: immutable candidate handoff, DSSE-style
Ed25519 attestation, and fail-closed verification with root-pinned production trust.

TRUST MODEL (three independent barriers make production_valid unreachable from
inside the authoring domain):

  1. No production PRIVATE key exists here (only a published demo keypair whose
     public key is a demo key, never production).

  2. Production public keys are NOT trusted because of where a file lives. They
     are accepted ONLY from a trust bundle that is itself Ed25519-signed by a
     PINNED ROOT key (`_PINNED_ROOT_KEYS`, a source constant a deployment sets via
     a control-plane change; empty in this template). An authoring agent can point
     `AERS_TRUST_BUNDLE` at any file it likes, but cannot forge the root signature,
     so it cannot introduce a production root. Caller-supplied trust stores are
     never treated as production authority.

  3. `production_valid` additionally requires an AUDITED signature backend. The
     dependency-free pure-Python Ed25519 in `_ed25519.py` is used for demo
     verification only; production requires an audited library (e.g. `cryptography`)
     on the verifier side. In this environment no audited backend is present, so
     production_valid is structurally unreachable — matching "no production
     verifier is deployed."

Verification also recomputes the canonical handoff digest and validates the DSSE
payload type, in-toto statement/predicate types, subject, and profile, so no
handoff field can be altered while reusing a signed attestation.
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
from aers.util import canonical_json, load_json, sha256_bytes, sha256_text, utc_now
from . import _ed25519 as ed

# --- Signature backend: prefer an audited library; production needs it. --------
try:  # pragma: no cover - environment dependent
    import _cffi_backend  # noqa: F401  cryptography's native dep; its absence (or a
    # broken build) means no audited backend — checking first avoids a noisy panic.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    def _verify_sig(sig: bytes, msg: bytes, pub: bytes) -> bool:
        try:
            Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg)
            return True
        except (InvalidSignature, ValueError):
            return False
    AUDITED_BACKEND = True
    BACKEND_NAME = "cryptography-ed25519"
except BaseException:  # audited lib absent OR broken (e.g. panics) -> reference, demo-only
    # BaseException on purpose: a broken native binding can raise a non-Exception
    # (pyo3 PanicException); we must still fall back to the reference verifier.
    def _verify_sig(sig: bytes, msg: bytes, pub: bytes) -> bool:
        return ed.checkvalid(sig, msg, pub)
    AUDITED_BACKEND = False
    BACKEND_NAME = "reference-pure-python"

# Pinned production roots. EMPTY in this template (no production verifier). A
# deployment sets these to its operator root public key(s) via a control-plane
# change; only a trust bundle signed by one of these roots can introduce
# production/isolation keys.
_PINNED_ROOT_KEYS: dict[str, str] = {}

DEMO_KEY_ID = "aers-offline-demo-ed25519-v1"
_DEMO_SEED = hashlib.sha256(b"AERS-OFFLINE-DEMO-SEED-NOT-FOR-PRODUCTION").digest()
DEMO_PUBLIC_HEX = ed.publickey(_DEMO_SEED).hex()

PAYLOAD_TYPE = "application/vnd.aers.verification+json"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://aers.dev/attestation/verification/v1"
BUNDLE_TYPE = "application/vnd.aers.trust-bundle+json"
VALID_VERDICTS = {"VERIFIED", "REJECTED", "INFRASTRUCTURE_ERROR"}

POLICY_FILES = [
    ".agents/policies/protected-paths.json", ".agents/policies/verification-policy.json",
    ".agents/policies/autonomy-policy.json", ".agents/policies/capability-policy.json",
    ".agents/policies/command-policy.json", ".agents/policies/release-policy.json",
    ".agents/policies/memory-policy.json", ".agents/policies/skills-policy.json", "aers.toml",
]


# --- DSSE primitives -----------------------------------------------------------
def _pae(payload_type: str, payload: bytes) -> bytes:
    return b"DSSEv1 %d %s %d %s" % (len(payload_type), payload_type.encode("utf-8"), len(payload), payload)


def _sign(payload_type: str, statement: dict[str, Any], seed: bytes, keyid: str) -> dict[str, Any]:
    payload = canonical_json(statement).encode("utf-8")
    sig = ed.signature(_pae(payload_type, payload), seed, ed.publickey(seed))
    return {"payloadType": payload_type, "payload": base64.standard_b64encode(payload).decode("ascii"),
            "signatures": [{"keyid": keyid, "sig": sig.hex()}]}


def sign_demo(statement: dict[str, Any]) -> dict[str, Any]:
    return _sign(PAYLOAD_TYPE, statement, _DEMO_SEED, DEMO_KEY_ID)


# --- Root-pinned trust bundle --------------------------------------------------
def sign_trust_bundle(keys: dict[str, Any], root_seed: bytes, root_keyid: str) -> dict[str, Any]:
    """Sign a trust bundle ({production_keys, isolation_keys}) with a ROOT key.
    Used by a platform operator (and tests); the root private key is not in the repo."""
    return _sign(BUNDLE_TYPE, {"keys": keys}, root_seed, root_keyid)


def load_trust_bundle(path: str | None, pinned_roots: dict[str, str]) -> dict[str, Any]:
    """Return the bundle's keys ONLY if it is signed by a pinned root; else {}."""
    if not path or not pinned_roots:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        envelope = load_json(p)
        payload = base64.standard_b64decode(envelope["payload"])
        keyid = envelope["signatures"][0]["keyid"]
        sig = bytes.fromhex(envelope["signatures"][0]["sig"])
    except Exception:
        return {}
    root_hex = pinned_roots.get(keyid)
    if root_hex is None:
        return {}
    if not ed.checkvalid(sig, _pae(envelope.get("payloadType", BUNDLE_TYPE), payload), bytes.fromhex(root_hex)):
        return {}
    return json.loads(payload).get("keys", {})


def default_trust_store(pinned_roots: dict[str, str] | None = None) -> dict[str, Any]:
    """Demo keys always; production/isolation keys ONLY from a root-signed bundle."""
    roots = _PINNED_ROOT_KEYS if pinned_roots is None else pinned_roots
    store: dict[str, Any] = {"demo_keys": {DEMO_KEY_ID: DEMO_PUBLIC_HEX}, "production_keys": {}, "isolation_keys": {}}
    bundle = load_trust_bundle(os.environ.get("AERS_TRUST_BUNDLE"), roots)
    for group in ("production_keys", "isolation_keys"):
        for kid, kh in (bundle.get(group) or {}).items():
            store[group][str(kid)] = str(kh)
    return store


# --- Immutable candidate handoff ----------------------------------------------
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


def _handoff_digest(core: dict[str, Any]) -> str:
    return sha256_text(canonical_json({k: v for k, v in core.items() if k != "handoff_digest"}))


def build_handoff(repo: Path, feature_id: str, task_id: str, candidate_ref: str,
                  author_report_path: Path, profile: str, contract_ref: str | None = None) -> dict[str, Any]:
    candidate_sha = rev_parse(repo, candidate_ref)
    contract_sha = rev_parse(repo, contract_ref) if contract_ref else candidate_sha
    feature_path = f".specify/specs/{feature_id}/feature.contract.json"
    tasks_path = f".specify/specs/{feature_id}/tasks.json"
    source_digest = run_git(repo, ["rev-parse", f"{candidate_sha}^{{tree}}"]).stdout.strip()
    author_report = load_json(author_report_path)
    core = {
        "schema_version": 1, "repo_identity": _repo_identity(repo), "candidate_sha": candidate_sha,
        "source_tree_digest": source_digest, "feature_id": feature_id, "task_id": task_id,
        "feature_contract_digest": sha256_bytes(read_file_at_ref(repo, contract_sha, feature_path)),
        "task_contract_digest": sha256_bytes(read_file_at_ref(repo, contract_sha, tasks_path)),
        "policy_digest": _policy_digest(repo, contract_sha),
        "author_evidence_digest": sha256_text(canonical_json(author_report)),
        "requested_profile": profile, "created_at": utc_now(),
    }
    core["handoff_digest"] = _handoff_digest(core)
    return core


# --- Attestation ---------------------------------------------------------------
def make_attestation(handoff: dict[str, Any], verdict: str, reason_codes: list[str],
                     verifier_identity: str, trust_domain: str = "offline-demo",
                     ttl_seconds: int = 3600, nonce: str | None = None,
                     signer_seed: bytes | None = None, keyid: str | None = None) -> dict[str, Any]:
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"Invalid verifier verdict: {verdict}")
    now = datetime.now(timezone.utc)
    statement = {
        "_type": STATEMENT_TYPE, "predicateType": PREDICATE_TYPE,
        "subject": [{"name": handoff["repo_identity"], "digest": {"gitCommit": handoff["candidate_sha"]}}],
        "predicate": {
            "verdict": verdict, "handoff_digest": handoff["handoff_digest"],
            "candidate_digest": handoff["candidate_sha"], "source_tree_digest": handoff["source_tree_digest"],
            "policy_digest": handoff["policy_digest"], "evidence_digest": handoff["author_evidence_digest"],
            "profile": handoff["requested_profile"], "verifier_identity": verifier_identity,
            "trust_domain": trust_domain, "reason_codes": sorted(set(reason_codes)),
            "timestamp": now.isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z"),
            "nonce": nonce or hashlib.sha256(canonical_json(handoff).encode() + now.isoformat().encode()).hexdigest()[:16],
        },
    }
    if signer_seed is not None:
        return _sign(PAYLOAD_TYPE, statement, signer_seed, keyid or "external-production-key")
    return sign_demo(statement)


def _now_dt(now_iso: str | None) -> datetime:
    return datetime.fromisoformat(now_iso.replace("Z", "+00:00")) if now_iso else datetime.now(timezone.utc)


def verify_attestation(envelope: dict[str, Any], handoff: dict[str, Any],
                       trust_store: dict[str, Any] | None = None, now_iso: str | None = None,
                       pinned_roots: dict[str, str] | None = None) -> dict[str, Any]:
    """Verify a DSSE/Ed25519 attestation against the immutable handoff. Fail-closed.

    `production_valid` is True ONLY when every check below passes AND the signing
    key is a ROOT-PINNED production key AND an audited signature backend is in use.
    A caller-supplied trust store is never production authority; a filesystem
    location is never trust."""
    reasons: list[str] = []
    result: dict[str, Any] = {"valid": False, "production_valid": False, "verdict": None, "keyid": None,
                              "trust_domain": None, "backend": BACKEND_NAME, "reasons": reasons}
    authority = default_trust_store(pinned_roots)              # root-validated production keys
    prod_authority = authority["production_keys"]
    vstore = trust_store if trust_store is not None else authority
    verify_keys = {**dict(vstore.get("demo_keys", {})), **dict(vstore.get("production_keys", {})),
                   **dict(authority.get("demo_keys", {})), **prod_authority}

    if envelope.get("payloadType") != PAYLOAD_TYPE:
        reasons.append("WRONG_PAYLOAD_TYPE"); return result
    try:
        payload = base64.standard_b64decode(envelope["payload"])
        keyid = envelope["signatures"][0]["keyid"]
        presented_sig = bytes.fromhex(envelope["signatures"][0]["sig"])
    except (KeyError, IndexError, ValueError):
        reasons.append("MALFORMED_ENVELOPE"); return result
    result["keyid"] = keyid
    key_hex = verify_keys.get(keyid)
    if key_hex is None:
        reasons.append("UNKNOWN_SIGNING_KEY"); return result
    if not _verify_sig(presented_sig, _pae(PAYLOAD_TYPE, payload), bytes.fromhex(key_hex)):
        reasons.append("SIGNATURE_MISMATCH"); return result

    statement = json.loads(payload)
    predicate = statement.get("predicate", {})
    result["verdict"] = predicate.get("verdict")
    result["trust_domain"] = predicate.get("trust_domain")

    # Statement metadata must be the AERS types.
    if statement.get("_type") != STATEMENT_TYPE or statement.get("predicateType") != PREDICATE_TYPE:
        reasons.append("STATEMENT_TYPE_MISMATCH")

    # The handoff must be internally consistent: recompute its canonical digest.
    if _handoff_digest(handoff) != handoff.get("handoff_digest"):
        reasons.append("HANDOFF_DIGEST_MISMATCH")

    # Every signed field must bind to THIS handoff, including handoff_digest,
    # profile, and subject (so no handoff field can be swapped under a reused sig).
    bindings = {
        "candidate_digest": handoff["candidate_sha"], "policy_digest": handoff["policy_digest"],
        "evidence_digest": handoff["author_evidence_digest"], "handoff_digest": handoff["handoff_digest"],
        "source_tree_digest": handoff["source_tree_digest"], "profile": handoff["requested_profile"],
    }
    for field, expected in bindings.items():
        if predicate.get(field) != expected:
            reasons.append(f"BINDING_MISMATCH:{field}")
    subject = (statement.get("subject") or [{}])[0]
    if subject.get("name") != handoff["repo_identity"] or subject.get("digest", {}).get("gitCommit") != handoff["candidate_sha"]:
        reasons.append("SUBJECT_MISMATCH")

    try:
        if _now_dt(now_iso) > datetime.fromisoformat(predicate["expires_at"].replace("Z", "+00:00")):
            reasons.append("ATTESTATION_EXPIRED")
    except (KeyError, ValueError):
        reasons.append("MISSING_EXPIRY")
    if predicate.get("verdict") != "VERIFIED":
        reasons.append(f"VERDICT_{predicate.get('verdict')}")

    # Note (not fatal to `valid`, but to production): a caller supplied a root.
    caller_root_ignored = (trust_store is not None and keyid in dict(trust_store.get("production_keys", {}))
                           and keyid not in prod_authority)
    if caller_root_ignored:
        reasons.append("UNTRUSTED_CALLER_ROOT")

    all_ok = not reasons
    result["valid"] = all_ok
    is_root_production = keyid in prod_authority
    result["production_valid"] = all_ok and is_root_production and AUDITED_BACKEND
    if all_ok and not result["production_valid"]:
        if is_root_production and not AUDITED_BACKEND:
            reasons.append("REFERENCE_BACKEND_NOT_PRODUCTION")
        else:
            reasons.append("DEMO_TRUST_DOMAIN_ONLY")
    return result
