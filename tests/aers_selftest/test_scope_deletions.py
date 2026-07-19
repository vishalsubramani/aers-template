"""The scope gate must see DELETIONS: deleting a protected guardrail, a test
(as an implementer), or an out-of-scope file must fail the gate. Also covers the
symlink-escape check, which had no test."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from aers.scope import evaluate_scope

FEATURE = {"schema_version": 1, "feature_id": "FEAT-X", "title": "x feature", "spec_mode": "S1",
           "risk_tier": "R1", "status": "approved", "base_ref": "HEAD",
           "acceptance_criteria": [{"id": "AC-001", "statement": "works", "evidence": ["test"]}],
           "contracts": [], "quality": {"security": [], "reliability": [], "observability": []},
           "rollout": {"strategy": "flag", "rollback": "disable"}}
POLICY = {"version": 1, "always_protected": [".agents/**", "CODEOWNERS"],
          "test_patterns": ["tests/**"], "generated_patterns": [], "sensitive_patterns": []}


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


def scaffold(td, write_scope):
    repo = Path(td)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@invalid.local")
    (repo / ".agents/policies").mkdir(parents=True)
    (repo / ".agents/policies/protected-paths.json").write_text(json.dumps(POLICY))
    (repo / ".specify/specs/FEAT-X").mkdir(parents=True)
    (repo / ".specify/specs/FEAT-X/feature.contract.json").write_text(json.dumps(FEATURE))
    task = {"id": "T-001", "title": "t", "role": "implementer", "depends_on": [],
            "write_scope": write_scope, "acceptance": ["AC-001"], "commands": [],
            "budget": {"max_attempts": 2, "max_files": 20, "max_lines": 500, "max_seconds": 60}}
    (repo / ".specify/specs/FEAT-X/tasks.json").write_text(
        json.dumps({"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task]}))
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text("x = 1\n")
    (repo / "tests").mkdir()
    (repo / "tests/test_app.py").write_text("def test_x():\n    assert True\n")
    (repo / "CODEOWNERS").write_text("* @team\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "contract")
    return repo, git(repo, "rev-parse", "HEAD")


class DeletionScopeTests(unittest.TestCase):
    def evaluate(self, repo, base):
        return evaluate_scope(repo, "FEAT-X", "T-001", base, contract_ref=base)

    def test_deleting_protected_guardrail_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**", "CODEOWNERS"])
            (repo / "CODEOWNERS").unlink()
            git(repo, "commit", "-aqm", "delete guardrail")
            report = self.evaluate(repo, base)
            self.assertIn("PROTECTED_PATH", {f["code"] for f in report.findings})
            self.assertFalse(report.passed)

    def test_implementer_deleting_a_test_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**", "tests/**"])
            (repo / "tests/test_app.py").unlink()
            git(repo, "commit", "-aqm", "delete the test that catches my bug")
            report = self.evaluate(repo, base)
            self.assertIn("IMPLEMENTER_EDITED_TEST", {f["code"] for f in report.findings})
            self.assertFalse(report.passed)

    def test_deleting_out_of_scope_file_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"])
            (repo / "CODEOWNERS").unlink()
            git(repo, "commit", "-aqm", "delete out of scope")
            report = self.evaluate(repo, base)
            codes = {f["code"] for f in report.findings}
            self.assertTrue({"OUTSIDE_WRITE_SCOPE", "PROTECTED_PATH"} & codes)
            self.assertFalse(report.passed)

    def test_in_scope_deletion_is_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"])
            (repo / "src/extra.py").write_text("y = 2\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "add")
            base2 = git(repo, "rev-parse", "HEAD")
            (repo / "src/extra.py").unlink()
            git(repo, "commit", "-aqm", "delete in-scope file")
            # Re-register base for the new commit chain is unnecessary; evaluate against base2.
            report = evaluate_scope(repo, "FEAT-X", "T-001", base2, contract_ref=base)
            self.assertNotIn("OUTSIDE_WRITE_SCOPE", {f["code"] for f in report.findings})


class BudgetAndRoleTests(unittest.TestCase):
    def test_line_budget_exceeded_fails(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"])
            # tiny budget, then a large change
            tp = repo / ".specify/specs/FEAT-X/tasks.json"
            doc = json.loads(tp.read_text())
            doc["tasks"][0]["budget"]["max_lines"] = 3
            tp.write_text(json.dumps(doc))
            git(repo, "commit", "-aqm", "tighten budget")
            base2 = git(repo, "rev-parse", "HEAD")
            (repo / "src/big.py").write_text("\n".join(f"x{i} = {i}" for i in range(50)) + "\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "big change")
            report = evaluate_scope(repo, "FEAT-X", "T-001", base2, contract_ref=base2)
            self.assertIn("DIFF_LINE_BUDGET", {f["code"] for f in report.findings})
            self.assertFalse(report.passed)

    def test_read_only_role_write_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"])
            tp = repo / ".specify/specs/FEAT-X/tasks.json"
            doc = json.loads(tp.read_text())
            doc["tasks"][0]["role"] = "reviewer"
            tp.write_text(json.dumps(doc))
            git(repo, "commit", "-aqm", "reviewer role")
            base2 = git(repo, "rev-parse", "HEAD")
            (repo / "src/app.py").write_text("x = 99\n")
            git(repo, "commit", "-aqm", "reviewer wrote code")
            report = evaluate_scope(repo, "FEAT-X", "T-001", base2, contract_ref=base2)
            self.assertIn("READ_ONLY_ROLE_WROTE", {f["code"] for f in report.findings})
            self.assertFalse(report.passed)


class SymlinkEscapeTests(unittest.TestCase):
    def test_symlink_escaping_repo_is_flagged(self):
        with tempfile.TemporaryDirectory() as outer:
            with tempfile.TemporaryDirectory() as td:
                repo, base = scaffold(td, ["src/**"])
                link = repo / "src" / "escape"
                os.symlink(outer, link)  # points outside the repo
                git(repo, "add", "-A")
                git(repo, "commit", "-qm", "symlink")
                report = evaluate_scope(repo, "FEAT-X", "T-001", base, contract_ref=base)
                self.assertIn("SYMLINK_PATH", {f["code"] for f in report.findings})
                self.assertFalse(report.passed)


if __name__ == "__main__":
    unittest.main()
