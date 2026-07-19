# The AERS Gold Standard — Top 0.1% Agentic Repository
## Verified Autonomy, Integrity-First Edition

**Status:** Reference architecture and executable starter  
**Date:** July 19, 2026  
**Scope:** Autonomous coding agents, repository guardrails, specification-driven delivery, context and memory,
multi-agent execution, verification, evaluation, security, release, operability, and controlled self-improvement

---

## 1. Executive standard

A top-tier agentic repository is not a repository with the longest instruction file, the most agents, or the most
aggressive autonomous loop. It is a repository whose **intent, authority, execution, verification, release, and
learning signals remain trustworthy when the authoring agent is mistaken, pressured, injected, compromised, or
optimizing the wrong objective**.

AERS defines the gold standard as:

> **Specification-driven candidate generation under immutable task authority, exact scoped writes, bounded
> fresh-context execution, deterministic and independent evidence gates, external trusted verification, signed
> provenance, staged release, and curated eval-gated learning.**

The repository may produce **AUTHOR_READY**. Only a separate verifier trust domain may issue **VERIFIED**.

This is the foundational distinction of AERS. It prevents a local agent, test suite, prompt reviewer, hook, worktree,
CI workflow, memory file, or self-modified policy from declaring its own output trustworthy.

---

## 2. Why verification integrity is Plane 0

Every higher-order capability depends on a reward signal:

- The loop stops because checks say the task is complete.
- The orchestrator selects a patch because an evaluator prefers it.
- Memory promotes a lesson because prior runs appeared successful.
- Prompt optimization preserves changes because the eval score increased.
- Auto-merge trusts required checks.
- Release automation trusts the artifact and health gates.

If that signal can be edited, leaked, retrieved, hardcoded, bypassed, mis-specified, or observed by the candidate,
more autonomy accelerates false confidence. Therefore verification is not the final step in AERS; it is the root of
trust for the entire system.

### 2.1 Two verdicts

| Verdict | Issuer | Meaning |
|---|---|---|
| `AUTHOR_READY` | Repository-side orchestrator after public checks, scope, audit, and review | The candidate is ready to be judged by trusted infrastructure |
| `VERIFIED` | External protected verifier identity | The exact immutable candidate satisfied trusted policy and protected acceptance evidence |

No local code path can transform one into the other.

### 2.2 Trust-domain requirements

The verifier must be outside the implementation agent's writable domain and preferably outside its readable domain.
It receives an immutable candidate artifact/digest and returns a bounded signed result. Hidden tests, evaluator data,
runner configuration, signing credentials, and release identity never enter the author process.

A private test mounted into the same broadly privileged job that executes untrusted candidate code is not inherently
private. The code can attempt to inspect the filesystem, process tree, environment, logs, kernel interfaces, or
network. The production design must isolate the oracle and minimize one-way output.

---

## 3. The seven planes

### Plane 0 — Verification kernel

- Exact candidate commit/artifact
- Clean export or immutable build image
- Protected public and private evidence
- No-network or explicitly allowlisted execution
- Scrubbed environment and least-privilege identity
- Test integrity and oracle isolation
- Deterministic trajectory/diff audit
- Typed independent reviewer
- Signed attestation bound to source, policy, and evidence digests

### Plane 1 — Intent and contracts

- Engineering constitution
- S0/S1/S2 specification sizing
- Human-readable spec, plan, task graph, acceptance, validation, decision log
- Machine-readable feature and task contracts
- Objective acceptance IDs and evidence methods
- Contract compatibility, failure behavior, observability, rollout, rollback, and non-goals

### Plane 2 — Context and knowledge

- Concise root `AGENTS.md` as a map
- Nested path-specific instructions for high-signal local rules
- Generated repository map and curated hot context
- Primary-source precedence
- Drop/mask/offload/fresh-context before lossy compaction
- Hash-addressed context packets
- Quarantined memory and locked skills

### Plane 3 — Work and execution

