from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import atomic_write_json, hash_object, load_json, utc_now


def propose(repo: Path, statement: str, scope: list[str], provenance: list[str], review_by: str) -> Path:
    if not statement.strip() or not provenance:
        raise ValueError("Memory proposal requires a statement and provenance")
    record_id = f"MEM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    record: dict[str, Any] = {"schema_version":1,"id":record_id,"status":"quarantine","statement":statement.strip(),
                              "scope":scope,"provenance":provenance,"review_by":review_by,"validation":[],"conflicts":[]}
    record["sha256"] = hash_object({k:v for k,v in record.items() if k != "sha256"})
    path = repo / ".agents/memory/quarantine" / f"{record_id}.json"
    atomic_write_json(path, record)
    return path


def promote(repo: Path, record_path: Path, validation: list[str]) -> Path:
    curator = os.environ.get("AERS_CURATOR_ID")
    if not curator:
        raise ValueError("AERS_CURATOR_ID is required; the proposer/author process must not self-promote memory")
    record = load_json(record_path)
    if record.get("status") != "quarantine":
        raise ValueError("Only quarantined memory may be promoted")
    if len(set(validation)) < 2:
        raise ValueError("Promotion requires evidence from at least two distinct validation runs")
    expected = hash_object({k:v for k,v in record.items() if k != "sha256"})
    if expected != record.get("sha256"):
        raise ValueError("Memory proposal hash mismatch")
    record["status"] = "active"
    record["validation"] = validation
    record["curator"] = curator
    record["activated_at"] = utc_now()
    record["sha256"] = hash_object({k:v for k,v in record.items() if k != "sha256"})
    active_path = repo / ".agents/memory/active" / record_path.name
    atomic_write_json(active_path, record)
    index_path = repo / ".agents/memory/index.json"
    index = load_json(index_path)
    existing = [item for item in index.get("active_records", []) if item.get("id") != record["id"]]
    existing.append({"id":record["id"],"path":active_path.relative_to(repo).as_posix(),"sha256":record["sha256"],"review_by":record["review_by"],"curator":curator})
    index["active_records"] = sorted(existing, key=lambda x: x["id"])
    atomic_write_json(index_path, index)
    return active_path
