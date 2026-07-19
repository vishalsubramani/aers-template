# Spec-Driven Workflow

Use S0 when ambiguity is cheap, S1 for ordinary behavior changes, and S2 for system/security/data changes.
Human-readable artifacts explain the problem and tradeoffs; `feature.contract.json` and `tasks.json` compile
intent into gates. Every acceptance criterion has an ID and evidence method. Review the plan before code,
and verify task-by-task to prevent error propagation.