- External queryable ledger
- Immutable roles, scopes, dependencies, budgets, and base commit
- One task per fresh process
- Single writer by default
- Parallel read/review/research roles
- Worktree isolation
- Candidate commit owned by orchestrator
- Failed-attempt rollback and repeated-failure stop

### Plane 4 — Security and governance

- Rule of Two capability analysis
- Least privilege and short-lived scoped identities
- Deny-by-default egress and filesystem boundaries
- Prompt-injection assumption
- Secrets/data minimization
- Hook defense in depth
- Control-plane CODEOWNERS and branch protection
- Dependency, skill, MCP/tool, and memory supply-chain governance
- R0–R3 autonomy tiers

### Plane 5 — Release and operability

- Immutable build
- SBOM and dependency lock
- Signed provenance/attestation
- Separate release identity
- Staged rollout, health gates, and automatic rollback
- Telemetry, capacity, degradation, recovery, and runbooks
- Post-deploy observation and release evidence

### Plane 6 — Evaluation and controlled learning

- Public smoke/adversarial cases
- External private holdouts
- Multiple trials and evaluator-health checks
- Trajectory fault taxonomy
- False-pass and false-reject measurement
- Cost, latency, loops, scope, and safety metrics
- Quarantined lesson/skill/prompt proposals
- Baseline comparison, canary, rollback, and delayed activation

---

## 4. Canonical repository layout

```text
/
├── MISSION.md                        # human-owned repository intent; direction, not authority
├── AGENTS.md                         # concise universal map and invariants
├── CLAUDE.md                         # @AGENTS.md + thin Claude adapter
├── GEMINI.md                         # thin Gemini adapter
├── README.md / TUTORIAL.md           # adopter-facing docs
├── install.sh                        # non-destructive install into existing repos
├── aers.toml                         # runtime-neutral configuration
├── .agents/                          # canonical vendor-neutral control plane
│   ├── constitution.md
│   ├── operating-model.md
│   ├── context/
│   ├── policies/*.json
│   ├── schemas/*.json
│   ├── roles/*.md
│   ├── skills/**/SKILL.md
│   ├── skills/skills.lock.json
│   ├── memory/{quarantine,active}/
│   ├── evals/
│   ├── telemetry/
│   └── trusted/                      # external trust-domain contracts only
├── .specify/                         # Spec Kit-compatible feature packs
│   ├── constitution.md
│   ├── templates/
│   └── specs/<feature-id>/
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       ├── acceptance.md
│       ├── validation.md
│       ├── decision-log.md
│       ├── feature.contract.json
│       ├── tasks.json
│       └── [S2 threat/migration/runbook files]
├── agent_docs/                       # progressive-disclosure procedures (incl. kickoff.md)
├── .claude/{hooks,agents,commands}/  # concrete thin adapter
├── scripts/aers/                     # executable control plane
├── scripts/loop.py                   # candidate-only single-task loop
├── scripts/run_ready.py              # outer runner across a feature's ready tasks
├── evals/                            # public cases + external private interface
├── examples/                         # runnable offline demo with stub adapters
├── tests/aers_selftest/              # control-plane self-tests (namespaced)
├── .github/workflows/                # author checks; trusted verifier external
├── docs/{adr,runbooks}/
└── .aers-runtime / .aers-evidence    # ignored local defaults; external in production
```

### 4.1 Markdown has three jobs only

1. Provide high-signal human/model context.
2. Explain intent, tradeoffs, and operating procedure.
3. Point to executable truth.

Markdown must not be the only enforcement for write scope, permissions, status, risk, tests, release, or memory
promotion.

---

## 5. Root instruction design

The root file should contain only facts every run needs:

- one-line mission
- source-of-truth order
- exact canonical commands
- mandatory workflow
- immutable boundaries
- definition of readiness
- stop conditions
- pointers to deeper documents

It should not contain a full architecture manual, every style rule, historical lessons, or vendor-specific syntax.
Instruction-budget heuristics are evaluated per repository rather than treated as universal model laws.

