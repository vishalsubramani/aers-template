#!/usr/bin/env python3
"""Fail-closed independent-review evidence gate (author-side, additive).

Closes the hole this rebuild exposed: AERS's per-task enforcement lives inside
`scripts/loop.py`, so work implemented by hand (bypassing the loop) can reach a
green PR with no independent review. This gate runs at `make check` / CI time and
refuses to pass unless every approved feature carries a candidate-bound,
INDEPENDENT reviewer report — regardless of how the work was produced.

For each approved feature in `.specify/specs/*/feature.contract.json` whose risk
tier is in the required set, it requires `assurance/reviews/<FEAT>.review.json`
that:
  * is schema-shaped (required keys present, verdict in the enum),
  * binds `candidate_sha` to a REAL commit that touches the feature's write scope,
  * has `verdict == "pass"` with no unresolved high/critical findings,
  * reviewed every acceptance criterion in the contract,
  * was produced by a reviewer whose `reviewer_id` is NOT the author id
    (independence — a self-review does not count).

Standard library only. Exit 0 = pass; exit 1 = fail closed.
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPECS = REPO / ".specify" / "specs"
REVIEWS = REPO / "assurance" / "reviews"
CONFIG = REVIEWS / "config.json"

VALID_VERDICTS = {"pass", "fail", "needs_review"}
BLOCKING = {"high", "critical"}


def load_config() -> dict:
    default = {"author_id": "primary-implementer", "required_risk_tiers": ["R2"], "exclude_features": []}
    if CONFIG.exists():
        default.update(json.loads(CONFIG.read_text()))
    return default


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, check=False,
    ).stdout.strip()


def commit_exists(sha: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "-e", f"{sha}^{{commit}}"],
        capture_output=True, check=False,
    ).returncode == 0


def commit_paths(sha: str) -> list[str]:
    out = git("show", "--name-only", "--pretty=format:", sha)
    return [p for p in out.splitlines() if p.strip()]


def write_scopes(feature_dir: Path) -> list[str]:
    tasks = json.loads((feature_dir / "tasks.json").read_text())
    scopes: list[str] = []
    for t in tasks.get("tasks", []):
        scopes.extend(t.get("write_scope", []))
    return scopes


def scope_prefixes(scopes: list[str]) -> list[str]:
    # Turn glob write-scopes into simple path prefixes for a touch check.
    prefixes = []
    for s in scopes:
        prefixes.append(s.split("*", 1)[0].rstrip("/"))
    return [p for p in prefixes if p]


def check_feature(feature_dir: Path, cfg: dict) -> list[str]:
    fid = feature_dir.name
    errors: list[str] = []
    if fid in cfg.get("exclude_features", []):
        print(f"  (excluded from gate: {fid} — non-product scaffolding per config.json)")
        return []
    contract = json.loads((feature_dir / "feature.contract.json").read_text())
    if contract.get("status") != "approved":
        return []  # only approved features are gated
    if contract.get("risk_tier") not in cfg["required_risk_tiers"]:
        return []  # tier not required to have an independent review

    review_path = REVIEWS / f"{fid}.review.json"
    if not review_path.exists():
        return [f"{fid}: MISSING independent review artifact ({review_path.relative_to(REPO)})"]

    try:
        r = json.loads(review_path.read_text())
    except json.JSONDecodeError as e:
        return [f"{fid}: review artifact is not valid JSON ({e})"]

    for key in ("schema_version", "feature_id", "candidate_sha", "verdict",
                "findings", "acceptance_reviewed", "reviewer_id"):
        if key not in r:
            errors.append(f"{fid}: review missing required key '{key}'")
    if errors:
        return errors

    if r["feature_id"] != fid:
        errors.append(f"{fid}: review feature_id '{r['feature_id']}' does not match")
    if r["verdict"] not in VALID_VERDICTS:
        errors.append(f"{fid}: invalid verdict '{r['verdict']}'")
    if r["verdict"] != "pass":
        errors.append(f"{fid}: verdict is '{r['verdict']}', not pass")

    # Independence: the reviewer must not be the author.
    if r["reviewer_id"] == cfg["author_id"]:
        errors.append(f"{fid}: reviewer_id equals author id '{cfg['author_id']}' — self-review does not count")

    # Candidate binding: sha must be a real commit that touches the write scope.
    sha = str(r["candidate_sha"])
    if not commit_exists(sha):
        errors.append(f"{fid}: candidate_sha {sha} is not a commit in history")
    else:
        touched = commit_paths(sha)
        prefixes = scope_prefixes(write_scopes(feature_dir))
        if prefixes and not any(p.startswith(tuple(prefixes)) for p in touched):
            errors.append(f"{fid}: candidate {sha} touches no path in the feature write scope")

    # No unresolved blocking findings.
    for f in r.get("findings", []):
        if f.get("severity") in BLOCKING and not f.get("resolved"):
            errors.append(f"{fid}: unresolved {f['severity']} finding — {f.get('message','')[:80]}")

    # Coverage: every acceptance criterion reviewed.
    contract_acs = {ac["id"] for ac in contract.get("acceptance_criteria", [])}
    reviewed = set(r.get("acceptance_reviewed", []))
    missing = contract_acs - reviewed
    if missing:
        errors.append(f"{fid}: acceptance criteria not reviewed: {sorted(missing)}")

    return errors


def main() -> int:
    cfg = load_config()
    feature_dirs = sorted(
        Path(p).parent for p in glob.glob(str(SPECS / "*" / "feature.contract.json"))
    )
    all_errors: list[str] = []
    gated = 0
    for fd in feature_dirs:
        contract = json.loads((fd / "feature.contract.json").read_text())
        if (fd.name not in cfg.get("exclude_features", [])
                and contract.get("status") == "approved"
                and contract.get("risk_tier") in cfg["required_risk_tiers"]):
            gated += 1
        all_errors.extend(check_feature(fd, cfg))

    if all_errors:
        print("INDEPENDENT-REVIEW GATE: FAIL (fail-closed)")
        for e in all_errors:
            print(f"  - {e}")
        print(f"\nRequired risk tiers: {cfg['required_risk_tiers']}; author id: {cfg['author_id']}")
        return 1

    print(f"INDEPENDENT-REVIEW GATE: PASS — {gated} gated feature(s) carry a candidate-bound independent review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
