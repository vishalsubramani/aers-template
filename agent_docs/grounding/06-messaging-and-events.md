# Grounding — Messaging & event-driven systems

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing anything with a queue, topic, event, webhook, background job,
saga, or stream processor — including the sync-vs-async fork itself (DF-03).
**Doctrine hooks:** AX-01, AX-06, AX-09, AX-10, AX-14, AX-17, AX-18, AX-21, AX-22, DD-02, DD-06,
DD-13, DD-16, DD-17, DD-18, PAT-04, PAT-05, PAT-06, PAT-07, PAT-11, PAT-12, PAT-13, PAT-20,
DF-03, DF-04, DF-05, DF-06

## Design checklist

- [ ] Is async actually justified over a synchronous call, and does the plan state how duplicates,
      reordering, and eventual consistency are handled? *(DF-03)*
- [ ] Which delivery guarantee does the broker really give, and is every consumer idempotent under
      it? *(AX-10, PAT-06)*
- [ ] What is the partition key, and does the ordering the business needs survive retries,
      rebalances, and DLQ detours?
- [ ] Does every event emission share a transaction with the state change it announces (outbox),
      or is there a dual-write? *(PAT-11, DD-16)*
- [ ] Are event schemas versioned contracts with enforced compatibility and tolerant readers?
      *(AX-06, DD-02, DD-13)*
- [ ] Where do poison messages go, who gets alerted, and what is the rehearsed replay procedure?
      *(PAT-07)*
- [ ] What bounds backpressure — bounded queues, paused consumption, or load shedding — and what
      is the retry amplification budget? *(PAT-20, AX-09)*
- [ ] Are consumer lag, DLQ depth, redelivery rate, and end-to-end latency measured with SLOs?
      *(AX-14, AX-22)*
- [ ] For multi-step business flows, is there an explicit saga/workflow with tested compensations,
      or just hope? *(DD-16)*
- [ ] Is the broker managed or self-hosted, and did an ADR price the operational burden? *(DF-06)*

## Queues, streams, and delivery

- **Message queues vs streams (SQS-style vs Kafka-style)** — queues delete on ack and scale
  consumers freely; streams keep ordered, replayable history per partition. Choose from replay and
  ordering needs, not fashion; prefer managed either way *(DF-06, AX-01)*.
- **Pub/sub & fan-out** — decouples producers from N consumers, but every new subscriber silently
  multiplies load and failure surface; keep subscribers owned and discoverable, and don't fan out
  state a consumer could query *(PAT-12, DD-18)*.
- **Delivery guarantees** — at-most-once loses, at-least-once duplicates; **"exactly-once"** is
  at-least-once plus idempotency you construct, never a broker checkbox — design every consumer
  for duplicates *(AX-10, PAT-06)*.
- **Ordering guarantees & partition keys** — order exists only within a partition/key; a hot key
  caps throughput, and retries or DLQ detours break order anyway. Derive the key from the
  invariant that needs ordering, usually the entity ID.
- **Consumer groups, offsets, commits, rebalancing** — commit after processing, not on receipt,
  or you've built at-most-once; rebalances redeliver in-flight work, so handlers must survive
  replay and long processing needs heartbeat/pause tuning *(AX-10)*.
- **Visibility timeouts** — a timeout shorter than worst-case processing yields concurrent
  duplicate processing; size it from measured p99 (not defaults) and heartbeat-extend for long
  work *(AX-18)*.

## Failure handling and redelivery

- **Dead letter queues & poison messages** — a deterministically failing message retries forever
  and blocks its partition; after bounded retries park it in a DLQ with alerting and a rehearsed
  replay path *(PAT-07, AX-09)*.
- **Retry topics; backoff with jitter** — in-partition retries block successors, so move retries
  to delay/retry topics; use exponential backoff with jitter and a total retry budget so
  redelivery doesn't amplify an outage *(PAT-05, PAT-20)*.
- **Idempotent consumers; dedup keys & windows** — dedup stores are windowed, so state what
  happens when a duplicate arrives after the window; prefer naturally idempotent writes (upsert,
  compare-and-set) over remembered keys *(AX-10, PAT-06)*.
- **Competing consumers** — free parallelism, but ordering is gone across workers; scale via
  partitions/keys where order matters and cap concurrency so downstream stores aren't overrun
  *(PAT-20)*.
- **Priority queues & delayed delivery** — priority bands starve the low band under sustained
  load — separate queues with separate workers are safer; delayed delivery beats sleep-and-retry
  loops but check the broker's delay ceiling.

## Consistency and event design

- **Transactional outbox / inbox** — commit-then-publish dual-writes lose or invent events; write
  the event in the same transaction and relay it asynchronously, and use an inbox table for
  consumer-side dedup *(PAT-11, DD-16, AX-10)*.
- **Event sourcing** — makes every read a projection and every event schema permanent; adopt only
  for a demonstrated audit/replay requirement via ADR — outbox plus CRUD covers most needs
  *(AX-17, DD-17)*.
- **Event-carried state transfer vs notification events** — fat events cut read-back traffic but
  freeze the payload as a contract and go stale; thin notifications keep the source authoritative
  at the cost of callback load. Name the choice per event *(PAT-12, DD-17)*.
- **Schema registries; backward/forward compatibility** — enforce compatibility at publish time in
  the registry, not in a wiki; consumers ignore unknown fields and producers never repurpose an
  existing one *(DD-02, DD-13, AX-06)*.
- **Event versioning** — additive first; a breaking change is a new event version published
  alongside the old through a deprecation window with telemetry on old-version consumers
  *(AX-06, PAT-04)*.

## Workflows and coordination

- **Saga pattern: orchestration vs choreography; compensating transactions** — pure choreography
  past ~3 steps means nobody can answer "where is order 123"; prefer an explicit orchestrator,
  and treat compensations as first-class tested steps — some actions can't be compensated
  *(DD-16, DF-05)*.
- **Process managers / durable execution (Temporal-style)** — persists workflow state through
  crashes, but handler code must stay deterministic and be versioned for in-flight runs; adopting
  an engine is a plan-level dependency decision *(AX-21, DF-04)*.

## Stream processing

- **Windowing (tumbling, sliding, session), watermarks, late data** — windowed results are
  provisional until the watermark passes; explicitly decide to drop, re-emit, or side-output late
  events, and keep event time distinct from processing time *(DD-06)*.
- **Backpressure in streams** — unbounded buffering converts overload into OOM and unbounded lag;
  pause consumption or shed at a bounded queue, and alert on lag before consumers fall
  irrecoverably behind *(PAT-20, AX-14)*.
- **Stream–table duality** — a table is a compacted stream; changelogs plus materialized views can
  replace read-side caches, but they are rebuildable projections that never write back to the
  source *(DD-17)*.

## Operating async systems

- **Consumer lag as an SLI** — lag and DLQ depth are the primary health signals of an async
  system; alert on them against stated SLOs, because "the queue is up" says nothing about
  staleness *(AX-14, AX-22)*.
- **Change data capture (CDC)** — owned by 05-data-scale; the messaging-side gotcha: emitted
  events publish your table shape as a contract — interpose a translation layer *(DD-02,
  PAT-12)*.
- **Message envelope & trace propagation** — carry correlation/trace IDs, event time, schema
  version, and idempotency key in a standard envelope, or cross-hop day-2 debugging is guesswork
  *(PAT-13, AX-14)*.
