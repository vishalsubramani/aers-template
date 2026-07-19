#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
_ = sys.stdin.read();path=os.environ.get("AERS_TRAJECTORY_PATH")
if path:
    event={"timestamp":datetime.now(timezone.utc).isoformat(),"run_id":os.environ.get("AERS_RUN_ID","unknown"),"event_type":"stop","result":"session_end","redacted":True}
    with open(path,"a",encoding="utf-8") as f:f.write(json.dumps(event)+"\n")
print(json.dumps({"decision":"allow"}))
