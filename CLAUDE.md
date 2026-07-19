@AGENTS.md

# Claude Code adapter

The canonical policy is `AGENTS.md` and `.agents/`. Claude hooks provide early feedback but are not the
security boundary. `TaskCompleted` must run the author gate; `ConfigChange` and protected paths are
blocked; `PreCompact` writes no durable memory. Specialized procedures live in `.claude/agents/` and
`agent_docs/` and are loaded only for the active role.