### 5.1 Static versus retrieved context

Keep universally required safety, commands, and invariants static. Retrieve specialized procedures, large domain
references, and infrequent skills on demand. Measure retrieval success in the repository's eval suite. Neither
"everything static" nor "everything as a skill" is universally correct.

### 5.2 Nested instructions

Use nearest-path `AGENTS.md` files for control-plane code, specs, workflows, generated code, data/migrations, or
other distinct surfaces. Nested files narrow rules; they do not redefine the constitution.

---

## 6. Specification-driven development

### 6.1 Choose the smallest adequate spec mode

| Mode | Use when | Required artifacts |
|---|---|---|
| S0 | Tiny local change; misunderstanding is cheap and reversible | change brief, acceptance, typed task |
| S1 | Normal behavior or cross-module feature | full spec, plan, tasks, acceptance, validation, contract |
| S2 | Security, data, migration, infrastructure, public contract, reliability, or multi-service change | S1 plus ADR/threat/migration/runbook artifacts as applicable |

A spec is not a ceremonial essay. It compiles into constraints.

### 6.2 Typed feature contract

The machine contract includes:

- stable feature ID and version
- spec mode and risk tier
- approved status and registration commit
- objective acceptance criteria
- affected APIs/events/schemas/data/UI/CLI contracts
- compatibility classification
- security, reliability, performance, and observability quality attributes
- rollout, health gates, and rollback
- non-goals

### 6.3 Typed task contract

Each task includes:

- stable ID and role
- dependencies
- exact write scopes
- acceptance IDs served
- exact command argv arrays and timeouts
- network requirement
- attempt/file/line/time budgets
- notes and explicit stop conditions

Task definitions are immutable during execution and are loaded from the registered commit, not from the agent's
modified worktree.

### 6.4 Task-by-task validation

Do not wait for the end of a multi-day implementation. Each task creates a separately reviewable candidate or
checkpoint with evidence. Integration acceptance remains mandatory; individually passing tasks can compose into a
failing system.

---

## 7. External work ledger

Markdown todos are useful views but weak authority. AERS uses a queryable ledger that records:

- feature and task definition hashes
- immutable base/contract commit
- roles, dependencies, budgets, and leases
- attempts and state transitions
- candidate SHAs
- failure fingerprints
- evidence locations
- append-only hash-chained events

The author agent cannot erase failed attempts, edit its role, change the task scope, grant itself another attempt,
or mark itself verified by modifying a file.

### 7.1 Required states

`pending → leased → implementing → scope_passed → candidate_committed → author_verifying → auditing → reviewing → author_ready`

External systems may continue:

`author_ready → verified/rejected → merged → released`

Invalid transitions are rejected.

---

## 8. Fresh-context autonomy loop

### 8.1 One task per pass

Every pass launches a new agent process with:

- immutable feature/task identity
- context packet and hashes
- exact scope and budget
- relevant acceptance criteria
- canonical commands
- explicit stop conditions
- external trajectory path

It performs one role and one task. The process does not own task status, candidate commits, push, merge, release,
or verification authority.

### 8.2 Outer orchestrator sequence

1. Resolve and hash the approved contract commit.
2. Register immutable definitions in the external ledger.
3. Confirm dependencies, risk tier, capability policy, and budget.
4. Create an isolated worktree/branch.
5. Generate a context packet.
6. Launch the author in a fresh process with no shell-generated command string.
7. Evaluate exact changed paths, tests, protected surfaces, symlinks, and diff budgets.
8. Stage only approved paths and create the candidate commit itself.
9. Run clean-export author verification.
10. Run deterministic trajectory/diff audit.
11. Obtain a schema-valid independent reviewer report.
12. Mark the candidate `AUTHOR_READY` and stop.

The default loop never pushes, merges, releases, or invokes private tests.

### 8.3 Failure behavior

