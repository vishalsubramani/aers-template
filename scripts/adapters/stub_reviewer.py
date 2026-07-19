#!/usr/bin/env python3
"""Offline reviewer stub: emits a schema-valid pass report bound to the candidate.

Wire: AERS_REVIEWER_CMD_JSON='["python3","scripts/adapters/stub_reviewer.py","--output","{output}","--candidate","{candidate_sha}"]'
Reads AERS_FEATURE_ID / AERS_TASK_ID from the loop environment and the immutable
task contract (for acceptance IDs) from cwd. For pipeline testing only — a stub
cannot judge correctness; use a real reviewer for real work.
"""
import argparse, json, os
from pathlib import Path

p = argparse.ArgumentParser(); p.add_argument('--output', required=True); p.add_argument('--candidate', required=True)
a = p.parse_args()
feature_id = os.environ['AERS_FEATURE_ID']; task_id = os.environ['AERS_TASK_ID']
tasks = json.loads(Path(f'.specify/specs/{feature_id}/tasks.json').read_text(encoding='utf-8'))
task = next(t for t in tasks['tasks'] if t['id'] == task_id)
report = {"schema_version": 1, "feature_id": feature_id, "task_id": task_id, "candidate_sha": a.candidate,
          "verdict": "pass", "findings": [], "acceptance_reviewed": task['acceptance'],
          "statement": "STUB reviewer for pipeline testing only"}
Path(a.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('stub reviewer: pass')
