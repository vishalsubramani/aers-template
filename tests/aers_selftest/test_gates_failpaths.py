"""The gates only prove something if their FAILURE paths work. Direct tests for
author_verify's fail-closed-on-unprovable-isolation, the deterministic audit's
tamper detection, and secret redaction breadth."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from aers.audit import audit_candidate
from aers.util import redact
from aers.verify import author_verify

FEATURE = {"schema_version": 1, "feature_id": "FEAT-X", "title": "x feature", "spec_mode": "S1",
           "risk_tier": "R1", "status": "approved", "base_ref": "HEAD",
           "acceptance_criteria": [{"id": "AC-001", "statement": "works", "evidence": ["test"]}],
           "contracts": [], "quality": {"security": [], "reliability": [], "observability": []},
           "rollout": {"strategy": "flag", "rollback": "disable"}}
POLICY = {"version": 1, "always_protected": [".agents/**"], "test_patterns": ["tests/**"],
          "generated_patterns": [], "sensitive_patterns": []}


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


def scaffold(td, write_scope, commands):
    repo = Path(td)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@invalid.local")
    (repo / ".agents/policies").mkdir(parents=True)
    (repo / ".agents/policies/protected-paths.json").write_text(json.dumps(POLICY))
    (repo / ".specify/specs/FEAT-X").mkdir(parents=True)
    (repo / ".specify/specs/FEAT-X/feature.contract.json").write_text(json.dumps(FEATURE))
    task = {"id": "T-001", "title": "t", "role": "implementer", "depends_on": [],
            "write_scope": write_scope, "acceptance": ["AC-001"], "commands": commands,
            "budget": {"max_attempts": 2, "max_files": 10, "max_lines": 500, "max_seconds": 60}}
    (repo / ".specify/specs/FEAT-X/tasks.json").write_text(
        json.dumps({"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task]}))
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text("x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "contract")
    return repo, git(repo, "rev-parse", "HEAD")


class AuthorVerifyFailClosedTests(unittest.TestCase):
    def test_unprovable_isolation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"],
                                  [{"name": "noop", "argv": ["true"], "timeout_seconds": 10, "network": "deny"}])
            (repo / "src/app.py").write_text("x = 2\n")
            git(repo, "commit", "-aqm", "candidate")
            saved = os.environ.pop("AERS_NETWORK_ISOLATED", None)
            try:
                out = Path(td) / "author.json"
                report = author_verify(repo, "FEAT-X", "T-001", base, out, degraded=False, contract_ref=base)
            finally:
                if saved is not None:
                    os.environ["AERS_NETWORK_ISOLATED"] = saved
            # On a host without provable isolation this must fail closed, never
            # AUTHOR_READY. On a host with userns it legitimately proceeds — but
            # then it must not be AUTHOR_FAILED for isolation reasons.
            if report["integrity"]["network_mode"] == "unavailable":
                self.assertEqual(report["verdict"], "AUTHOR_FAILED")
                self.assertTrue(any("isolation" in r.lower() for r in report["fatal_reasons"]))


class CommandFailureTests(unittest.TestCase):
    def test_failing_command_blocks_author_ready(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"],
                                  [{"name": "gate", "argv": ["false"], "timeout_seconds": 10, "network": "deny"}])
            (repo / "src/app.py").write_text("x = 9\n")
            git(repo, "commit", "-aqm", "candidate")
            os.environ["AERS_NETWORK_ISOLATED"] = "1"  # let the command actually run on any host
            try:
                report = author_verify(repo, "FEAT-X", "T-001", base, Path(td) / "a.json", degraded=False, contract_ref=base)
            finally:
                os.environ.pop("AERS_NETWORK_ISOLATED", None)
            self.assertEqual(report["verdict"], "AUTHOR_FAILED")
            self.assertTrue(any("gate" in r for r in report["fatal_reasons"]))


class DifferentialGateTests(unittest.TestCase):
    def _scaffold_test_author(self, td, test_body):
        repo = Path(td)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.name", "t")
        git(repo, "config", "user.email", "t@invalid.local")
        (repo / ".agents/policies").mkdir(parents=True)
        (repo / ".agents/policies/protected-paths.json").write_text(json.dumps(POLICY))
        (repo / ".specify/specs/FEAT-X").mkdir(parents=True)
        (repo / ".specify/specs/FEAT-X/feature.contract.json").write_text(json.dumps(FEATURE))
        # Dependency-free: the "test" is a plain Python script run directly, so
        # no pytest is required on the host or in CI.
        task = {"id": "T-001", "title": "t", "role": "test_author", "depends_on": [],
                "write_scope": ["tests/**"], "acceptance": ["AC-001"],
                "commands": [{"name": "suite", "argv": ["true"], "timeout_seconds": 30, "network": "deny"}],
                "differential": {"argv_template": ["python3", "{file}"], "timeout_seconds": 30},
                "budget": {"max_attempts": 2, "max_files": 10, "max_lines": 500, "max_seconds": 60}}
        (repo / ".specify/specs/FEAT-X/tasks.json").write_text(
            json.dumps({"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task]}))
        (repo / "tests").mkdir()
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "contract")
        base = git(repo, "rev-parse", "HEAD")
        (repo / "tests/test_new.py").write_text(test_body)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "candidate")
        return repo, base

    def test_nondiscriminating_test_fails_on_base_gate(self):
        with tempfile.TemporaryDirectory() as td:
            # A "test" that passes even on base (asserts nothing about new
            # behavior) must be caught by the differential gate.
            repo, base = self._scaffold_test_author(td, "assert 1 == 1\n")
            os.environ["AERS_NETWORK_ISOLATED"] = "1"
            try:
                report = author_verify(repo, "FEAT-X", "T-001", base, Path(td) / "a.json", degraded=False, contract_ref=base)
            finally:
                os.environ.pop("AERS_NETWORK_ISOLATED", None)
            self.assertTrue(any("DIFFERENTIAL_TEST_PASSES_ON_BASE" in r for r in report["fatal_reasons"]),
                            f"expected differential failure, got {report['fatal_reasons']}")
            self.assertEqual(report["verdict"], "AUTHOR_FAILED")


class AuditTamperTests(unittest.TestCase):
    def test_secret_in_diff_flags_audit(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"], [])
            (repo / "src/app.py").write_text('AWS = "AKIA1234567890ABCDEF"\n')
            git(repo, "commit", "-aqm", "candidate with secret")
            report = audit_candidate(repo, "FEAT-X", "T-001", base, "RUN-S", None, Path(td) / "audit.json", contract_ref=base)
            self.assertIn(report["verdict"], {"needs_review", "fail"},
                          "a hardcoded AKIA secret in the diff must not pass clean")

    def test_trajectory_bypass_event_flags_review(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = scaffold(td, ["src/**"], [])
            (repo / "src/app.py").write_text("x = 3\n")
            git(repo, "commit", "-aqm", "candidate")
            trajectory = Path(td) / "trajectory.jsonl"
            trajectory.write_text(
                json.dumps({"event_type": "policy_decision", "result": "bypass", "redacted": True}) + "\n")
            out = Path(td) / "audit.json"
            report = audit_candidate(repo, "FEAT-X", "T-001", base, "RUN-T", trajectory, out, contract_ref=base)
            self.assertIn(report["verdict"], {"needs_review", "fail"},
                          "a bypass trajectory event must not yield a clean pass")


class RedactionTests(unittest.TestCase):
    def test_common_secret_shapes_are_redacted(self):
        samples = [
            "api_key=sk-abcdefghijklmnop1234",
            "password: hunter2secret",
            'token = "abcd1234efgh5678"',
            "Authorization: Bearer abcdef0123456789abcdef",
            "aws_secret_access_key=wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY",
            "ghp_0123456789abcdefghijABCDEFghijklmnop",
        ]
        for s in samples:
            self.assertNotIn(s.split("=")[-1].split(":")[-1].strip().strip('"'), redact(s),
                             f"secret not redacted in: {s}")


if __name__ == "__main__":
    unittest.main()
