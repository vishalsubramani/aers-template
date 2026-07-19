# Operating Model

## Trust domains

| Domain | May read | May write | May issue |
|---|---|---|---|
| Author agent | approved context and public tests | exact task scope | candidate changes |
| Orchestrator | immutable task definitions, author workspace | external runtime ledger and candidate commits | `AUTHOR_READY` request |
| External verifier | exact candidate artifact, private checks | verifier evidence store | `VERIFIED` attestation |
| Release controller | verified immutable artifact | deployment system | release record |
| Memory curator | quarantined proposals and evidence | signed active memory | promotion record |

The same autonomous identity may not collapse these domains for high-risk work.

## State machine

`INTAKE → CLASSIFY → SPECIFY → PLAN → PLAN_VERIFY → REGISTER → CONTEXT → IMPLEMENT → SCOPE_GATE → CANDIDATE_COMMIT → AUTHOR_VERIFY → AUDIT → REVIEW → AUTHOR_READY → EXTERNAL_VERIFY → VERIFIED → MERGE → RELEASE → OBSERVE → LEARN`

Gate failures return to the nearest correctable state. Repeated failures, authorization gaps, or integrity
failures enter `SAFE_STOP`. Runtime state is held outside the repository in an append-only ledger.

## Spec modes

- **S0 — Change brief:** tiny, low-risk, local changes where misinterpretation is cheap.
- **S1 — Standard feature:** normal behavior changes with spec, plan, task graph, and typed contract.
- **S2 — System change:** cross-service, security, data, migration, infrastructure, or reliability changes;
  requires ADR/threat model/migration/runbook artifacts as applicable.

Risk tier and spec mode are independent. A small auth change can be R3/S0-sized but still non-autonomous.

## Separation of duties

- Orchestrator owns state, budgets, leases, routing, and cleanup—not implementation.
- Explorer and reviewers are read-only.
- Architect writes specs and decisions before execution.
- Implementer writes only source paths listed in an immutable task definition.
- Test author operates as a separate task and cannot alter implementation while reviewing it.
- Deterministic auditor runs before any model-based reviewer.
- External verifier owns hidden checks and attestation.

## Evidence packet

Every candidate records feature/task/run IDs; immutable base and candidate SHAs; contract hashes; changed
path and line counts; commands and results; network isolation mode; trajectory audit; reviewer findings;
residual risk; rollout/rollback; and evidence hashes. Logs are external and redacted by default.
