#!/usr/bin/env python3
"""Offline LLM-auditor stub: emits a schema-valid pass report bound to the candidate.

Wire: AERS_AUDITOR_CMD_JSON='["python3","scripts/adapters/stub_auditor.py","--output","{output}","--candidate","{candidate_sha}"]'
For pipeline testing only.
"""
import argparse, json, os
from pathlib import Path

p = argparse.ArgumentParser(); p.add_argument('--output', required=True); p.add_argument('--candidate', required=True)
a = p.parse_args()
report = {"schema_version": 1, "feature_id": os.environ['AERS_FEATURE_ID'], "task_id": os.environ['AERS_TASK_ID'],
          "candidate_sha": a.candidate, "verdict": "pass", "confidence": 0.5, "findings": [],
          "statement": "STUB auditor for pipeline testing only"}
Path(a.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('stub auditor: pass')
