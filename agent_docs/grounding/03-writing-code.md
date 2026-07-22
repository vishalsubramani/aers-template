# Grounding — Writing code: practices, naming, version control, testing

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** implementing or reviewing any diff — function structure, error handling, naming,
commit/branch strategy, or designing the test plan for a task.
**Doctrine hooks:** AX-08, AX-11, AX-15, AX-16, AX-17, AX-19, AX-20, AX-21, PAT-01, DF-04

## Design checklist

- [ ] Is every expected failure a typed, handled outcome, and every unexpected one loud — no
      swallowed errors anywhere in the diff? *(AX-11)*
- [ ] Is external input parsed into typed structures at one boundary, with the interior trusting
      its types instead of re-validating defensively? *(PAT-01, AX-08)*
- [ ] Do names state intent, use the codebase's existing vocabulary, and follow the language's
      idiom — with units and boolean prefixes where they apply? *(AX-19)*
- [ ] Does every new behavior arrive with a test that fails without it, at the lowest pyramid
      level that can prove it? *(AX-16)*
- [ ] Are the tests hermetic — time frozen, randomness seeded, no shared state — so they pass in
      parallel and in any order?
- [ ] Is the change one atomic, revertible commit series with a PR small enough to review
      properly? *(AX-15)*
- [ ] Are new dependencies justified against stdlib-first order, pinned, and lockfile-committed?
      *(AX-21, DF-04)*
- [ ] Is anything the diff made dead — code, flags, comments-as-archive — actually deleted?
      *(AX-20)*
- [ ] Would a reader need a comment to know *why*; and if so, is that comment present and is
      nothing else commented? *(AX-19)*

## Coding best practices

- **Small functions, single level of abstraction** — a function mixing policy and mechanics is
  the smell; extract until each reads at one level. Size follows from that, not a line count.
  *(AX-19)*
- **Guard clauses & early returns**, **shallow nesting** — handle rejects first and return;
  three-plus indent levels means invert conditions or extract, not add an else branch.
- **Cyclomatic & cognitive complexity limits** — enforce via linter thresholds in `make check`;
  the fix for a violation is decomposition, never raising the limit per-file.
- **Parse, don't validate** — convert raw input into a type that cannot hold the invalid case;
  a boolean check that's forgettable downstream is the anti-pattern. *(PAT-01, AX-08)*
- **Make illegal states unrepresentable** — if two fields can contradict each other, redesign
  the type (sum types, enums, constraints) instead of documenting the rule. *(AX-08, DD-07)*
- **Null safety (Option/Maybe types)** — make absence explicit in the signature; a nullable that
  "is never null in practice" is a latent crash. Pairs with DD-05 for persisted data.
- **Errors as values vs exceptions** — pick one strategy per codebase and be consistent; mixing
  them means callers miss failures on whichever channel they forgot. *(AX-11)*
- **Never swallow exceptions** — an empty catch or log-and-continue hides the first failure and
  ships the second; handle it, wrap it, or let it crash loudly. *(AX-11)*
- **Error wrapping with context** — attach what operation failed on what input at each boundary;
  a bare "connection refused" five layers up is undebuggable. *(AX-11)*
- **Validate at the boundary, trust the core** — one validation layer at the edge; defensive
  re-checks scattered through the interior are noise that hides which check is load-bearing.
  *(PAT-01)*
- **Assertions & offensive programming** — assert invariants the types can't express so bugs
  fail at the cause, not two modules later; never assert on external input — that's validation.
- **Comments explain *why*; code explains *what*** — a comment restating the code rots into a
  lie; reserve comments for constraints, invariants, and why-not-the-obvious-way. *(AX-19)*
- **TODO/FIXME hygiene** — every TODO carries an owner and a ticket or it's a lie the codebase
  tells itself; review comments should reject anonymous ones.
- **Self-documenting code** — restructure and rename before commenting; if the explanation fits
  in a function name, the comment was a missing extraction. *(AX-19)*
