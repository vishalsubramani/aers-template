# Grounding — Distributed systems theory

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing anything that spans more than one process or node —
replication, failover, leader election, distributed locks or caches, cross-service invariants,
consistency choices, clock- or ordering-dependent logic.
**Doctrine hooks:** AX-01, AX-09, AX-10, AX-12, DD-06, DD-09, DD-16, PAT-05, PAT-06, PAT-09,
PAT-11, PAT-15, DF-03, DF-04, DF-05

## Design checklist

- [ ] Which operations need which consistency level, and is the per-operation split recorded
      *(DF-05)*?
- [ ] For every cross-process call: what happens on partition or no reply — timeout, bounded
      retry, defined fallback *(AX-09, PAT-05)*?
- [ ] Is every externally-triggered mutation idempotent, since exactly-once delivery is
      unattainable *(AX-10, PAT-06)*?
- [ ] Does any correctness property depend on synchronized wall clocks (ordering, lease expiry,
      uniqueness)? If yes, redesign or bound the skew explicitly *(DD-06)*.
- [ ] Are leader/lock holders fenced so a paused or partitioned ex-holder cannot corrupt shared
      state *(AX-12)*?
- [ ] Is a distributed transaction (2PC) creeping in where an outbox/saga would do *(PAT-11,
      DD-16)*?
- [ ] How are concurrent writes to the same datum resolved — single writer, CAS, or explicit
      merge — never silent last-write-wins *(DD-09)*?
- [ ] Are we hand-rolling consensus, membership, election, or locking instead of using a proven
      coordination service *(AX-01, DF-04)*?
- [ ] How will gray failures (slow, flaky, partially wrong) be detected when binary health
      checks stay green *(AX-14, PAT-15)*?
- [ ] What staleness bound do stale reads and caches serve under, and is it stated *(PAT-09,
      DF-05)*?

## Theory you eventually hit

- **CAP theorem / PACELC** — CAP only constrains behavior during partitions; PACELC adds the
  everyday latency-vs-consistency trade you pay even without one — decide both, per operation
  *(DF-05)*.
- **Eight fallacies of distributed computing** — review every remote-call design assuming the
  network is slow, lossy, insecure, and changing; any design premised on a fallacy fails in
  production *(AX-09)*.
- **Consistency spectrum (linearizable → sequential → causal → eventual)** — name the level
  each operation actually needs; "eventually consistent" without a staleness bound is not a
  specification *(DF-05, PAT-09)*.
- **Session guarantees (read-your-writes, monotonic reads/writes)** — often what users need
  instead of full linearizability; get them cheaply via session pinning or read-from-primary
  after write.
- **Quorums (R + W > N)** — overlap gives per-key read-visibility only, not transactions or
  linearizability; sloppy quorums and failover can silently break the arithmetic.
- **Consensus (Paxos, Raft)** — never implement it yourself; delegate election, config, and
  membership to a proven coordination service and treat it as a dependency that can be down
  *(AX-01, DF-04, AX-09)*.
- **Leader election, leases, fencing tokens** — a lease holder can stall (GC, VM pause) past
  expiry and act on stale authority; every guarded write must carry a fencing token the
  resource checks *(AX-12)*.
- **FLP impossibility** — async consensus cannot be both safe and always live; correct systems
  stall (lose liveness) under bad timing rather than corrupt state — plan for stalls, alert on
  them *(AX-14)*.
- **Two Generals problem** — no protocol yields certain agreement over a lossy link; stop
  designing for confirmed delivery and design for retry plus idempotent receipt *(AX-10)*.
- **Logical time (Lamport, vector, hybrid logical clocks)** — cross-node ordering by wall-clock
  timestamp is a bug; use logical or hybrid clocks when causality or ordering matters.
- **Physical time (clock skew, NTP, leap seconds)** — clocks drift, step, and smear; keep
  wall time out of correctness logic and persist it as UTC only for humans and records
  *(DD-06)*.
- **Failure detection (heartbeats, phi accrual, SWIM/gossip)** — detectors output suspicion,
  not truth: a "dead" node may still be writing — pair detection with fencing before acting.
- **Split brain** — two primaries accepting writes after a partition; prevent with quorum-based
  election plus fencing, never with failover timers alone *(AX-12)*.
- **Network partitions / partial failure as the default** — "no answer" is a distinct outcome
  from "failed": the operation may have succeeded, so every caller needs timeout-plus-idempotent
  -retry semantics *(AX-09, AX-10)*.
- **Gray failures** — slow-and-wrong hurts more than dead; health checks pass while users
  suffer, so watch percentile latency and error rates per dependency, not liveness *(AX-14,
  PAT-15)*.
- **Anti-entropy, read repair, hinted handoff, Merkle trees** — the convergence machinery of
  leaderless stores; before adopting one, know which it uses and its repair lag, because that
  is your real staleness bound *(PAT-09)*.
- **CRDTs and conflict resolution** — default last-write-wins silently discards concurrent
  updates; where concurrent writes are legitimate, choose explicit merge semantics (CRDT or
  application-level) or restore a single writer *(DD-09)*.
- **Byzantine vs crash faults** — assume crash-stop inside one trust boundary; Byzantine
  tolerance is for adversarial multi-party settings and is very expensive — do not buy it by
  accident *(AX-17)*.
- **The end-to-end argument** — reliability added in the middle (TCP, queue dedup, retrying
  proxies) never removes the need for end-to-end checks: application idempotency keys, acks,
  and checksums *(AX-10, PAT-06)*.
- **Distributed transactions (2PC, 3PC)** — 2PC blocks all participants on coordinator failure
  and couples availability; design around it with outbox and sagas as the default *(PAT-11,
  DD-16, DF-05)*.
- **Distributed locks (and Redlock's caveats)** — without fencing tokens a distributed lock is
  advisory, and Redlock's safety depends on timing assumptions; prefer single-writer designs or
  compare-and-set *(AX-12, DD-09)*.
- **Service discovery (client-side vs server-side; DNS vs registry)** — DNS caching and stale
  registry entries route traffic to dead instances; set low TTLs deliberately and gate targets
  on readiness *(PAT-15)*.
- **Consistent hashing and virtual nodes** — the default for cache and shard placement so
  scaling moves ~1/N of keys; use virtual nodes to smooth hotspots, and still plan for hot
  keys.
- **Exactly-once is a lie; idempotency is the truth** — exactly-once *processing* is built from
  at-least-once delivery plus idempotent handlers and dedup keys; any design claiming
  exactly-once delivery is hiding a gap *(AX-10, PAT-06, PAT-07)*.
- **Safety vs liveness** — classify every guarantee: correct systems give up liveness (stall)
  under partitions and bad timing, never safety; a design that trades safety for availability
  needs DF-05 on record.
- **Jepsen-style fault injection** — vendor consistency claims routinely fail under partition
  tests; check published analyses before relying on a store's guarantee, and verify your own
  claims with injected faults *(AX-18)*.
