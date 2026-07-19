"""Unit tests for the outer runner's scheduling: dependency gating, attempt
budgets, and terminal-state exclusion."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import run_ready
from aers.ledger import Ledger

FEATURE = {"schema_version": 1, "feature_id": "FEAT-X", "title": "valid title", "spec_mode": "S1",
           "risk_tier": "R1", "status": "approved", "base_ref": "abc",
           "acceptance_criteria": [{"id": "AC-001", "statement": "works", "evidence": ["test"]}],
           "contracts": [], "quality": {"security": [], "reliability": [], "observability": []},
           "rollout": {"strategy": "flag", "rollback": "disable"}}


def tasks_doc(max_attempts=2):
    def task(task_id, deps):
        return {"id": task_id, "title": "task", "role": "implementer", "depends_on": deps,
                "write_scope": ["src/**"], "acceptance": ["AC-001"], "commands": [],
                "budget": {"max_attempts": max_attempts, "max_files": 5, "max_lines": 100, "max_seconds": 60}}
    return {"schema_version": 1, "feature_id": "FEAT-X", "tasks": [task("T-001", []), task("T-002", ["T-001"])]}


def walk_to_author_ready(ledger, task_id):
    run = ledger.start_run("FEAT-X", task_id, "test")
    for state in ("implementing", "scope_passed", "candidate_committed", "author_verifying", "auditing", "reviewing", "author_ready"):
        ledger.transition("FEAT-X", task_id, state, run)
    return run


class ReadyTasksTests(unittest.TestCase):
    def ledger(self, max_attempts=2):
        self.tmp = tempfile.TemporaryDirectory()
        ledger = Ledger(Path(self.tmp.name) / "ledger.db")
        ledger.register(FEATURE, tasks_doc(max_attempts), "a" * 40)
        return ledger

    def ready_ids(self, ledger):
        return [t["task_id"] for t in run_ready.ready_tasks(ledger, "FEAT-X")]

    def test_dependent_task_blocked_until_dependency_ready(self):
        ledger = self.ledger()
        self.assertEqual(self.ready_ids(ledger), ["T-001"])
        walk_to_author_ready(ledger, "T-001")
        self.assertEqual(self.ready_ids(ledger), ["T-002"])

    def test_attempt_budget_excludes_task(self):
        ledger = self.ledger(max_attempts=1)
        run = ledger.start_run("FEAT-X", "T-001", "test")
        ledger.transition("FEAT-X", "T-001", "implementing", run)
        ledger.transition("FEAT-X", "T-001", "failed", run)
        self.assertEqual(self.ready_ids(ledger), [])  # 1 attempt used, budget 1

    def test_safe_stopped_task_never_rescheduled(self):
        ledger = self.ledger()
        run = ledger.start_run("FEAT-X", "T-001", "test")
        ledger.transition("FEAT-X", "T-001", "implementing", run)
        ledger.transition("FEAT-X", "T-001", "failed", run)
        ledger.transition("FEAT-X", "T-001", "safe_stopped", run)
        self.assertEqual(self.ready_ids(ledger), [])


if __name__ == "__main__":
    unittest.main()
