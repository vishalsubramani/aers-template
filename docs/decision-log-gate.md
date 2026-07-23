# Decision-log gate

Additive, author-side hardening that makes the **record of agent judgment** — decision
points, assumptions, trade-offs — a reviewable artifact whose *absence* is unskippable at
merge time for every gated feature, regardless of which vendor's agent (Claude, Codex,
Gemini, a human) produced the work. What the gate can and cannot guarantee is stated plainly
under "What the gate cannot see" below — this is a process control, not a proof of honesty.

## Why

Humans do not read every line of AI-generated code, and pretending otherwise makes review
theater. What a human *can* review is the control plane: which forks the agent hit, what it
assumed when the spec was silent, what it traded away, and how confident it was. Today that
record exists only as ADRs (deliberately few) and evaporating PR comments. Everything
between — the dozens of implementation-level judgments per feature — is invisible unless
someone re-derives it from the diff.

The decision log (`agent_docs/decision-log.md`) fixes the artifact; this gate makes its
absence impossible to miss. The design goal: **put the human back in the control seat**
through the decisions and the philosophy used to make them, not through line-by-line
reading.

## What it does

`scripts/checks/decision_log_gate.py` runs on every `make check` (and thus in CI),
fail-closed:

- Every **approved** feature whose `risk_tier` is in `required_risk_tiers` must carry
  `.specify/specs/<FEAT>/decision-log.jsonl` with at least one schema-valid entry.
- Every decision-log line in the repository (feature packs and `docs/decisions/`) must
  validate: required fields, enums, unique ids, doctrine refs well-formed (`AX-/DD-/PAT-/
  DF-`), deviation entries naming their accepted ADR.
- For gated features, **risky entries demand a human**: reversibility `one-way`, confidence
  `low`, or any assumption flagged `needs_human_validation` must be `validated` or
  `countered`, with `validated_by` set to a human id that is **not** the configured agent
  `author_id`. A countered entry must carry a `follow_up`. CI stays red until the human
  acts — that is the mechanism working.

Config is shared with the independent-review gate (`assurance/reviews/config.json`:
`author_id`, `required_risk_tiers`, `exclude_features`) so one policy governs both
artifacts. Exclusions are logged loudly, never silent.

## How it composes with the existing controls

- The **independent-review gate** proves a second set of eyes judged the *outcome*; this
  gate preserves the *reasoning* those eyes (and the human) judged. One without the other
  is either unexplained approval or unexamined explanation.
- The **PR template** front-loads the log: reviewers are pointed at the new log lines in
  the diff before the code, with a checkbox attesting each assumption was validated or
  countered.
- **ADR discipline** is unchanged: an entry never authorizes deviation; `deviation-adr`
  entries must point at an accepted ADR, and load-bearing entries get promoted.
- Like every author-side control, this proves process, not truth. The boundary remains
  human review, CODEOWNERS, and branch protection. An agent can write a self-serving log;
  what the gate guarantees is that it cannot write an *absent* one, cannot relax the policy
  in the same PR, and cannot mark a risky entry validated without a non-author handle — but
  the handle's humanity, and the honesty of the entry's self-declared risk, are the human
  reviewer's job, not the gate's.

## What the gate cannot see (limits, stated honestly)

A gate proves process, not truth. These are the known gaps; the compensating control for
each is human review plus the protections in `docs/proposed-control-plane-change/`.

- **Humanity of `validated_by`.** The gate checks the handle is present and is not the agent
  author id; it cannot prove a human typed it. An agent that invents a plausible handle
  passes this check. Compensating control: CODEOWNERS on the log paths (`.specify/specs/**`,
  `docs/decisions/**`) so a real reviewer's approval is required to merge the change that
  sets it.
- **Honesty of self-declared risk.** `reversibility` and `confidence` are asserted by the
  author. Labeling a one-way decision `cheap`, or a shaky assumption `high` confidence,
  dodges the mandatory-human rule. The gate cannot adjudicate this; reviewers should be
  skeptical of any entry touching migrations, schemas, or public APIs that claims `cheap`,
  and of a large feature whose entries flag *zero* assumptions for validation.
- **Completeness.** The gate checks the log is present, valid, and append-only; it cannot
  know a decision was made but *not logged*. A minimal-compliance log with one trivial entry
  passes presence. The reviewer's question — "does this log explain the decisions I see in
  the diff?" — is the real completeness check; the gate's computed salience line (entry and
  risky-entry counts) exists to make that comparison cheap.
- **Timing.** "Log at decision time" is a discipline, not a mechanical guarantee; a log
  written wholesale at the end passes. Under squash-merge the git timestamps that might
  reveal this are erased, so it is not enforced.
- **Volume / flooding.** Nothing caps entry count. Many trivial entries can bury a risky one.
  The salience line surfaces the risky subset by id so burial is visible, but attention is
  finite — the reviewer must still read the flagged entries.

The mechanical guarantees the gate *does* provide: a gated feature cannot merge with an
absent, empty, malformed, or non-append-only log; risky entries cannot go green while
`pending`; a "validated"/"countered" label requires a non-author handle (and a counter a
follow-up); and the policy and gated status are read from the committed baseline, so a PR
cannot relax its own gate. Everything above is what those guarantees deliberately do **not**
cover.

## Reviewing a PR through the log

1. Open the diff of `decision-log.jsonl` — the new lines are this PR's judgment.
2. For each: is the context real, are the rejected options fairly stated, is the trade-off
   acceptable, is the assumption true?
3. Agree → set `human_status: "validated"`, `validated_by: "<you>"`.
   Disagree → set `"countered"` plus a `follow_up` (fix task, ADR, or constraint), and the
   correction lives in the record every future agent reads — not in a comment thread that
   evaporates.

## Format

See `agent_docs/decision-log.md` for the entry schema, writing discipline, and the full
review protocol; `examples/feature-pack/FEAT-001/decision-log.jsonl` shows the artifact;
`docs/decisions/` holds logs for non-feature work (including this kit's own).