- Save redacted stdout/stderr, normalized events, reports, and a patch externally.
- Reset and remove the failed worktree and branch.
- Record a hash fingerprint of the failure.
- Retry only within the immutable attempt budget and with a materially new hypothesis.
- Safe-stop on repeated fingerprints, risk increase, permission need, integrity failure, or ambiguity.

No failed attempt is checkpoint-committed as progress.

---

## 9. Exact scoped writes

Write scope is a capability, not advice.

The authoritative gate checks:

- every tracked and untracked changed path
- exact task globs
- role-specific restrictions
- protected control-plane paths
- co-located test patterns
- generated/vendor surfaces
- sensitive paths
- file and line budgets
- symlink traversal and escape
- staged path equality before commit

### 9.1 Role restrictions

- **Implementer:** approved source scope; never tests or control plane.
- **Test author:** approved tests/fixtures only; separate from implementation.
- **Architect:** feature specs and ADR/architecture docs only.
- **Documentation:** documentation only.
- **Explorer/reviewer/security/SRE:** read-only during review roles.

A larger task must be repartitioned rather than widening the role casually.

---

## 10. Hooks and runtime adapters

Hooks are valuable because they block obvious violations before wasted work. AERS supplies Claude adapters for:

- `PreToolUse` write/command checks
- `TaskCompleted` scope gate
- `ConfigChange` denial during autonomous runs
- `PreCompact` trajectory note without durable memory write
- `SessionEnd` trajectory closure

But hooks are not the trust boundary. They may be absent, bypassed, misconfigured, or limited to named tools. The
outer orchestrator and operating-system sandbox remain authoritative.

Runtime commands are JSON argv arrays. AERS never invokes a model-generated shell string and never silently adds a
permission-bypass flag.

---

## 11. Hermetic author verification

The author verifier:

1. Resolves base and candidate commit SHAs or stops.
2. Requires a clean candidate worktree.
3. Loads feature/task contracts from the immutable base commit.
4. Re-runs the exact scope gate.
5. Exports the candidate through `git archive` into a clean temporary directory.
6. Rejects unsafe archive paths/symlinks.
7. Scrubs the environment and creates a temporary HOME.
8. Requires externally asserted network isolation or a verified OS network namespace.
9. Executes exact task command arrays with timeouts.
10. Redacts output and produces a hash-bound JSON report.

If isolation is unavailable, a developer may explicitly create `DEGRADED` evidence. Degraded evidence cannot issue
`AUTHOR_READY` or `VERIFIED`.

### 11.1 Why clean export matters

It eliminates stray untracked files, shadowed modules, alternate configs, local caches, or modified tooling that are
not part of the candidate commit. Verification judges the artifact being proposed, not the author's ambient machine.

---

## 12. Deterministic audit and independent review

### 12.1 Deterministic audit first

Before a model reviewer, inspect:

- protected/test/scope findings
- test-runner manipulation
- forced-success patterns
- secret-like content
- dangerous commands
- non-blocked network attempts
- policy bypass/disablement
- malformed or missing trajectory events
- candidate and evidence hashes

High/critical findings fail. Medium findings require explicit review.

### 12.2 Typed reviewer second

The reviewer re-reads the original spec, examines the exact candidate diff and evidence, covers every acceptance ID,
and flags only evidence-backed correctness, scope, security, reliability, operability, or compositional gaps.

Its JSON output must bind to feature ID, task ID, candidate SHA, acceptance IDs, findings, and verdict. A text token
or natural-language "looks good" is never accepted.

The reviewer remains advisory to the external verifier and cannot issue `VERIFIED`.

---

## 13. Hardened external verification

A production verifier should:

- fetch an immutable source/artifact by digest
- use a protected runner image and policy digest
- deny network by default
- expose no broad repository/release secrets
- isolate private tests from candidate filesystem/process introspection where feasible
- reveal only bounded failure categories or redacted diagnostics
- check public, private, integration, compatibility, security, reliability, and test-integrity evidence
- detect leakage/retrieval and evaluator health failures
- sign an attestation binding candidate, source digest, policy, runner, tests/evals, timestamp, and result

