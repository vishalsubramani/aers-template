# AERS Tutorial — from "files in my repo" to verified autonomous tasks

The one rule everything serves: **your repo can produce an `AUTHOR_READY`
candidate; only an independent verifier trust domain may say `VERIFIED`.**
Everything below is the machinery that makes `AUTHOR_READY` hard to fake.

Lifecycle you are operating:

```text
SPECIFY -> REGISTER -> (per task) fresh agent -> SCOPE GATE -> candidate commit
        -> hermetic AUTHOR VERIFY (+ differential) -> deterministic AUDIT
        -> optional LLM AUDIT -> REVIEW -> AUTHOR_READY -> external VERIFY -> merge
```

---

## Part 1 — Adopting AERS in an existing repository

New repository: use the GitHub template and skip to Step 1. Existing
repository: `bash install.sh /path/to/your/repo` copies the kit in without
overwriting anything you already have (drop `examples/` later if you want a
lean tree).

**Step 1 — Sanity.** Everything is stdlib Python 3.11+.

```bash
python3 scripts/aers.py lint          # must pass before anything else
python3 -m unittest discover -s tests -p 'test_*.py'
```

**Step 2 — State intent and fill the always-loaded map.** Edit `MISSION.md`
with the repository's goal, definition of done, constraints, and non-goals —
agents refuse to kick off while it is still the placeholder. Then edit
`AGENTS.md`: one line of purpose, your stack, and your exact commands. Keep it
short; deep material goes in `agent_docs/`. Commit both.

Skim `.agents/doctrine/` too: those are the engineering axioms, data rules,
and default patterns every plan will be held against. They are deliberately
stack-neutral; your stack-specific choices land in the foundation ADRs
(architecture and data baselines) that kickoff drafts for your approval before
any feature work. If your organization disagrees with a default, change the
doctrine file up front through a reviewed control-plane PR — not silently,
later, mid-feature.

**Step 3 — Wire your real gates.** Replace the placeholder bodies of `check`,
`test`, `security` in `Makefile` with your project's real commands. The
verifier never trusts prose — only these commands and the per-task command
arrays.

**Step 4 — Author your first feature pack.** (First time only: draft and get
approval on the foundation ADRs — ADR-0001 architecture baseline, ADR-0002
data baseline — from `docs/adr/ADR-0000-template.md` per `agent_docs/kickoff.md`
step 3. `/kickoff` does this automatically; on this manual path, do it by hand.
Every plan cites them, so they must exist before feature work.)

```bash
python3 scripts/aers.py init-feature FEAT-101 --title "Your feature" --mode S1 --risk R1
```

Then edit `.specify/specs/FEAT-101/`:
- `spec.md` — the human story (problem, non-goals).
- `feature.contract.json` — EARS-style `acceptance_criteria` (each with an id,
  a testable statement, and evidence type), `contracts`, `rollout.rollback`.
- `tasks.json` — the task graph. For each task: `role` (`test_author` writes
  tests first; `implementer` cannot touch tests), `write_scope` globs,
  `acceptance` ids it covers, `commands` as **argv arrays** with
  `network: "deny"`, a `budget`, and — for test-author tasks — a
  `differential.argv_template` containing `{file}` so new tests are proven to
  fail on base. Copy the shapes from `examples/feature-pack/FEAT-001/`.

A human reviews and approves the pack: set `status` to `"approved"` and replace
the `REPLACE_WITH_OWNER` scaffold owner in `feature.contract.json` — registration
mechanically refuses drafts and scaffold owners. Then **commit it** — contracts
are read at an immutable ref; uncommitted contracts don't exist.

**Step 5 — Register.**

```bash
python3 scripts/aers.py ledger-init
python3 scripts/aers.py register --feature FEAT-101
python3 scripts/aers.py ledger-show --feature FEAT-101
```

Registration hashes the contract into SQLite; any later edit to the pack is
rejected as a mismatch (author a new approved version instead).

