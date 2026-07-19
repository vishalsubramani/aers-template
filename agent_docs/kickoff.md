# Kickoff — from MISSION.md to the first approved feature packs

Vendor-neutral procedure for bootstrapping autonomous engineering in this
repository. Claude Code exposes it as `/kickoff`; any other agent (Codex,
Gemini, Copilot, a human) follows it verbatim.

1. Read `MISSION.md`, `AGENTS.md`, `.agents/constitution.md`, and
   `.agents/doctrine/`. If
   `MISSION.md` still contains its `<!-- PLACEHOLDER` marker, stop and ask the
   human to fill it in and commit — do not invent a mission. (The task runners
   also refuse mechanically: `scripts/loop.py` and `scripts/run_ready.py`
   safe-stop while the marker is present.)
2. Sanity-check the control plane: `python3 scripts/aers.py lint` and
   `make bootstrap` must pass. If the repository has existing code, also read
   `.agents/context/` and update stale facts there via the normal control-plane
   change process (human-approved PR), not silently.
3. Lay the foundation before any feature. If `docs/adr/` has no accepted
   baseline ADRs, draft them now from `.agents/doctrine/` defaults using
   `docs/adr/ADR-0000-template.md`:
   - **ADR-0001 Architecture baseline** — module boundaries, dependency
     direction (AX-03/04), stack choices with innovation tokens spent (AX-01),
     and how the architecture rule is enforced in `make check`.
   - **ADR-0002 Data baseline** — store choice, schema conventions (DD-04..07),
     migration mechanism and zero-downtime posture (DD-10/11), and dataset
     ownership (DD-18).
   These are proposals: a human accepts them before they bind. Every later
   plan cites them, so nothing about structure or data shape is decided
   ad hoc inside a feature task.
4. Derive a roadmap: decompose the mission into the smallest useful sequence of
   features. For each of the first one to three features, scaffold a pack with
   `python3 scripts/aers.py init-feature <FEAT-ID> --title "..." --mode S1` and
   complete `spec.md`, `feature.contract.json` (EARS-style acceptance criteria
   with evidence types), and `tasks.json` (test_author before implementer, argv
   command arrays, tight write scopes and budgets), following
   `.specify/templates/` and `examples/feature-pack/FEAT-001/`.
5. Present the roadmap and the drafted packs to the human for review. Do not
   implement in this role.
6. The human approves by editing each `feature.contract.json`: set `status` to
   `"approved"` and replace the `REPLACE_WITH_OWNER` scaffold owner, then
   commit. Registration refuses drafts and scaffold owners, so this step cannot
   be skipped.
7. After the approval commit: `python3 scripts/aers.py ledger-init`, then
   `python3 scripts/aers.py register --feature <FEAT-ID>`, then hand off to the
   task loop (`scripts/loop.py` or `scripts/run_ready.py`) per `TUTORIAL.md`
   Part 1.

Completion of any task is `AUTHOR_READY` at most. Never claim `VERIFIED`.
