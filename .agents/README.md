# Canonical Agent Control Plane

`.agents/` is vendor-neutral and authoritative. Tool-specific adapters may reference it but may not
fork its meaning.

- `constitution.md` — non-negotiable principles
- `operating-model.md` — states, roles, trust domains, and evidence
- `context/` — curated repository facts and generated navigation
- `policies/` — machine-readable authority and risk rules
- `schemas/` — typed contracts and evidence formats
- `roles/` — role-specific capability contracts
- `skills/` — reviewed procedures with a lockfile
- `memory/` — quarantine and active curated knowledge
- `evals/` — public smoke suite and private-eval interface
- `telemetry/` — trajectory event conventions and fault taxonomy
- `trusted/` — contracts for infrastructure that must live outside the author domain
