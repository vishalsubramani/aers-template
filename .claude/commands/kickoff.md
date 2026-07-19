Bootstrap autonomous engineering for this repository from its mission: follow the vendor-neutral
procedure in `agent_docs/kickoff.md` exactly. In short: read `MISSION.md` (stop if it is still the
placeholder) and `.agents/doctrine/`, sanity-check the control plane, draft the foundation ADRs
(architecture and data baselines) if none are accepted yet, derive a roadmap of one to three feature
packs with `python3 scripts/aers.py init-feature`, present everything for human review, and only after
the human flips each contract to `status: "approved"` with a real owner and commits, register and hand
off to the task loop. Do not implement in this role. Completion is `AUTHOR_READY` at most; never claim
`VERIFIED`.
