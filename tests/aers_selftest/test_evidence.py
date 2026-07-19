"""Evidence manifest: bound to the exact candidate, generated from a clean
export, and never green on a dirty tree or a partial required control."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import evidence
from aers.git import head_sha, is_clean

REPO = Path(__file__).resolve().parents[2]


@unittest.skipUnless((REPO / ".git").exists(),
                     "evidence manifest needs a git worktree; skipped in a hermetic clean export")
class EvidenceTests(unittest.TestCase):
    def test_manifest_binds_candidate_and_runs_from_clean_export(self):
        manifest = evidence.build_manifest(REPO, profile="standard")
        self.assertEqual(manifest["candidate_sha"], head_sha(REPO))  # exact-candidate binding
        self.assertIn("export", manifest["generated_from"])
        self.assertEqual(set(manifest["gates"]), {
            "assessment", "adversarial_benchmark", "assurance_case", "threat_model", "evaluator_health"})
        self.assertFalse(manifest["verified"])  # never asserts VERIFIED
        # If the worktree is dirty, the manifest must not be green.
        if not is_clean(REPO):
            self.assertFalse(manifest["author_side_all_green"])
            self.assertTrue(any("DIRTY" in r for r in manifest["not_green_reasons"]))

    def test_partial_required_control_is_not_green(self):
        # High Assurance has externally-dependent required controls that are
        # PARTIAL from inside the repo; the manifest must report NOT green.
        manifest = evidence.build_manifest(REPO, profile="high-assurance")
        self.assertNotEqual(manifest["gates"]["assessment"]["overall"], "PASS")
        self.assertFalse(manifest["gates"]["assessment"]["green"])
        self.assertFalse(manifest["author_side_all_green"])


if __name__ == "__main__":
    unittest.main()