**Step 6 — Choose your agent adapter** (Part 3) and export the two required
env vars. **Step 7 — Run one task** with `scripts/loop.py`, or all ready tasks
with `scripts/run_ready.py`. **Step 8 — Read the evidence** (Part 4), then
hand the branch to your external verifier / normal PR review for `VERIFIED`
and merge.

Production hardening (before real autonomy): run inside the sandbox in
`agent_docs/sandbox-setup.md`; add `CODEOWNERS` teams; enable the CI workflows
in `.github/workflows/`; keep private acceptance tests, the trusted verifier,
and signing outside this repo (`docs/THREAT-MODEL.md`).

---

## Part 2 — The demo, end to end (no model, no network)

Prove the whole pipeline on a real tiny codebase first. The demo app is an
in-memory `TodoList`; the approved feature `FEAT-001` adds priorities via two
tasks: T-001 (`test_author`, TDD red) then T-002 (`implementer`, TDD green).

```bash
bash examples/setup-demo.sh /tmp/aers-demo
cd /tmp/aers-demo

export AERS_AGENT_CMD_JSON='["python3","scripts/adapters/stub_agent.py","--prompt-file","{prompt_file}"]'
export AERS_REVIEWER_CMD_JSON='["python3","scripts/adapters/stub_reviewer.py","--output","{output}","--candidate","{candidate_sha}"]'
export AERS_STUB_PATCH_DIR="$PWD/examples/patches"
# Hosts without Linux user namespaces (e.g. macOS) cannot *prove* isolation, so
# author verification fails closed. For this offline stub demo it is safe to
# assert the environment instead:
export AERS_NETWORK_ISOLATED=1

python3 scripts/run_ready.py --feature FEAT-001 --max-runs 4
```

What just happened, per task: a **fresh worktree** was created from the
contract commit (T-002's worktree then merged T-001's candidate first — its
integration start — so its verification ran T-001's new tests against T-002's
implementation); the stub "agent" applied a prepared change (a real agent
would think here); the **scope gate** compared the exact git diff against the
task's immutable `write_scope`, role rules, and budgets; the orchestrator
staged **only** the approved paths and committed the candidate; **author
verification** exported that exact commit to a clean directory and ran the
task's argv commands inside a network namespace with a scrubbed environment;
for T-001 the **differential gate** additionally copied the new test onto the
base export and required it to *fail* there; the deterministic **audit**
scanned the diff and trajectory; the **reviewer** wrote a JSON report bound to
the candidate SHA; the ledger recorded every transition in a hash-chained
event log.

Now watch it catch attacks. A finished task cannot be re-run (that is the state
machine doing its job), so set up a fresh demo dir first and bring only T-001
to `author_ready`:

```bash
bash examples/setup-demo.sh /tmp/aers-attack && cd /tmp/aers-attack
# (re-export the AERS_* variables from above)
AERS_STUB_PATCH="$PWD/examples/patches/T-001-tests.patch" \
  python3 scripts/loop.py --feature FEAT-001 --task T-001

# An implementer that loosens an existing test:
AERS_STUB_PATCH="$PWD/examples/patches/NEG-evil-loosen-test.patch" \
  python3 scripts/loop.py --feature FEAT-001 --task T-002
# -> exit 2, findings OUTSIDE_WRITE_SCOPE + IMPLEMENTER_EDITED_TEST,
#    worktree rolled back, failed-attempt.patch preserved in evidence.

# A test that does not actually test the new behavior (fresh dir again,
# since T-001 above is now author_ready):
AERS_STUB_PATCH="$PWD/examples/patches/NEG-differential-nondiscriminating.patch" \
  python3 scripts/loop.py --feature FEAT-001 --task T-001
# -> AUTHOR_FAILED: DIFFERENTIAL_TEST_PASSES_ON_BASE
```

---

