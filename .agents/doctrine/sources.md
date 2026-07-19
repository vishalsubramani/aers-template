# Source Register

The doctrine distills a small set of canonical bodies of engineering practice
into rules this repository enforces. This register keeps the distillation
attributable and reviewable: when a source materially updates, the
corresponding doctrine section is re-examined through a control-plane PR —
doctrine never silently drifts from, or lags, its sources.

External sources are a library; this repository's doctrine, ADRs, and gates
are the law. Agents cite doctrine IDs, not URLs.

| Source | What it anchors here |
|---|---|
| *Software Engineering at Google* (Winters, Manshreck, Wright) — https://abseil.io/resources/swe-book | Code health over cleverness (AX-19/20), testing discipline (AX-16), dependency management (AX-21, DF-04), review culture (reviewer role), sustainable change (AX-02/15) |
| Amazon Builders' Library — https://aws.amazon.com/builders-library/ | Timeouts/retries/jitter (PAT-05), idempotency (AX-10, PAT-06), overload management and static stability (PAT-20), deployment safety (AX-15), operational simplicity (AX-01) |
| Google SRE books (SRE, SRE Workbook, Building Secure & Reliable Systems) — https://sre.google/books/ | SLOs and error budgets (AX-22), observability as behavior (AX-14, PAT-13), toil elimination (DF-06), production readiness (quality gates, runbooks) |
| Azure Architecture Center / Well-Architected patterns — https://learn.microsoft.com/azure/architecture/ | The pattern-catalog approach itself and several reliability patterns (PAT-08 graceful degradation, PAT-09 caching, PAT-11 outbox, PAT-15 health probes) |
| OWASP ASVS, Cheat Sheet Series, SCVS, LLMSVS — https://owasp.org/ | Executable security requirements: the security baseline ADR adopts an ASVS level; `make security` implements its checks; supply chain per SCVS (AX-21); LLM-specific controls for agent-facing surfaces |
| Martin Fowler's architecture writing — https://martinfowler.com/architecture/ | Architecture as contextual trade-off, not universal answers — the framing of every DF-* entry and the design interrogation |
| ADR practice (Nygard) | The decision-record shape in `docs/adr/ADR-0000-template.md` |

Secondary indexes (useful for exploration, never authority): Awesome
Scalability, System Design Primer.
