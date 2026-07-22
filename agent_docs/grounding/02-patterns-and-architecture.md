# Grounding — Design patterns, architectural styles & DDD

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** drawing module/service boundaries, choosing an architectural style, planning a
migration or extraction, modeling a domain, reviewing class-level design, or introducing concurrency.
**Doctrine hooks:** AX-01..AX-12, AX-15, AX-17..AX-21, DD-01, DD-02, DD-04, DD-07, DD-14..DD-17,
PAT-02, PAT-03, PAT-05..PAT-07, PAT-11..PAT-14, PAT-17, PAT-20, DF-01..DF-06

## Design checklist

- [ ] Is each pattern resolving a named force, or applied for its own sake *(AX-17)*? Two fixed
      variants rarely justify a pattern.
- [ ] Do dependencies point inward — domain core free of framework, ORM, and vendor imports
      *(AX-04, PAT-02)*?
- [ ] Is this the modular-monolith default, or is a service split justified by a named DF-01
      driver (scaling, cadence, fault isolation, ownership)?
- [ ] Do module boundaries follow bounded contexts, with translation at integration seams
      instead of shared models?
- [ ] Does each aggregate get one repository, and does the transaction boundary match the
      aggregate boundary *(PAT-03, DD-16)*?
- [ ] For every async/event edge: how are duplicates, ordering, and eventual consistency
      handled *(DF-03, PAT-12)*?
- [ ] Does every piece of shared mutable state have one declared owner — lock, actor, single
      writer, or database *(AX-12)*?
- [ ] Are CQRS, event sourcing, or a multi-tenancy model being introduced without an ADR
      naming the trade-off *(DF-02, DD-17)*?
- [ ] Is the migration incremental — strangler fig or branch by abstraction — rather than a
      rewrite or long-lived branch *(AX-02, AX-15)*?
- [ ] Are money and precise quantities exact types wrapped in value objects *(DD-07)*?

## Design patterns — Gang of Four

### Creational

- **Singleton** — global mutable state in disguise; hurts tests and concurrency *(AX-12)*. Default:
  one instance injected from the composition root, used sparingly if at all.
- **Factory Method** — use when construction varies by subtype; if it only hides a `new`, a plain
  function is enough *(AX-17)*.
- **Abstract Factory** — only when families of related objects must stay mutually consistent
  (per-backend adapter sets, PAT-02); otherwise ceremony.
- **Builder** — earns its place at many optional parameters or staged validation; prefer named/
  keyword arguments where the language has them *(AX-17)*.
- **Prototype** — clone-based construction; the gotcha is shallow copies aliasing mutable fields,
  a classic source of spooky shared state *(AX-12)*.

### Structural

- **Adapter** — the mechanism behind PAT-02: wrap third-party interfaces at the boundary so the
  domain never imports vendor types *(AX-03)*.
- **Bridge** — split abstraction from implementation only when both axes vary independently; one
  varying axis needs just an interface *(AX-17)*.
- **Composite** — uniform treatment of items and groups; verify every operation makes sense on
  both, or leaf-only methods leak into the shared interface.
- **Decorator** — layer cross-cutting behavior (retry, cache, logging) without touching the
  wrapped class; stacking order is behavior — fix it in the composition root *(PAT-05)*.
- **Facade** — one narrow entry point over a messy subsystem keeps the public surface small
  *(AX-05)*; watch it accreting into a god object.
- **Flyweight** — share immutable intrinsic state to cut memory, only with a measurement proving
  the footprint problem *(AX-18)*.
- **Proxy** — same interface, added control (lazy load, access check, remoting); the gotcha is
  hidden I/O behind an innocent call — keep latency and failure visible *(AX-09)*.

### Behavioral

- **Chain of Responsibility** — handler/middleware pipelines; make fall-through explicit — a
  request no handler claims must fail loudly, never vanish *(AX-11)*.
