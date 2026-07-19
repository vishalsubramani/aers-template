from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import find_repo_root


@dataclass(frozen=True)
class Config:
    repo: Path
    raw: dict[str, Any]

    @property
    def state_dir(self) -> Path:
        override = os.environ.get("AERS_STATE_DIR")
        value = override or self.raw.get("state_dir", ".aers-runtime")
        path = Path(value)
        return path if path.is_absolute() else self.repo / path

    @property
    def evidence_dir(self) -> Path:
        override = os.environ.get("AERS_EVIDENCE_DIR")
        value = override or self.raw.get("evidence_dir", ".aers-evidence")
        path = Path(value)
        return path if path.is_absolute() else self.repo / path

    @property
    def feature_root(self) -> Path:
        return self.repo / self.raw.get("feature_root", ".specify/specs")

    @property
    def require_network_isolation(self) -> bool:
        return bool(self.raw.get("verification", {}).get("require_network_isolation", True))


def load_config(repo: Path | None = None) -> Config:
    root = find_repo_root(repo)
    path = root / "aers.toml"
    if not path.exists():
        raise ValueError(f"Missing AERS configuration: {path}")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML in {path}: {exc}") from exc
    if raw.get("version") != 1:
        raise ValueError("aers.toml must declare version = 1")
    return Config(root, raw)
