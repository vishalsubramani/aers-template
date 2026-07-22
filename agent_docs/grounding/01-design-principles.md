# Grounding — Software design principles & anti-patterns

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing module boundaries, abstractions, interfaces, refactors, or any
plan/diff where "is this the right structure?" or "is this smell worth a comment?" is in question.
**Doctrine hooks:** AX-01..AX-08, AX-10..AX-13, AX-16..AX-21, DD-07, DD-17, PAT-01, PAT-02, PAT-06,
PAT-16, PAT-17, DF-01..DF-06

## Design checklist

- [ ] Can each touched module's responsibility be stated in one sentence, and does the diff touch
      only modules whose sentence changed? *(AX-03)*
- [ ] Does any abstraction here exist before its third concrete use — and what future is it betting
      on? *(AX-17)*
- [ ] Is behavior composed from small explicit interfaces rather than inherited from open-ended base
      classes? *(AX-07)*
- [ ] Are invalid states unrepresentable in the types/schema, or merely validated somewhere?
      *(AX-08, PAT-01)*
- [ ] Is every externally-triggered mutation safe when delivered twice? *(AX-10, PAT-06)*
- [ ] Does every piece of mutable shared state have one declared owner — and could it be immutable
      instead? *(AX-12)*
- [ ] Does each fact have one authoritative home, with every copy a rebuildable projection carrying
      a staleness bound? *(DD-17, PAT-09)*
- [ ] Would a maintainer be surprised by anything here — a misleading name, hidden side effect, or
      unexpected default? *(AX-19)*
- [ ] What does this change delete — dead code, flags, dependencies — not just add? *(AX-20)*
- [ ] Is every novel technology or pattern choice a deliberate, ADR-recorded innovation token?
      *(AX-01, DF-04)*

## Software design principles

- **Separation of concerns** — if one change request fans out across unrelated modules, concerns are
  tangled; redraw the boundary before adding more features to it *(AX-03)*.
- **Single Responsibility Principle** — test: name the one actor whose requirement change forces
  this module to change; two actors means split it *(AX-03)*.
- **Open/Closed Principle** — extend via new implementations behind stable interfaces rather than
  editing shipped ones; but don't pre-build extension points nobody asked for *(AX-02, AX-17)*.
- **Liskov Substitution Principle** — a subtype that strengthens preconditions, weakens
  postconditions, or throws "not supported" breaks callers silently; prefer composition over forcing
  the hierarchy *(AX-07)*.
- **Interface Segregation Principle** — fat interfaces force clients to depend on methods they never
  call; split by consumer and export the minimum *(AX-05)*.
- **Dependency Inversion Principle** — domain code imports interfaces it defines; infrastructure
  implements them. A driver/SDK import inside business logic is the review flag *(AX-04, PAT-02)*.
- **DRY vs. the wrong abstraction** — deduplicate knowledge (rules, constants), not coincidentally
  similar code; a shared helper sprouting boolean parameters means re-inline it *(AX-17)*.
- **KISS** — the simplest design meeting the contract wins review ties; added complexity must name
  what it buys *(AX-17, AX-19)*.
- **YAGNI** — build for the approved contract, not imagined futures; speculative capability is
  negative value because it must be maintained and later removed *(AX-17)*.
- **Rule of three** — tolerate duplication until the third occurrence proves the abstraction's real
  shape; two instances usually guess it wrong *(AX-17)*.
- **Composition over inheritance** — reach for inheritance only for true is-a substitutability; deep
  hierarchies and open-ended base classes need justification *(AX-07)*.
- **High cohesion, loose coupling** — measure by change ripple: related things change together in
  one place, and unrelated changes never collide *(AX-03, AX-04)*.
- **Encapsulation & information hiding** — hide the decisions likely to change (storage shape,
  algorithm) behind the interface; a leaked internal becomes a compatibility promise *(AX-03, AX-05)*.
- **Law of Demeter** — chains like `a.getB().getC().do()` hard-code the object graph into every
  caller; ask the immediate collaborator to do it instead *(AX-03)*.
- **Principle of least astonishment** — a surprise (misleading name, hidden side effect, odd
  default) is a defect even when the code is correct; fix the surprise, not the reader *(AX-19)*.
- **Principle of least privilege** — every component, token, and job gets the minimum access needed;
  deny by default and review permission scope like code *(PAT-17)*.
- **Fail fast** — detect bad state at the earliest boundary (startup config, input parse) and stop
  loudly; limping onward corrupts data downstream *(AX-11, PAT-16)*.
- **Design by contract** — state preconditions, postconditions, and invariants explicitly (types,
  asserts, schemas) so violations fail at the boundary, not three calls later *(AX-06, AX-08, PAT-01)*.
- **Idempotence** — retries and redelivery are inevitable; design every externally-triggered
  mutation to be safe delivered twice before it ships, not after the incident *(AX-10, PAT-06)*.
- **Immutability** — the default for values and shared data; mutation requires a named owner.
  Immutable data deletes whole classes of aliasing and concurrency bugs *(AX-12)*.
- **Pure functions & referential transparency** — push I/O, clocks, and randomness to the edges so
  the core is deterministic and trivially testable; a buried `now()` call is a review flag *(AX-16)*.
- **Convention over configuration** — follow the repo/framework convention unless a contract forces
  deviation; every knob exposed is surface to validate, document, and support *(AX-13, PAT-16)*.
- **Single source of truth** — every fact gets one authoritative home; each copy needs an owner, a
  rebuild path, and a staleness bound or it silently diverges *(DD-17, PAT-09)*.
- **Orthogonality** — features should combine without special cases; if enabling X changes Y's
  behavior, that coupling must become explicit or be removed *(AX-03)*.
