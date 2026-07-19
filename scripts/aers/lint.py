"""Control-plane lint: required files, schema/JSON/TOML/Python validity, placeholders, skill hashes, memory integrity."""
from __future__ import annotations

import hashlib
import json
import py_compile
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_feature, validate_tasks
from .util import load_json


def lint_repo(repo: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    required = ["AGENTS.md","aers.toml",".agents/constitution.md",".agents/policies/autonomy-policy.json",
                ".agents/schemas/feature-contract.schema.json","scripts/aers.py","scripts/loop.py",
                ".agents/doctrine/engineering-axioms.md",".agents/doctrine/data-doctrine.md",
                ".agents/doctrine/pattern-library.md",".agents/doctrine/decision-frameworks.md"]
    for rel in required:
        if not (repo / rel).exists():
            findings.append({"severity":"error","code":"MISSING_REQUIRED","message":rel})
    try:
        raw = tomllib.loads((repo / "aers.toml").read_text(encoding="utf-8"))
        if raw.get("version") != 1:
            findings.append({"severity":"error","code":"CONFIG_VERSION","message":"aers.toml version must be 1"})
    except Exception as exc:
        findings.append({"severity":"error","code":"INVALID_TOML","message":str(exc)})

    for path in repo.rglob("*.json"):
        if any(part in {".git", ".aers-runtime", ".aers-evidence"} for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            findings.append({"severity":"error","code":"INVALID_JSON","message":f"{path.relative_to(repo)}: {exc}"})

    for path in repo.rglob("*.py"):
        if ".git" in path.parts:
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            findings.append({"severity":"error","code":"PYTHON_SYNTAX","message":f"{path.relative_to(repo)}: {exc}"})

    for path in repo.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.count("```") % 2:
            findings.append({"severity":"error","code":"UNBALANCED_FENCE","message":str(path.relative_to(repo))})
        if "<<PLACEHOLDER" in text:
            findings.append({"severity":"error","code":"UNRESOLVED_PLACEHOLDER","message":str(path.relative_to(repo))})

    # Load-bearing docs must not reference repo files that do not exist —
    # mechanical guard against doc/code drift. Conservative: inline-code refs
    # only (fenced blocks skipped), known top-level dirs only, placeholders and
    # example/future IDs (FEAT-*, ADR-0001+, runtime artifacts) skipped.
    doc_files = ["README.md", "TUTORIAL.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "MISSION.md",
                 "CONTRIBUTING.md", ".agents/README.md", ".agents/memory/README.md"]
    doc_files += sorted(str(p.relative_to(repo)) for p in (repo / ".agents/doctrine").glob("*.md") if p.is_file())
    doc_files += sorted(str(p.relative_to(repo)) for p in (repo / "agent_docs").glob("*.md") if p.is_file())
    known_dirs = {"scripts", ".agents", ".specify", ".claude", ".github", "docs", "evals", "examples", "agent_docs", "tests", "memory"}
    ref_pattern = re.compile(r"`([A-Za-z0-9_.\-/]+\.(?:md|py|sh|json|toml|yml|jsonl))`")
    for rel in doc_files:
        doc_path = repo / rel
        if not doc_path.exists():
            continue
        prose = re.sub(r"```.*?```", "", doc_path.read_text(encoding="utf-8", errors="replace"), flags=re.S)
        for ref in sorted(set(ref_pattern.findall(prose))):
            if "/" not in ref or ref.split("/", 1)[0] not in known_dirs:
                continue
            if re.search(r"FEAT-|T-\d|MEM-|RUN-|ADR-000[1-9]", ref):
                continue
            if not (repo / ref).exists():
                findings.append({"severity":"error","code":"MISSING_DOC_REFERENCE","message":f"{rel} references nonexistent {ref}"})

    lock_path = repo / ".agents/skills/skills.lock.json"
    if lock_path.exists():
        lock = load_json(lock_path)
        for skill in lock.get("skills", []):
            path = repo / skill["path"]
            if not path.exists():
                findings.append({"severity":"error","code":"MISSING_SKILL","message":skill["path"]})
            elif hashlib.sha256(path.read_bytes()).hexdigest() != skill["sha256"]:
                findings.append({"severity":"error","code":"SKILL_HASH_MISMATCH","message":skill["path"]})

    feature_root = repo / ".specify/specs"
    if feature_root.exists():
        for directory in feature_root.iterdir():
            if not directory.is_dir():
                continue
            fp, tp = directory / "feature.contract.json", directory / "tasks.json"
            if fp.exists() or tp.exists():
                try:
                    feature, tasks = load_json(fp), load_json(tp)
                    validate_feature(feature)
                    validate_tasks(tasks, feature)
                except Exception as exc:
                    findings.append({"severity":"error","code":"INVALID_FEATURE_PACK","message":f"{directory.name}: {exc}"})

    # Active memory integrity and expiration.
    index = load_json(repo / ".agents/memory/index.json")
    today = datetime.now(timezone.utc).date()
    for item in index.get("active_records", []):
        path = repo / item["path"]
        if not path.exists():
            findings.append({"severity":"error","code":"MISSING_ACTIVE_MEMORY","message":item["path"]})
            continue
        record = load_json(path)
        if record.get("sha256") != item.get("sha256"):
            findings.append({"severity":"error","code":"MEMORY_HASH_MISMATCH","message":item["path"]})
        from .util import hash_object
        if hash_object({k: v for k, v in record.items() if k != "sha256"}) != record.get("sha256"):
            findings.append({"severity":"error","code":"MEMORY_CONTENT_TAMPERED","message":item["path"]})
        try:
            if datetime.fromisoformat(record["review_by"].replace("Z", "+00:00")).date() < today:
                findings.append({"severity":"error","code":"MEMORY_EXPIRED","message":item["path"]})
        except Exception:
            findings.append({"severity":"error","code":"MEMORY_REVIEW_DATE","message":item["path"]})

    return {"passed":not any(x["severity"] == "error" for x in findings),"findings":findings}
