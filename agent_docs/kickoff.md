# Kickoff — from MISSION.md to the first approved feature packs

Vendor-neutral procedure for bootstrapping autonomous engineering in this
repository. Claude Code exposes it as `/kickoff`; any other agent (Codex,
Gemini, Copilot, a human) follows it verbatim.

1. Read `MISSION.md`, `AGENTS.md`, and `.agents/constitution.md`. If
   `MISSION.md` still contains its `<!-- PLACEHOLDER` marker, stop and ask the
   human to fill it in and commit — do not invent a mission. (The task runners
   also refuse mechanically: `scripts/loop.py` and `scripts/run_ready.py`
   safe-stop while the marker is present.)
2. Sanity-check the control plane: `python3 scripts/aers.py lint` and
   `make bootstrap` must pass. If the repository has existing code, also read
   `.agents/context/` and update stale facts there via the normal control-plane
   change process (human-approved PR), not silently.
3. Derive a roadmap: decompose the mission into the smallest useful sequence of
   features. For each of the first one to three features, scaffold a pack with
   `python3 scripts/aers.py init-feature <FEAT-ID> --title "..." --mode S1` and
   complete `spec.md`, `feature.contract.json` (EARS-style acceptance criteria
   with evidence types), and `tasks.json` (test_author before implementer, argv
   command arrays, tight write scopes and budgets), following
   `.specify/templates/` and `examples/feature-pack/FEAT-001/`.
4. Present the roadmap and the drafted packs to the human for review. Do not
   implement in this role.
5. The human approves by editing each `feature.contract.json`: set `status` to
   `"approved"` and replace the `REPLACE_WITH_OWNER` scaffold owner, then
   commit. Registration refuses drafts and scaffold owners, so this step cannot
   be skipped.
6. After the approval commit: `python3 scripts/aers.py ledger-init`, then
   `python3 scripts/aers.py register --feature <FEAT-ID>`, then hand off to the
   task loop (`scripts/loop.py` or `scripts/run_ready.py`) per `TUTORIAL.md`
   Part 1.

Completion of any task is `AUTHOR_READY` at most. Never claim `VERIFIED`.
