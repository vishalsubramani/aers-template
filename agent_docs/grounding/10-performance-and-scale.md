# Grounding — Performance & scale

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** setting latency/throughput targets, sizing or scaling a service, designing hot
paths or fan-out, reviewing benchmarks or load tests, choosing serialization or batching,
planning autoscaling, capacity, or serverless deployment.
**Doctrine hooks:** AX-09, AX-14, AX-18, AX-22, DD-08, DD-17, PAT-05, PAT-07, PAT-09, PAT-10,
PAT-20, DF-01, DF-02, DF-03, DF-06

## Design checklist

- [ ] Are latency targets stated as percentiles (p95/p99) tied to an SLO — not averages *(AX-22)*?
- [ ] Has back-of-envelope QPS/storage/bandwidth math been done before committing to a design?
- [ ] Does the hot path fan out to N dependencies, and is tail amplification accounted for *(AX-09, PAT-05)*?
- [ ] What utilization does capacity planning assume, and is it safely below the ~70–80% knee?
- [ ] Is every optimization in the plan backed by a profile or measurement, before and after *(AX-18)*?
- [ ] Can the service scale horizontally — is all session/request state externalized *(DF-01)*?
- [ ] Are round trips, payload sizes, and serialization/compression choices deliberate and bounded *(PAT-10)*?
- [ ] Do the availability targets survive serial composition across the dependency chain *(AX-09, AX-22)*?
- [ ] If autoscaling: which metric, what cooldown, what happens at scale-to-zero and on cold start?
- [ ] Are benchmarks realistic — warmed up, real data shapes, coordinated omission avoided?

## Latency, tails, and queueing math

- **Latency vs throughput** — optimizing one usually costs the other (batching raises throughput,
  adds latency); the contract must name which dominates before tuning *(AX-22, DF-03)*.
- **Percentiles (p50/p95/p99/p999)** — averages hide the users having a bad day; specify, measure,
  and alert on percentiles; never average percentiles across hosts *(AX-14, AX-22)*.
- **Tail latency amplification under fan-out** — a request touching N backends rides the slowest;
  at N=100, p99 backend latency hits nearly every request. Cut fan-out, or hedge/timeout *(AX-09, PAT-05)*.
- **Coordinated omission** — load tools that wait for slow responses under-record them; use
  fixed-rate open-loop load generation or corrected histograms before trusting latency numbers.
- **Little's law** — L = λW: concurrency, arrival rate, and latency are locked together; use it to
  size pools, queues, and worker counts instead of guessing *(PAT-07)*.
- **Amdahl's law & the Universal Scalability Law** — the serial or coordination fraction caps
  speedup, and contention plus crosstalk make throughput *drop* past a point; find the serial part first.
- **Queueing intuition** — latency explodes past ~70–80% utilization; plan headroom there, and
  treat "we'll run it at 90%" in a capacity plan as a defect *(PAT-20)*.
- **Latency numbers every programmer should know** — keep orders of magnitude live (RAM ~100ns,
  SSD ~100µs, same-DC RTT ~0.5ms, cross-region ~100ms); designs that ignore them fail estimation.

## Efficiency: batching, the wire, and the CPU

- **Batching & pipelining** — amortize per-request overhead when throughput matters, but bound
  batch size and add a max-wait so latency and memory stay capped *(DF-03, PAT-07)*.
- **Chatty vs chunky APIs** — N+1 round trips over a network dwarf compute; design boundary calls
  to fetch what one interaction needs in few exchanges *(AX-06, PAT-10)*.
- **N+1 queries** — the database edition of chatty: per-item queries in a loop; reviewers should
  hunt for it in any list-rendering or ORM code path *(PAT-03)*.
- **Serialization cost (JSON vs binary)** — parse/encode can dominate hot-path CPU; measure before
  swapping formats, and treat the format as a versioned contract, not an optimization knob *(AX-18, DD-02)*.
- **Compression tradeoffs** — trades CPU for bytes on the wire; wins on slow links and big
  payloads, loses on small hot messages — pick per path with measurements *(AX-18)*.
- **Zero-copy** — copies between buffers/kernel/userspace quietly eat throughput on data-heavy
  paths; reach for sendfile/slices/views only after a profile names copying as the cost *(AX-18)*.
- **Hot paths; profile before optimizing** — most code is cold; find the hot 3% with a profiler
  and leave the rest clear — evidence before and after is mandatory *(AX-18, AX-19)*.
- **Benchmark pitfalls** — warmup (JIT/caches), dead-code elimination of unused results, and
  unrealistically uniform data all fabricate wins; benchmark with production-shaped data and sinks.
- **Connection pooling** — per-request TCP/TLS/DB handshakes destroy latency and exhaust server
  resources; pool with bounded size (Little's law) and health-checked reuse *(AX-09)*.

## Scaling out

- **Horizontal vs vertical scaling** — scale up first (it's free of coordination cost) until price
  or ceiling bites; scaling out requires statelessness and load-balancing design *(DF-01, AX-18)*.
- **Stateless services; externalized session state** — any instance-local state (sessions, caches
  used as truth, sticky uploads) blocks scale-out and safe deploys; put it in a shared store *(DD-17, PAT-09)*.
- **Data locality** — moving compute to data beats moving data to compute; cross-region or
  cross-service data pulls on hot paths are a design smell to interrogate *(DF-02, DD-17)*.
- **Autoscaling** — pick a metric that leads load (queue depth, concurrency, not CPU alone), add
  cooldowns to stop flapping, and decide scale-to-zero vs floor deliberately — cold starts are the price.
- **Predictive scaling** — reactive scaling always lags spikes; for known cycles (business hours,
  launches) schedule capacity ahead instead of eating the lag.

## Capacity, availability, and serverless

- **Capacity planning & headroom** — plan for peak plus failure headroom (survive one zone/instance
  loss at target utilization), and revisit on a schedule, not after the outage *(AX-22, PAT-20)*.
- **Back-of-envelope estimation** — QPS × payload × retention math takes five minutes and kills
  wrong architectures early; a plan without it is guessing (design interrogation Q1).
- **Availability math** — nines multiply: serial dependencies compose *down* (three 99.9% services
  ≈ 99.7%), redundancy composes up; your SLO cannot exceed a hard serial dependency's *(AX-09, AX-22)*.
- **Cold starts & mitigations** — first-request latency on scale-up or scale-to-zero breaks p99;
  mitigate with provisioned concurrency, snapshotting, warm pools — or keep a floor *(AX-22)*.
- **Serverless limits** — duration, payload size, and concurrency caps are hard platform
  constraints; check them against the workload before choosing the platform, not in production *(DF-06)*.