Branch protection accepts only the trusted attestation identity. A repository-local job with the same author token is
not an independent verifier.

---

## 14. Context engineering

### 14.1 Source precedence

1. Protected executable contracts/evidence
2. Approved feature/task contracts
3. ADRs and invariants
4. Primary code/tests/docs
5. Curated active memory
6. Task-local observations
7. Model inference

Conflicts cause safe-stop or explicit resolution.

### 14.2 Context packet

Generate a small packet containing:

- run/feature/task IDs
- base commit and contract hashes
- role, scope, budgets, and commands
- relevant acceptance criteria
- likely source/test/ADR/runbook paths
- invariants and stop conditions

The packet is navigational. Load-bearing facts are read from primary files.

### 14.3 Context pressure order

1. Drop stale tool results.
2. Mask irrelevant observations.
3. Offload large artifacts and reference hashes.
4. Start a fresh task/role process.
5. Summarize only when necessary and mark it lossy.

Never replace full-fidelity evidence with a summary and then delete the source.

---

## 15. Memory management

### 15.1 Four layers

- **Working:** current hypotheses and next actions; external and disposable.
- **Episodic:** immutable run traces/evidence for replay; retention governed.
- **Semantic:** verified lessons/failure patterns with scope and expiry.
- **Procedural:** versioned skills with locked digests and evaluations.

Specifications and ADRs remain separate sources of truth.

### 15.2 Promotion flow

`proposal → quarantine → independent reproduction → regression eval → curator approval → signed activation → monitoring → expiry/revocation`

Required fields include provenance, content hash, scope, validation runs, conflicts, curator, activation time, and
review/expiry date. The proposer cannot approve its own lesson, and activation cannot occur in the same run.

Most tasks should produce no durable memory change.

### 15.3 Memory poisoning defense

Any agent-writable content that future agents auto-load is an instruction channel. Quarantined records are not
loaded. Active records are individually hashed and indexed. Curator identity and expiration are checked. A changed
hash or expired record fails control-plane lint.

---

## 16. Skills, MCP tools, and dependencies

Treat skills and tool descriptions like dependencies. Each active skill records:

- source and version
- SHA-256 digest
- permissions and capabilities
- tool and network requirements
- evaluation coverage
- status and approver

Unpinned or mutated skills are denied. Third-party skills run in quarantine. Changes activate only after independent
evaluation and approval.

Apply equivalent governance to MCP servers, plugins, agent images, reusable workflows, models, and tool adapters.

---

## 17. Multi-agent and fleet orchestration

### 17.1 Default pattern

Parallelize intelligence:

- repository exploration
- research
- architecture alternatives
- threat modeling
- test proposals
- code review
- trajectory analysis

Serialize authoritative writes.

### 17.2 When parallel writers are allowed

Only when all are true:

- path partitions are non-overlapping
- interfaces are frozen and machine-checked
- ownership leases are explicit
- integration order is defined
- each partition has independent verification
- merge queue detects conflicts and re-verifies the combined candidate

Shared schemas, migrations, manifests, dependencies, cross-cutting refactors, and release state remain serialized.

### 17.3 Fleet maturity rule

Add orchestration only when task independence and throughput justify coordination cost. A swarm is not evidence of
maturity. A reliable single-writer system with parallel reviewers is often stronger.

---

## 18. Security model

### 18.1 Rule of Two

Evaluate whether a session can:

1. read untrusted content
2. access sensitive data/systems
3. create external effects or exfiltrate

An autonomous session holds at most two. If all three are required, decompose into isolated sessions/trust domains or
insert an appropriate approval gate.

### 18.2 Sandbox baseline

- ephemeral workspace
- no production credentials
- deny-by-default egress
- no host Docker socket
- no cloud metadata
- no shared SSH agent
- minimal mounts
- non-root/least privilege
- process, CPU, memory, disk, and time limits
- immutable base image
- restricted inter-process visibility
- external logs/evidence with redaction

