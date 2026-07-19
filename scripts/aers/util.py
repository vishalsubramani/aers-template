"""Shared helpers: repo root discovery, atomic writes, hashing, redaction, timestamps."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),                       # Slack tokens
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),                             # OpenAI-style keys
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWTs
    re.compile(r"(?i)\b(?:bearer|authorization)\b\s*[:=]?\s*[A-Za-z0-9._~+/-]{16,}"),
    re.compile(r"(?i)\baws[_-]?secret[_-]?access[_-]?key\b\s*[:=]\s*\S{16,}"),
    # quoted OR unquoted key=value / key: value secrets
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd|access[_-]?key|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd|access[_-]?key|client[_-]?secret)\s*[:=]\s*(?!['\"])\S{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def hash_object(value: Any) -> str:
    return sha256_text(canonical_json(value))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Required JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=False) + "\n")


def redact(text: str, limit: int = 20000) -> str:
    result = text[:limit]
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    if len(text) > limit:
        result += f"\n[TRUNCATED {len(text) - limit} CHARACTERS]"
    return result


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "aers.toml").exists():
            return candidate
    raise ValueError(f"Could not locate repository root from {current}")


def safe_relpath(path: Path, root: Path) -> str:
    resolved_root = root.resolve()
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path escapes repository root: {path}") from exc
