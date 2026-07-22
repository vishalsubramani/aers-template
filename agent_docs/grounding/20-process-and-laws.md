# Grounding — People, process & eponymous laws

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** planning delivery/rollout, writing or reviewing ADRs and design docs, sizing or
splitting tasks, defining metrics or SLO targets, deprecating or migrating anything, drawing module
or team ownership boundaries, or running an incident review.
**Doctrine hooks:** AX-01, AX-02, AX-05, AX-06, AX-15, AX-17, AX-18, AX-20, AX-21, DD-09, DD-10,
DD-11, DD-18, PAT-04, PAT-14, DF-01

## Design checklist

- [ ] Is this the smallest reversible increment, shipped behind a flag with an owner and removal
  date rather than a big-bang branch? *(AX-15, PAT-14)*
- [ ] Every deviation or notable fork recorded as an ADR with trade-offs and a revisit trigger —
  not relitigated in chat? *(DF preamble)*
- [ ] For any target metric introduced: what happens when people optimize it directly (Goodhart),
  and what countervailing metric pairs with it?
- [ ] Does the new public surface invite Hyrum's-law dependence on incidental behavior — is
  everything not contractual kept private? *(AX-05, AX-06)*
- [ ] Who owns each path and dataset touched, and does the change respect single-writer
  ownership? *(DD-09, DD-18)*
- [ ] Before deleting or "fixing" surprising existing code: is Chesterton's fence answered — do we
  know why it was there? *(AX-20)*
- [ ] Does the migration plan cost the contract phase — backfill, verification, old-shape
  removal — not just the expand step? *(DD-10, DD-11)*
- [ ] Was a premortem run: assume this shipped and failed — what broke, and how would we have
  noticed? *(DF-06 interrogation, AX-14)*
- [ ] Is the build reproducible from a clean checkout (`make bootstrap`, pinned lockfile), with no
  reliance on local state? *(AX-21)*
- [ ] How many innovation tokens does the design spend, and is each named in an ADR? *(AX-01)*
- [ ] Does the deprecation have a stated window, telemetry on remaining usage, and a deletion
  date? *(PAT-04, AX-06)*

## Delivery flow

- **DORA metrics** — deploy frequency, lead time, change-failure rate, time to restore: optimize
  the system, not individuals; small reversible batches move all four together, so speed and
  stability are not a trade-off *(AX-15)*.
- **Trunk-based development + flags** — long-lived branches hide integration risk until merge day;
  default to short-lived branches into trunk with incomplete work dark behind expiring flags
  *(PAT-14, AX-15)*.
- **WIP limits & flow** — kanban's actual point: starting more work slows finishing work; when
  blocked, swarm on finishing in-flight items instead of opening new ones. One task at a time.
- **Estimation humility; Hofstadter's law** — it always takes longer, even accounting for that;
  respond with scope cuts and explicit budgets, not padded dates — and safe-stop when a budget
  exhausts rather than quietly overrunning.

## Documentation and knowledge

- **Design docs & RFCs; ADRs** — an unwritten decision gets relitigated forever; record context,
  rejected options, and a revisit trigger before implementing, in the repo's ADR shape
  *(DF preamble)*.
- **Diátaxis** — tutorials, how-tos, reference, explanation serve different reader modes; a doc
  mixing quadrants serves none — pick one per document and link across.
- **READMEs & onboarding as products** — the setup path is an interface with users; test it from
  a clean machine (`make bootstrap`) and treat a stale README as a bug, not decoration.
- **Runbook culture** — write the operational response when you design the failure mode, not
  during the incident; every alert should link to a runbook with concrete commands *(AX-14)*.

## Teams and organization

- **Code ownership models** — unowned code rots and shared-write code races; every path needs an
  accountable owner even under collective ownership, mirroring single-writer data ownership
  *(DD-09, DD-18)*.
- **Pairing & mobbing** — cheapest tool for bus-factor and high-risk changes; prefer it over
  async review when feedback latency or context transfer dominates the cost.
- **Conway's law & the inverse Conway maneuver** — shipped architecture copies the communication
  structure; choose module/service boundaries and team boundaries together, or the org will
  redraw your design for you *(DF-01)*.
