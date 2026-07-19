#!/usr/bin/env python3
"""Offline agent stub for pipeline testing: applies a prepared patch in cwd.

Wire:  AERS_AGENT_CMD_JSON='["python3","scripts/adapters/stub_agent.py","--prompt-file","{prompt_file}"]'
Then:  AERS_STUB_PATCH=/abs/path/to/change.patch
The stub leaves the worktree uncommitted, exactly as a real agent must.
"""
import argparse, os, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser(); p.add_argument('--prompt-file', required=True); a = p.parse_args()
patch = os.environ.get('AERS_STUB_PATCH')
patch_dir = os.environ.get('AERS_STUB_PATCH_DIR')
if not patch and patch_dir:
    task_id = os.environ.get('AERS_TASK_ID', '')
    matches = sorted(Path(patch_dir).glob(f'{task_id}-*.patch'))
    patch = str(matches[0]) if matches else None
if not patch or not Path(patch).exists():
    print('AERS_STUB_PATCH (or AERS_STUB_PATCH_DIR with <task-id>-*.patch) must point to an existing patch', file=sys.stderr); raise SystemExit(1)
print(f'stub agent: read prompt {a.prompt_file}; applying {patch}')
proc = subprocess.run(['git', 'apply', '--allow-empty', patch])
raise SystemExit(proc.returncode)
