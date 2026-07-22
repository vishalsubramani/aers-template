"""The decision-log gate only proves something if its FAILURE paths work: missing
logs on gated features, schema-invalid entries, and unvalidated risky decisions
must all fail closed; valid logs must pass."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "checks"))

import decision_log_gate as gate

ENTRY = {
    "schema_version": 1, "id": "DEC-FEAT-X-001", "feature_id": "FEAT-X", "task_id": "T-001",
    "date": "2026-07-22", "agent": {"vendor": "anthropic", "model": "claude-code", "role": "implementer"},
    "decision_point": "Retry policy", "context": "Contract silent on retry limits.",
    "options": [{"option": "unbounded retry", "rejected_because": "retry storm risk"}],
    "selected": "3 attempts with jittered backoff", "trade_offs": "Added worst-case latency.",
    "assumptions": [{"assumption": "endpoint is idempotent", "needs_human_validation": False}],
    "doctrine_basis": "cited", "doctrine_refs": ["PAT-05"], "adr_ref": None,
    "reversibility": "cheap", "confidence": "high",
    "human_status": "pending", "validated_by": None, "follow_up": None,
}

CONTRACT = {"schema_version": 1, "feature_id": "FEAT-X", "status": "approved", "risk_tier": "R2"}
CONFIG = {"author_id": "primary-implementer", "required_risk_tiers": ["R2"], "exclude_features": []}


def entry(**overrides):
    e = json.loads(json.dumps(ENTRY))
    e.update(overrides)
    return e


def scaffold(td, entries, contract=CONTRACT, config=CONFIG, write_log=True):
    repo = Path(td)
    feature = repo / ".specify" / "specs" / "FEAT-X"
    feature.mkdir(parents=True)
    (feature / "feature.contract.json").write_text(json.dumps(contract))
    if write_log:
        (feature / "decision-log.jsonl").write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n")
    reviews = repo / "assurance" / "reviews"
    reviews.mkdir(parents=True)
    (reviews / "config.json").write_text(json.dumps(config))
    return repo


def git(repo, *a):
    import subprocess
    return subprocess.run(["git", "-C", str(repo), *a], check=True,
                          capture_output=True, text=True).stdout.strip()


def scaffold_git(td, entries, contract=CONTRACT, config=CONFIG):
    """A committed baseline on 'main' plus a working-tree state, so baseline-read
    and append-only checks can be exercised."""
    repo = scaffold(td, entries, contract=contract, config=config)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@invalid.local")
    git(repo, "config", "user.name", "t")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "baseline")
    return repo


class ValidateEntryTests(unittest.TestCase):
    def test_valid_entry_passes(self):
        self.assertEqual(gate.validate_entry(entry(), "x"), [])

    def test_missing_field_fails(self):
        e = entry()
        del e["trade_offs"]
        self.assertTrue(any("trade_offs" in err for err in gate.validate_entry(e, "x")))

    def test_cited_requires_refs(self):
        e = entry(doctrine_refs=[])
        self.assertTrue(any("non-empty doctrine_refs" in err for err in gate.validate_entry(e, "x")))

    def test_bad_ref_prefix_fails(self):
        e = entry(doctrine_refs=["OWASP-1"])
        self.assertTrue(any("AX-/DD-/PAT-/DF-" in err for err in gate.validate_entry(e, "x")))

    def test_deviation_requires_adr(self):
        e = entry(doctrine_basis="deviation-adr", adr_ref=None)
        self.assertTrue(any("adr_ref" in err for err in gate.validate_entry(e, "x")))

    def test_bad_enum_fails(self):
        e = entry(reversibility="maybe")
        self.assertTrue(any("reversibility" in err for err in gate.validate_entry(e, "x")))


class HumanRuleTests(unittest.TestCase):
    def test_one_way_pending_fails(self):
        e = entry(reversibility="one-way")
        errs = gate.validate_human_rule(e, "x", "primary-implementer")
        self.assertTrue(any("must validate or counter" in err for err in errs))

    def test_low_confidence_pending_fails(self):
        e = entry(confidence="low")
        self.assertTrue(gate.validate_human_rule(e, "x", "primary-implementer"))

    def test_flagged_assumption_pending_fails(self):
        e = entry(assumptions=[{"assumption": "a", "needs_human_validation": True}])
        self.assertTrue(gate.validate_human_rule(e, "x", "primary-implementer"))

    def test_self_validation_rejected(self):
        e = entry(reversibility="one-way", human_status="validated",
                  validated_by="primary-implementer")
        errs = gate.validate_human_rule(e, "x", "primary-implementer")
        self.assertTrue(any("self-validation" in err for err in errs))

    def test_counter_without_follow_up_fails(self):
        e = entry(reversibility="one-way", human_status="countered",
                  validated_by="a-human", follow_up=None)
        errs = gate.validate_human_rule(e, "x", "primary-implementer")
        self.assertTrue(any("follow_up" in err for err in errs))

    def test_human_validated_one_way_passes(self):
        e = entry(reversibility="one-way", human_status="validated", validated_by="a-human")
        self.assertEqual(gate.validate_human_rule(e, "x", "primary-implementer"), [])

    def test_cheap_high_confidence_pending_is_fine(self):
        self.assertEqual(gate.validate_human_rule(entry(), "x", "primary-implementer"), [])


class GateEndToEndTests(unittest.TestCase):
    def test_missing_log_on_gated_feature_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [], write_log=False)
            self.assertEqual(gate.main(repo), 1)

    def test_empty_log_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [])
            (repo / ".specify/specs/FEAT-X/decision-log.jsonl").write_text("")
            self.assertEqual(gate.main(repo), 1)

    def test_valid_log_passes(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry()])
            self.assertEqual(gate.main(repo), 0)

    def test_duplicate_ids_fail(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry(), entry()])
            self.assertEqual(gate.main(repo), 1)

    def test_invalid_json_line_fails(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry()])
            log = repo / ".specify/specs/FEAT-X/decision-log.jsonl"
            log.write_text(log.read_text() + "not json\n")
            self.assertEqual(gate.main(repo), 1)

    def test_unvalidated_risky_entry_fails_on_gated_feature(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry(reversibility="one-way")])
            self.assertEqual(gate.main(repo), 1)

    def test_excluded_feature_skips_but_logs(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(CONFIG, exclude_features=["FEAT-X"])
            repo = scaffold(td, [], config=cfg, write_log=False)
            self.assertEqual(gate.main(repo), 0)

    def test_below_tier_feature_not_gated_but_log_schema_checked(self):
        with tempfile.TemporaryDirectory() as td:
            contract = dict(CONTRACT, risk_tier="R1")
            bad = entry()
            del bad["confidence"]
            repo = scaffold(td, [bad], contract=contract)
            self.assertEqual(gate.main(repo), 1)

    def test_docs_decisions_schema_checked_without_human_rule(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry()])
            decisions = repo / "docs" / "decisions"
            decisions.mkdir(parents=True)
            # Risky-but-pending is allowed outside gated features; broken schema is not.
            ok = entry(id="DEC-DOC-001", feature_id=None, task_id=None, reversibility="one-way")
            (decisions / "log.jsonl").write_text(json.dumps(ok) + "\n")
            self.assertEqual(gate.main(repo), 0)
            bad = entry(id="DEC-DOC-002", doctrine_basis="vibes")
            (decisions / "log.jsonl").write_text(json.dumps(bad) + "\n")
            self.assertEqual(gate.main(repo), 1)


class HardeningTests(unittest.TestCase):
    """Regression tests for the red-team findings: each asserts a demonstrated
    bypass is now blocked."""

    def test_empty_required_tiers_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(CONFIG, required_risk_tiers=[])
            repo = scaffold(td, [entry()], config=cfg)
            self.assertEqual(gate.main(repo), 1)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry()])
            log = repo / ".specify/specs/FEAT-X/decision-log.jsonl"
            # A trailing 'reversibility":"cheap' would win last-wins parsing and hide
            # a one-way decision; duplicate keys must be rejected outright.
            log.write_text('{"reversibility": "one-way", "reversibility": "cheap"}\n')
            self.assertEqual(gate.main(repo), 1)

    def test_non_dict_line_is_handled(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold(td, [entry()])
            log = repo / ".specify/specs/FEAT-X/decision-log.jsonl"
            log.write_text("[1, 2, 3]\n")
            self.assertEqual(gate.main(repo), 1)

    def test_empty_options_and_assumptions_fails(self):
        e = entry(options=[], assumptions=[])
        self.assertTrue(any("neither an option nor an assumption" in err
                            for err in gate.validate_entry(e, "x")))

    def test_empty_options_with_assumption_is_allowed(self):
        e = entry(options=[], assumptions=[{"assumption": "spec is silent", "needs_human_validation": False}])
        self.assertEqual(gate.validate_entry(e, "x"), [])

    def test_validated_veneer_on_non_risky_entry_rejected(self):
        # Cheap/high-confidence entry cannot wear a "validated" label with no human.
        e = entry(human_status="validated", validated_by=None)
        self.assertTrue(gate.validate_human_rule(e, "x", "primary-implementer"))
        e2 = entry(human_status="validated", validated_by="primary-implementer")
        self.assertTrue(any("self-validation" in err
                            for err in gate.validate_human_rule(e2, "x", "primary-implementer")))

    def test_baseline_config_defeats_self_ungating(self):
        # Baseline gates R2; the PR rewrites config to exclude the feature. The gate
        # must use the baseline policy and still demand the (missing) log.
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold_git(td, [entry()])
            # Attacker removes the log and self-excludes in the working tree.
            (repo / ".specify/specs/FEAT-X/decision-log.jsonl").unlink()
            (repo / "assurance/reviews/config.json").write_text(
                json.dumps(dict(CONFIG, exclude_features=["FEAT-X"])))
            self.assertEqual(gate.main(repo), 1)

    def test_baseline_contract_defeats_tier_downgrade(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold_git(td, [entry()])
            (repo / ".specify/specs/FEAT-X/decision-log.jsonl").unlink()
            # Downgrade R2 -> R1 in the working tree to dodge gating.
            (repo / ".specify/specs/FEAT-X/feature.contract.json").write_text(
                json.dumps(dict(CONTRACT, risk_tier="R1")))
            self.assertEqual(gate.main(repo), 1)

    def test_append_only_deletion_detected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold_git(td, [entry(id="DEC-FEAT-X-001"), entry(id="DEC-FEAT-X-002")])
            # Working tree drops the second entry.
            (repo / ".specify/specs/FEAT-X/decision-log.jsonl").write_text(
                json.dumps(entry(id="DEC-FEAT-X-001")) + "\n")
            self.assertEqual(gate.main(repo), 1)

    def test_append_only_rewrite_detected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold_git(td, [entry(id="DEC-FEAT-X-001", selected="original choice")])
            (repo / ".specify/specs/FEAT-X/decision-log.jsonl").write_text(
                json.dumps(entry(id="DEC-FEAT-X-001", selected="rewritten choice")) + "\n")
            self.assertEqual(gate.main(repo), 1)

    def test_append_only_human_fields_may_change(self):
        with tempfile.TemporaryDirectory() as td:
            repo = scaffold_git(td, [entry(id="DEC-FEAT-X-001", reversibility="one-way")])
            # A human validating an existing entry is legitimate, not a rewrite.
            (repo / ".specify/specs/FEAT-X/decision-log.jsonl").write_text(
                json.dumps(entry(id="DEC-FEAT-X-001", reversibility="one-way",
                                 human_status="validated", validated_by="a-human")) + "\n")
            self.assertEqual(gate.main(repo), 0)


if __name__ == "__main__":
    unittest.main()
