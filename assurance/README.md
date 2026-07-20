# AERS Assurance Layer

Additive, machine-readable assurance for AERS. Everything here is **author-side**
— it never issues `VERIFIED` and never mutates the protected control plane. Drive
it with `python3 scripts/assure.py <command>` or the `make` targets.

## Contents

| Path | What |
|------|------|
| `profiles/` | Versioned assurance profiles (Lite, Standard, High Assurance, Regulated) as JSON with REQUIRED/RECOMMENDED/OPTIONAL/NOT_APPLICABLE per control |
| `controls.json` | Control catalog: description, category, evidence source, remediation, whether a failure blocks AUTHOR_READY or VERIFIED |
| `benchmark/cases.jsonl` | Seeded adversarial cases; each drives a live control |
| `threats/threat-model.json` | Structured threat matrix (source for the generated doc) |
| `assurance-case/assurance-case.json` | Evidence-linked claims → implementation, tests, benchmark cases, pinned digests |
| `health/health-cases.jsonl` | Evaluator-health cases (seeded defects + canaries) |
| `schemas/` | Verifier handoff/attestation/request-response and reviewer-independence schemas |

## Commands

```
python3 scripts/assure.py assess --profile high-assurance   # compliance/maturity
python3 scripts/assure.py benchmark                          # adversarial benchmark
python3 scripts/assure.py assurance                          # evidence-linked assurance case
python3 scripts/assure.py threat-model [--render]            # validate / render threat matrix
python3 scripts/assure.py evaluator-health                   # test the evaluator itself
python3 scripts/assure.py isolation --risk R2                # classify isolation state
python3 scripts/assure.py handoff ...                        # build immutable candidate handoff
python3 scripts/assure.py attest-demo --handoff h.json       # OFFLINE demo attestation (never production-valid)
python3 scripts/assure.py verify-attestation ...             # fail-closed attestation verification
python3 scripts/assure.py evidence-manifest                  # aggregate author-side evidence
python3 scripts/assure.py migrate --assess /path/to/repo     # non-destructive adoption plan
```

## The one invariant that matters most

`verify-attestation` returns `production_valid: true` only when the signing key is
a **production** key in the trust store. The repository trust store has **no**
production keys, and the demo key is explicitly non-production. Therefore no code
in this repository can produce a production-valid `VERIFIED`. That is proven by
`tests/aers_selftest/test_verifier.py` and `BENCH-ATT-001`.
