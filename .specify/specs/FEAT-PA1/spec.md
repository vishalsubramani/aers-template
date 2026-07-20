# FEAT-PA1 — Production-assurance layer

## Goal
Take AERS from a strong reference architecture to a defensible production-grade
standard by making every important trust claim **falsifiable, externally
verifiable, operationally adoptable, and hard for an autonomous agent to
bypass** — without weakening any existing control.

## Why an additive layer
The control-plane surface (`scripts/aers/**`, `.agents/**`, `.claude/**`,
`.github/workflows/**`, `aers.toml`, `evals/**`) is protected: both the harness
deny-list and the pre-tool hook block writes to it, and AERS's own constitution
forbids expanding permissions or modifying-and-relying-on a guardrail in the same
run. Rather than bypass those controls, this feature delivers the new capability
as an **additive package** (`scripts/aers_assure/**`, `assurance/**`,
`tests/aers_selftest/**`, `docs/**`) that reuses the engine read-only and never
mutates the control plane. The small set of in-place control-plane edits that
would strengthen defaults (e.g. `require_second_reviewer_r2 = true`) is delivered
as a **reviewed patch + ADR** for a human control-plane owner to apply — the AERS
dogfooding model. See `docs/adr/ADR-0001-additive-assurance-layer.md`.

## Deliverables
- External verifier reference (handoff + DSSE attestation + fail-closed verify).
- Adversarial benchmark (≥25 executable cases).
- Assurance profiles (Lite / Standard / High Assurance / Regulated).
- Compliance/maturity `assess` command.
- Evidence-linked assurance case + `assurance` command.
- Isolation truth model (five states; R2+ fails closed on ASSERTED).
- Structured, testable threat model.
- Evaluator-health suite.
- Non-destructive, idempotent migration/adoption path.

## Non-goals
No production verifier is deployed here (that is external by design). This layer
never issues VERIFIED and never marks an externally-dependent control PASS from
inside the repository.

## Verification
`make verify` plus `make benchmark`, `make assess`, `make assurance`,
`make threat-model`, `make evaluator-health`, and the assurance-layer self-tests
under `tests/aers_selftest/`.
