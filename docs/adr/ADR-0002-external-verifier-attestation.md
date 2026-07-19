# ADR-0002: DSSE-style bound attestation for the external verifier

- **Status:** accepted
- **Date:** 2026-07-19
- **Doctrine:** PAT (immutable reference), data-doctrine (content-addressed
  integrity). No override.
- **Owners:** security

## Context

AERS requires that `VERIFIED` be issued only by a separate, protected
verification trust domain, and that repository-local code can never mint a
production-valid `VERIFIED`. We need a concrete, testable attestation format that
resists result tampering, candidate/policy/evidence substitution, and stale
replay, while remaining understandable and replaceable.

## Constraints

- Offline-demonstrable without pretending to provide production isolation.
- No production signing key may live in the repository.
- Must bind the exact candidate, policy digest, and author-evidence digest.

## Quality attributes

Integrity and non-repudiation of the verdict; deliberately not confidentiality
(the attestation is meant to be shared).

## Options considered

1. **Ad-hoc JSON with a hash field.** Simple, but easy to get subtly wrong
   (unbound payloads, replay).
2. **In-toto/DSSE-compatible envelope** over a canonical statement, with the
   verdict binding candidate/policy/evidence digests, an expiry, and a nonce.
   Recognized structure, swappable signer.

## Selected option

Option 2. `scripts/aers_assure/verifier.py` builds an immutable candidate
**handoff** (repo identity, candidate SHA, source-tree digest, feature/task
contract digests, policy digest, author-evidence digest, requested profile,
`handoff_digest`) and a **DSSE envelope** over an in-toto statement. Verification
recomputes the MAC, checks every digest binding, checks freshness, and scopes
trust: `production_valid` is True only when the signing key is a **production**
key in the trust store. The repository trust store has **no** production keys and
the demo key is explicitly non-production, so local code cannot produce a
production-valid `VERIFIED`.

## Benefits

- Tamper, substitution, and stale replay are each detected and unit-tested.
- The signer is replaceable: production swaps in a real private key held in the
  verifier's own trust domain; the repo only ever holds the public/demo side.

## Costs

- HMAC demo signer is symmetric; production deployments should use asymmetric
  signatures (documented as a production step, not a repo capability).

## Consequences

The "local cannot VERIFIED" invariant is now a structural property with a
failing-path test (`test_verifier.py`) and benchmark cases (`BENCH-ATT-00x`).
