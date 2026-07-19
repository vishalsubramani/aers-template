#!/usr/bin/env python3
import json, os, sys
_ = sys.stdin.read()
if os.environ.get("AERS_RUN_ID"):
    print(json.dumps({"decision":"block","reason":"Configuration changes are forbidden during an autonomous task run"}))
    raise SystemExit(2)
print(json.dumps({"decision":"allow","reason":"No autonomous run identity is active"}))
