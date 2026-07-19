"""assess must detect deliberately missing controls; assurance must detect a
deliberately broken claim mapping. Both are tested through their failure paths."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import assess, assurance, profiles

REPO = Path(__file__).resolve().parents[2]


class ProfileTests(unittest.TestCase):
    def test_all_profiles_load_and_are_ordered(self):
        loaded = profiles.load_all_profiles(REPO)
        self.assertEqual(set(loaded), set(profiles.PROFILE_IDS))
        req = {pid: sum(1 for v in p["controls"].values() if v == "REQUIRED") for pid, p in loaded.items()}
        self.assertLess(req["lite"], req["standard"])
        self.assertLess(req["standard"], req["high-assurance"])
        self.assertLessEqual(req["high-assurance"], req["regulated"])


class AssessTests(unittest.TestCase):
    def test_real_repo_passes_lite_required(self):
        report = assess.assess(REPO, "lite")
        failing = [r for r in report["results"] if r["requirement"] == "REQUIRED" and r["status"] == "FAIL"]
        self.assertEqual(failing, [], failing)

    def test_detects_deliberately_missing_control(self):
        # Copy the assurance metadata into a temp repo that OMITS the Makefile;
        # the stable-commands control must be detected as FAIL, not assumed.
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td)
            shutil.copytree(REPO / "assurance", fake / "assurance")
            (fake / "aers.toml").write_text("version = 1\n", encoding="utf-8")
            # no Makefile, no scripts/aers -> required controls fail
            report = assess.assess(fake, "lite")
            codes = {r["control_id"]: r["status"] for r in report["results"]}
            self.assertEqual(codes["CTRL-STABLE-COMMANDS"], "FAIL")
            self.assertEqual(codes["CTRL-SCOPE-ENFORCEMENT"], "FAIL")
            self.assertEqual(report["overall"], "FAIL")

    def test_external_dependent_controls_are_never_pass_from_repo(self):
        report = assess.assess(REPO, "high-assurance")
        by_id = {r["control_id"]: r for r in report["results"]}
        # An external verifier deployment cannot be PASS from inside the repo.
        self.assertEqual(by_id["CTRL-EXTERNAL-VERIFIER"]["status"], "PARTIAL")


class AssuranceTests(unittest.TestCase):
    def test_real_assurance_case_has_no_broken_or_unsupported_claims(self):
        report = assurance.run_assurance(REPO)
        self.assertEqual(report["broken"], 0, [r for r in report["results"] if r["status"] == "BROKEN"])
        self.assertEqual(report["unsupported"], 0)

    def test_detects_broken_claim_mapping(self):
        case = json.loads((REPO / assurance.CASE_PATH).read_text())
        case["claims"].append({
            "id": "CLAIM-BROKEN", "text": "deliberately broken",
            "enforcing_control": "CTRL-ATTESTATION",
            "implementation": ["scripts/aers_assure/does_not_exist.py"],
            "tests": ["tests/aers_selftest/nope.py::test_nope"],
            "benchmark_cases": ["BENCH-NOPE"], "evidence_digest": "x",
            "residual_limitations": "",
        })
        with tempfile.TemporaryDirectory() as td:
            tampered = Path(td) / "case.json"
            tampered.write_text(json.dumps(case), encoding="utf-8")
            report = assurance.run_assurance(REPO, tampered)
            self.assertFalse(report["passed"])
            broken = [r for r in report["results"] if r["claim_id"] == "CLAIM-BROKEN"]
            self.assertEqual(broken[0]["status"], "BROKEN")
            self.assertTrue(broken[0]["broken_refs"])

    def test_detects_stale_claim_after_edit(self):
        case = json.loads((REPO / assurance.CASE_PATH).read_text())
        # Point a claim at a real file but with a wrong pinned digest -> STALE.
        case["claims"] = [{
            "id": "CLAIM-STALE", "text": "stale mapping",
            "enforcing_control": "CTRL-ATTESTATION",
            "implementation": ["scripts/aers_assure/verifier.py"],
            "tests": ["tests/aers_selftest/test_verifier.py"],
            "benchmark_cases": [], "evidence_digest": "0000wrong",
            "residual_limitations": "",
        }]
        with tempfile.TemporaryDirectory() as td:
            tampered = Path(td) / "case.json"
            tampered.write_text(json.dumps(case), encoding="utf-8")
            report = assurance.run_assurance(REPO, tampered)
            self.assertEqual(report["results"][0]["status"], "STALE")


if __name__ == "__main__":
    unittest.main()
