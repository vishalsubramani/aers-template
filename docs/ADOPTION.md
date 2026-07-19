# Adopting AERS: profiles and the incremental path

AERS is adoptable in stages. You do not need the full High Assurance architecture
to get value on day one. Pick the lowest profile that fits, then climb.

## Profiles at a glance

| Profile | Required controls | Adds over previous |
|---------|-------------------|--------------------|
| **Lite** | stable commands, scope gate, protected paths, static checks, tests, deterministic audit | the minimum guardrails |
| **Standard** | + typed contracts, fresh process/task, differential gate, independent reviewer, memory quarantine, rollback | most autonomous work |
| **High Assurance** | + external verifier, private holdouts, proven/attested isolation, signed provenance, two R2 reviewers, release segregation, evaluator health | regulated-adjacent / high-blast-radius |
| **Regulated** | + segregation of duties, retained evidence, approval records, policy pinning, auditable exceptions, retention/redaction | compliance regimes |

Definitions are machine-readable under `assurance/profiles/*.json`. Assess any
repository against one with:

```
python3 scripts/assure.py assess --profile standard --json
```

`assess` reports `PASS / FAIL / PARTIAL / NOT_APPLICABLE / UNVERIFIABLE` per
control. Controls that depend on an external trust domain (a deployed verifier,
private holdouts, production signing) are reported `PARTIAL`/`UNVERIFIABLE` from
inside the repo — never `PASS`. That is deliberate honesty, not a gap in scoring.

## Quick start to Lite (small repo)

1. `bash install.sh /path/to/your/repo` — non-destructive; it never overwrites.
2. Fill in `MISSION.md`, commit everything.
3. Wire the `Makefile` targets (`check`, `test`, `security`) to your real tools.
4. `python3 scripts/aers.py lint` and `python3 scripts/assure.py assess --profile lite`.

## Lite → Standard

- Add a typed feature pack under `.specify/specs/<FEAT-ID>/` (see
  `examples/feature-pack/`).
- Enable the differential gate (a new regression test must fail on base).
- Wire an independent reviewer (`AERS_REVIEWER_CMD_JSON`) whose report binds the
  exact `candidate_sha`.

## Standard → High Assurance

- Stand up the **external verifier** in a separate protected repository or runner
  (see `.github/workflows/TRUSTED-VERIFIER.reference.yml.disabled` and
  `scripts/aers_assure/verifier.py`). Local code must never hold the production
  signing key.
- Require a second, different-harness reviewer for R2
  (`require_second_reviewer_r2 = true`, `AERS_SECOND_REVIEWER_CMD_JSON`).
- Move private holdouts into the verifier trust domain.
- Turn on the evaluator-health gate (`make evaluator-health`).

Re-run `assess` after each step to see controls flip from `PARTIAL`/`FAIL` to
`PASS`.
