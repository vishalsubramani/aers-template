#!/usr/bin/env python3
"""Fail-closed decision-log gate (author-side, additive).

Humans reviewing AI-generated code review the control plane, not every line. The
decision log (`agent_docs/decision-log.md`) is the reviewable record of the
decision points, assumptions, and trade-offs an agent made while producing a
change — vendor-neutral (Claude, Codex, Gemini, a human) and committed with the
work so the PR diff shows exactly the decisions added.

This gate runs at `make check` / CI time and refuses to pass unless:
  * every approved feature at a required risk tier carries
    `.specify/specs/<FEAT>/decision-log.jsonl` with at least one valid entry;
  * every decision-log line in the repository (feature packs and
    `docs/decisions/`) is schema-valid, with unique ids, no duplicate JSON keys,
    and no entry that lists neither an option nor an assumption;
  * entries whose doctrine_basis is "cited" carry doctrine refs, and
    "deviation-adr" entries name the accepted ADR;
  * risky entries — reversibility "one-way", confidence "low", or any assumption
    with needs_human_validation=true — have been validated or countered BY A
    HUMAN (human_status set, validated_by present and not the configured agent
    author id), and countered entries carry a follow_up; any non-pending entry is
    held to the same validated_by rule so a "validated" veneer cannot be
    self-applied;
  * the log is append-only: no entry present at the branch baseline may be
    deleted, and only human-review fields may change on an existing entry.

Hardening against self-relaxation: the policy (assurance/reviews/config.json) and
each contract's gated status are read from the committed BASELINE (merge-base with
the default branch), not the working tree, so a PR cannot un-gate itself by
editing config or downgrading a risk tier in the same change. See _baseline.py.

Standard library only. Exit 0 = pass; exit 1 = fail closed.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _baseline  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

REQUIRED_FIELDS = (
    "schema_version", "id", "feature_id", "task_id", "date", "agent",
    "decision_point", "context", "options", "selected", "trade_offs",
    "assumptions", "doctrine_basis", "doctrine_refs", "adr_ref",
    "reversibility", "confidence", "human_status", "validated_by", "follow_up",
)
AGENT_FIELDS = ("vendor", "model", "role")
DOCTRINE_BASES = {"cited", "none-applies", "deviation-adr"}
REVERSIBILITY = {"cheap", "costly", "one-way"}
CONFIDENCE = {"high", "medium", "low"}
HUMAN_STATUS = {"pending", "validated", "countered"}
DOCTRINE_PREFIXES = ("AX-", "DD-", "PAT-", "DF-")
CONFIG_REL = "assurance/reviews/config.json"
# Fields a human may change when validating/countering an existing entry; every
# other field is immutable once written (append-only content).
HUMAN_MUTABLE = {"human_status", "validated_by", "follow_up"}

DEFAULT_CONFIG = {"author_id": "primary-implementer", "required_risk_tiers": ["R2"], "exclude_features": []}


def _no_duplicate_keys(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key '{k}'")
        seen[k] = v
    return seen


def load_config(repo: Path) -> tuple[dict, list[str]]:
    """Return (config, notes). Prefer the baseline-committed config so a PR cannot
    relax its own gate; fall back to the working tree only when no baseline exists,
    and say so."""
    notes: list[str] = []
    default = dict(DEFAULT_CONFIG)
    baseline_raw = _baseline.read_baseline_file(repo, CONFIG_REL)
    worktree_path = repo / CONFIG_REL
    worktree_raw = worktree_path.read_text() if worktree_path.exists() else None
    if baseline_raw is not None:
        default.update(json.loads(baseline_raw))
        if worktree_raw is not None and worktree_raw != baseline_raw:
            notes.append("note: assurance/reviews/config.json differs from baseline; "
                         "the gate uses the BASELINE policy (a policy change takes effect "
                         "only after it is reviewed and merged).")
    elif worktree_raw is not None:
        default.update(json.loads(worktree_raw))
        if _baseline.is_git_repo(repo):
            notes.append("note: no baseline ref resolved (shallow checkout?); gate read "
                         "config from the working tree — fetch the base branch for full "
                         "self-relaxation protection.")
    return default, notes


def _contract_gated(contract: dict, cfg: dict) -> bool:
    return (contract.get("status") == "approved"
            and contract.get("risk_tier") in cfg["required_risk_tiers"])


def feature_is_gated(repo: Path, fid: str, worktree_contract: dict, cfg: dict) -> bool:
    """Gated if the working tree OR the baseline marks it gated — so downgrading a
    real feature's risk tier or flipping status within the PR cannot drop it."""
    if fid in cfg.get("exclude_features", []):
        return False
    if _contract_gated(worktree_contract, cfg):
        return True
    baseline_raw = _baseline.read_baseline_file(repo, f".specify/specs/{fid}/feature.contract.json")
    if baseline_raw:
        try:
            if _contract_gated(json.loads(baseline_raw), cfg):
                return True
        except json.JSONDecodeError:
            pass
    return False


