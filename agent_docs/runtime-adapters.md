# Runtime Adapters

AERS never assumes a particular agent CLI and never appends a skip-permissions flag. Configure outer commands as
JSON argv arrays so the orchestrator does not invoke a shell.

```bash
export AERS_AGENT_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{prompt_file}","--cwd","{worktree}","--inner-env","AERS_AGENT_INNER_CMD_JSON"]'
export AERS_AGENT_INNER_CMD_JSON='["claude","-p","{prompt}","--output-format","json"]'

export AERS_REVIEWER_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{review_prompt}","--cwd","{worktree}","--inner-env","AERS_REVIEWER_INNER_CMD_JSON"]'
# The reviewer command must create the requested schema-valid output file; use a runtime adapter/subagent capable of doing so.
```

Exact flags vary by runtime and version; validate the adapter in a sandbox. The outer orchestrator remains the
owner of scope checks, commits, rollback, and evidence. Tool-native hooks are early controls, not authority.
