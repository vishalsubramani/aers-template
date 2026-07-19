"""Installation must be non-destructive and idempotent; migration planning must
never write to the target."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import migrate

REPO = Path(__file__).resolve().parents[2]


class MigrateTests(unittest.TestCase):
    def test_plan_is_non_destructive_and_lists_additions(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "empty"
            target.mkdir()
            plan = migrate.plan(REPO, target)
            self.assertFalse(plan["destructive"])
            self.assertGreater(plan["add_count"], 20)
            self.assertEqual(plan["skip_count"], 0)
            # Planning must not have created anything in the target.
            self.assertEqual(list(target.iterdir()), [])

    def test_recommend_profile_for_empty_repo(self):
        with tempfile.TemporaryDirectory() as td:
            rec = migrate.recommend_profile(Path(td))
            self.assertEqual(rec["detected_level"], "none")

    def test_install_is_idempotent(self):
        install = REPO / "install.sh"
        if not install.exists():
            self.skipTest("install.sh not present")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "repo"
            target.mkdir()
            subprocess.run(["git", "init", "-q", str(target)], check=True)
            first = subprocess.run(["bash", str(install), str(target)], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertIn("Installed", first.stdout)
            # Second run must add zero files (every file already present).
            second = subprocess.run(["bash", str(install), str(target)], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(second.returncode, 0, second.stdout)
            self.assertIn("Installed 0 files", second.stdout)
            # After install, the plan should have nothing left to add.
            plan = migrate.plan(REPO, target)
            self.assertEqual(plan["add_count"], 0, plan["would_add"][:10])


if __name__ == "__main__":
    unittest.main()
