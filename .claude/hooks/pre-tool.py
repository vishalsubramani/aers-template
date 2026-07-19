#!/usr/bin/env python3
import json, subprocess, sys
payload=sys.stdin.read()
proc=subprocess.run([sys.executable,"scripts/aers.py","hook","pre-tool"],input=payload,text=True)
raise SystemExit(proc.returncode)
