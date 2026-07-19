# Context Policy

Build a task packet from primary evidence: typed contract, exact symbols, relevant tests, contracts, ADRs,
recent failures, and commands. Preserve full artifacts externally and reference them by hash. Manage
pressure in this order: drop stale output, mask irrelevant observations, offload large artifacts, start a
fresh role/task process, then summarize only when unavoidable. Mark summaries as lossy.

Do not depend on the agent remembering to discover universally required constraints. Keep those in
`AGENTS.md`; keep specialized procedures here and evaluate retrieval success on repository tasks.
