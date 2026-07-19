#!/usr/bin/env python3
import subprocess, sys
proc=subprocess.run([sys.executable,"scripts/aers.py","hook","task-completed"])
raise SystemExit(proc.returncode)
