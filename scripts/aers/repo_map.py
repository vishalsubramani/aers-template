"""Generate the repository navigation map used in context packets."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .git import head_sha, run_git
from .util import atomic_write_text, utc_now


def generate(repo: Path, output: Path) -> dict:
    sha = head_sha(repo)
    files = [x for x in run_git(repo, ["ls-tree", "-r", "--name-only", sha]).stdout.splitlines() if x]
    top = Counter(p.split("/", 1)[0] for p in files)
    extensions = Counter(Path(p).suffix or "[none]" for p in files)
    lines = ["# Generated Repository Map", "", f"Generated: {utc_now()}", f"Commit: `{sha}`", "", "## Top-level surfaces"]
    lines += [f"- `{name}`: {count} tracked files" for name,count in sorted(top.items())]
    lines += ["", "## Dominant file types"]
    lines += [f"- `{ext}`: {count}" for ext,count in extensions.most_common(20)]
    lines += ["", "## Tracked paths"]
    lines += [f"- `{p}`" for p in files[:1000]]
    if len(files)>1000: lines.append(f"- … {len(files)-1000} additional paths omitted")
    atomic_write_text(output, "\n".join(lines)+"\n")
    return {"commit":sha,"files":len(files),"output":str(output)}
