# Agentic Development Threat Model

Protect: source integrity, tests/evals, specifications, secrets/data, verifier identity, release artifacts,
memory/skills, logs, and production systems.

Assume threats from indirect prompt injection, malicious issues/docs/dependencies/skills, compromised model or
tool output, role escalation through writable state, test/eval tampering, history/internet solution retrieval,
hardcoded expectations, shell/path/symlink bypass, secret exfiltration, poisoned memory, trace leakage, evaluator
overfitting, CI token abuse, and malicious or accidental production changes.

Primary controls: capability reduction, Rule of Two, immutable contracts, exact scopes, OS sandbox, egress deny,
external ledger, protected oracle, deterministic audit, external attestation, signed supply chain, staged release,
and revocable curated memory.
