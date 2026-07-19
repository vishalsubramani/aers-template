# Architecture Context

Describe THIS repository's system boundaries, trust boundaries, data flows, public contracts,
dependency direction, reliability model, consistency choices, retries/idempotency, backpressure,
timeouts, degradation, and authoritative ADRs. Enforce critical dependency rules with architecture
tests wired into `make check`.

The universal rules live in `.agents/doctrine/` (axioms `AX-*`, data `DD-*`, patterns `PAT-*`);
the repository-specific application of them lives in `docs/adr/` starting with the foundation ADRs
(ADR-0001 architecture baseline, ADR-0002 data baseline) created at kickoff. This file summarizes
the current state those decisions produced.
