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
    `docs/decisions/`) is schema-valid with unique ids;
  * entries whose doctrine_basis is "cited" carry doctrine refs, and
    "deviation-adr" entries name the accepted ADR;
  * risky entries — reversibility "one-way", confidence "low", or any
    assumption with needs_human_validation=true — have been validated or
    countered BY A HUMAN (human_status set, validated_by present and not the
    configured agent author id), and countered entries carry a follow_up.

Shares config with the independent-review gate (assurance/reviews/config.json:
required_risk_tiers, exclude_features, author_id). Standard library only.
Exit 0 = pass; exit 1 = fail closed.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

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


def load_config(repo: Path) -> dict:
    default = {"author_id": "primary-implementer", "required_risk_tiers": ["R2"], "exclude_features": []}
    cfg_path = repo / "assurance" / "reviews" / "config.json"
    if cfg_path.exists():
        default.update(json.loads(cfg_path.read_text()))
    return default


def validate_entry(entry: dict, where: str) -> list[str]:
    errors: list[str] = []
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
    if not isinstance(entry["options"], list) or any(
        not isinstance(o, dict) or not o.get("option") or not o.get("rejected_because")
        for o in entry["options"]
    ):
        errors.append(f"{where}: options must be a list of {{option, rejected_because}}")
    if not isinstance(entry["assumptions"], list) or any(
        not isinstance(a, dict) or not a.get("assumption")
        or not isinstance(a.get("needs_human_validation"), bool)
        for a in entry["assumptions"]
    ):
        errors.append(f"{where}: assumptions must be a list of {{assumption, needs_human_validation:bool}}")

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
    errors: list[str] = []
    if not requires_human(entry):
        return errors
    if entry.get("human_status") not in {"validated", "countered"}:
        errors.append(
            f"{where}: entry '{entry.get('id')}' is one-way/low-confidence/needs-validation "
            f"but human_status is '{entry.get('human_status')}' — a human must validate or counter it"
        )
        return errors
    validated_by = entry.get("validated_by")
    if not validated_by:
        errors.append(f"{where}: entry '{entry.get('id')}' human_status set without validated_by")
    elif validated_by == author_id:
        errors.append(
            f"{where}: entry '{entry.get('id')}' validated_by equals agent author id "
            f"'{author_id}' — self-validation does not count"
        )
    if entry.get("human_status") == "countered" and not entry.get("follow_up"):
        errors.append(
            f"{where}: entry '{entry.get('id')}' is countered without a follow_up — "
            f"countering without consequence is theater"
        )
    return errors


def validate_log(path: Path, repo: Path, author_id: str, enforce_human: bool = True) -> tuple[int, list[str]]:
    """Validate one decision-log file. Returns (entry_count, errors).

    enforce_human applies the mandatory human-validation rule for risky entries.
    It is True for gated features (red CI until a human validates is the point)
    and False for non-gated logs (docs/decisions/, non-approved features), whose
    human review happens through the PR template checklist instead.
    """
    rel = path.relative_to(repo)
    errors: list[str] = []
    seen_ids: set[str] = set()
    count = 0
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{rel}:{lineno}"
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{where}: invalid JSON ({e})")
            continue
        count += 1
        errors.extend(validate_entry(entry, where))
        eid = entry.get("id")
        if isinstance(eid, str):
            if eid in seen_ids:
                errors.append(f"{where}: duplicate id '{eid}'")
            seen_ids.add(eid)
        if enforce_human:
            errors.extend(validate_human_rule(entry, where, author_id))
    return count, errors


def main(repo: Path = REPO) -> int:
    cfg = load_config(repo)
    author_id = cfg["author_id"]
    all_errors: list[str] = []
    gated = 0

    # 1) Presence for gated features.
    for contract_path in sorted(glob.glob(str(repo / ".specify" / "specs" / "*" / "feature.contract.json"))):
        feature_dir = Path(contract_path).parent
        fid = feature_dir.name
        contract = json.loads(Path(contract_path).read_text())
        if fid in cfg.get("exclude_features", []):
            print(f"  (excluded from gate: {fid} — non-product scaffolding per config.json)")
            continue
        if contract.get("status") != "approved":
            continue
        if contract.get("risk_tier") not in cfg["required_risk_tiers"]:
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
            gated_dir = (fid is not None
                         and (path.parent / "feature.contract.json").exists()
                         and json.loads((path.parent / "feature.contract.json").read_text()).get("status") == "approved"
                         and json.loads((path.parent / "feature.contract.json").read_text()).get("risk_tier") in cfg["required_risk_tiers"])
            if gated_dir:
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

    print(f"DECISION-LOG GATE: PASS — {gated} gated feature(s) carry a valid decision log; "
          f"{len(validated_paths)} log file(s) schema-checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
