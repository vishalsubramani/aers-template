# Decision Frameworks

Architecture is contextual: "best practice" without context is cargo cult. For
the recurring forks below, agents state the context, apply the default, and
record the decision (foundation ADRs or a feature ADR) with an explicit
trigger to revisit. A recommendation without a named trade-off is not a
recommendation.

Every framework answer takes this shape (mirrored by `docs/adr/ADR-0000-template.md`):
context → constraints → quality attributes → options → selected option →
benefits → costs → failure modes → reversibility → assumptions → evidence →
trigger to revisit.

## DF-01 Monolith vs services

**Default:** a modular monolith with enforced internal boundaries (AX-03/04).
Module boundaries are cheap to draw and cheap to move; network boundaries are
neither. **Choose services only when** a boundary needs independent scaling,
independent deployment cadence, fault isolation, or separate ownership — and
name which one in the ADR. **Revisit when** team count, deploy contention, or
divergent scaling profiles cross the thresholds the ADR states.

## DF-02 SQL vs NoSQL vs specialized stores

**Default:** a relational database with constraints (DD-03) — it preserves the
most optionality and the strongest integrity for unknown future queries.
**Choose a specialized store only for** a demonstrated access pattern it
serves better (document blobs, extreme write throughput, graph traversal,
full-text search, time series), as a *secondary* projection where possible
(DD-17). **Revisit when** measured load or query shape invalidates the ADR's
stated assumptions.

## DF-03 Synchronous call vs asynchronous event

**Default:** synchronous request/response — it is simpler to reason about,
trace, and test. **Choose async (queue/event, PAT-07/11/12) when** the caller
does not need the result to proceed, the work is retryable/batchable, or
coupling to the callee's availability is unacceptable. Async buys resilience
and costs ordering, duplicate delivery, and eventual consistency — the plan
must say how each is handled (AX-10, DD-16). **Revisit when** latency budgets
or consistency complaints contradict the choice.

## DF-04 Build vs buy vs adopt

**Default order:** standard library → dependency already in the tree → managed
service or established library → build (AX-21, AX-01). Building is justified
when the capability is core to the mission's differentiation or the external
option fails a stated constraint (license, data residency, latency, cost
ceiling). Record the losing options and why. **Revisit when** maintenance
cost, vendor risk, or the differentiation claim changes.

## DF-05 Consistency vs availability

**Default:** strong consistency within one datastore's transaction boundary
(DD-16); do not distribute an invariant without need. When a boundary must
span systems or regions, pick per operation: user-facing writes that must not
be lost or contradicted get consistency; read paths and derived views may
serve stale data with a stated staleness bound (PAT-09). The ADR names which
operations sit on which side. **Revisit when** an incident or SLO breach shows
the bound is wrong.

## DF-06 Managed vs self-hosted infrastructure

**Default:** managed services for anything that is not a differentiator —
databases, queues, secrets, observability. Operating infrastructure is a
permanent tax paid in on-call and expertise (SRE: toil). **Self-host when** a
stated constraint forces it (cost at scale, data control, capability gap) and
the ADR prices the operational burden honestly. **Revisit when** the
constraint or the price changes.

## Design interrogation

Before a plan or foundation ADR is presented for approval, the architect
answers these — in the artifact, not silently:

1. What problem and scale are we actually designing for (not imagining)?
2. Which two or three quality attributes dominate (latency, integrity, cost,
   velocity, availability)? What is deliberately sacrificed?
3. What is the simplest viable design, and why is it (in)sufficient?
4. What assumptions would invalidate this design, and how would we notice?
5. Where are the synchronous dependencies, and what happens when each is slow
   or down (AX-09)?
6. How are retries, timeouts, idempotency, and backpressure handled (PAT-05,
   PAT-20)?
7. What data can be lost, duplicated, delayed, or reordered — and is that
   acceptable (DD-13, DD-16)?
8. How is the behavior observed and operated on day 2 (AX-14)?
9. What is the migration, rollback, and recovery path (AX-15, DD-10/11)?
10. What security boundaries and abuse cases exist (PAT-17, threat model)?
11. What complexity is being introduced, and what does it buy (AX-17)?
12. Which alternative was rejected, and what evidence would reopen it?