- **Command** — reify an action as data to queue, log, retry, or undo; pairs with background jobs
  *(PAT-07)* and needs idempotency keys on redelivery *(PAT-06)*.
- **Interpreter** — small DSLs only; first ask whether a config schema or existing expression
  library suffices *(AX-17, AX-21)*.
- **Iterator** — language-native now; the live concern is invalidation — mutating a collection
  while iterating it, especially across threads *(AX-12)*.
- **Mediator** — centralizes many-to-many object chatter; keep it routing, not deciding, or it
  becomes the god object it was meant to prevent.
- **Memento** — state snapshots for undo/rollback without breaking encapsulation; if snapshots
  persist, they are a versioned schema *(DD-02)*.
- **Observer** — in-process pub/sub; gotchas are unsubscribed-listener leaks, hidden execution
  order, and one observer's exception silently killing the rest *(AX-11)*.
- **State** — replace state-flag conditionals with one type per state; makes illegal transitions
  unrepresentable *(AX-08)*.
- **Strategy** — swap algorithms behind an interface; the composition-over-inheritance workhorse
  *(AX-07)*. Two fixed variants may just be a function parameter *(AX-17)*.
- **Template Method** — inheritance-based hook points are an implicit fragile contract; prefer
  Strategy/composition *(AX-07)*.
- **Visitor** — double dispatch over a closed hierarchy; adding a type breaks every visitor, so
  use only when operations vary faster than types — sum types with pattern matching often
  supersede it *(AX-08)*.

### Honorable additions

- **Object Pool** — only for genuinely expensive resources (connections, threads), with a
  measurement otherwise *(AX-18)*; reset state on return or leak data across borrowers.
- **Lazy Initialization** — moves cost and failure to first use and invites races; guard with the
  language's blessed idiom *(AX-12)*.
- **Null Object** — kills null-checks but silently swallows calls; never use where absence is an
  error that must surface *(AX-11)*.
- **Specification** — composable predicate objects for business rules/queries; justified only
  when rules combine dynamically, else plain functions *(AX-17)*.

## Enterprise & data-access patterns

- **Repository** — the repo default for persistence *(PAT-03)*; keep it per-aggregate and
  intention-revealing, not a generic CRUD wrapper leaking ORM/query types across boundaries.
- **Unit of Work** — one transaction per use case, matching the invariant boundary *(DD-16)*; it is
  usually the ORM session — do not hand-roll a second one alongside it.
- **Active Record vs Data Mapper** — Active Record suits CRUD-simple contexts; complex invariants
  need Data Mapper so domain objects stay persistence-free *(PAT-02)*. Choose once, in an ADR.
- **DTOs** — separate wire/API shapes from domain objects; exposing entities directly welds the
  persistence schema to the public contract *(AX-06, DD-02)*. Skip inside one module.
- **Identity Map** — one in-memory instance per entity per session prevents lost updates from
  duplicate loads; your ORM already has one — learn its cache scope before "fixing" stale reads.
- **Service Layer** — thin use-case orchestration over the domain; when it holds business rules,
  the model has gone anemic (see DDD below).
- **Gateway** — one class owns each external system's protocol details *(PAT-02)* with timeout/
  retry/breaker applied there *(PAT-05)*; vendor SDK types never cross into domain code.
- **Money pattern** — amount plus currency code as an immutable value object in integer minor
  units or decimals, never binary floats *(DD-07)*; mixing currencies must not typecheck *(AX-08)*.

## Concurrency patterns

- **Producer–Consumer** — decouples rates via a queue, but the queue must be bounded with a
  stated full-queue policy (block, drop, shed) — unbounded queues turn overload into OOM *(PAT-20)*.
- **Reactor / Proactor** — event-loop I/O (async runtimes); one blocking or CPU-heavy call stalls
  every connection — keep such work off the loop and in a pool.
