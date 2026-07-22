# Grounding — Resilience patterns

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing any remote call, retry/queue/cache path, overload or
capacity plan, deploy/shutdown lifecycle, HA/DR posture, or an incident-driven fix.
**Doctrine hooks:** AX-09, AX-10, AX-11, AX-22, PAT-05, PAT-07, PAT-08, PAT-09, PAT-15,
PAT-17, PAT-20, DD-15, DF-05

## Design checklist

- [ ] Does every outbound call have an explicit timeout, with the caller's deadline propagated
      so inner timeouts sum under the outer one? *(AX-09, PAT-05)*
- [ ] Are retries restricted to idempotent operations and capped by a global retry budget —
      what is the worst-case load amplification through all retry layers? *(AX-10, PAT-20)*
- [ ] For each synchronous dependency: what happens when it is slow (not just down) — degrade,
      queue, or fail fast, named per dependency? *(AX-09, PAT-08)*
- [ ] Under overload, who gets turned away, how early, and by what priority — and is every
      queue bounded? *(PAT-20)*
- [ ] Can the data plane keep serving when config, discovery, or the control plane is
      unavailable (static stability)? *(PAT-20)*
- [ ] Do liveness and readiness check different things, and can a deep readiness check mark a
      whole fleet unready at once? *(PAT-15)*
- [ ] What bounds the blast radius of one bad instance, cell, or customer (bulkheads, cells,
      shuffle sharding) — and is that bound stated in the plan?
- [ ] Has every fallback path been exercised recently, and will it hold production load when
      the primary fails? *(PAT-08)*
- [ ] Which failures are correlated (shared zone, dependency, cert, config push, deploy wave)
      and therefore one failure domain, not redundancy?
- [ ] What are the stated RTO/RPO, and when was a restore last actually performed? *(AX-22)*
- [ ] On SIGTERM, does the process drain in-flight work within the deployer's grace period —
      and is a hard kill mid-work safe anyway? *(AX-10)*
- [ ] For each guard dependency (auth, limiter, flags): does it fail open or fail closed, and
      was that direction chosen deliberately? *(PAT-17)*

## Timeouts, retries, and circuit breaking

- **Timeouts everywhere** — every remote call gets an explicit one; propagate the caller's
  **deadline** downstream and budget so inner timeouts sum under the outer, or you burn
  capacity on answers nobody awaits *(AX-09, PAT-05)*.
- **Retries** — idempotent operations only, capped by a shared retry budget rather than
  per-callsite counts; stacked retry layers multiply load exactly when the dependency can
  least afford it *(AX-10, PAT-05, PAT-20)*.
- **Exponential backoff + full jitter** — backoff without jitter synchronizes clients into
  waves; use full jitter by default and honor server-signaled `Retry-After` over your own
  schedule *(PAT-05)*.
- **Retry storms & metastable failures** — retry load can hold a system down after the
  trigger clears; recovery needs a pre-built switch to shed or disable retries, because you
  cannot design it mid-incident *(PAT-20)*.
- **Circuit breakers (closed/open/half-open)** — scope per dependency (often per endpoint),
  and define what "open" means for callers — documented fallback or fast typed error, never
  silent partial success *(PAT-05, AX-11)*.

## Overload control

- **Bulkheads** — partition thread pools, connections, and queues per dependency or tenant so
  one slow dependency cannot exhaust shared resources and drag down unrelated paths *(AX-09)*.
- **Load shedding & admission control** — reject excess work at the front door with a cheap
  check, by request class; serving everyone slowly from a saturated queue is worse than fast
  429s for some *(PAT-20)*.
- **Rate limiting: token bucket, leaky bucket, fixed window, sliding window, GCRA** — default
  to token bucket for burst tolerance; fixed windows double-spike at boundaries, so prefer
  sliding window or GCRA for strictness *(PAT-20)*.
- **Backpressure** — bound every queue and buffer; when full, block or reject upstream — an
  unbounded queue converts overload into memory exhaustion plus latency no client outlives
  *(PAT-20, PAT-07)*.
- **Fail open vs fail closed** — for each guard dependency (auth, limiter, flag service),
  choose the safe failure direction in advance: security controls fail closed, throttles
  usually fail open *(PAT-17)*.

## Degradation, hedging, and coalescing

- **Graceful degradation & fallbacks** — degraded behavior is designed, documented, and
  logged when served; fallbacks fail too — cold, untested, and often sharing fate with the
  primary — so exercise them regularly *(PAT-08, AX-14)*.
- **Hedged requests** — after the ~p95 mark, duplicate the call to another replica to cut
  tail latency; idempotent reads only, with a hedge cap so the cure doesn't become
  self-inflicted overload *(AX-10)*.
- **Request coalescing** — collapse concurrent identical fetches into one in-flight call;
  it is the standing fix for cache-miss stampedes on hot keys *(PAT-09)*.

## Health and lifecycle

- **Health checks: liveness vs readiness vs startup** — liveness ("restart me") must not
  check dependencies; readiness ("route to me") may; **deep checks cascade** — one flaky
  dependency can unready a fleet. Use startup probes for slow boots *(PAT-15)*.
- **Graceful shutdown: SIGTERM → drain → exit** — stop accepting, drain in-flight work, then
  exit; verify the orchestrator's grace period exceeds drain time, or every deploy is an
  error spike.
- **Crash-only design** — if correctness requires a clean shutdown, the design is wrong,
  because hard kills happen anyway; make cold start after kill the recovery path and all work
  resumable *(AX-10)*.
- **Static stability** — keep serving from last-known-good config, discovery, and credentials
  when the control plane is down; a data plane that fails on refresh turns a control-plane
  blip into an outage *(PAT-20)*.

## Isolation and blast radius

- **Shuffle sharding** — give each customer a random small subset of nodes so a poison
  request harms only the few customers sharing that exact subset, not an entire partition.
- **Cell isolation & blast radius** — partition into independent cells with no cross-cell
  dependencies; size cells so losing one is survivable, route customers deterministically,
  and state the max blast radius in the plan.
- **Thundering herd** — anything synchronized (cache TTLs, cron, reconnect-after-outage)
  stampedes; desynchronize with jitter, staggered expiry, and coalescing *(PAT-09)*.
- **Correlated failures & shared fate** — redundancy is fiction when replicas share a zone,
  dependency, cert expiry, config push, or deploy wave; enumerate shared fate explicitly —
  most "independent" failures aren't.

## Chaos, recovery, and multi-region

- **Chaos engineering** — requires a falsifiable steady-state hypothesis, a bounded blast
  radius, and an abort switch, or it is just breaking prod; game days test humans and
  runbooks, not only systems *(AX-22)*.
- **Disaster recovery: RTO/RPO** — choose the tier (backup → pilot light → warm standby →
  active-active) from stated RTO/RPO and cost, not aspiration; an undrilled DR plan is a
  document, not a capability *(AX-22)*.
- **Backups** — untested restores don't count: drill restores on a schedule, verify with
  checksums, and keep one copy outside the account/deletion path that could eat the primary
  *(DD-15)*.
- **Failover & failback** — automate and regularly exercise failover; failback is the
  forgotten half — plan how writes accepted during failover reconcile when the primary
  returns.
- **Multi-region deployments** — active-passive is simpler but the passive side rots
  unexercised; active-active forces per-datum conflict and consistency decisions *(DF-05)*;
  **data residency** constrains **replication topology** before performance does.
