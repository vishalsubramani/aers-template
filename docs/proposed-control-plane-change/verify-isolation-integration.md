# Integrating the isolation truth model into `author_verify`

The isolation gate currently lives in the additive layer
(`scripts/aers_assure/isolation.py`) and is enforced by the benchmark and
self-tests. To enforce it in-place during author verification, apply the
following change to `scripts/aers/verify.py` (protected — control-plane owner
only).

## Sketch

At the top of `author_verify`, after resolving `risk_tier` from the feature
contract:

```python
from aers_assure.isolation import gate_author_ready  # sibling package on sys.path

risk_tier = bundle.feature["risk_tier"]
iso = gate_author_ready(risk_tier)
integrity["isolation"] = iso
if not iso["allowed"] and not degraded:
    fatal.append(iso["reason"])  # R2+ fails closed on ASSERTED-only isolation
```

Keep `_network_prefix()` for actually running commands under a namespace; the new
gate governs whether the *state* is strong enough for the risk tier, replacing the
prior all-or-nothing boolean.

## Test to add (protected test path — test_author role)

```python
def test_r2_author_verify_fails_closed_on_asserted_isolation(self):
    # With only AERS_NETWORK_ISOLATED=1 and no namespace, an R2 feature must not
    # reach AUTHOR_READY.
    ...
```

## Rollback

Revert `verify.py` to the prior `_network_prefix()`-only gate. No data migration.
