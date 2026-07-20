# ADR-0004: AERS governs changes to its own control plane (dogfooding)

- **Status:** accepted
- **Date:** 2026-07-19
- **Doctrine:** source-of-truth order (protected controls outrank task prose);
  "control-plane change is a stop condition." No override.
- **Owners:** security / principal-architect

## Context

Changes to schemas, policies, audit logic, the verifier protocol, memory
promotion, task orchestration, benchmark definitions, or release controls are the
highest-risk changes in the repository. They must not be made by the same
execution that then relies on them, and they must not be self-approved.

## Selected option

Control-plane changes receive **elevated (R3-class) handling**:

1. Immutable base commit and a dedicated task contract.
2. Explicit, non-blanket write scope that does not silently reach guardrail
   surfaces (enforced by `contracts.validate_tasks`).
3. Differential or mutation/tamper testing where applicable
   (`assurance/benchmark` provides tamper tests for critical controls).
4. Independent review of the exact candidate (candidate-bound reviewer report).
5. **No same-run policy activation** (`ConfigChange` hook blocks changes during a
   run; policies are read at the immutable contract ref, not the working tree).
6. External or simulated-external verifier evidence
   (`scripts/aers_assure/verifier.py`).
7. Recorded rollback instructions.

The in-place strengthenings this program identified (flip
`require_second_reviewer_r2` to `true`; integrate the isolation gate into
`verify.py`; add reviewer independence metadata to the reviewer schema) are
staged in `docs/proposed-control-plane-change/` as a reviewed patch for a human
control-plane owner to apply under this workflow — not applied by the authoring
run that proposed them.

## Consequences

The additive layer (ADR-0001) can be developed and merged normally; the protected
strengthenings go through this elevated path. `docs/proposed-control-plane-change/`
includes a representative evidence bundle for one such change.