- **Thread Pool** — size for the workload (CPU vs I/O bound) and bound the submission queue
  *(PAT-20)*; never block a pool task waiting on another task in the same pool — a deadlock class
  *(AX-12)*.
- **Future / Promise** — an unawaited future swallows its exception *(AX-11)*; every await needs a
  timeout *(AX-09)*; blocking synchronously on async results deadlocks single-threaded runtimes.
- **Monitor Object** — mutex plus condition variable; document the invariant the lock protects
  *(AX-12)* and always wait in a loop against spurious wakeups.
- **Read–Write Lock** — pays off only for read-heavy, long-hold workloads; under short holds a
  plain mutex is faster, and writers can starve. Consider immutable snapshots instead *(AX-12)*.
- **Double-Checked Locking** — subtly broken without correct memory ordering (volatile/atomics);
  use the language's blessed lazy-init idiom rather than writing it *(AX-01, AX-12)*.
- **Pipeline** — stage-parallel processing; throughput equals the slowest stage, and stages need
  backpressure between them or the fastest stage floods memory *(PAT-20)*.
- **Actor Model** — single-threaded message handling gives clean state ownership *(AX-12)*, but
  messages can be lost, reordered, or duplicated — apply event discipline *(AX-10)* and bound
  mailboxes *(PAT-20)*.

## Architectural styles & tradeoffs

- **Layered (n-tier)** — fine default for simple apps; enforce downward-only dependencies with a
  lint *(AX-04)* or it rots, and watch the sinkhole smell of every change touching every layer.
- **Hexagonal (Ports & Adapters)** — the repo's boundary default *(PAT-02)*: domain defines ports,
  infrastructure adapts, and the core tests without I/O.
- **Clean / Onion Architecture** — same inward-dependency rule as hexagonal; the invariant is
  direction *(AX-04)*, not layer count — don't cargo-cult four layers into a small service *(AX-17)*.
- **MVC / MVP / MVVM** — UI-separation variants; the shared rule is logic out of views so it is
  testable — follow the framework's native idiom rather than fighting it *(AX-01)*.
- **Microkernel (plugin architecture)** — stable core plus plugins; justified when third parties
  or optional features extend the system, and the plugin API is a versioned public contract
  *(AX-05, AX-06)*.
- **Pipes & Filters** — composable independent stages (ETL, stream jobs); keep filters stateless
  for reordering/parallelism and give mid-pipe failures a dead-letter path *(PAT-07)*.
- **Event-Driven Architecture** — buys decoupling, costs traceability and consistency; decide per
  interaction *(DF-03)*, events carry versioned facts *(PAT-12)*, correlation IDs mandatory *(PAT-13)*.
- **Space-Based Architecture** — in-memory data grids for extreme burst load; the consistency
  story is expensive, so it needs measured load, not anticipated load *(AX-18, DF-02)*.
- **Serverless architecture** — no servers but cold starts, execution limits, and vendor
  coupling; keep domain logic portable behind ports *(PAT-02)* and price sustained load before
  committing *(DF-06)*.
- **Service-Oriented Architecture** — the historical lesson: smart ESBs and shared canonical
  schemas recreate coupling in middleware; keep integration logic in endpoints, not the bus.
- **Monolith → Modular Monolith → Microservices** — the ordering is doctrine: default modular
  monolith *(DF-01)*; extract a service only for a named driver, one at a time *(AX-15)*.
- **Distributed monolith** — the failure mode: services that deploy together or chain synchronous
  calls; if extraction didn't buy independent deployability, you paid network cost for nothing
  *(DF-01, AX-09)*.
- **Nanoservices** — the overcorrection: per-function services whose operational overhead exceeds
  their value; size services by bounded context, never by "smaller is better."
- **Strangler Fig migration** — route through a facade and replace the legacy slice by slice
  *(AX-02, AX-15)*; schedule deletion of strangled parts *(AX-20)* or you operate two systems forever.
