# Proposed control-plane changes (apply under the dogfooding workflow)

These are the **protected** in-place strengthenings identified by the
production-assurance program. They are delivered here as a reviewed changeset —
NOT applied by the run that proposed them — because AERS forbids an execution from
modifying a guardrail and then relying on it in the same run (ADR-0004). A human
control-plane owner applies them under elevated (R3-class) handling: dedicated
task contract, independent review of the exact candidate, no same-run activation,
and recorded rollback.

## Changes

### 1. Default `require_second_reviewer_r2 = true` (Standard+/High Assurance)
- **File:** `aers.toml` (protected)
- **Patch:** `second-reviewer-default.patch`
- **Why:** R2 work should fail closed without a second, different-harness reviewer
  by default. The mechanism already exists in `scripts/loop.py`; this flips the
  default from opt-in to opt-out.
- **Rollback:** revert the one-line change; behavior returns to opt-in.
- **Evidence:** `evidence-bundle.json` (this directory).

### 2. Integrate the isolation truth model into `author_verify`
- **File:** `scripts/aers/verify.py` (protected)
- **How:** replace the `_network_prefix()` boolean with
  `aers_assure.isolation.gate_author_ready(risk_tier)`; refuse AUTHOR_READY when
  `allowed` is False (R2+ must be ≥ `EXTERNALLY_ATTESTED_ISOLATED`). See
  `verify-isolation-integration.md`.
- **Rollback:** revert to the prior `_network_prefix()` gate.

### 3. Add reviewer independence metadata to the reviewer schema
- **File:** `.agents/schemas/reviewer-report.schema.json` (protected)
- **How:** adopt `assurance/schemas/reviewer-independence.schema.json` as the
  reviewer report shape; `loop.validate_reviewer` additionally rejects a report
  whose `independence.context_id` equals the author context.
- **Rollback:** revert the schema; the base reviewer binding still applies.

## Applying

1. Open a dedicated feature/task contract for the control-plane change.
2. `git apply docs/proposed-control-plane-change/second-reviewer-default.patch`
   (control-plane owner, not an autonomous run).
3. Run `make verify` and `make assure`; the assurance layer's `assess` will flip
   `CTRL-SECOND-REVIEWER-R2` from `PARTIAL` to `PASS`.
4. Obtain independent review of the exact candidate and external verifier
   evidence, then merge.
