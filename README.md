# AERS — Autonomous Engineering Repository Standard

A plug-and-play control plane that turns any repository into a safe home for
autonomous AI engineering. Drop it into a repo, state the repo's goal in
`MISSION.md`, and agents build it out methodically — spec-first, test-gated,
scope-limited, and evidence-backed — while you review contracts and merge
verified work.

Everything is standard-library Python 3.11+ and git. Zero dependencies, no
network required, vendor-neutral (Claude Code, Codex, Gemini, Copilot — any
agent that can read `AGENTS.md` and run a command).

The whole design serves one rule:

> A repository may produce an **AUTHOR_READY** candidate. Only an independent
> verifier trust domain may issue **VERIFIED**.

That distinction is what makes autonomy safe: no implementation agent, local
loop, prompt reviewer, writable test suite, or compromised workflow can declare
its own work trustworthy.

## Quick start — new repository

1. **Use this template.** Click *Use this template* on GitHub (or clone and
   re-init), so the kit is your repo's starting point.
2. **State the goal.** Edit `MISSION.md` — what the repository must become,
   definition of done, constraints, non-goals. Commit.
3. **Kick off.** Open your agent in the repo (e.g. `claude`) and run
   `/kickoff`.

From there the agent derives a roadmap from your mission, drafts typed feature
packs for your approval, and — once you approve and commit them — the task loop
implements them one bounded task at a time, each gated by scope checks,
hermetic verification, differential tests, audits, and review.

## Quick start — existing repository

```bash
git clone https://github.com/vishalsubramani/aers-template
bash aers-template/install.sh /path/to/your/repo
```

`install.sh` copies the control plane in without ever overwriting your files,
reports anything it skipped, and prints the same three next steps: fill
`MISSION.md`, wire your real build/test commands into the `Makefile`, run
`/kickoff`. `TUTORIAL.md` Part 1 walks through adoption in detail.

## How autonomous building works

```text
MISSION.md  →  /kickoff  →  approved feature packs (.specify/specs/)
            →  per task: fresh agent in a clean worktree, stacked on
               dependency candidates (integration-true verification)
            →  SCOPE GATE (exact diff vs immutable write scope)
            →  candidate commit (orchestrator stages approved paths only)
            →  hermetic AUTHOR VERIFY (+ differential test gate)
            →  deterministic AUDIT  →  optional LLM audit  →  REVIEW
            →  AUTHOR_READY  →  external verify / PR review  →  VERIFIED  →  merge
```

Every step produces machine-checkable evidence recorded in an append-only,
hash-chained SQLite ledger outside the agent's writable domain. A failure is
never translated into a weaker definition of success — the system safe-stops
instead of lowering a gate to finish.

## What's executable in this kit

- **Typed intent** — feature and task contracts (JSON Schema-validated), EARS
  acceptance criteria, risk tiers and spec modes, immutable once registered
- **Committed engineering doctrine** — a protected school of thought
  (`.agents/doctrine/`): 22 architecture axioms, 18 data-modeling and
  migration rules, a 20-pattern default library, and 6 contextual decision
  frameworks with a design interrogation — distilled from SWE-at-Google, the
  Amazon Builders' Library, Google SRE, the Azure pattern catalog, and OWASP
  (see `sources.md`). Plans cite the IDs they apply; deviations need an
  accepted ADR; kickoff derives foundation ADRs (architecture, data, and
  security baselines) before the first feature, so structure, data shape, and
  security posture are decided deliberately, never improvised mid-task
- **External ledger** — SQLite runtime state with hash-chained events; markdown
  is a view, never authority
- **Exact scoped writes** — per-task glob write scopes, role rules
  (`test_author` vs `implementer`), diff budgets, protected paths, symlink
  checks
- **Hermetic author verification** — clean export of the exact candidate
  commit, argv-array commands (never model-generated shell strings), fail-closed
  network isolation
- **Differential test gate** — new tests must *fail* on the base commit, so
  test-first work is proven discriminating, not decorative
- **Deterministic audit + independent review** — trajectory and diff audit
  before any model-based reviewer; reviewer reports are schema-bound to the
  candidate SHA (no grep-accepted prose)
