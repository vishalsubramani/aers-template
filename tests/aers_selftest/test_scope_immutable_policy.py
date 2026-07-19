"""Regression for the scope-gate escalation: (1) the classification policy is
read from the IMMUTABLE contract ref, not the mutable working tree, so a
candidate cannot weaken it and write a protected path in the same diff; (2)
contract validation refuses any write_scope that could reach the policy in the
first place. Both defenses are tested independently."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from aers.contracts import validate_feature, validate_tasks
from aers.scope import load_protected_policy

STRONG = {"version": 1, "always_protected": [".agents/**", ".claude/settings.json"],
          "test_patterns": ["tests/**"], "generated_patterns": [], "sensitive_patterns": []}
WEAK = {"version": 1, "always_protected": [], "test_patterns": [],
        "generated_patterns": [], "sensitive_patterns": []}

FEATURE = {"schema_version": 1, "feature_id": "FEAT-X", "title": "x feature", "spec_mode": "S1",
           "risk_tier": "R1", "status": "approved", "base_ref": "HEAD",
           "acceptance_criteria": [{"id": "AC-001", "statement": "works", "evidence": ["test"]}],
           "contracts": [], "quality": {"security": [], "reliability": [], "observability": []},
           "rollout": {"strategy": "flag", "rollback": "disable"}}


def task(write_scope):
    return {"id": "T-001", "title": "t", "role": "implementer", "depends_on": [],
            "write_scope": write_scope, "acceptance": ["AC-001"], "commands": [],
            "budget": {"max_attempts": 2, "max_files": 10, "max_lines": 500, "max_seconds": 60}}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class ImmutablePolicyReadTests(unittest.TestCase):
    def test_policy_read_from_ref_ignores_weakened_working_tree(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "user.name", "t")
            git(repo, "config", "user.email", "t@invalid.local")
            (repo / ".agents/policies").mkdir(parents=True)
            (repo / ".agents/policies/protected-paths.json").write_text(json.dumps(STRONG))
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "contract")
            contract = git(repo, "rev-parse", "HEAD")
            # Attacker weakens the working-tree policy after the contract commit.
            (repo / ".agents/policies/protected-paths.json").write_text(json.dumps(WEAK))
            policy = load_protected_policy(repo, contract)
            self.assertEqual(policy["always_protected"], STRONG["always_protected"],
                             "gate must classify using the committed policy, not the weakened working tree")


class WriteScopeGuardTests(unittest.TestCase):
    def test_blanket_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, "blanket"):
            validate_tasks({"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task(["**"])]}, FEATURE)

    def test_policy_reaching_scope_rejected(self):
        for scope in ([".agents/**"], [".agents/policies/**"], [".claude/hooks/**"]):
            with self.assertRaisesRegex(ValueError, "guardrail-defining surface"):
                validate_tasks({"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task(scope)]}, FEATURE)

    def test_ordinary_scope_accepted(self):
        validate_feature(FEATURE)
        validate_tasks({"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task(["src/**"])]}, FEATURE)


if __name__ == "__main__":
    unittest.main()
