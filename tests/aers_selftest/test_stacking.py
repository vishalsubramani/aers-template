"""Unit tests for stacked branching: dependency-candidate integration into the
fresh worktree, conflict fail-closed behavior, and merge determinism."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import loop


class FakeLedger:
    def __init__(self, candidates):
        self.candidates = candidates

    def task(self, feature_id, task_id):
        return {"candidate_sha": self.candidates.get(task_id)}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def make_repo(td):
    repo = Path(td) / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@invalid.local")
    (repo / "base.txt").write_text("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo, git(repo, "rev-parse", "HEAD")


def branch_commit(repo, base, name, filename, content):
    git(repo, "checkout", "-q", "-b", name, base)
    (repo / filename).write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", name)
    sha = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    return sha


class IntegrateDependenciesTests(unittest.TestCase):
    def test_disjoint_dependencies_merge_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = make_repo(td)
            c1 = branch_commit(repo, base, "cand-a", "a.txt", "a\n")
            c2 = branch_commit(repo, base, "cand-b", "b.txt", "b\n")
            ledger = FakeLedger({"T-001": c1, "T-002": c2})
            task = {"depends_on": ["T-002", "T-001"]}
            integrated = loop.integrate_dependencies(ledger, repo, "FEAT-X", task)
            self.assertEqual([d for d, _ in integrated], ["T-001", "T-002"])  # sorted, deterministic
            self.assertTrue((repo / "a.txt").exists() and (repo / "b.txt").exists())
            self.assertNotEqual(git(repo, "rev-parse", "HEAD"), base)

    def test_no_dependencies_leaves_head_at_contract(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = make_repo(td)
            self.assertEqual(loop.integrate_dependencies(FakeLedger({}), repo, "FEAT-X", {"depends_on": []}), [])
            self.assertEqual(git(repo, "rev-parse", "HEAD"), base)

    def test_conflicting_candidates_safe_stop_and_abort(self):
        with tempfile.TemporaryDirectory() as td:
            repo, base = make_repo(td)
            c1 = branch_commit(repo, base, "cand-a", "same.txt", "version a\n")
            c2 = branch_commit(repo, base, "cand-b", "same.txt", "version b\n")
            ledger = FakeLedger({"T-001": c1, "T-002": c2})
            with self.assertRaisesRegex(RuntimeError, "INTEGRATION_CONFLICT"):
                loop.integrate_dependencies(ledger, repo, "FEAT-X", {"depends_on": ["T-001", "T-002"]})
            status = git(repo, "status", "--porcelain")
            self.assertEqual(status, "", "merge must be aborted, worktree left clean")

    def test_ready_dependency_without_candidate_refused(self):
        with tempfile.TemporaryDirectory() as td:
            repo, _ = make_repo(td)
            with self.assertRaisesRegex(RuntimeError, "INTEGRATION_MISSING_CANDIDATE"):
                loop.integrate_dependencies(FakeLedger({"T-001": None}), repo, "FEAT-X", {"depends_on": ["T-001"]})


if __name__ == "__main__":
    unittest.main()
