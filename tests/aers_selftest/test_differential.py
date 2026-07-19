import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from aers.contracts import validate_tasks

FEATURE = {"schema_version": 1, "feature_id": "FEAT-X", "title": "x", "spec_mode": "S1", "risk_tier": "R1",
           "status": "approved", "base_ref": "HEAD",
           "acceptance_criteria": [{"id": "AC-001", "statement": "s", "evidence": "unit test"}],
           "contracts": [], "quality": {}, "rollout": {"strategy": "s", "rollback": "r"}}
TASKS = {"schema_version": 1, "feature_id": "FEAT-X", "tasks": [{
    "id": "T-001", "title": "t", "role": "test_author", "depends_on": [], "write_scope": ["tests/**"],
    "acceptance": ["AC-001"],
    "commands": [{"name": "c", "argv": ["true"], "timeout_seconds": 10, "network": "deny"}],
    "budget": {"max_attempts": 1, "max_files": 1, "max_lines": 10, "max_seconds": 60}}]}


class TestDifferentialContract(unittest.TestCase):
    def test_valid_differential_accepted(self):
        tasks = copy.deepcopy(TASKS)
        tasks["tasks"][0]["differential"] = {"argv_template": ["python3", "{file}"], "timeout_seconds": 30}
        validate_tasks(tasks, FEATURE)

    def test_differential_without_file_placeholder_rejected(self):
        tasks = copy.deepcopy(TASKS)
        tasks["tasks"][0]["differential"] = {"argv_template": ["python3", "run-all"]}
        with self.assertRaises(ValueError):
            validate_tasks(tasks, FEATURE)

    def test_differential_bad_timeout_rejected(self):
        tasks = copy.deepcopy(TASKS)
        tasks["tasks"][0]["differential"] = {"argv_template": ["python3", "{file}"], "timeout_seconds": 0}
        with self.assertRaises(ValueError):
            validate_tasks(tasks, FEATURE)


if __name__ == "__main__":
    unittest.main()
