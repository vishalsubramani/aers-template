#!/usr/bin/env bash
# Create a self-contained demo repository: AERS kit + tiny todo app + an
# approved feature pack, ready for the tutorial walkthrough.
# Usage: bash examples/setup-demo.sh /path/to/new/demo-dir
set -euo pipefail
TARGET="${1:?usage: setup-demo.sh <target-dir>}"
KIT="$(cd "$(dirname "$0")/.." && pwd)"
[ -e "$TARGET" ] && { echo "refusing: $TARGET already exists" >&2; exit 1; }
mkdir -p "$TARGET"
# Kit files — copy only the known control-plane surfaces, never the whole host
# tree (which could include an adopter's unrelated, lint-breaking files).
KIT_PATHS=(.agents .specify .claude .github agent_docs docs evals scripts tests examples \
           AGENTS.md CLAUDE.md GEMINI.md README.md TUTORIAL.md CONTRIBUTING.md MISSION.md \
           SECURITY.md CODEOWNERS Makefile aers.toml pyproject.toml .gitignore install.sh)
present=()
for p in "${KIT_PATHS[@]}"; do [ -e "$KIT/$p" ] && present+=("$p"); done
( cd "$KIT" && tar -cf - "${present[@]}" ) | ( cd "$TARGET" && tar -xf - )
# Demo application
( cd "$KIT/examples/demo-src" && tar -cf - . ) | ( cd "$TARGET" && tar -xf - )
# Approved feature pack
mkdir -p "$TARGET/.specify/specs/FEAT-001"
cp "$KIT"/examples/feature-pack/FEAT-001/* "$TARGET/.specify/specs/FEAT-001/"
# A filled mission (the task runners refuse the template placeholder)
cat > "$TARGET/MISSION.md" <<'MISSION'
# Mission

## What this repository builds
A deliberately tiny in-memory todo list library used to demonstrate the AERS
pipeline end to end: typed feature packs, the scope gate, hermetic author
verification with a differential test gate, deterministic audit, and review.

## Definition of done for v1
- Todos can be added, listed, and completed (existing behavior stays green).
- FEAT-001 adds per-todo priorities via a test-first task pair.

## Constraints
- Standard-library Python only; no network; no new dependencies.

## Non-goals
- Persistence, concurrency, or any user interface.
MISSION
cd "$TARGET"
git init -q .
git config user.name "demo" >/dev/null; git config user.email "demo@invalid.local" >/dev/null
git add -A
git commit -qm "base: AERS kit + todo demo + approved FEAT-001"
python3 scripts/aers.py lint >/dev/null
python3 scripts/aers.py ledger-init >/dev/null
python3 scripts/aers.py register --feature FEAT-001 >/dev/null
BASE="$(git rev-parse HEAD)"
cat <<DONE
Demo ready at: $TARGET   (base commit $BASE)
Next (offline pipeline test with stubs — same flow as README/TUTORIAL Part 2):
  cd $TARGET
  export AERS_AGENT_CMD_JSON='["python3","scripts/adapters/stub_agent.py","--prompt-file","{prompt_file}"]'
  export AERS_REVIEWER_CMD_JSON='["python3","scripts/adapters/stub_reviewer.py","--output","{output}","--candidate","{candidate_sha}"]'
  export AERS_STUB_PATCH_DIR="\$PWD/examples/patches"
  python3 scripts/run_ready.py --feature FEAT-001 --max-runs 4
If your host lacks Linux user namespaces (e.g. macOS), also:
  export AERS_NETWORK_ISOLATED=1
  # an operator assertion that the outer environment denies egress; the
  # offline stub demo makes no network calls, so it is safe here.
Or with a real agent: see TUTORIAL.md sections 3-4.
DONE
