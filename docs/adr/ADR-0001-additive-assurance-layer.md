# ADR-0001: Deliver production assurance as an additive, non-control-plane layer

- **Status:** accepted
- **Date:** 2026-07-19
- **Doctrine:** AX (smallest correct, secure, reversible change), PAT (immutable
  reference + independent verification). Does not override any axiom.
- **Owners:** principal-architect / security

## Context

The production-assurance work (external verifier, adversarial benchmark,
compliance assessment, assurance case, isolation truth model, structured threat
model, evaluator health) needs new engine code, data, and tests. The natural
home for engine code is `scripts/aers/**` and for data `.agents/**` — both are
**protected control-plane surfaces**. The harness deny-list and the pre-tool hook
block writes there, and AERS's constitution forbids expanding permissions to
unblock oneself and forbids modifying-and-relying-on a guardrail in the same run.

## Constraints

- Do not weaken or bypass any existing control.
- Do not modify the control plane and then rely on the modified control plane.
- Preserve backward compatibility; installation stays non-destructive.
- All new behavior must run offline with safe stubs.

## Quality attributes

Optimizes **trustworthiness** and **reviewability**; deliberately sacrifices the
convenience of editing the engine in place.

## Options considered

1. **Edit the control plane in place** (flip defaults, extend `scripts/aers/`,
   add `.agents/` data). Highest task fidelity, but requires an autonomous/agent
   execution to edit the guardrails it runs under — precisely the posture AERS
   warns against — and would have to defeat the deny-list.
2. **Additive layer** (`scripts/aers_assure/**`, `assurance/**`,
   `tests/aers_selftest/**`, `docs/**`) that reuses the engine read-only, plus a
   reviewed patch for the few in-place default changes. Lower friction to review,
   nothing bypassed.

## Selected option

Option 2. The assurance engine lives in `scripts/aers_assure/` (a new,
unprotected package) with entrypoint `scripts/assure.py`; data lives in a new
top-level `assurance/`; tests under `tests/aers_selftest/`. The small set of
in-place control-plane strengthenings (e.g. `require_second_reviewer_r2 = true`,
integrating the isolation gate into `verify.py`) is delivered as a **reviewed
patch + this ADR** under `docs/proposed-control-plane-change/` for a human
control-plane owner to apply out-of-band.

## Benefits

- No guardrail is modified-and-relied-upon in the same execution.
- The new layer is additive and reversible with a clean `git revert`.
- `make verify` gains author-side assurance gates without weakening prior checks.

## Costs

- Two engine packages (`aers` and `aers_assure`) instead of one.
- Default strengthenings require a separate human-applied control-plane change.

## Consequences

The repository can be assessed, benchmarked, and attested against without ever
granting the authoring agent write access to its own guardrails. The dogfooding
workflow (ADR-0004) governs the eventual in-place changes.
