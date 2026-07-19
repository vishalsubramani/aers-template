# Memory

- `.aers-runtime/` (ignored/external): active task state, run logs, hypotheses, handoffs
- `.agents/memory/quarantine/`: proposed durable lessons; not auto-loaded
- `.agents/memory/active/`: curated signed lessons only
- `docs/adr/`: durable architecture decisions
- `.specify/specs/`: feature intent and decisions

Do not create a parallel source of truth. Use `python3 scripts/aers.py memory-propose` and a distinct curator
for promotion. Active records are individually hashed and indexed; expiration is enforced by lint.

Recall closes the loop: context packets automatically include active lessons whose `scope` globs intersect
the task's write scope — via a tracked path both match, or at the pattern level so creation tasks recall
lessons for files that do not exist yet — plus records one hop away via `links` (associative recall).
At most 8 lessons are recalled, newest first. Selection is deterministic glob intersection — auditable and
reproducible, never similarity scoring. Recall fails closed: only records inside `active/` with status
`active`, an index-matching sha256, and a recomputed content hash are eligible; quarantined or tampered
records are never loaded.
