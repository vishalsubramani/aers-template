# Integrating the isolation truth model into `author_verify`

The isolation gate lives in the additive layer
(`scripts/aers_assure/isolation.py`) and is enforced by the benchmark and
self-tests. To enforce it in-place during author verification, apply this change
to `scripts/aers/verify.py` (protected — control-plane owner only, separate human
PR per ADR-0004). The harness deny-list blocks the authoring run from making it.

## Change to `author_verify`

After resolving the bundle and before running commands, replace reliance on the
`AERS_NETWORK_ISOLATED` boolean with the truth-model gate, binding the candidate
and policy:

```python
from aers_assure.isolation import gate_author_ready  # sibling package on sys.path

risk_tier = bundle.feature["risk_tier"]
iso = gate_author_ready(
    risk_tier,
    bindings={"candidate": candidate_sha, "policy_digest": scope.contract_hashes.get("tasks", "")},
)
integrity["isolation"] = iso
# R2+ must be >= EXTERNALLY_ATTESTED_ISOLATED; R3 must be PROVEN_ISOLATED.
# A bare AERS_NETWORK_ISOLATED=1 is only ASSERTED and is rejected for R2/R3.
if not iso["allowed"] and not degraded:
    fatal.append(iso["reason"])
```

Keep `_network_prefix()` for actually running commands inside a demonstrated
namespace; the new gate governs whether the isolation *state* is strong enough
for the risk tier. Because `gate_author_ready` treats an unsigned/forged
`AERS_ISOLATION_ATTESTATION` as not-attested (only an Ed25519-signed, unexpired,
bound token from an issuer key in the out-of-repo trust store counts), neither a
boolean nor a fake token can lift an R2 task to AUTHOR_READY.

## Integration test to add (protected test path — `test_author` role)

```python
def test_r2_author_verify_fails_closed_on_asserted_isolation(self):
    # Build an R2 feature pack; with only AERS_NETWORK_ISOLATED=1 and no
    # namespace/attestation, author_verify must NOT return AUTHOR_READY.
    env = {"AERS_NETWORK_ISOLATED": "1", "AERS_DISABLE_ISOLATION_PROBE": "1"}
    report = author_verify(repo, "FEAT-R2", "T-1", base, out, env=env)
    self.assertNotEqual(report["verdict"], "AUTHOR_READY")
    self.assertTrue(any("ISOLATION_INSUFFICIENT" in r for r in report["fatal_reasons"]))

def test_r2_author_verify_rejects_forged_isolation_token(self):
    env = {"AERS_ISOLATION_ATTESTATION": "forged", "AERS_DISABLE_ISOLATION_PROBE": "1"}
    report = author_verify(repo, "FEAT-R2", "T-1", base, out, env=env)
    self.assertNotEqual(report["verdict"], "AUTHOR_READY")
```

## Rollback

Revert `verify.py` to the prior `_network_prefix()`-only gate. No data migration.