"Running in a container" alone proves none of these.

### 18.3 Intent-level authorization

Filesystem/network/IAM controls are necessary but not sufficient. Tools that legitimately share, publish, deploy,
email, or mutate systems need purpose, target, data class, and effect constraints. A valid identity can still perform
an unintended legitimate operation.

---

## 19. Testing strategy

A mature repository combines:

- static/type/schema/architecture checks
- unit tests
- contract and consumer tests
- integration/compositional tests
- end-to-end acceptance
- property/fuzz tests where useful
- mutation testing for critical logic
- security and dependency scans
- performance, load, reliability, and rollback tests
- test-integrity checks
- private holdouts

New behavior should have a discriminating test that would fail without the change where practical. The implementer
cannot weaken or rewrite the oracle. Test-authoring is a separate role/task.

Verification must detect feature-level passes that fail when components are composed.

---

## 20. Trajectory observability

Record the path, not only the answer:

- state transitions and role boundaries
- instruction, contract, skill, model, and harness versions
- tool calls/results
- file reads/writes
- network attempts
- policy decisions
- hypotheses and rejected approaches
- command evidence
- retries and budgets
- reviewer/verifier outcomes
- errors and safe stops

Use normalized redacted JSONL and align with OpenTelemetry GenAI concepts where practical. Content capture is disabled
by default. Traces are evidence and sensitive data; they need retention, access control, redaction, and integrity.

### 20.1 Fault taxonomy

At minimum classify specification gaps, context failure, coordination failure, scope violation, test tampering,
oracle leakage, retrieval shortcut, hardcoding, policy evasion, network/secret violations, false pass/false reject,
compositional failure, rollback failure, nondeterminism, and budget exhaustion.

---

## 21. Evaluation system

### 21.1 Public versus private

- **Public cases:** fast smoke/adversarial checks for obvious regression and developer feedback.
- **Private holdouts:** external, contamination-controlled tasks used for promotion decisions.

The authoring agent cannot read the only oracle used to approve its own instruction/harness changes.

### 21.2 Required metrics

- task success and acceptance coverage
- false-pass and false-reject rates
- scope/test/policy violations
- security incidents and safe-stop quality
- cost, latency, loops, and tool failures
- nondeterminism across multiple trials
- reviewer/verifier agreement
- rollback success
- post-release defect/incident rate

### 21.3 Evaluator health

Regularly audit tasks for impossible prompts, underspecified requirements, under/over-strict tests, low coverage,
leakage, stale dependencies, and misleading labels. A model score is meaningless when the benchmark is broken.

---

## 22. Controlled self-improvement

### 22.1 Improvement candidates

A run may propose:

- a repository bug/tooling fix
- a new regression test
- a context/index change
- a lesson or failure pattern
- a skill update
- an instruction/hook/policy change
- a harness change

The proposal is not active.

### 22.2 Promotion pipeline

1. Quarantine the delta with provenance.
2. Reproduce the failure independently.
3. Add a regression evaluation.
4. Evaluate against public and private holdouts over multiple trials.
5. Compare success, safety, false-pass, cost, and latency to a frozen baseline.
6. Review for overfitting and leakage.
7. Canary on low-risk work.
8. Activate in a later version/run through a distinct curator/owner.
9. Monitor and automatically revoke on regression.

Machine optimization of prompts/docs is allowed only after this evaluation substrate exists. Otherwise it optimizes
noise, leakage, or an exploitable oracle.

---

## 23. Risk-tiered autonomy

| Tier | Typical work | Candidate generation | Auto-merge after VERIFIED | Release |
|---|---|---:|---:|---:|
| R0 | docs, formatting, nonbehavioral tests | eligible | eligible after qualification | no |
| R1 | localized behavior, no public/data/auth/infra change | eligible | eligible after qualification | staged system only |
| R2 | cross-module, compatible contracts/dependencies | eligible | normally no | explicit release policy |
| R3 | auth, secrets, privacy, regulated data, destructive migration, infra, control plane, release | no autonomous candidate by default | no | stronger approval path |

