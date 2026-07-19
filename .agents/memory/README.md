# Memory

- `.aers-runtime/` (ignored/external): active task state, run logs, hypotheses, handoffs
- `.agents/memory/quarantine/`: proposed durable lessons; not auto-loaded
- `.agents/memory/active/`: curated signed lessons only
- `docs/adr/`: durable architecture decisions
- `.specify/specs/`: feature intent and decisions

Do not create a parallel source of truth. Use `python3 scripts/aers.py memory-propose` and a distinct curator
for promotion. Active records are individually hashed and indexed; expiration is enforced by lint.
