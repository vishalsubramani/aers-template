# Grounding — Observability & operations

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** specifying a feature's telemetry (AX-14), designing dashboards or alerts, setting
SLIs/SLOs, planning on-call/runbooks, reviewing incident response, or pricing telemetry cost.
**Doctrine hooks:** AX-01, AX-09, AX-14, AX-15, AX-18, AX-22, DD-14, DD-15, DD-18, PAT-13, PAT-14,
DF-06

## Design checklist

- [ ] Does the plan name the feature's logs, metrics, and trace propagation before code, not
      after an incident? *(AX-14, PAT-13)*
- [ ] Can an unknown-unknown be debugged from emitted telemetry alone — high-cardinality fields
      included — without a new deploy?
- [ ] Are SLIs measured where the user is, with an SLO and an error-budget policy someone will
      actually enforce? *(AX-22)*
- [ ] Does every alert page on a symptom, link a runbook, and have a named owner — and would you
      accept being woken by it? *(DD-18)*
- [ ] Is metric label cardinality bounded by design (no user IDs, no raw URLs), and is the
      telemetry bill/retention tier stated?
- [ ] Are PII and secrets provably absent from logs, traces, and wide events? *(DD-14, PAT-13)*
- [ ] Are audit-relevant actions logged to a separate, retained, tamper-resistant stream with its
      own retention decision? *(DD-15)*
- [ ] Who gets paged for this component, is that recorded in ownership metadata, and does the
      dependency map say who they call next? *(DD-18)*
- [ ] Do postmortem action items land in the task backlog with owners and dates, not in a doc
      nobody reopens?
- [ ] Has recovery (runbook, rollback, DR path) been exercised, not just written? *(AX-15)*

## Observability

- **Monitoring vs observability** — dashboards answer known-unknowns; design telemetry rich
  enough to interrogate unknown-unknowns, or every novel incident needs a new deploy to debug
  *(AX-14)*.
- **Structured logging** — key-value from day one; grep-era format strings can't be queried, and
  retrofitting structure during an incident is too late *(PAT-13)*.
- **Log levels used with intent** — define what pages, what's investigated, what's noise; if
  ERROR doesn't mean "a human should look," alerting on it is impossible.
- **Correlation IDs; context propagation** — adopt W3C traceparent at every boundary including
  queues and jobs; one dropped hop severs the whole request story *(PAT-13, AX-14)*.
- **Distributed tracing: spans, head vs tail sampling** — head sampling is cheap but blind to
  rare failures; tail sampling keeps the interesting traces at collector cost — pick per
  debugging need, not default.
- **OpenTelemetry** — instrument against the vendor-neutral API so the backend stays swappable;
  vendor SDK lock-in is a rewrite you pay at contract renewal *(DF-06, AX-01)*.
- **Metrics: counters, gauges, histograms** — compute percentiles from histograms at query time;
  pre-averaged percentiles cannot be aggregated across instances and silently lie.
- **Cardinality** — unbounded label values (user ID, URL path) are both the metrics bill and the
  metrics outage; bound label sets at design review, push high-cardinality data to events/traces.
- **Golden signals** — latency, traffic, errors, saturation per service is the floor for any new
  dashboard; if one is missing, say why *(AX-14)*.
- **RED & USE methods** — RED (rate, errors, duration) for request-driven services, USE
  (utilization, saturation, errors) for resources; apply the matching template instead of
  inventing per-service dashboards.
- **Wide structured events** — one context-rich event per request unit beats dozens of scattered
  log lines; it is the default answer to high-cardinality debugging without metric blowup.
- **Dashboards: overview → drill-down** — structure as questions an on-call asks in order, top
  level to cause; a wall of unowned charts is decoration, not operations.
- **Alerting: symptom-based, actionable, owned** — every alert needs a user-visible symptom, a
  linked action, and an owner; fail any alert lacking one of the three *(DD-18)*.
- **Alert fatigue & tuning** — review alert volume regularly and delete or demote anything
  routinely acked-and-ignored; an ignored page trains on-call to miss the real one.
- **SLIs → SLOs → error budgets → burn-rate alerts** — page on budget burn rate, not raw
  thresholds: fast-burn pages, slow-burn tickets — this is how AX-22 becomes alerting *(AX-22)*.