- **Team Topologies** — stream-aligned, platform, enabling, complicated-subsystem: default to
  stream-aligned teams; a platform earns its existence only by reducing others' cognitive load,
  not by mandating itself.
- **Cognitive load as the limiting resource** — the binding constraint on team output; smaller
  public surfaces and boring technology are load-shedding decisions, not aesthetics
  *(AX-01, AX-05)*.
- **Two-pizza teams** — communication paths grow quadratically with headcount; if a team can't
  own its slice end to end, split the boundary, not the accountability *(DF-01)*.
- **Brooks's law** — adding people to a late project makes it later: onboarding and coordination
  costs land immediately, output later; cut scope instead *(AX-17)*.
- **Second-system effect** — the follow-up to a successful simple system attracts every deferred
  feature; treat "this time we'll do it right" rewrites as a red flag *(AX-02)*.
- **Bus factor** — count the people who can safely touch each critical area; a bus factor of one
  is an outage waiting on a vacation — fix with pairing, docs, and rotation.

## Eponymous laws and effects

- **Goodhart's law** — a metric made a target stops measuring; never reward proxies (coverage
  percent, velocity, LOC) directly — pair each target with a countervailing check.
- **Gall's law** — working complex systems evolve from working simple ones; designing the
  complex end state up front fails — ship the simple system and grow it *(AX-02, AX-17)*.
- **Hyrum's law** — with enough users, every observable behavior gets depended on: error strings,
  ordering, timing; minimize what's observable and treat any change to it as breaking
  *(AX-05, AX-06, DD-13)*.
- **Parkinson's law** — work expands to fill the time allotted; give tasks explicit budgets and
  stop conditions, and timebox open-ended investigation.
- **Bike-shedding (law of triviality)** — review effort flows to what's easy to opine on; cap
  debate on trivia with a linter or convention, and spend review on correctness and scope.
- **Wirth's law** — software slows faster than hardware speeds up; performance regressions
  compound silently, so budget and measure them per change instead of assuming headroom
  *(AX-18)*.
- **The Lindy effect** — technology that has survived decades will likely survive more; weight
  longevity as evidence when choosing dependencies over this year's framework *(AX-01, AX-21)*.
- **Chesterton's fence** — it belongs everywhere: never remove code, a constraint, or a config
  you can't explain; git-blame and ask before deleting, then delete decisively *(AX-20)*.
- **Hanlon's razor** — in incident reviews, assume process gaps before malice or incompetence;
  blame ends the learning, so ask what made the mistake easy to make.
- **Blameless postmortems** — the point of Hanlon applied: people report honestly only when the
  review fixes systems, not people; punish concealment, never disclosure.
- **Cunningham's law** — the fastest way to a right answer is posting a wrong one; circulate a
  concrete strawman design to draw out corrections a blank question never surfaces.

## Working habits and debugging

- **The XY problem** — people ask about their attempted solution, not their actual problem;
  before answering (or asking), restate the underlying goal and check the framing.
- **Rubber-duck debugging** — explaining the bug aloud forces assumptions explicit; the written
  form is a falsifiable hypothesis in your notes before touching the code.
- **Yak shaving** — nested prerequisite detours quietly replace the task; when a fix demands a
  fix, log the detour, check it against the approved scope, and return or safe-stop.
- **Premortems** — before rollout, assume it failed and write the story; it surfaces failure
  modes that optimistic review misses and feeds the ADR's failure-mode section *(AX-15)*.

## Change discipline

- **Migration discipline** — the last 10% is 90% of the work: the contract phase (backfill,
  verification, removing the old path) is the migration — plan and budget it up front
  *(DD-10, DD-11, DD-12)*.
- **Deprecation as a feature** — removal needs the same design as addition: a stated window,
  telemetry on remaining callers, and a deletion date — or the old path lives forever
  *(PAT-04, AX-06)*.
- **"It works on my machine" → reproducible environments** — untracked local state is a latent
  outage; pin toolchains and lockfiles so a clean checkout plus `make bootstrap` reproduces the
  build exactly *(AX-21)*.
- **Innovation tokens** — spend few, spend wisely: each novel technology is an operational debt
  the team pays at 3am; budget roughly one per system and record each spend in an ADR *(AX-01)*.