- **Leaky abstractions** — every abstraction leaks under load, failure, or latency; wrap
  dependencies thinly and know what the layer hides rather than pretending it doesn't *(PAT-02)*.
- **Twelve-Factor App** — config from environment, stateless processes, logs to stdout, disposable
  workers; local disk state and in-code config are the review flags *(AX-13)*.
- **Postel's law & its critiques** — "liberal in what you accept" breeds divergent parsers and
  security holes; the modern default is strict, versioned contracts — parse, don't tolerate
  *(AX-06, PAT-01)*.
- **Make it work, make it right, make it fast** — in that order, with evidence gates: don't refactor
  before it works or optimize before a measurement *(AX-18)*.
- **Premature optimization vs. premature pessimization** — skip needless micro-tuning, but don't
  bake in O(n²) or chatty I/O when the obvious design is equally clear; architecture is expensive to
  fix later *(AX-18)*.
- **Boring technology / innovation tokens** — novelty is a budget spent deliberately in an ADR,
  never a task-level choice; pick what the team can debug at 3am *(AX-01, DF-04)*.
- **Unix philosophy** — small tools with one job, composed through simple stream/text interfaces; a
  component you can't describe without "and" wants splitting *(AX-03, AX-07)*.
- **Mechanical sympathy** — know the costs your abstractions sit on (cache lines, syscalls, network
  round trips) and shape data access to flow with them — once measurement says it matters *(AX-18)*.
- **Hyrum's law** — with enough users, every observable behavior becomes a contract; changing
  timing, ordering, or error text is a breaking change regardless of what the docs promise
  *(AX-05, AX-06)*.
- **Chesterton's fence** — before deleting odd code, learn why it exists (blame, tests, ADRs); if no
  reason surfaces, delete deliberately with evidence, never silently *(AX-20)*.

## Anti-patterns & code smells

- **Big ball of mud** — the absence of enforced boundaries; fix by drawing one boundary at a time
  behind an interface, never by a big-bang rewrite *(AX-02, AX-03)*.
- **God object** — the class/module everything depends on and every diff touches; split by
  responsibility before it becomes the merge-conflict and test bottleneck *(AX-03)*.
- **Spaghetti / lasagna / ravioli code** — no structure, too many pass-through layers, and too many
  tiny pieces all hurt; each layer must earn its keep by hiding a real decision *(AX-03, AX-19)*.
- **Golden hammer** — reaching for the familiar tool regardless of fit; state context, options, and
  trade-offs per the decision frameworks before defaulting *(DF-01..DF-06)*.
- **Cargo-cult programming** — adopting a practice without the context that justified it; "best
  practice" without a named trade-off is not a recommendation — demand the causal story *(AX-18)*.
- **Copy-paste programming** — cloned logic diverges silently as fixes land in one copy;
  deduplicate knowledge at the third occurrence and flag clones in review *(AX-17)*.
- **Magic numbers & strings** — unexplained literals hide intent and invite typo bugs; name them,
  and constrain enumerations in types or schema, never free strings *(AX-19, DD-07)*.
- **Shotgun surgery** — one logical change requiring edits in many places means the concept has no
  home; consolidate before the next change misses a spot *(AX-03)*.
- **Feature envy** — a method that mostly reads another object's data belongs on that object; move
  the behavior to the data *(AX-03)*.
- **Primitive obsession** — raw strings/ints for domain concepts (IDs, money, emails) let any value
  cross any boundary; introduce typed wrappers so illegal states can't be built *(AX-08, DD-07)*.
- **Data clumps** — the same trio of parameters traveling together is a missing type; name it and
  its invariants come along for free *(AX-08)*.
- **Long parameter lists** — beyond three or four, callers transpose arguments and defaults sprawl;
  group into typed objects and reconsider the function's responsibility *(AX-19)*.
- **Speculative generality** — hooks, parameters, and layers with one implementation and no second
  in sight; delete now — version control remembers *(AX-17, AX-20)*.
- **Dead code & lava flow** — unused code and "don't touch, unclear why" code both tax every reader;
  delete deliberately after a Chesterton's-fence check *(AX-20)*.
- **Boat anchor** — the dependency or component kept "in case we need it"; every retained artifact
  costs upgrades and security surface — remove it *(AX-20, AX-21)*.
- **Inner-platform effect** — configurable systems that reimplement their platform badly (rules
  engines, entity-attribute-value schemas); use the language and database directly *(AX-01)*.
- **Not-invented-here syndrome** — building what a vetted library or service already does; walk the
  build-vs-buy ladder and record why the external options lose *(DF-04, AX-21)*.
- **Stringly-typed code** — structure encoded in strings (comma lists, status codes, JSON-in-a-
  column) defeats compiler and database alike; parse into typed structures at the boundary
  *(AX-08, PAT-01, DD-07)*.
- **Boolean blindness** — `f(true, false)` call sites and bare bool returns erase meaning; use enums
  or named types so intent survives to the reader and the type checker *(AX-08, AX-19)*.
- **Global mutable state** — invisible coupling between everything that touches it and a concurrency
  bug in waiting; give state one declared owner or make it immutable *(AX-12)*.
- **Hidden coupling & temporal coupling** — "call init() before use" and order-sensitive steps
  nothing enforces; make ordering explicit via types/constructors or collapse the steps
  *(AX-03, AX-08)*.
- **Callback hell** — deep async nesting hides control flow and drops error paths; flatten with the
  language's structured async and verify every path handles failure *(AX-11, AX-19)*.
- **Second-system effect** — the follow-up design bloated with everything version one deferred;
  evolve incrementally, and treat any rewrite as an R2+ ADR decision *(AX-02, AX-15)*.
- **Resume-driven development** — technology chosen for careers, not the mission; each novelty is an
  innovation token requiring ADR-recorded justification *(AX-01, DF-04)*.
