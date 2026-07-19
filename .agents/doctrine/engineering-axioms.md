# Engineering Axioms

Stack-neutral axioms every design and diff is held against. Cite IDs in plans
and ADRs. Deviation requires an ADR naming the axiom (see `README.md`).

## Architecture

- **AX-01 Boring technology by default.** Prefer proven, widely-operated
  technology the team can debug at 3am. Each genuinely novel choice is a
  spent innovation token recorded in an ADR.
- **AX-02 Evolve, don't rewrite.** Extend and refactor incrementally behind
  stable interfaces. A rewrite is an R2+ decision with an ADR, a migration
  plan, and a parallel-run or cutover strategy — never a task-level choice.
- **AX-03 Explicit boundaries.** The system is modules with named public
  interfaces; everything else is private. Cross-module access goes through the
  interface, never through internals, file reach-ins, or shared mutable state.
- **AX-04 One-way dependencies.** Dependency direction is declared (core
  domain depends on nothing; adapters depend on the domain, never the
  reverse) and cycles are forbidden. Enforce with an architecture test or
  import linter wired into `make check`.
- **AX-05 Smallest public surface.** Export the minimum. Every public
  interface is a compatibility promise; keeping something private is free,
  un-publishing it is a breaking change.
- **AX-06 Contract-first at the edges.** External interfaces (APIs, events,
  files, CLIs) are specified before implementation, versioned explicitly, and
  changed backward-compatibly: additive first; removal only after a
  deprecation window with a stated timeline.
- **AX-07 Composition over inheritance.** Behavior is assembled from small
  parts with explicit interfaces. Deep inheritance hierarchies and open-ended
  base classes are design smells requiring justification.
- **AX-08 Make illegal states unrepresentable.** Use the type system and
  schema constraints so invalid combinations cannot be constructed, instead
  of validating them away at runtime in scattered places.

## Behavior under failure

- **AX-09 Design for failure at every boundary.** Every remote or cross-process
  call has an explicit timeout, a bounded retry policy with backoff and
  jitter, and a defined behavior when the dependency is down (degrade, queue,
  or fail fast) — never unbounded waiting or silent loss.
- **AX-10 Idempotency at the edges.** Any externally-triggered mutation is
  safe to deliver twice (idempotency keys, natural dedup, or compare-and-set).
  Exactly-once is a property you construct, not one you assume.
- **AX-11 Errors are part of the interface.** Expected failures are typed,
  documented outcomes handled at the boundary; unexpected failures fail fast
  and loudly. Never swallow an error without recording it; never use
  exceptions for control flow.
- **AX-12 Explicit concurrency ownership.** Every piece of mutable shared
  state has one declared owner (a lock, an actor, a single writer, the
  database). Immutability is the default; unsynchronized sharing is a bug
  even when it hasn't fired yet.

## Operability and change

- **AX-13 Configuration is environment, not code.** Behavior toggles, limits,
  and endpoints come from declared, validated configuration with safe
  defaults. No environment-specific branches in code; no secrets in code,
  config files, or logs — secrets come from a secret store at runtime.
- **AX-14 Observability is a feature requirement.** Every feature ships with
  structured logs for its decisions, metrics for its rates and failures, and
  trace propagation across its boundaries — specified in the plan, not
  retrofitted after an incident.
- **AX-15 Small reversible steps.** Prefer the smallest change that can ship,
  behind a flag when risk warrants, with a tested rollback. If a change
  cannot be reverted cheaply, that fact must appear in the plan's rollout
  section and raise the risk tier.
- **AX-16 The test pyramid is load-bearing.** Fast deterministic unit tests
  dominate; integration tests cover real boundaries; end-to-end tests are few
  and high-value. New behavior arrives with a test that fails without it — the
  differential gate proves this mechanically for test-author tasks that
  declare a `differential` spec (the default in the templates; omit it only
  for characterization tests of existing behavior, which legitimately pass on
  base).

## Simplicity

- **AX-17 YAGNI, with the rule of three.** Build for the requirement in the
  contract, not imagined futures. Abstract only after the third concrete
  occurrence proves the shape; a premature framework is harder to remove
  than duplication.
- **AX-18 Optimize with evidence.** Correct and clear first. Performance work
  requires a measurement showing the problem and a measurement showing the
  fix; both belong in the evidence packet.
- **AX-19 Code is read far more than written.** Choose clarity over
  cleverness, names that state intent, and comments that record only what the
  code cannot say (constraints, invariants, why-not-the-obvious-way).
- **AX-20 Delete what is dead.** Unused code, flags, and dependencies are
  removed, not commented out or kept "just in case" — version control is the
  archive.
- **AX-21 Dependencies are liabilities.** Prefer the standard library, then a
  dependency already in the tree, then — only for real complexity — a new one.
  Adding a runtime dependency is a plan-level decision, named in the plan with
  its license, maintenance health, and transitive surface considered; versions
  are pinned through a committed lockfile and vetted by `make security`.
  Trivial functionality is written, not imported.
