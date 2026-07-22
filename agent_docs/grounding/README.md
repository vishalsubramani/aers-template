# Grounding library — production-engineering awareness for agents

This directory is the awareness layer beneath `.agents/doctrine/`. Doctrine is small and
enforced: axioms (`AX-*`), data rules (`DD-*`), patterns (`PAT-*`), and frameworks (`DF-*`)
that every plan must cite and every diff is held against. This library is broad and
advisory: the full vocabulary of concepts between "it runs on my laptop" and "it runs at
scale", each phrased as a decision heuristic — when it bites, and what the default move is.

Fluency in every item is not the goal. The goal is the checklist effect: at decision time,
the relevant file surfaces the concerns an unaided draft would miss, so failure modes are
named in the plan instead of discovered in production.

## Precedence

1. `.agents/doctrine/` and accepted ADRs are law. Where a grounding entry cites a doctrine
   ID, the doctrine text governs; the entry is a pointer, not a restatement.
2. Grounding entries never authorize deviation from doctrine. Deviation still requires an
   ADR (`.agents/doctrine/README.md`).
3. Grounding is context, not scope: reading a file here never expands a task's write scope,
   budget, or authority.

## Load discipline — this library must not become a distraction

- Load **only the files the trigger table maps to the decision at hand** — usually one or
  two, three at most. Never bulk-load the directory; breadth lives on disk, not in context.
- Architect role: consult the matching files while drafting a spec, plan, or ADR, and answer
  each loaded file's **Design checklist** in the artifact (alongside the design
  interrogation in `.agents/doctrine/decision-frameworks.md`). A checklist question that is
  irrelevant is answered "n/a" — silently skipping one is how gaps ship.
- Implementer role: consult the matching files when a task touches the domain; use the
  checklist as a self-review pass before claiming `AUTHOR_READY`.
- Reviewer/auditor roles: use the checklists as probes — an unanswered applicable question
  in a plan is a finding.
- When an entry changes a decision, cite the concept by name in the plan or review comment
  so the reasoning is auditable.

## Trigger table

| You are about to… | Load |
|---|---|
| Shape modules, boundaries, or abstractions; judge a refactor | `01-design-principles.md` |
| Pick a pattern, architectural style, or service split; model a domain | `02-patterns-and-architecture.md` |
| Write or review code, name things, structure commits/branches, design tests | `03-writing-code.md` |
| Design a schema, query, index, transaction, or migration | `04-data-storage.md` |
| Replicate, shard, cache, or move data between stores; add analytics or search | `05-data-scale.md` |
| Add a queue, event, stream, or background job | `06-messaging-and-events.md` |
| Span more than one node/region; reason about consistency, consensus, or time | `07-distributed-systems-theory.md` |
| Call anything remote; design for failure, overload, or disaster recovery | `08-resilience.md` |
| Touch threads, async, memory, processes, signals, or the OS boundary | `09-runtime.md` |
| Set latency/throughput targets; scale, load-test, or optimize | `10-performance-and-scale.md` |
| Cross the network: DNS, TCP/TLS, HTTP, proxies, load balancers, CDNs, browsers | `11-networking-and-web.md` |
| Build UI: components, state, rendering, a11y, i18n, web performance | `12-frontend.md` |
| Design or evolve an API, webhook, or wire contract | `13-apis-and-contracts.md` |
| Provision cloud/infra, containerize, orchestrate, ship through CI/CD or IaC | `14-infrastructure-and-delivery.md` |
| Add telemetry, alerts, SLOs; prepare for on-call and incidents | `15-observability-and-operations.md` |
| Handle untrusted input, authn/authz, secrets, crypto, or sensitive data | `16-security.md` |
| Make a choice with a cloud bill attached | `17-finops.md` |
| Build on or with LLMs: prompts, RAG, tools, evals, agent loops | `18-ai-llm-engineering.md` |
| Choose a data structure or algorithm; handle scale in-process | `19-algorithms.md` |
| Plan delivery, team process, docs, migrations, deprecations | `20-process-and-laws.md` |

Cross-cutting decisions load the intersection: e.g. "add a Redis cache" → `05-data-scale.md`
+ `08-resilience.md`; "new public endpoint" → `13-apis-and-contracts.md` + `16-security.md`.

## File anatomy

Every file has the same shape, so it can be skimmed in seconds:

- **Load when** — the triggers, restated locally.
- **Doctrine hooks** — the doctrine IDs the domain touches.
- **Design checklist** — 6–12 questions; the distillation. If time is short, use only this.
- **Concept sections** — one bullet per concept: bold term, the gotcha or heuristic, and
  doctrine cross-references in *(italics)*.

## Maintenance

This library is maintained reference, not doctrine: it lives in `agent_docs/` and changes by
normal PR. When an entry hardens into a rule this repository should enforce, promote it into
`.agents/doctrine/` through a control-plane PR and leave the entry pointing at the new ID.
When an incident or review reveals a missing concept, add it to the matching file in the
same spirit: heuristic phrasing, one bullet, no essays.
