# Independent-review evidence gate

Additive, author-side hardening that makes AERS's independent-review requirement
**unskippable at merge time** — not only inside `scripts/loop.py`.

## Why

AERS already requires a candidate-bound independent reviewer report before a task
reaches `AUTHOR_READY`. But that enforcement lives inside the task loop. Work
implemented **outside** the loop — by hand, or by an agent that skipped it — can
reach a green PR carrying **zero** independent review, because `make check/test/
security/evals` never look for a reviewer report. An author can also silently
self-review.

This was observed in practice: a repository built on AERS reached "all author gates
green" while the sole agent was **both author and reviewer**. When four fresh-context
independent reviewers were finally run over that "green" core, one found a real
safety-relevant defect the author's own exhaustive tests had missed. The gate below
turns that lesson into a mechanical, fail-closed check.

## What it does

`scripts/checks/independent_review_gate.py` runs on every `make check` (and thus in
CI). For every **approved** feature whose `risk_tier` is in `required_risk_tiers`
(default `["R2"]`), it refuses to pass unless `assurance/reviews/<FEAT>.review.json`:

- has the reviewer-report fields plus `reviewer_id`;
- has `verdict: "pass"` with no unresolved `high`/`critical` findings;
- **binds `candidate_sha`** to a real commit that touches the feature's write scope;
- reviewed **every** acceptance criterion in the contract; and
- was produced by a reviewer whose **`reviewer_id != author_id`** (a self-review
  does not count).

Config: `assurance/reviews/config.json`
(`author_id`, `required_risk_tiers`, `exclude_features`). Exclusions are logged
loudly so one can never silently hide a real feature. See
`assurance/reviews/FEAT-XXX.review.json.example` for the artifact format.

## How it composes with the existing controls

| Control | Today | Recommended for rigid setups |
|---|---|---|
| Independent review required (R2) | inside `loop.py` only | **also at `make check`/CI (this gate)** |
| `require_second_reviewer_r2` (aers.toml) | `false` | **`true`** — a human-approved control-plane change; the agent cannot flip it (protected path). |
| Reviewer ≠ author | convention | **checked mechanically by this gate** |
| Review bound to the exact candidate | in the loop | **re-verified from committed evidence** |

> Note: `aers.toml` is a protected path — the implementing agent is intentionally
> unable to edit it. Flipping `require_second_reviewer_r2 = true` is a deliberate
> human decision. The evidence gate enforces independent review regardless of that
> flag; the flag additionally makes `loop.py` demand a *second, different* reviewer.

## Wire-up

`make check` already depends on `review-gate`. In CI, the author-visible workflow
runs `make check`, so no workflow edit is needed. A feature reaches `AUTHOR_READY`
only when its review artifact exists, passes, and binds to the candidate.

## What it still does not give you

The gate makes review **unskippable**; it does not let a repository self-certify
`VERIFIED`. A fresh-context reviewer is stronger than a self-review but is not yet a
**different model/harness** — that is what `AERS_SECOND_REVIEWER_CMD_JSON` plus the
external verifier trust domain provide.