Autonomy is earned per task class, repository, verifier, model/harness version, and recent evidence—not granted once
forever.

---

## 24. Release and software supply chain

Release only an immutable `VERIFIED` artifact. Require:

- reproducible/controlled build
- locked dependencies
- SBOM
- vulnerability and license policy
- source/build provenance
- artifact signature/attestation
- separate deployment identity
- staged rollout and health gates
- automatic rollback
- post-deploy observation

Never release from an agent worktree or mutable artifact. Never give the implementation agent a production shell.

---

## 25. Maturity scorecard — 100 points

### A. Verification integrity — 20
- external verifier trust domain: 5
- private oracle isolation and no-network execution: 4
- exact candidate/clean export and immutable contracts: 4
- test-integrity and deterministic trajectory audit: 3
- signed attestation bound to evidence/policy: 4

### B. Intent and typed contracts — 12
- constitution and spec sizing: 2
- objective acceptance and non-goals: 3
- machine feature/task contracts: 3
- compatibility/failure/observability/rollout/rollback: 4

### C. Work, scope, and orchestration — 14
- external ledger and valid state transitions: 3
- immutable role/scope/dependency/budget authority: 3
- fresh-context bounded loop: 2
- exact scope/test/symlink/diff enforcement: 4
- failed-attempt rollback and repeated-failure stop: 2

### D. Security and governance — 14
- Rule of Two/capability decomposition: 3
- sandbox/egress/secret containment: 4
- protected control plane and branch ownership: 2
- prompt-injection and intent-level authorization model: 3
- dependency/skill/tool governance: 2

### E. Testing and quality — 10
- layered automated tests and architecture checks: 3
- independent test author/test integrity: 2
- integration/compositional and rollback validation: 3
- performance/reliability/security coverage: 2

### F. Context, memory, and skills — 10
- concise/static root plus progressive disclosure: 2
- generated context packet and primary-source precedence: 2
- drop/mask/offload/fresh-context policy: 2
- quarantined curated memory with expiry/conflicts: 2
- locked evaluated skills: 2

### G. Observability and evaluations — 10
- normalized trajectory events and trace integrity: 3
- fault taxonomy and transcript/diff audit: 2
- public and external private evals: 2
- multiple trials, evaluator health, false-pass/false-reject metrics: 3

### H. Release and operability — 10
- immutable build/SBOM/provenance/signature: 3
- staged rollout/health gates/rollback: 3
- telemetry, runbooks, degradation, recovery: 2
- separate release identity and post-release measurement: 2

### Qualification bands

- **0–59:** assisted development only
- **60–74:** R0 candidate generation in sandbox; human merge
- **75–84:** bounded R0/R1 candidates with external verification; human merge
- **85–92:** qualified R0/R1 auto-merge after trusted attestation and measured rollback
- **93–100:** gold-standard candidate, subject to no disqualifier and sustained production evidence

"Top 0.1%" is an aspirational engineering threshold, not a statistically certified market percentile.

### Critical disqualifiers

Any one disqualifies autonomous top-tier status:

- local agent/workflow can issue or forge VERIFIED
- implementer can edit tests/evals/contracts/policies used to judge itself
- missing base or failed verification can be ignored
- unrestricted network plus secrets/sensitive data plus external effects
- private tests exposed to broadly privileged candidate code
- task role/scope/status is author-editable
- force push, direct production shell, or release from worktree
- unreviewed memory/skills auto-load into future runs
- no rollback for meaningful behavior/data/infra changes
- no preserved evidence bound to candidate SHA
- evaluator/prompt changes approved only by the eval they modified

---

## 26. Adoption roadmap

### Phase 1 — Repository legibility

