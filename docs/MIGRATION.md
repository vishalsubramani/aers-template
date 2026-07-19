# Migrating an existing repository to AERS

Installation is **non-destructive** and **idempotent**: `install.sh` never
overwrites an existing file, and running it twice adds zero files the second time
(proven by `tests/aers_selftest/test_migrate_idempotency.py`).

## 1. Plan first (dry run — writes nothing)

```
python3 scripts/assure.py migrate --assess /path/to/your/repo --json
```

You get:

- `would_add` / `would_skip` — exactly which files the install would add vs keep.
- `conflicts` — existing control-plane files (`.claude/settings.json`, hooks,
  `Makefile`, `.gitignore`, `aers.toml`) that would be kept, so AERS enforcement
  is **not** active until you merge them.
- `profile_recommendation` — the lowest profile your repo already satisfies and
  the next step to climb (see `docs/ADOPTION.md`).
- `backup_guidance` — back up with `git stash` or a commit before merging any
  kept control-plane files.

## 2. Install

```
bash install.sh /path/to/your/repo
```

It reports installed vs skipped files and prints follow-up notes for any kept
control-plane files (hooks, Makefile, `.gitignore`).

## 3. Activate enforcement

Merge the kept control-plane files flagged as `conflicts` (most importantly
`.claude/settings.json` and `.claude/hooks/`), fill `MISSION.md`, and wire the
`Makefile` targets to your real tools.

## 4. Verify and assess

```
python3 scripts/aers.py lint
python3 scripts/assure.py assess --profile lite
```

## Backup / rollback

The install only ever adds files, so rollback is `git checkout -- .` plus
removing the newly added AERS directories, or `git revert` of the install commit.
No existing file is modified in place.

## Uninstall

Remove the added control-plane directories (`.agents/`, `.specify/`, `.claude/`,
`scripts/aers/`, `scripts/aers_assure/`, `assurance/`, AERS `.github/workflows/`)
and the AERS `Makefile` targets. Your application code and tests are untouched.