- **Linting & auto-formatting** — end style debates by automation in `make check`; any style
  point a formatter can enforce is banned from human review. *(AX-19)*
- **Static analysis & type checking** — run in CI at maximum practical strictness from day one;
  ratcheting strictness up later costs a migration each notch.
- **Gradual typing** — in optionally-typed languages, type the boundaries and new code first,
  and ratchet coverage — never let untyped `Any` leak through a public interface.
- **Code coverage as a signal, not a target** — a coverage gate breeds assertion-free tests;
  read uncovered lines as risk hints and prove behavior with failing-first tests. *(AX-16)*
- **Boy Scout Rule** — improve what the diff already touches, but keep opportunistic cleanup
  inside the approved write scope; larger cleanups become their own task.
- **Refactoring as a habit, not a project** — continuous small refactors behind green tests;
  a scheduled "refactoring sprint" signals the habit already failed. *(AX-02, AX-15)*
- **Technical debt quadrant** — classify debt deliberate/inadvertent × prudent/reckless before
  arguing about it; deliberate-prudent debt gets a recorded revisit trigger, reckless gets fixed.
- **Dependency minimalism (standard library first)** — stdlib → dependency already in tree →
  new dependency, and only for real complexity; trivial functionality is written, not imported.
  *(AX-21, DF-04)*
- **Pin dependencies; commit lockfiles** — a floating version makes builds nondeterministic and
  turns a transitive release into an unreviewed deploy. *(AX-21)*
- **Vendoring tradeoffs** — vendor only for supply-chain isolation or a dead upstream; you
  inherit the update and CVE-patch burden, so record the decision and exit plan in an ADR.
- **Readability over cleverness** — code is read far more than written; a clever one-liner that
  needs a comment to decode should be the boring three lines. *(AX-19)*
- **Delete code fearlessly (version control remembers)** — commented-out blocks and "just in
  case" branches are noise with a perfect archive already in git. *(AX-20)*

## Naming conventions

- **Casing (camelCase, PascalCase, snake_case, SCREAMING_SNAKE_CASE, kebab-case)** — **follow
  the language's idiom, not your favorite one**; mixed conventions in one codebase make every
  identifier a guess and grep unreliable.
- **Intention-revealing names** — the name should answer why it exists and how it's used; if a
  reader must open the body to know, rename before shipping. *(AX-19)*
- **Searchable, pronounceable names** — single letters and clever abbreviations outside tiny
  scopes defeat grep and code discussion; `MAX_RETRIES` beats `mr` everywhere it matters.
- **One word per concept** — `fetch` vs `get` vs `retrieve`: pick one per codebase; synonyms
  make readers hunt for a semantic difference that doesn't exist.
- **Classes are nouns; functions are verbs** — a verb-named class or noun-named function usually
  marks a responsibility confusion worth a review comment, not just a rename.
- **Booleans: is/has/can/should — never negated** — `isNotDisabled` forces double-negative
  reasoning at every call site; name the positive and let callers negate.
- **Name length proportional to scope length** — `i` is fine in a three-line loop and a bug in a
  module-level export; the wider the visibility, the more context the name must carry.
- **Units in names** — `timeoutMs`, `sizeBytes`: unit-free numerics cause silent
  seconds-vs-milliseconds bugs; encode the unit in the name or, better, the type. *(DD-07)*
- **Avoid noise words: Manager, Helper, Util, Data, Info** — they name a dumping ground, not a
  responsibility; a `FooManager` in a diff is a design question, not a style nit.
- **Avoid Hungarian notation** — type prefixes (`strName`, `iCount`) duplicate what the type
  system already tracks and rot the moment the type changes.
- **Plural names for collections** — `users` for the list, `user` for the element; a singular
  name holding a collection reliably produces off-by-one thinking in reviews.
- **Consistent domain vocabulary (ubiquitous language)** — code uses the domain's own terms,
  identically to specs and conversation; a code-only synonym for a domain concept is a bug farm.
