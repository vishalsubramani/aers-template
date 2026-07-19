# Repository Invariants

| ID | Property that must remain true | Executable enforcement | Owner |
|---|---|---|---|
| INV-001 | Control-plane changes cannot self-activate in the author run | scope policy + protected workflow | Agent platform |
| INV-002 | Local processes cannot issue `VERIFIED` | attestation policy | Security |
| INV-003 | Implementer cannot modify tests or task contracts | immutable role + scope gate | Engineering |

Replace examples with repository-specific invariants. Every load-bearing invariant should point to a check.