Implement stable commands, concise AGENTS map, repository map, invariants, ownership, architecture tests, and S0/S1
feature packs. Measure build/test reproducibility.

### Phase 2 — Candidate containment

Deploy sandbox, exact write scopes, protected tests/control plane, external ledger, fresh task loop, diff budgets,
rollback, and author evidence. Keep all merges human-controlled.

### Phase 3 — Trusted verification

Deploy separate verifier infrastructure, private integration/acceptance checks, bounded result channel, attestation,
branch protection, and immutable artifact pipeline.

### Phase 4 — Qualified autonomy

Choose narrow R0/R1 task classes. Run shadow/candidate mode, multiple trials, incident analysis, and rollback drills.
Enable auto-merge only after sustained false-pass and operational thresholds are met.

### Phase 5 — Fleet and learning

Add parallel readers, proven writer partitions, merge queue, private eval service, curated memory, skill registry, and
controlled prompt/harness optimization. Expand only where measured throughput exceeds coordination/risk cost.

---

## 27. The executable starter

This repository is itself the executable starter, containing:

- root and nested agent contracts, with `MISSION.md` as the human-owned intent
- Spec Kit-compatible templates and typed schemas
- stdlib-only Python control plane
- SQLite hash-chained work ledger
- scope/test/protected-path/symlink/diff enforcement
- clean-export author verifier with a differential test gate
- deterministic auditor and optional LLM trajectory auditor
- candidate-only fresh-process loop and an outer multi-task runner
- typed reviewer and external verifier contracts
- Claude hooks and thin adapters
- context packet and repository map generators
- memory quarantine/promotion and skill lock
- public adversarial evaluations
- GitHub author/control-plane workflow references
- a runnable offline demo with stub adapters (`examples/`)
- unit tests and threat-model, ADR, and runbook documentation

### Reproducible checks

- control-plane lint: `python3 scripts/aers.py lint`
- unit tests: `python3 -m unittest discover -s tests -p 'test_*.py'`
- public adversarial smoke cases: `python3 scripts/aers.py eval-public`
- end-to-end scoped candidate pipeline, including the blocked
  test-loosening and non-discriminating-test attacks: `TUTORIAL.md` Part 2

The starter proves the repository-side workflow. It cannot by itself prove that an organization's external runner,
identity, private oracle, branch protection, or release system is correctly deployed.

---

## 28. Primary references to study

Prefer primary sources and verify current versions during implementation:

- OpenAI, *Harness engineering: leveraging Codex in an agent-first world* — https://openai.com/index/harness-engineering/
- OpenAI, Symphony — https://github.com/openai/symphony
- OpenAI, *Why SWE-bench Verified no longer measures frontier coding capabilities* — https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- Anthropic, *Building effective agents* — https://www.anthropic.com/research/building-effective-agents
- Anthropic Claude Code hooks — https://docs.anthropic.com/en/docs/claude-code/hooks
- Anthropic Claude Code memory/instructions — https://docs.anthropic.com/en/docs/claude-code/memory
- GitHub Spec Kit — https://github.com/github/spec-kit
- Meta, *Practical AI agent security / Agents Rule of Two* — https://ai.meta.com/blog/practical-ai-agent-security/
- OpenTelemetry GenAI semantic conventions — https://opentelemetry.io/docs/specs/semconv/gen-ai/
- SLSA specification — https://slsa.dev/spec/
- GitHub artifact attestations — https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations
- GitHub Actions security hardening — https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- NIST Secure Software Development Framework — https://csrc.nist.gov/Projects/ssdf

Use community projects for implementation inspiration, but do not inherit their trust claims without inspecting the
actual scripts and threat boundaries.

---

## 29. Final theorem

> **Agent autonomy should scale only after verification integrity, scope authority, rollback, and evidence quality
> have scaled first.**

A repository becomes smarter not when every run writes another lesson, but when it converts repeatable evidence into
a controlled improvement without weakening the signal used to judge future work.
