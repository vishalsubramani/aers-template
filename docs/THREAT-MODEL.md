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

## Autonomous-agent failure modes

Beyond adversarial threats, an autonomous agent fails in three characteristic ways even with benign intent.
AERS is structured to contain each one — not by asking the agent to try harder, but by architecture:

| Failure mode | What it looks like | Structural containment |
|---|---|---|
| **Agentic laziness** — declaring done early | Claims success without doing the work; skips edge cases; "tests pass" without a test that could fail | Acceptance criteria mapped to fresh evidence; the differential gate (a new test must fail on base); author verification runs the real commands from the exact candidate |
| **Self-preferential bias** — grading its own work | Confirms its own output; a reviewer that is the same context as the author rubber-stamps | AUTHOR_READY ≠ VERIFIED; deterministic audit before any model review; an independent reviewer (and a second, different-harness reviewer for R2) in a separate context; the external verifier trust domain |
| **Goal drift** — losing the original constraints | Scope creep across a long context; the task quietly becomes a different task | Fresh process per task; contracts read at an immutable pinned ref; the scope gate diffs against the original write scope; typed contracts constrain, prose only explains |

The design lesson: parallelize intelligence freely, but give every verification an *independent* context and an
*immutable* reference. A single long-lived context that plans, implements, and grades itself exhibits all three.
