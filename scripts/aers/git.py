"""Thin subprocess wrappers over git: rev-parse, diff, clean-export, worktree helpers."""
from __future__ import annotations

import io
import os
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


def run_git(repo: Path, args: Iterable[str], check: bool = True) -> CommandResult:
    argv = ["git", "-C", str(repo), *list(args)]
    proc = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = CommandResult(argv, proc.returncode, proc.stdout, proc.stderr)
    if check and proc.returncode != 0:
        raise ValueError(f"Git command failed ({proc.returncode}): {' '.join(argv)}\n{proc.stderr.strip()}")
    return result


def ensure_git_repo(repo: Path) -> None:
    result = run_git(repo, ["rev-parse", "--is-inside-work-tree"], check=False)
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise ValueError(f"Not a Git worktree: {repo}")


def rev_parse(repo: Path, ref: str) -> str:
    result = run_git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"], check=False)
    if result.returncode != 0:
        raise ValueError(f"Required Git base/candidate ref cannot be resolved: {ref}")
    return result.stdout.strip()


def head_sha(repo: Path) -> str:
    return rev_parse(repo, "HEAD")


def is_clean(repo: Path) -> bool:
    return not run_git(repo, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout.strip()


def read_file_at_ref(repo: Path, ref: str, relpath: str) -> bytes:
    rev_parse(repo, ref)
    result = run_git(repo, ["show", f"{ref}:{relpath}"], check=False)
    if result.returncode != 0:
        raise ValueError(f"Required immutable contract not found at {ref}:{relpath}")
    return result.stdout.encode("utf-8")


def _name_status(repo: Path, base_sha: str) -> list[tuple[str, str]]:
    """Parse `git diff --name-status` into (status, path) pairs. Renames/copies
    yield both a delete of the source and an add of the destination so no
    affected path — including the vacated one — escapes classification."""
    out = run_git(repo, ["diff", "--name-status", "-z", base_sha, "--"]).stdout
    tokens = out.split("\0")
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        status = tokens[i].strip()
        if not status:
            i += 1
            continue
        code = status[0]
        if code in {"R", "C"}:  # rename/copy: <status>\0<old>\0<new>
            old, new = tokens[i + 1], tokens[i + 2]
            if code == "R":
                pairs.append(("D", old))
            pairs.append(("A", new))
            i += 3
        else:
            pairs.append((code, tokens[i + 1]))
            i += 2
    return pairs


def changed_paths(repo: Path, base_ref: str) -> list[str]:
    """Every path the candidate touches, INCLUDING deletions — a deleted
    guardrail or test must still be classified and gated."""
    base_sha = rev_parse(repo, base_ref)
    tracked = [p for _s, p in _name_status(repo, base_sha)]
    untracked = run_git(repo, ["ls-files", "--others", "--exclude-standard"]).stdout.splitlines()
    return sorted({p.strip() for p in [*tracked, *untracked] if p.strip()})


def deleted_paths(repo: Path, base_ref: str) -> set[str]:
    """Paths removed by the candidate (absent from the candidate tree). The
    scope gate classifies these but skips filesystem-dependent checks on them."""
    base_sha = rev_parse(repo, base_ref)
    return {p for s, p in _name_status(repo, base_sha) if s == "D"}


def diff_numstat(repo: Path, base_ref: str) -> tuple[int, dict[str, int]]:
    base_sha = rev_parse(repo, base_ref)
    output = run_git(repo, ["diff", "--numstat", base_sha, "--"]).stdout
    total = 0
    by_path: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        count = 1 if added == "-" or deleted == "-" else int(added) + int(deleted)
        by_path[path] = count
        total += count
    for path in run_git(repo, ["ls-files", "--others", "--exclude-standard"]).stdout.splitlines():
        p = repo / path
        try:
            count = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            count = 1
        by_path[path] = count
        total += count
    return total, by_path


def diff_text(repo: Path, base_ref: str, max_bytes: int = 2_000_000) -> str:
    base_sha = rev_parse(repo, base_ref)
    result = run_git(repo, ["diff", "--no-ext-diff", "--unified=3", base_sha, "--"], check=False)
    text = result.stdout
    return text[:max_bytes]


def safe_extract_tar(data: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        root = destination.resolve()
        for member in archive.getmembers():
            target = (destination / member.name).resolve(strict=False)
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"Unsafe path in git archive: {member.name}") from exc
            if member.issym() or member.islnk():
                # Preserve repository symlinks only when their targets remain relative; scope gate separately rejects changed symlinks.
                if os.path.isabs(member.linkname) or ".." in Path(member.linkname).parts:
                    raise ValueError(f"Unsafe symlink in archive: {member.name} -> {member.linkname}")
        archive.extractall(destination)


def export_commit(repo: Path, commit: str, destination: Path) -> str:
    sha = rev_parse(repo, commit)
    proc = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", sha], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise ValueError(f"git archive failed: {proc.stderr.decode(errors='replace')}")
    safe_extract_tar(proc.stdout, destination)
    return sha
