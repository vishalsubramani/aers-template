#!/usr/bin/env python3
"""Safe argv adapter for prompt-driven agent/reviewer CLIs.

Example:
  AERS_AGENT_CMD_JSON='["python3","scripts/adapters/run_prompt.py","--prompt-file","{prompt_file}","--cwd","{worktree}","--inner-env","AERS_AGENT_INNER_CMD_JSON"]'
  AERS_AGENT_INNER_CMD_JSON='["claude","-p","{prompt}","--output-format","json"]'

No shell is used and no skip-permissions flag is added automatically.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--prompt-file',required=True);p.add_argument('--cwd',required=True);p.add_argument('--inner-env',required=True)
a=p.parse_args(); raw=os.environ.get(a.inner_env)
if not raw: raise SystemExit(f'{a.inner_env} is required')
try: template=json.loads(raw)
except json.JSONDecodeError as exc: raise SystemExit(f'invalid {a.inner_env}: {exc}')
if not isinstance(template,list) or not template or not all(isinstance(x,str) for x in template): raise SystemExit(f'{a.inner_env} must be a JSON string array')
prompt=Path(a.prompt_file).read_text(encoding='utf-8')
argv=[x.replace('{prompt}',prompt).replace('{prompt_file}',a.prompt_file).replace('{cwd}',a.cwd) for x in template]
proc=subprocess.run(argv,cwd=a.cwd)
raise SystemExit(proc.returncode)
