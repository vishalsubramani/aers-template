"""Read committed-baseline versions of gate policy and contracts.

Both author-side gates must not be relaxable by the same change that edits their
policy: an agent that adds itself to `exclude_features`, empties
`required_risk_tiers`, swaps `author_id`, or downgrades a contract's `risk_tier`
in its own PR would otherwise be judged by the loosened policy it just wrote.
This mirrors the rule the scope gate already enforces for protected paths —
never rely, in one run, on a guardrail that same run modified.

The gates therefore read policy/contract state from the merge-base with the
default branch, not from the working tree. Tightening or loosening a policy takes
effect only after it is reviewed and merged (CODEOWNERS on the policy paths is the
human boundary; this is the mechanical half).

Degrade safely: when there is no git, no resolvable baseline ref (e.g. a shallow
CI checkout that did not fetch the base), or the file did not exist at baseline (a
genuinely new feature), return None and let the caller fall back to the working
tree with a visible note. Standard library only.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=False)


def is_git_repo(repo: Path) -> bool:
    return _run(repo, "rev-parse", "--is-inside-work-tree").returncode == 0


def baseline_ref(repo: Path) -> str | None:
    """Resolve the ref to read baseline state from: the merge-base of HEAD with the
    default branch, so we compare against this branch's starting point. Honors
    AERS_BASELINE_REF for CI setups that name the base explicitly."""
    override = os.environ.get("AERS_BASELINE_REF")
    candidates = [override] if override else []
    candidates += ["origin/main", "origin/master", "main", "master"]
    for ref in candidates:
        if not ref:
            continue
        if _run(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
            continue
        mb = _run(repo, "merge-base", "HEAD", ref)
        if mb.returncode == 0 and mb.stdout.strip():
            return mb.stdout.strip()
        return ref
    return None


def read_baseline_file(repo: Path, relpath: str) -> str | None:
    """Text of relpath at the baseline ref, or None if unavailable (no git, no
    baseline ref, or the path did not exist at baseline)."""
    ref = baseline_ref(repo)
    if not ref:
        return None
    r = _run(repo, "show", f"{ref}:{relpath}")
    if r.returncode != 0:
        return None
    return r.stdout