- **REST resources: plural nouns, lowercase, hyphens** — `/user-accounts/{id}`, not verbs or
  camelCase paths; the URL surface is a contract, so fix it before first release. *(AX-06)*
- **Database naming conventions** — pick one (typically snake_case, plural tables, `_id`
  suffixes) and enforce it in review; renames after data exists are migrations. *(DD-01, DD-10)*
- **Env vars: SCREAMING_SNAKE_CASE** — with a consistent app prefix to avoid collisions;
  they're part of the declared configuration surface. *(AX-13, PAT-16)*
- **Branch & commit naming (Conventional Commits)** — machine-parseable `type(scope): summary`
  enables changelog and semver automation; enforce with a commit lint, not review nagging.
- **Test names describe behavior (`should_X_when_Y`)** — a failing test's name should state the
  broken requirement without opening the file; `test_process_2` tells a reviewer nothing.

## Version control & collaboration

- **Trunk-based development** — default to integrating into main at least daily behind flags;
  long-lived branches convert merge pain into a delayed, compounding integration test.
  *(AX-15, PAT-14)*
- **Git flow vs GitHub flow** — heavyweight git flow suits versioned/released software; for
  continuously deployed services it adds ceremony branches with no consumer — prefer the simpler
  flow.
- **Short-lived branches** — measure branch age; anything alive past a few days is drifting from
  main and should be split or merged behind a flag. *(AX-15)*
- **Atomic commits** — one logical change per commit that builds and passes tests, so revert and
  bisect operate at the granularity of intent, not archaeology.
- **Conventional Commits** — the payoff is automated changelogs and release semantics; adopting
  the format without the automation is pure ceremony.
- **Rebase vs merge; squash policies** — pick one policy repo-wide: never rewrite shared
  history, and don't squash away commit boundaries that bisect would need.
- **Merge queues** — two green PRs can be red combined; once merge frequency makes that likely,
  a queue testing each PR against latest main replaces "merge fast and hope."
- **Branch protection & required checks** — required checks and no force-push on main are the
  mechanical floor; a check that can be skipped under deadline is advisory, not a gate.
- **CODEOWNERS** — route review by path so nothing merges unseen by its owner; an unowned
  directory is a review gap, and a stale owner is a merge bottleneck — audit both.
- **Pre-commit hooks** — fast local feedback for format/lint only; hooks are trivially skipped,
  so CI must re-run every hook check as the actual enforcement.
- **git bisect** — binary-search the offending commit instead of reading diffs; it's the payoff
  for atomic always-green commits and can be scripted with `git bisect run`.
- **Cherry-picking (sparingly)** — acceptable for hotfix backports to release branches; as a
  routine flow it forks history and produces subtle double-merge conflicts.
- **Monorepo vs polyrepo** — monorepos buy atomic cross-cutting changes but demand tooling
  investment (selective CI, ownership boundaries); don't adopt one without funding the tooling.
  *(AX-03)*
- **Git LFS** — large binaries in plain git bloat every clone forever; route them to LFS or
  artifact storage before the first one lands, because history rewrites are expensive.
- **Signed commits** — commit authorship is spoofable by default; signing (plus server-side
  verification) is a supply-chain control for provenance-sensitive repos, not a vanity badge.
- **PR size limits & review latency** — review quality collapses past a few hundred lines while
  rubber-stamp odds rise; small PRs plus fast turnaround beat big PRs reviewed "thoroughly."
  *(AX-15)*
- **Code review: correctness over style (bots handle style)** — human attention goes to
  correctness, design, and scope; any style comment a linter could make is a linter config gap.
  *(AX-19)*

## Testing

- **Test pyramid (and the testing-trophy rebuttal)** — fast unit tests dominate, few E2E; the
  trophy's point stands where units are heavily mocked — prefer integration tests that exercise
  real boundaries. *(AX-16)*
- **Unit / integration / component / end-to-end tests** — name which layer proves each
  acceptance criterion in the plan; a criterion proven only at E2E level is a slow, flaky
  guarantee. *(AX-16)*
