"""Unit tests for the pre-tool hook guard: dangerous commands, protected-path
writes (Write tools and best-effort Bash screening), and interactive mode."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from aers.hooks import _bash_write_targets, pre_tool_guard

POLICY = {
    "version": 1,
    "always_protected": ["MISSION.md", "AGENTS.md", ".agents/**", "scripts/aers/**"],
    "test_patterns": ["tests/**"],
    "generated_patterns": [],
    "sensitive_patterns": [],
}


@contextlib.contextmanager
def fixture_repo():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "aers.toml").write_text("version = 1\n")
        (repo / ".agents/policies").mkdir(parents=True)
        (repo / ".agents/policies/protected-paths.json").write_text(json.dumps(POLICY))
        previous_cwd = os.getcwd()
        saved = {k: os.environ.pop(k, None) for k in ("AERS_FEATURE_ID", "AERS_TASK_ID", "AERS_BASE_SHA")}
        os.chdir(repo)
        try:
            yield repo
        finally:
            os.chdir(previous_cwd)
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value


def guard(payload):
    with contextlib.redirect_stdout(io.StringIO()):
        return pre_tool_guard(payload)


class BashWriteTargetTests(unittest.TestCase):
    def test_redirects_and_tee_and_rm_detected(self):
        self.assertIn("MISSION.md", _bash_write_targets("echo hacked > MISSION.md"))
        self.assertIn("AGENTS.md", _bash_write_targets("cat x | tee AGENTS.md"))
        self.assertIn("MISSION.md", _bash_write_targets("rm -f MISSION.md"))
        self.assertIn("state.json", _bash_write_targets("python3 gen.py >> state.json"))

    def test_reads_and_heredoc_markers_ignored(self):
        self.assertEqual(_bash_write_targets("cat MISSION.md"), [])
        self.assertEqual(_bash_write_targets("grep -rn pattern scripts/"), [])


class PreToolGuardTests(unittest.TestCase):
    def test_dangerous_command_denied(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Bash", "tool_input": {"command": "git push origin main --force"}}), 2)

    def test_bash_redirect_to_protected_denied(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Bash", "tool_input": {"command": "echo pwned > MISSION.md"}}), 2)

    def test_bash_redirect_to_ordinary_path_allowed(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Bash", "tool_input": {"command": "echo ok > notes.txt"}}), 0)

    def test_interactive_write_to_protected_denied(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Write", "tool_input": {"file_path": "MISSION.md"}}), 2)
            self.assertEqual(guard({"tool_name": "Write", "tool_input": {"file_path": ".agents/doctrine/x.md"}}), 2)

    def test_interactive_write_to_ordinary_path_allowed(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Write", "tool_input": {"file_path": "src/app.py"}}), 0)

    def test_write_escaping_repository_denied(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Write", "tool_input": {"file_path": "../outside.txt"}}), 2)

    def test_write_without_path_denied(self):
        with fixture_repo():
            self.assertEqual(guard({"tool_name": "Write", "tool_input": {}}), 2)


if __name__ == "__main__":
    unittest.main()