- **SLA vs SLO** — SLA is the external contract with penalties, SLO the internal target; set the
  SLO stricter than the SLA or the contract is your early-warning system.
- **Synthetic monitoring & real-user monitoring** — synthetics catch outages when traffic is
  absent (nights, new endpoints); RUM measures what users actually experienced — you need both,
  they answer different questions.
- **Continuous profiling in production** — always-on profiles turn "it's slow sometimes" into a
  flame graph diff; it is the measurement AX-18 demands before optimizing *(AX-18)*.
- **Telemetry economics: sampling, retention tiers** — telemetry cost scales with traffic and
  can dwarf compute; decide sampling rates and hot/cold retention at design time, not at invoice
  time *(DF-06)*.
- **PII scrubbing in logs and traces** — scrub at the SDK/collector edge, not per-callsite
  discipline; one forgotten log line makes the whole telemetry store subject to erasure requests
  *(DD-14)*.
- **Audit logs are not debug logs** — separate stream, longer retention, tamper-resistance, and
  guaranteed delivery; debug logs get sampled and rotated, audit logs must not *(DD-15)*.
- **Deploy markers & change correlation** — overlay deploys, flag flips, and config changes on
  every dashboard; most incidents are changes, and the first diagnostic question is "what
  changed?" *(AX-15, PAT-14)*.

## SRE & incident management

- **Toil identification & automation** — track manual, repetitive, automatable ops work
  explicitly and budget its elimination; unmeasured toil silently consumes the team that should
  be shipping *(DF-06)*.
- **Error budget policy** — write down what actually happens when the budget is spent (feature
  freeze, reliability sprint) before you need it; an unenforced budget is a dashboard, not a
  policy *(AX-22)*.
- **Production readiness reviews** — gate first production traffic on a checklist (SLOs, alerts,
  runbooks, ownership, capacity); retrofitting readiness after launch is an incident-driven
  process.
- **Runbooks & playbooks, linked from alerts** — the page must carry the link; a runbook the
  on-call has to search for at 3am does not exist. Test runbooks like code.
- **On-call: rotations, handoffs, escalation** — design sustainable load (page budgets, minimum
  rotation size) and explicit handoff notes; an overloaded rotation degrades into ignored pages.
- **Page on symptoms; ticket on causes** — page only for user-impacting symptoms; cause-level
  signals (disk filling, cert expiring) become tickets with deadlines, or they become pages later.
- **Incident severity taxonomy** — pre-agree severity levels with response expectations per
  level; debating "is this a SEV1" during the incident wastes the minutes that matter.
- **Incident command: roles, comms cadence, status pages** — separate the fixer from the
  communicator; a named incident commander and a stated update cadence prevent the
  everyone-debugging-nobody-deciding failure.
- **MTTD / MTTR limits** — averages hide the tail incident and invite gaming; use them for
  trends, never as individual targets, and pair with incident narratives.
- **Incidents as learning opportunities; blameless postmortems; contributing factors** — the
  incident already paid its cost, so extract the systemic fixes: hunt contributing factors, not
  a single root cause or a person — blame teaches people to hide what the next incident needs.
- **Action items that actually ship** — postmortem items go into the tracked backlog with owners
  and due dates, and get reviewed; unshipped action items are how the same incident recurs.
- **Game days & DR drills** — exercise failure paths (failover, restore, region loss) on a
  schedule; an untested recovery path fails exactly when needed *(AX-09, AX-15)*.
- **Change freezes** — freezes batch risk into the thaw and rot deploy muscle; prefer raising
  rigor (more review, smaller changes, better rollback) over stopping change *(AX-15)*.
- **Dependency mapping & service catalogs** — keep a queryable map of who depends on what;
  during an incident, blast radius and "who do we call" must be lookups, not archaeology
  *(DD-18)*.
- **Ownership metadata** — every service, dataset, alert, and dashboard names an owning team in
  the catalog; unowned components are where incidents stall *(DD-18)*.
- **Dead man's switch alerts** — alert on the absence of expected telemetry (heartbeats, cron
  completions); a silent pipeline looks identical to a healthy one until the data is missed.