- **Contract testing (consumer-driven, Pact)** — verify provider against consumers' recorded
  expectations in CI, replacing most cross-service E2E; a provider change breaking a contract
  fails before deploy. *(AX-06, PAT-04)*
- **Smoke & sanity tests** — a minutes-fast "is it fundamentally alive" suite gates deploys and
  runs post-release; it answers rollback-now questions the full suite is too slow for.
- **Regression tests** — every bug fix lands with a test that fails on the pre-fix code —
  that's the discriminating-test rule in this repo's problem-solving discipline; no test, no fix.
- **Snapshot & approval testing** — cheap for complex serialized output, but bulk-updated
  snapshots become approve-anything noise; treat every snapshot diff as a reviewable behavior
  change.
- **Visual regression testing** — pixel/DOM diffs catch CSS breakage functional tests can't;
  budget for anti-aliasing flake and a deliberate baseline-approval workflow.
- **Property-based testing** — state invariants and let the framework hunt inputs; strongest on
  parsers, codecs, and round-trips. Persist shrunk counterexamples as regression cases.
- **Fuzzing** — throw malformed input at every parser of untrusted data; it finds the crashes
  and hangs example-based tests never imagine. Keep the corpus and run continuously.
- **Mutation testing** — mutates code to see if tests notice; the honest audit of assertion
  quality that coverage can't give. Too slow for every PR — run scheduled on critical modules.
- **Mocks vs stubs vs fakes vs spies** — stub queries, mock/spy commands, prefer an in-memory
  fake for whole dependencies; asserting every stub interaction welds tests to implementation.
- **Classical (Detroit) vs mockist (London) TDD** — default classical (real collaborators,
  state assertions); mockist isolation couples tests to internals so refactors break green
  behavior.
- **TDD / BDD / ATDD** — the transferable core is test-first for design pressure and
  business-readable acceptance criteria; adopting Gherkin tooling without customer collaboration
  is ceremony.
- **Arrange–Act–Assert; Given–When–Then** — one behavior per test, phases visibly separated;
  interleaved act/assert blocks mean the test covers several behaviors and fails ambiguously.
- **Fixtures, factories, test data builders** — builders with intention-revealing defaults beat
  shared fixtures; a giant shared fixture couples every test to every field it carries.
- **Hermetic, deterministic tests (freeze time, seed randomness)** — inject the clock, seed or
  fix randomness, no real network or wall-clock sleeps; `sleep()` in a test is a flake IOU.
- **Test isolation & parallel execution** — each test owns its state and passes in any order;
  order-dependence hides until parallelization or a re-run exposes it as "random" failure.
- **Flaky test quarantine** — a flaky test in the gating suite teaches everyone to ignore red;
  quarantine it with an owner and a deadline — quarantine is triage, not a graveyard.
- **Testcontainers** — real databases/queues as ephemeral containers beat in-memory stand-ins
  whose SQL dialect and transaction semantics quietly differ from production. *(AX-16)*
- **Load / stress / soak / spike testing** — pick per question: capacity at target, behavior
  past breaking, leaks over hours, and reaction to sudden bursts; a load test answers only the
  first. *(AX-22)*
- **Open vs closed workload models** — closed-loop tools self-throttle when the system slows,
  hiding queueing collapse; use open (arrival-rate) models to see real overload behavior.
  *(PAT-20)*
- **Testing in production, safely (shadow traffic, synthetics)** — staging never matches prod
  data and scale; mirror traffic to new code without serving results, and run synthetic probes
  continuously. *(AX-14)*
- **Coverage types: line, branch, path** — line coverage flatters: a hit line whose branch
  never went false counts. Prefer branch coverage as the signal; path coverage is combinatorial
  and mostly theoretical. *(AX-16)*
- **Characterization tests** — before refactoring untested legacy behavior, pin what it
  currently does (bugs included) so the refactor has a net; they legitimately pass on base.
  *(AX-02, AX-16)*