- **Branch by Abstraction** — the in-repo strangler: seam interface, two implementations, a flag
  to switch *(PAT-14)*, delete the old path — large refactors on trunk, no long-lived branch.
- **Backend for Frontend (BFF)** — per-client API layer; use when client needs genuinely diverge,
  else it is N copies of one aggregation. It aggregates — business rules stay in the domain.
- **CQRS** — split read/write models only when read-shape divergence or load proves it; it
  doubles the surfaces to keep consistent, so it needs an ADR *(DF-02, DD-17)*.
- **Event Sourcing** — buys audit and temporal queries; costs event-schema versioning forever,
  replay infrastructure, and hard deletes *(DD-15)*. Almost never the default *(AX-01)* — state plus
  an audit log usually suffices.
- **Cell-based architecture** — shard the whole stack into independent cells to cap blast radius;
  requires a cell router and per-cell capacity management — a large-scale, ADR-level choice.
- **Shared-nothing architecture** — nodes hold no shared state so scale-out is linear; state
  concentrates in the data tier and the partition key becomes the critical design choice *(DF-05)*.
- **Multi-tenancy models: silo / bridge / pool** — choose per data classification and isolation
  requirement *(DD-14)*; pool is cheapest, silo strongest, and the choice is nearly irreversible
  once tenant data lands — ADR up front.
- **Tenant isolation & noisy neighbors** — in pooled tenancy every query is tenant-scoped through
  one enforced mechanism (e.g., RLS, PAT-17), and per-tenant quotas stop one tenant starving the
  rest *(PAT-20)*.

## Domain-Driven Design

- **Ubiquitous language** — code names must match domain-expert vocabulary within a context
  *(AX-19)*; a translation gap between code and conversation is where requirement bugs breed.
- **Bounded contexts** — the primary input for module/service boundaries *(AX-03, DF-01)*; one term
  meaning two things ("customer" in billing vs support) signals a boundary, not a shared model.
- **Context mapping** — name the relationship at each integration seam before wiring it: a
  **shared kernel** couples release cadences (use sparingly); **customer–supplier** and
  **conformist** encode who absorbs whose changes *(AX-03)*.
- **Anti-corruption layer / published language** — the defaults at foreign seams: an ACL
  translating the external model into your own *(PAT-02)*, or a versioned published language as
  the shared contract *(AX-06)*.
- **Subdomains: core / supporting / generic** — spend design effort on the core; buy or CRUD the
  generic and supporting ones *(DF-04)* — gold-plating a generic subdomain wastes innovation
  tokens *(AX-01)*.
- **Entities vs Value Objects** — identity vs values: default to immutable value objects *(AX-08,
  AX-12)* for money, ranges, addresses *(DD-07)*; entities carry stable surrogate IDs *(DD-04)*.
- **Aggregates & aggregate roots** — the consistency boundary: one transaction per aggregate
  *(DD-16)*, external references by root ID only, cross-aggregate consistency eventual via events
  *(PAT-11)*. A large aggregate is a contention smell.
- **Domain events** — past-tense facts published via the outbox in the owning transaction
  *(PAT-11)*, never dual-written; consumers handle duplicates and reordering *(AX-10, PAT-12)*.
- **Domain services vs application services** — domain services hold multi-entity domain logic;
  application services orchestrate use cases (transactions, authorization, ports). Business
  rules drifting into application services signals an anemic model.
- **Repositories & factories** — one repository per aggregate root only *(PAT-03)* — repositories
  for interior entities break the boundary; factories keep complex construction invariant-safe
  *(AX-08)*.
- **Anemic domain model (smell)** — data classes plus logic-in-services scatters invariants;
  acceptable in CRUD contexts, a smell in the core subdomain — move behavior onto the entities
  owning the state *(AX-03)*.
- **Event storming** — a cheap workshop to surface bounded contexts, aggregates, and events
  before code; run it before committing boundaries — moving one later is expensive *(DD-01,
  AX-15)*.
