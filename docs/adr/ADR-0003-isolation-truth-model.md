# ADR-0003: Isolation truth model replaces asserted-boolean isolation

- **Status:** accepted
- **Date:** 2026-07-19
- **Doctrine:** "never manufacture confidence"; environment assertions are not
  evidence. No override.
- **Owners:** sre / security

## Context

The prior verification path treated `AERS_NETWORK_ISOLATED=1` or a policy
requirement as if it meant isolation actually held. An environment variable is an
assertion, not proof. High-risk work must not advance on an assertion.

## Selected option

`scripts/aers_assure/isolation.py` defines five explicit states —
`PROVEN_ISOLATED`, `EXTERNALLY_ATTESTED_ISOLATED`, `ASSERTED_ISOLATED`,
`NOT_ISOLATED`, `UNKNOWN` — and a per-risk-tier minimum:

| Tier | Minimum state for AUTHOR_READY |
|------|-------------------------------|
| R0/R1 | `ASSERTED_ISOLATED` |
| R2 | `EXTERNALLY_ATTESTED_ISOLATED` |
| R3 | `PROVEN_ISOLATED` |

`PROVEN_ISOLATED` requires an actual demonstration (a user network namespace),
`EXTERNALLY_ATTESTED_ISOLATED` requires an out-of-band attestation token, and a
bare boolean is only `ASSERTED_ISOLATED`. Production `VERIFIED` never rests on a
repository-local isolation claim. The gate fails closed.

## Benefits

- R2 and above fail closed on asserted-only isolation (`BENCH-ISO-001/002`,
  `test_isolation.py`).
- Documentation can now distinguish demo safety from production security honestly.

## Costs

- A host without a namespace mechanism cannot reach `PROVEN` locally; such work
  must run on trusted infrastructure that supplies an attestation.

## Consequences

Integrating this gate into `scripts/aers/verify.py` is a protected control-plane
change delivered as the reviewed patch in `docs/proposed-control-plane-change/`.
Until applied in-place, the model is enforced by the assurance layer and its
benchmark/self-tests.
