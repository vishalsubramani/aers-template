"""Unit tests for loop.py's security-relevant validators: typed argv parsing and
identity-bound reviewer/auditor report validation."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import loop


class CommandEnvTests(unittest.TestCase):
    def test_missing_env_rejected(self):
        os.environ.pop("AERS_TEST_CMD", None)
        with self.assertRaisesRegex(ValueError, "JSON array"):
            loop.parse_command_env("AERS_TEST_CMD")

    def test_shell_string_rejected(self):
        os.environ["AERS_TEST_CMD"] = '"rm -rf /tmp/x && echo done"'
        with self.assertRaisesRegex(ValueError, "string array"):
            loop.parse_command_env("AERS_TEST_CMD")

    def test_invalid_json_rejected(self):
        os.environ["AERS_TEST_CMD"] = "not json"
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            loop.parse_command_env("AERS_TEST_CMD")

    def test_empty_and_nonstring_tokens_rejected(self):
        for bad in ("[]", '["ok", ""]', '["ok", 3]'):
            os.environ["AERS_TEST_CMD"] = bad
            with self.assertRaises(ValueError):
                loop.parse_command_env("AERS_TEST_CMD")

    def test_valid_argv_accepted_and_rendered(self):
        os.environ["AERS_TEST_CMD"] = '["python3", "x.py", "--prompt-file", "{prompt_file}"]'
        argv = loop.parse_command_env("AERS_TEST_CMD")
        rendered = loop.render_argv(argv, {"prompt_file": "/tmp/p.md"})
        self.assertEqual(rendered, ["python3", "x.py", "--prompt-file", "/tmp/p.md"])


class ReviewerReportTests(unittest.TestCase):
    def report(self, **overrides):
        base = {"schema_version": 1, "feature_id": "FEAT-X", "task_id": "T-001",
                "candidate_sha": "c" * 40, "verdict": "pass", "findings": [],
                "acceptance_reviewed": ["AC-001"]}
        base.update(overrides)
        return base

    def write(self, tmp, report):
        path = Path(tmp) / "reviewer-report.json"
        path.write_text(json.dumps(report))
        return path

    def test_valid_report_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, self.report())
            value = loop.validate_reviewer(path, "FEAT-X", "T-001", "c" * 40, ["AC-001"])
            self.assertEqual(value["verdict"], "pass")

    def test_wrong_candidate_sha_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, self.report(candidate_sha="d" * 40))
            with self.assertRaisesRegex(ValueError, "identity"):
                loop.validate_reviewer(path, "FEAT-X", "T-001", "c" * 40, ["AC-001"])

    def test_unreviewed_acceptance_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, self.report())
            with self.assertRaisesRegex(ValueError, "acceptance"):
                loop.validate_reviewer(path, "FEAT-X", "T-001", "c" * 40, ["AC-001", "AC-002"])

    def test_missing_report_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "did not create"):
                loop.validate_reviewer(Path(tmp) / "absent.json", "FEAT-X", "T-001", "c" * 40, [])

    def test_llm_audit_bad_verdict_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = {"schema_version": 1, "feature_id": "FEAT-X", "task_id": "T-001",
                      "candidate_sha": "c" * 40, "verdict": "looks_good", "findings": []}
            path = Path(tmp) / "llm-audit-report.json"
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "verdict"):
                loop.validate_llm_audit(path, "FEAT-X", "T-001", "c" * 40)


if __name__ == "__main__":
    unittest.main()
