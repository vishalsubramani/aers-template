# AERS Residual-Risk Register

Explicit, non-hidden residual risks after the production-assurance program. A
risk being listed here is the honest alternative to converting an incomplete
production integration into a `PASS`.

| ID | Risk | Why it remains | Mitigation / owner | Accepted until |
|----|------|----------------|--------------------|----------------|
| RR-01 | **No production verifier is deployed.** The external verifier protocol and offline demo exist, but production `VERIFIED` requires deploying the verifier in a separate protected trust domain with a real private key. | Deploying/holding production keys is out of scope for a template repository. | `assess` reports `CTRL-EXTERNAL-VERIFIER` as `PARTIAL` (never `PASS`); deploy per `docs/ADOPTION.md`. Owner: security. | production rollout |
| RR-02 | **Demo signer is symmetric (HMAC).** | Keeps the protocol runnable fully offline. | Production swaps in asymmetric signatures; the repo only holds the public/demo side. Owner: security. | production rollout |
| RR-03 | **Private holdouts are contract-only.** The private-eval contract exists; real holdouts must live outside the author trust domain. | Holdouts inside a writable repo are not a boundary. | `CTRL-PRIVATE-ORACLE` reported `PARTIAL`. Owner: reviewer. | High Assurance adoption |
| RR-04 | **In-place default strengthenings are staged, not applied.** `require_second_reviewer_r2=true`, isolation-in-`verify.py`, reviewer-independence schema live in `docs/proposed-control-plane-change/`. | Applying them is a protected control-plane change that must not be made by the run proposing them (ADR-0004). | Control-plane owner applies under the dogfooding workflow. Owner: principal-architect. | next control-plane change window |
| RR-05 | **Evaluator-health covers the deterministic audit only.** Model-reviewer health needs live-model runs. | No live model is available offline. | Deterministic evaluator fully covered; add live-model canaries when a model is wired. Owner: reviewer. | live-model integration |
| RR-06 | **Isolation `PROVEN` depends on the host.** A host without a namespace mechanism cannot reach `PROVEN` locally. | Proof requires a real mechanism. | R2+ fails closed; run on trusted infra that supplies an attestation. Owner: sre. | infra provisioning |
| RR-07 | **Baseline comparison uses simulated trajectories.** The comparison harness distinguishes simulated from empirical evidence but has no live-model numbers yet. | No live model offline. | Clearly labeled simulated; re-run with a model for empirical numbers. Owner: reviewer. | live-model integration |
| RR-08 | **Two correlated reviewers can share a blind spot.** | Independence is structural, not perfect. | Evaluator-health monitors reviewer correlation; `THREAT-RUBBER-STAMP` tracks it. Owner: reviewer. | ongoing |

## Handling

Every item above is time-bounded and owned. `PARTIAL`/`UNVERIFIABLE` in `assess`
and the residual-risk statements in `assurance/threats/threat-model.json` and the
assurance case are the machine-readable counterparts of this register.
