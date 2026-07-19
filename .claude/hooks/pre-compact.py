#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
payload=sys.stdin.read()
path=os.environ.get("AERS_TRAJECTORY_PATH")
if path:
    event={"timestamp":datetime.now(timezone.utc).isoformat(),"run_id":os.environ.get("AERS_RUN_ID","unknown"),"event_type":"state","result":"pre_compact","redacted":True,"attributes":{"durable_memory_written":False}}
    with open(path,"a",encoding="utf-8") as f:f.write(json.dumps(event)+"\n")
print(json.dumps({"decision":"allow","reason":"Compaction noted; no durable memory was written"}))