## Part 3 — Wiring a real agent (this is the "real world" run)

Replace the stubs with your coding agent. Commands are **JSON argv arrays** —
never shell strings. The adapter `scripts/adapters/run_prompt.py` reads the
prompt file and substitutes it safely.

**Claude Code** (run inside the sandbox from `agent_docs/sandbox-setup.md`;
grant permissions via `.claude/settings.json`, not skip-flags):

```bash
export AERS_AGENT_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{prompt_file}","--cwd","{worktree}","--inner-env","AERS_AGENT_INNER_CMD_JSON"]'
export AERS_AGENT_INNER_CMD_JSON='["claude","-p","{prompt}","--output-format","text"]'

export AERS_REVIEWER_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{review_prompt}","--cwd","{worktree}","--inner-env","AERS_REVIEWER_INNER_CMD_JSON"]'
export AERS_REVIEWER_INNER_CMD_JSON='["claude","-p","{prompt}","--output-format","text"]'

# Optional third gate — the LLM trajectory auditor (rich prompt in .claude/agents/auditor.md):
export AERS_AUDITOR_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{audit_prompt}","--cwd","{worktree}","--inner-env","AERS_AUDITOR_INNER_CMD_JSON"]'
export AERS_AUDITOR_INNER_CMD_JSON='["claude","-p","{prompt}","--output-format","text"]'

# Optional risk-tiered review depth — a SECOND independent reviewer for R2 features
# (use a different model/harness than the first reviewer; the loop refuses an
# identical command array). Enforce it by setting
# require_second_reviewer_r2 = true in aers.toml [verification].
export AERS_SECOND_REVIEWER_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{review_prompt}","--cwd","{worktree}","--inner-env","AERS_SECOND_REVIEWER_INNER_CMD_JSON"]'
export AERS_SECOND_REVIEWER_INNER_CMD_JSON='["codex","exec","{prompt}"]'

python3 scripts/run_ready.py --feature FEAT-001 --max-runs 6
```

Notes that matter:
- The implementer prompt already tells the agent its role, scope, budgets, and
  acceptance criteria, and instructs it to leave the worktree **uncommitted**
  — the orchestrator owns commits. The reviewer/auditor prompts instruct the
  model to write **schema-valid JSON to an exact path**; the loop validates
  identity binding (feature, task, candidate SHA) and rejects anything else.
- Use a different model/harness for reviewer and auditor than for the
  implementer when the risk tier warrants independence.
- Codex/other CLIs: swap the inner argv (e.g.
  `["codex","exec","{prompt}"]`); the outer contract is identical.
- Real overnight runs: sandbox + egress allowlist first, then
  `python3 scripts/run_ready.py --feature FEAT-101 --max-runs 12`.
  Kill switch: `touch .aers-runtime/STOP`.

---

## Part 4 — Reading the evidence (your morning routine)

Everything lives under `.aers-evidence/RUN-*/`:

| File | What it proves |
|---|---|
| `prompt.md`, `context.md` | exactly what the agent was told, with file hashes |
| `scope.json` | the diff-vs-authority verdict, path by path |
| `author-report.json` | hermetic command results, network mode, differential results, `AUTHOR_READY` or the fatal reasons |
| `audit-report.json` | deterministic tamper/secret/trajectory findings |
| `llm-audit-report.json` | (optional) behavioral audit, candidate-bound |
| `reviewer-report.json` | requirement-fidelity verdict, acceptance IDs reviewed |
| `reviewer2-report.json` | (R2, when configured) the second independent reviewer's verdict |
| `agent.stdout.txt`, `trajectory.jsonl` | what actually happened, redacted |
| `failed-attempt.patch`, `failure.json` | on failure: the rolled-back change and fingerprint |