- **Fresh-context task loop** — one task per fresh process
  (`scripts/loop.py`), an outer runner for a whole feature's task graph
  (`scripts/run_ready.py`), failed-attempt rollback with preserved patches
- **Curated memory with a closed learning loop** — quarantined proposals,
  human-controlled promotion, and deterministic associative recall: promoted
  lessons flow back into every context packet whose task scope intersects the
  lesson's scope (plus linked lessons one hop away); agent output never
  silently becomes durable instruction
- **Guardrail hooks** — Claude Code hooks deny protected-path writes and
  config drift early (defense in depth; the gates are the boundary)
- **Public adversarial evals** — smoke cases that prove the gates actually
  block scope violations, test loosening, and non-discriminating tests

## Try the whole pipeline offline (5 minutes)

A complete worked example — tiny todo app, an approved feature pack, stub
adapters — runs the entire pipeline with no model and no network:

```bash
bash examples/setup-demo.sh /tmp/aers-demo && cd /tmp/aers-demo
export AERS_AGENT_CMD_JSON='["python3","scripts/adapters/stub_agent.py","--prompt-file","{prompt_file}"]'
export AERS_REVIEWER_CMD_JSON='["python3","scripts/adapters/stub_reviewer.py","--output","{output}","--candidate","{candidate_sha}"]'
export AERS_STUB_PATCH_DIR="$PWD/examples/patches"
export AERS_NETWORK_ISOLATED=1   # only if your host lacks Linux user namespaces (e.g. macOS);
                                 # asserts the environment denies egress — fine for this offline demo
python3 scripts/run_ready.py --feature FEAT-001 --max-runs 4
```

On Linux, drop the `AERS_NETWORK_ISOLATED` line: verification proves isolation
itself with `unshare` network namespaces and fails closed otherwise.

Then watch it catch attacks (a test-loosening implementer, a
non-discriminating test) — `TUTORIAL.md` Part 2.

## Integration contract

Every adopting repository keeps these commands stable; wire your real tools
into the `Makefile`:

```bash
make bootstrap   # deterministic setup
make check       # format, lint, types, schemas, architecture
make test        # unit and appropriate integration/contract tests
make security    # secrets, SAST, dependencies, licenses, IaC/policy
make evals       # agent-control-plane and behavioral regression evals
make verify      # all author-visible gates
```

## Directory map

- `MISSION.md` — human-owned goal of the repository; direction, not authority
- `AGENTS.md` — concise always-loaded agent map and non-negotiables
- `.agents/` — canonical vendor-neutral control plane (constitution, doctrine,
  policies, schemas, roles, skills, memory, telemetry)
- `.specify/` — Spec Kit-compatible feature packs: human spec + typed contracts
- `agent_docs/` — progressive-disclosure operating guides (kickoff, sandbox,
  memory, context, multi-agent, verification)
- `.claude/` — thin Claude Code adapter: hooks, `/kickoff`, `/specify`,
  `/verify`, reviewer/auditor roles
- `scripts/aers/` — the executable control plane (`python3 scripts/aers.py --help`)
- `scripts/loop.py`, `scripts/run_ready.py` — single-task loop and outer runner
- `evals/` — public adversarial smoke cases; private holdouts stay external
- `examples/` — runnable end-to-end demo with stub adapters
- `docs/` — `GOLD-STANDARD.md` (the full standard and its rationale),
  `THREAT-MODEL.md`, ADRs, runbooks

## Hardening for production autonomy

Before granting real autonomy: run the loop inside the sandbox described in
`agent_docs/sandbox-setup.md` (containment and egress denial are the actual
security floor — hooks and prompts are not); fill in `CODEOWNERS` with real
teams; enable branch protection and the `.github/workflows/` author checks; and
keep the five trust domains outside the agent's reach — private acceptance
tests, the trusted verifier identity, release credentials, memory promotion
approval, and private eval holdouts. `docs/THREAT-MODEL.md` enumerates the
threats; `SECURITY.md` states the Rule of Two for capability combinations.

## Learn more

- `TUTORIAL.md` — adoption, the demo end to end, wiring real agents, reading
  evidence, day-2 operations
- `docs/GOLD-STANDARD.md` — the full standard: seven planes, every practice,
  and why each exists
- `docs/THREAT-MODEL.md` — what can attack an autonomous repo and what
  contains it
