"""Assurance-profile and control-catalog loaders."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aers.util import load_json

REQUIREMENT_LEVELS = {"REQUIRED", "RECOMMENDED", "OPTIONAL", "NOT_APPLICABLE"}
PROFILE_IDS = ["lite", "standard", "high-assurance", "regulated"]


def assurance_root(repo: Path) -> Path:
    return repo / "assurance"


def load_profile(repo: Path, profile_id: str) -> dict[str, Any]:
    if profile_id not in PROFILE_IDS:
        raise ValueError(f"Unknown assurance profile '{profile_id}'; choose one of {PROFILE_IDS}")
    profile = load_json(assurance_root(repo) / "profiles" / f"{profile_id}.json")
    bad = {level for level in profile.get("controls", {}).values() if level not in REQUIREMENT_LEVELS}
    if bad:
        raise ValueError(f"Profile {profile_id} has invalid requirement levels: {sorted(bad)}")
    return profile


def load_controls(repo: Path) -> dict[str, Any]:
    return load_json(assurance_root(repo) / "controls.json")["controls"]


def load_all_profiles(repo: Path) -> dict[str, dict[str, Any]]:
    return {pid: load_profile(repo, pid) for pid in PROFILE_IDS}