**Branching and integration model.** Contracts live on the default branch;
each task run gets its own branch `aers/<feature>/<task>-<run>` in a worktree
outside the repo. Dependent tasks are **stacked**: the worktree starts from
the dependency candidates merged onto the contract commit (the *integration
start*, recorded as an `AERS-Start` commit trailer alongside `AERS-Run` and
`AERS-Contract`). The scope gate and differential tests diff against the
start; hermetic verification runs the suite with dependency work included —
so a green T-002 proves T-001's tests pass against T-002's implementation
*now*, not at merge day. A dependency candidate that does not merge cleanly is
an `INTEGRATION_CONFLICT` safe-stop: overlapping write scopes are a planning
defect, not something to auto-resolve. Merge candidates in task-graph order
(the last candidate in a chain already contains the whole chain), delete
`aers/...` branches after merge.

Ledger truth: `python3 scripts/aers.py ledger-show --feature FEAT-001`. Each
`author_ready` task has a candidate SHA on a branch
(`aers/feat-001/t-00N-*`); inspect with `git worktree list` / normal review,
then your **external verifier** (trusted CI outside author control, private
suite mounted) re-verifies that exact SHA and records `verified` — after
which you merge. Locally you can rehearse the external step with
`python3 scripts/aers.py author-verify ... --degraded` awareness of its
limits; never wire `allow_local_verified`.

---

## Part 5 — Day 2

- **Retries**: a `failed` task is retried automatically by `run_ready` until
  its `max_attempts`; the same failure fingerprint twice transitions the task
  to `safe_stopped` in the ledger, which halts the outer runner for human
  attention. A `safe_stopped`, `rejected`, or `author_ready` task is never
  silently re-run.
- **Learning**: propose lessons with `python3 scripts/aers.py memory-propose
  --statement "..." --scope "src/payments/**" --provenance RUN-...
  --review-by 2026-12-31 --link MEM-...`; they stay quarantined until
  `memory-promote` with validation — never active in the same run that
  produced them. Once promoted, lessons flow back automatically: every
  context packet recalls active lessons whose `--scope` globs intersect the
  task's write scope, plus records one hop away via `--link` — deterministic
  associative recall, so what the system learned about an area reaches the
  next agent that touches that area.
- **Stale stacks**: if a dependency is re-run after a dependent task finished,
  the dependent's evidence no longer reflects reality. `run_ready` and
  `ledger-show` report these as `stale_stacks`; re-run the dependent with
  `python3 scripts/aers.py requeue --feature FEAT-101 --task T-00N --reason
  "stale stack"` (an explicit human action recorded on the event chain) before
  external verification.
- **Cleanup**: after merge, `git worktree remove <path>` and delete the
  `aers/...` branch; evidence dirs are your audit trail — archive, don't
  delete.
- **Changing a contract**: registered packs are immutable; author a new
  version (new feature id or bumped version) and re-register.

## Troubleshooting

| Symptom | Meaning | Fix |
|---|---|---|
| `Network isolation could not be proven; fail closed` | no `unshare` userns and no outer sandbox asserted | run inside a sandbox that actually denies egress (see `agent_docs/sandbox-setup.md`) and set `AERS_NETWORK_ISOLATED=1` — that variable is an **operator assertion**, not a proof; setting it without such a sandbox falsifies the evidence. For manual `author-verify`, `--degraded` records weaker evidence explicitly instead (the loop stays strict on purpose) |
| `Candidate worktree is dirty` | verification only binds to exact commits | let the loop own commits; don't hand-edit its worktrees |
| `DIFFERENTIAL_TEST_PASSES_ON_BASE` | your new test doesn't test the new behavior | write a test that fails before the implementation exists |
| `Registered immutable feature/task definition differs` | contract edited after registration | new approved version, re-register |
| `Task cannot be leased from state: author_ready` | you're re-running finished work | fresh demo/feature, or proceed to external verify + merge |
| loop exit 2 with `IMPLEMENTER_EDITED_TEST` | working as intended | route test changes through a `test_author` task |
