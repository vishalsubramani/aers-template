"""Adoption and migration experience.

`migrate --assess <target>` inspects an existing repository and produces a
non-destructive migration plan: which AERS files would be ADDED vs SKIPPED
(already present), a recommended starting profile, conflict warnings, and backup
guidance. It never writes to the target — planning only. The actual copy is done
by the non-destructive `install.sh`; this module makes the plan inspectable and
testable, and its idempotency is proven by the self-tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Files the template contributes, grouped by the profile they first unlock. The
# plan uses these to recommend the lowest profile that fits the target today.
_LITE_MARKERS = ["aers.toml", ".agents/policies/protected-paths.json", "scripts/aers/scope.py", "Makefile"]
_STANDARD_MARKERS = [".agents/schemas/feature-contract.schema.json", ".specify/specs"]
_EXCLUDE_PARTS = {".git", ".aers-runtime", ".aers-evidence", "__pycache__"}


def _template_files(template_root: Path) -> list[str]:
    files = []
    for p in template_root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _EXCLUDE_PARTS for part in p.parts):
            continue
        if p.suffix == ".pyc" or p.name == ".DS_Store":
            continue
        rel = p.relative_to(template_root).as_posix()
        # install.sh does not copy these three template-only files.
        if rel in {"install.sh", "README.md", "pyproject.toml"}:
            continue
        files.append(rel)
    return sorted(files)


def plan(template_root: Path, target: Path) -> dict[str, Any]:
    """Compute the non-destructive install plan without touching the target."""
    files = _template_files(template_root)
    to_add, to_skip = [], []
    for rel in files:
        (to_skip if (target / rel).exists() else to_add).append(rel)
    # Conflicts of consequence: existing control-plane wiring that install.sh
    # would keep (so AERS enforcement would NOT be active until merged).
    critical = [".claude/settings.json", "Makefile", ".gitignore", "aers.toml"]
    conflicts = [rel for rel in to_skip if rel in critical or rel.startswith(".claude/hooks/")]
    return {
        "schema_version": 1,
        "target": str(target),
        "template_file_count": len(files),
        "would_add": to_add,
        "would_skip": to_skip,
        "add_count": len(to_add),
        "skip_count": len(to_skip),
        "conflicts": conflicts,
        "is_git_repo": (target / ".git").exists(),
        "destructive": False,
        "backup_guidance": "install.sh never overwrites; back up the target with `git stash` or a commit before "
                           "merging any SKIPPED control-plane files (see conflicts).",
    }


def recommend_profile(target: Path) -> dict[str, Any]:
    """Recommend the lowest AERS profile the target already satisfies, and the
    next step to climb. Presence-based (structural), not a documentation claim."""
    has_lite = all((target / m).exists() for m in _LITE_MARKERS)
    has_standard = has_lite and all((target / m).exists() for m in _STANDARD_MARKERS)
    if has_standard:
        current, nxt = "standard", "high-assurance (deploy an external verifier + private holdouts)"
    elif has_lite:
        current, nxt = "lite", "standard (add typed contracts under .specify/specs and enable the differential gate)"
    else:
        current, nxt = "none", "lite (run install.sh, fill MISSION.md, wire Make targets)"
    return {"detected_level": current, "recommended_next": nxt,
            "rationale": {"lite_markers_present": has_lite, "standard_markers_present": has_standard}}


def assess_target(template_root: Path, target: Path) -> dict[str, Any]:
    p = plan(template_root, target)
    p["profile_recommendation"] = recommend_profile(target)
    return p


def render_human(report: dict[str, Any]) -> str:
    rec = report["profile_recommendation"]
    lines = [
        f"AERS migration plan for {report['target']}",
        f"git repo: {report['is_git_repo']}   destructive: {report['destructive']}",
        f"would add {report['add_count']} files, skip {report['skip_count']} existing",
        f"detected level: {rec['detected_level']}  ->  next: {rec['recommended_next']}",
    ]
    if report["conflicts"]:
        lines.append(f"CONFLICTS (kept; merge manually to activate enforcement): {report['conflicts']}")
    return "\n".join(lines)
