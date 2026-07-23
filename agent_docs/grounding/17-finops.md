# Grounding — FinOps & cloud economics

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** choosing compute/storage/managed services, designing scaling or multi-tenant
capacity, reviewing plans with cloud spend impact, sizing observability, or costing LLM/GPU
workloads.
**Doctrine hooks:** AX-09, AX-12, AX-14, AX-18, AX-20, AX-22, DD-15, DD-16, PAT-07, PAT-13, PAT-20,
DF-04, DF-06

## Design checklist

- [ ] Is cost named among the dominant quality attributes — or explicitly sacrificed — in the
      design interrogation, with an estimate in the plan? *(AX-18, DF-06)*
- [ ] What is the unit of cost (request/user/tenant/feature), and how will it be measured in
      production? *(AX-14)*
- [ ] Are all resources tagged and allocatable at provision time, enforced by IaC/policy?
- [ ] What does this design pay in data transfer — egress, cross-AZ chatter, NAT paths?
- [ ] Does capacity scale down as deliberately as it scales up — scale-to-zero or off-hours
      schedules for anything without a night-time SLO? *(AX-22)*
- [ ] Is the telemetry bill bounded — sampling, retention per signal, cardinality caps?
      *(PAT-13, DD-15)*
- [ ] Are storage tiering and expiry decided now, at data introduction? *(DD-15)*
- [ ] Is the break-even arithmetic done — serverless vs provisioned, and build vs buy including
      people-time? *(DF-04, DF-06)*
- [ ] Who sees this spend (showback/chargeback), and what alarms before a budget overrun?
- [ ] Can one tenant's usage silently destroy margin — metering, quotas, caps? *(PAT-20)*
- [ ] For LLM/GPU work: are utilization, prompt caching, model routing, and batching considered
      before buying more capacity?

## Unit economics and allocation

- **Unit economics (cost per request/user/tenant/feature)** — a rising bill is meaningless
  without a denominator; instrument cost per unit at design time so growth and waste are
  distinguishable *(AX-14, AX-18)*.
- **COGS & gross margin** — cloud spend serving customers is COGS; a feature that erodes margin
  at scale is a design defect, so price the marginal customer before shipping.
- **Tagging & allocation discipline** — untagged resources are unallocatable forever; enforce
  tags at provision time via IaC/policy, not by cleanup campaigns.
- **Showback vs chargeback** — start with showback (visibility changes behavior); adopt
  chargeback only when teams can act on their bill, or you buy politics without savings.
- **Kubernetes cost allocation** — shared clusters hide who spends; allocate by
  namespace/label using requests-vs-actual-usage, and assign idle capacity to the platform
  deliberately, not by accident.
- **Multi-tenant cost isolation & noisy-neighbor economics** — meter per-tenant consumption
  and cap it (quotas, rate limits); an unmetered heavy tenant is a silent negative-margin
  customer *(PAT-20)*.

## Buying compute

- **Rightsizing as a habit, not a project** — utilization drifts, so downsizing is a recurring
  automated review; one-off rightsizing projects decay back to oversized defaults within
  quarters.
- **Commitment planning (reserved/savings coverage & utilization)** — commit only to the
  measured stable baseline, and track utilization as well as coverage: an unused commitment is
  prepaid waste *(AX-18)*.
- **Spot strategies & interruption tolerance** — spot only for work that checkpoints and drains
  on minutes' notice (queue-fed jobs, PAT-07); stateful or latency-critical paths do not
  qualify *(AX-09)*.
- **Serverless vs provisioned break-even math** — pay-per-use wins at spiky or low utilization,
  provisioned wins at steady load; do the arithmetic at expected traffic, including cold starts
  and concurrency limits *(DF-06, AX-18)*.
- **GPU utilization & scheduling** — idle GPUs are the bill: measure real utilization, batch and
  queue inference, and share capacity via scheduling before provisioning more.

## Elasticity

- **Autoscaling for cost, not just load** — scale-down policy deserves as much design as
  scale-up; validate that capacity actually returns to baseline after peaks, and shed rather
  than overscale under abuse *(PAT-20)*.
- **Scale-to-zero & off-hours schedules** — dev/staging, demos, and batch environments should
  sleep; anything running 24/7 without a night-time SLO is waste by default *(AX-22)*.

## Architecture decides the bill

- **Egress, cross-AZ, and NAT costs** — data transfer is priced by path: chatty cross-AZ calls,
  NAT-routed traffic to object stores (use gateway endpoints), and egress-heavy designs need
  pricing in the plan *(AX-18)*.
- **Storage lifecycle & tiering** — decide tiering and expiry when the data is introduced
  *(DD-15)*; hot-tier-forever is what not deciding buys you, and retrieval fees can flip
  cold-tier math.
- **Observability cost control (sampling, retention, cardinality)** — telemetry can out-cost the
  workload: sample traces, cap metric/label cardinality, and set retention per signal at design
  time *(PAT-13, AX-14)*.
- **Cost as a first-class design requirement** — a plan whose design review never states a cost
  estimate or unit-cost target is incomplete; treat cost like latency, with a number *(AX-18)*.
- **Build vs buy TCO (include people-time)** — price build, operations, on-call, and upgrades,
  not just license vs compute; self-hosting "to save money" usually loses once toil is counted
  *(DF-04, DF-06)*.
- **LLM economics (token costs, prompt caching, model routing, batch APIs)** — tokens are the
  unit cost: budget context, cache stable prompt prefixes, route easy traffic to cheaper
  models, and batch non-interactive work first.

## Governance and the operating loop

- **Orphaned resources & zombie infrastructure** — unattached volumes, idle load balancers,
  stale snapshots, and forgotten environments accrue forever; sweep on a schedule and delete —
  backups and version control are the archive *(AX-20)*.
- **Budgets, forecasts, anomaly detection** — set budgets that alert before overrun, forecast
  from unit economics rather than last month's bill, and alarm on spend anomalies like error
  rates *(AX-14)*.
- **Billing-data lag** — cost dashboards trail reality by 24–48 hours; the real-time defense is
  quotas and hard caps in the architecture, not the anomaly alert.
- **Race-safe spend caps (reserve-then-settle)** — enforce per-tenant caps with an atomic budget
  decrement: reserve the estimated cost before the call, settle actual cost after; read-then-check
  against lagging billing data lets concurrent requests blow the cap — LLM token costs settle late
  (`18-ai-llm-engineering.md`) *(AX-12, DD-16)*.
- **The FinOps loop (inform → optimize → operate)** — never skip the operate phase: an
  optimization lands with its measured saving *(AX-18)* plus the policy or automation that keeps
  it from regressing, or the next quarter's bill undoes it silently.
