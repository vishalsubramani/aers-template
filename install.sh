#!/usr/bin/env bash
# Install the AERS template into an existing repository.
#
# Usage: bash install.sh /path/to/your/repo
#
# Copies the control plane (.agents/, .specify/, .claude/, .github/, scripts/,
# evals/, docs, MISSION.md, AGENTS.md, adapters) plus the kit's self-tests
# (namespaced under tests/aers_selftest/) into the target. Never overwrites an
# existing file: collisions are reported for manual merge. The template's own
# root README.md and pyproject.toml are not copied; TUTORIAL.md covers usage.
set -euo pipefail

TARGET="${1:?usage: install.sh <existing-repo-dir>}"
SRC="$(cd "$(dirname "$0")" && pwd)"

[ -d "$TARGET" ] || { echo "error: $TARGET is not a directory" >&2; exit 1; }
TARGET="$(cd "$TARGET" && pwd)"
[ "$TARGET" != "$SRC" ] || { echo "error: target is the template itself" >&2; exit 1; }
case "$TARGET/" in "$SRC"/*) echo "error: target is inside the template" >&2; exit 1;; esac
case "$SRC/" in "$TARGET"/*) echo "error: template is inside the target" >&2; exit 1;; esac

installed=0
skipped=()
while IFS= read -r rel; do
  rel="${rel#./}"
  dest="$TARGET/$rel"
  if [ -e "$dest" ]; then
    skipped+=("$rel")
  else
    mkdir -p "$(dirname "$dest")"
    cp "$SRC/$rel" "$dest"
    installed=$((installed + 1))
  fi
done < <(
  cd "$SRC" && find . -type f \
    ! -path './.git/*' \
    ! -path './.aers-runtime/*' ! -path './.aers-evidence/*' ! -path './.aers-worktrees/*' \
    ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' \
    ! -path './install.sh' ! -path './README.md' ! -path './pyproject.toml'
)

echo "Installed $installed files into $TARGET"
echo "(Kit self-tests live under tests/aers_selftest/ so they stay separate from your suite.)"

if [ "${#skipped[@]}" -gt 0 ]; then
  echo
  echo "Skipped ${#skipped[@]} existing files (merge manually if you want the AERS version):"
  for f in "${skipped[@]}"; do echo "  $f"; done
fi

case " ${skipped[*]-} " in
  *' .gitignore '*)
    echo
    echo "Your .gitignore was kept. Append these AERS runtime entries:"
    echo "  .aers-runtime/"
    echo "  .aers-evidence/"
    echo "(Worktrees default to a sibling directory outside the repo; set AERS_WORKTREE_DIR to relocate.)"
    ;;
esac

case " ${skipped[*]-} " in
  *' Makefile '*)
    echo
    echo "Your Makefile was kept, but AERS agents and .github/workflows/aers-author.yml"
    echo "expect these targets — append them (bodies wired to your real tools):"
    echo "  bootstrap / check / test / security / evals / verify"
    echo "  aers-lint:  python3 scripts/aers.py lint"
    echo "See the template Makefile for reference stubs."
    ;;
esac

case " ${skipped[*]-} " in
  *' .claude/settings.json '*|*' .claude/hooks/'*)
    echo
    echo "WARNING: your existing .claude/settings.json (or hooks) was kept, so AERS"
    echo "hook enforcement (protected-path denies, PreToolUse guard, task gate) is NOT"
    echo "wired. Merge the hooks and deny entries from the template's"
    echo ".claude/settings.json into yours before autonomous runs."
    ;;
esac

if [ ! -d "$TARGET/.git" ]; then
  echo
  echo "note: $TARGET is not a git repository. Run 'git init' there first —"
  echo "AERS reads contracts at committed refs, so nothing works without git."
fi

cat <<'NEXT'

Next steps (inside your repository):
  1. Fill in MISSION.md with your repository's goal, then commit everything.
  2. python3 scripts/aers.py lint        # control-plane sanity
  3. Wire your real commands into the Makefile targets (check/test/security).
  4. Open your agent (e.g. `claude`) and run /kickoff — or follow the same
     procedure from agent_docs/kickoff.md with any agent, or TUTORIAL.md by hand.
NEXT