def validate_entry(entry: dict, where: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return [f"{where}: entry is not a JSON object"]
    for key in REQUIRED_FIELDS:
        if key not in entry:
            errors.append(f"{where}: missing required field '{key}'")
    if errors:
        return errors

    if entry["schema_version"] != 1:
        errors.append(f"{where}: unsupported schema_version {entry['schema_version']!r}")
    if not isinstance(entry["id"], str) or not entry["id"].startswith("DEC-"):
        errors.append(f"{where}: id must be a string starting with 'DEC-'")
    agent = entry["agent"]
    if not isinstance(agent, dict) or any(not agent.get(k) for k in AGENT_FIELDS):
        errors.append(f"{where}: agent must carry non-empty {AGENT_FIELDS}")
    for text_field in ("decision_point", "context", "selected", "trade_offs"):
        if not isinstance(entry[text_field], str) or not entry[text_field].strip():
            errors.append(f"{where}: '{text_field}' must be a non-empty string")
    options, assumptions = entry["options"], entry["assumptions"]
    if not isinstance(options, list) or any(
        not isinstance(o, dict) or not o.get("option") or not o.get("rejected_because")
        for o in options
    ):
        errors.append(f"{where}: options must be a list of {{option, rejected_because}}")
    if not isinstance(assumptions, list) or any(
        not isinstance(a, dict) or not a.get("assumption")
        or not isinstance(a.get("needs_human_validation"), bool)
        for a in assumptions
    ):
        errors.append(f"{where}: assumptions must be a list of {{assumption, needs_human_validation:bool}}")
    # A decision that names neither a rejected option nor an assumption is not a
    # decision point — it is an unfalsifiable assertion. The docs allow an empty
    # options list ONLY for pure assumptions; enforce that pairing.
    if isinstance(options, list) and isinstance(assumptions, list) and not options and not assumptions:
        errors.append(f"{where}: entry lists neither an option nor an assumption — "
                      f"an empty options list is only legitimate for a pure assumption")

    if entry["doctrine_basis"] not in DOCTRINE_BASES:
        errors.append(f"{where}: doctrine_basis must be one of {sorted(DOCTRINE_BASES)}")
    elif entry["doctrine_basis"] == "cited":
        refs = entry["doctrine_refs"]
        if not isinstance(refs, list) or not refs:
            errors.append(f"{where}: doctrine_basis 'cited' requires non-empty doctrine_refs")
        elif any(not isinstance(r, str) or not r.startswith(DOCTRINE_PREFIXES) for r in refs):
            errors.append(f"{where}: doctrine_refs must be AX-/DD-/PAT-/DF- ids")
    elif entry["doctrine_basis"] == "deviation-adr" and not entry["adr_ref"]:
        errors.append(f"{where}: doctrine_basis 'deviation-adr' requires adr_ref naming the accepted ADR")

    for field, allowed in (("reversibility", REVERSIBILITY), ("confidence", CONFIDENCE),
                           ("human_status", HUMAN_STATUS)):
        if entry[field] not in allowed:
            errors.append(f"{where}: {field} must be one of {sorted(allowed)}")
    return errors


def requires_human(entry: dict) -> bool:
    return (
        entry.get("reversibility") == "one-way"
        or entry.get("confidence") == "low"
        or any(a.get("needs_human_validation") for a in entry.get("assumptions", [])
               if isinstance(a, dict))
    )


def validate_human_rule(entry: dict, where: str, author_id: str) -> list[str]:
    """Enforce human validation for risky entries, and hold ANY non-pending entry
    to the validated_by rule so a 'validated' label cannot be self-applied."""
    errors: list[str] = []
    status = entry.get("human_status")
    if requires_human(entry) and status not in {"validated", "countered"}:
        errors.append(
            f"{where}: entry '{entry.get('id')}' is one-way/low-confidence/needs-validation "
            f"but human_status is '{status}' — a human must validate or counter it"
        )
        return errors
    if status in {"validated", "countered"}:
        validated_by = entry.get("validated_by")
        if not validated_by:
            errors.append(f"{where}: entry '{entry.get('id')}' human_status '{status}' without validated_by")
        elif validated_by == author_id:
            errors.append(
                f"{where}: entry '{entry.get('id')}' validated_by equals agent author id "
                f"'{author_id}' — self-validation does not count"
            )
        if status == "countered" and not entry.get("follow_up"):
            errors.append(
                f"{where}: entry '{entry.get('id')}' is countered without a follow_up — "
                f"countering without consequence is theater"
            )
    return errors


def _parse_entries(text: str, rel: str) -> tuple[list[dict], list[str]]:
    entries, errors = [], []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{rel}:{lineno}"
        try:
            entry = json.loads(line, object_pairs_hook=_no_duplicate_keys)
        except ValueError as e:
            errors.append(f"{where}: invalid JSON ({e})")
            continue
        entries.append((where, entry))
    return entries, errors


def validate_log(path: Path, repo: Path, author_id: str, enforce_human: bool = True) -> tuple[int, list[str]]:
    """Validate one decision-log file. Returns (entry_count, errors).

    enforce_human applies the mandatory human-validation rule for risky entries.
    It is True for gated features (red CI until a human validates is the point)
    and False for non-gated logs (docs/decisions/, non-approved features), whose
    human review happens through the PR template checklist instead.
    """
    rel = path.relative_to(repo).as_posix()
    parsed, errors = _parse_entries(path.read_text(), rel)
    seen_ids: set[str] = set()
    for where, entry in parsed:
        errors.extend(validate_entry(entry, where))
        if not isinstance(entry, dict):
            continue  # validate_entry already flagged it; nothing more to check
        eid = entry.get("id")
        if isinstance(eid, str):
            if eid in seen_ids:
                errors.append(f"{where}: duplicate id '{eid}'")
            seen_ids.add(eid)
        if enforce_human:
            errors.extend(validate_human_rule(entry, where, author_id))
    errors.extend(check_append_only(path, repo, rel))
    return len(parsed), errors


def check_append_only(path: Path, repo: Path, rel: str) -> list[str]:
    """No baseline entry may be deleted, and only human-review fields may change on
    an existing entry. Degrades to no-op when there is no baseline (new log)."""
    baseline_raw = _baseline.read_baseline_file(repo, rel)
    if baseline_raw is None:
        return []
    base_entries, _ = _parse_entries(baseline_raw, f"{rel}@baseline")
    base_by_id = {e["id"]: e for _, e in base_entries if isinstance(e, dict) and isinstance(e.get("id"), str)}
    cur_entries, _ = _parse_entries(path.read_text(), rel)
    cur_by_id = {e["id"]: e for _, e in cur_entries if isinstance(e, dict) and isinstance(e.get("id"), str)}
    errors: list[str] = []
    for eid, base_entry in base_by_id.items():
        if eid not in cur_by_id:
            errors.append(f"{rel}: entry '{eid}' present at baseline was deleted — the log is append-only")
            continue
        cur_entry = cur_by_id[eid]
        base_immutable = {k: v for k, v in base_entry.items() if k not in HUMAN_MUTABLE}
        cur_immutable = {k: v for k, v in cur_entry.items() if k not in HUMAN_MUTABLE}
        if base_immutable != cur_immutable:
            errors.append(f"{rel}: entry '{eid}' was rewritten — only human-review fields "
                          f"(human_status, validated_by, follow_up) may change on an existing entry")
    return errors


def _summarize(path: Path, repo: Path) -> str:
    """Machine-computed salience line so the PR template's self-reported counts are
    checkable, not testimony."""
    parsed, _ = _parse_entries(path.read_text(), path.relative_to(repo).as_posix())
    risky = [e["id"] for _, e in parsed if isinstance(e, dict) and requires_human(e)
             and e.get("human_status") not in {"validated", "countered"}]
    return (f"    {path.relative_to(repo).as_posix()}: {len(parsed)} entries, "
            f"{len(risky)} needing human validation"
            + (f" ({', '.join(risky)})" if risky else ""))


def main(repo: Path = REPO) -> int:
    cfg, notes = load_config(repo)
    for n in notes:
        print(n)
    author_id = cfg["author_id"]
    all_errors: list[str] = []
    summaries: list[str] = []
    gated = 0

    if not cfg.get("required_risk_tiers"):
        # An empty tier list would silently gate nothing — refuse it outright.
        print("DECISION-LOG GATE: FAIL (fail-closed)")
        print("  - required_risk_tiers is empty; the gate would enforce nothing. "
              "Set it in assurance/reviews/config.json (baseline-committed).")
        return 1

    # 1) Presence + validity for gated features.
    for contract_path in sorted(glob.glob(str(repo / ".specify" / "specs" / "*" / "feature.contract.json"))):
        feature_dir = Path(contract_path).parent
        fid = feature_dir.name
        contract = json.loads(Path(contract_path).read_text())
        if fid in cfg.get("exclude_features", []):
            print(f"  (excluded from gate: {fid} — non-product scaffolding per config.json)")
            continue
        if not feature_is_gated(repo, fid, contract, cfg):
            continue
        gated += 1
        log_path = feature_dir / "decision-log.jsonl"
        if not log_path.exists():
            all_errors.append(f"{fid}: MISSING decision log ({log_path.relative_to(repo)}) — "
                              f"see agent_docs/decision-log.md")
            continue
        count, errors = validate_log(log_path, repo, author_id)
        if count == 0:
            all_errors.append(f"{fid}: decision log exists but has no entries")
        all_errors.extend(errors)
        summaries.append(_summarize(log_path, repo))

    # 2) Validity for every other decision log in the repo (feature packs not gated
    #    above, and docs/decisions/): if it exists, it must be valid.
    validated_paths = set()
    for pattern in (".specify/specs/*/decision-log.jsonl", "docs/decisions/*.jsonl"):
        for raw in sorted(glob.glob(str(repo / pattern))):
            path = Path(raw)
            if path in validated_paths:
                continue
            validated_paths.add(path)
            fid = path.parent.name if "specs" in path.parts else None
            if fid and fid in cfg.get("exclude_features", []):
                continue
            if fid and (path.parent / "feature.contract.json").exists():
                contract = json.loads((path.parent / "feature.contract.json").read_text())
                if feature_is_gated(repo, fid, contract, cfg):
                    continue  # already validated in pass 1
            _, errors = validate_log(path, repo, author_id, enforce_human=False)
            all_errors.extend(errors)

    if all_errors:
        print("DECISION-LOG GATE: FAIL (fail-closed)")
        for e in all_errors:
            print(f"  - {e}")
        print(f"\nRequired risk tiers: {cfg['required_risk_tiers']}; agent author id: {author_id}")
        print("Format and review protocol: agent_docs/decision-log.md")
        return 1

    if summaries:
        print("Decision-log salience (compare against the PR template's self-reported counts):")
        for s in summaries:
            print(s)
    print(f"DECISION-LOG GATE: PASS — {gated} gated feature(s) carry a valid decision log; "
          f"{len(validated_paths)} log file(s) schema-checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
