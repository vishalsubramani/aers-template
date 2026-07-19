"""The adversarial benchmark, evaluator health, and threat model must hold."""
import copy, json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import baseline, benchmark, health, threats

REPO = Path(__file__).resolve().parents[2]


class BenchmarkTests(unittest.TestCase):
    def test_at_least_25_cases_all_contained(self):
        report = benchmark.run_benchmark(REPO)
        self.assertGreaterEqual(report["total"], 25)
        failed = [r for r in report["results"] if not r["passed"]]
        self.assertTrue(report["all_passed"], f"benchmark failures: {failed}")

    def test_every_case_drives_a_real_probe(self):
        for case in benchmark.load_cases(REPO):
            self.assertIn(case["kind"], benchmark._PROBES, case["id"])


class BaselineTests(unittest.TestCase):
    def test_more_gates_strictly_reduce_false_pass(self):
        report = baseline.run_baseline(REPO)
        by_mode = {r["mode"]: r["derived"]["false_pass_rate"] for r in report["rows"]}
        # Unconstrained lets everything through; AERS modes let strictly less.
        self.assertEqual(by_mode["unconstrained"], 1.0)
        self.assertLess(by_mode["aers_lite"], by_mode["unconstrained"])
        self.assertLess(by_mode["aers_standard"], by_mode["aers_lite"])
        self.assertLessEqual(by_mode["aers_high_assurance"], by_mode["aers_standard"])
        # High assurance contains every seeded attack kind in the benchmark.
        self.assertEqual(by_mode["aers_high_assurance"], 0.0)


class HealthTests(unittest.TestCase):
    def test_health_suite_passes_with_full_detection(self):
        report = health.run_health(REPO)
        self.assertTrue(report["passed"], report["regressions"])
        self.assertEqual(report["seeded_defect_detection_rate"], 1.0)
        self.assertEqual(report["false_acceptance_rate"], 0.0)
        self.assertEqual(report["nondeterministic_verdicts"], 0)

    def test_health_binds_to_evaluator_config_digest(self):
        report = health.run_health(REPO)
        self.assertEqual(len(report["evaluator_config_digest"]), 64)


class ThreatModelTests(unittest.TestCase):
    def test_threat_model_valid(self):
        report = threats.validate(REPO)
        self.assertTrue(report["passed"], report["findings"])
        self.assertGreaterEqual(report["total_threats"], 10)

    def test_critical_threat_without_benchmark_is_flagged(self):
        model = json.loads((REPO / threats.MODEL_PATH).read_text())
        broken = copy.deepcopy(model)
        for t in broken["threats"]:
            if t["severity"] == "critical":
                t["benchmark_cases"] = []
                break
        report = threats.validate(REPO, broken)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "CRITICAL_WITHOUT_BENCHMARK" for f in report["findings"]))

    def test_missing_benchmark_reference_is_flagged(self):
        model = json.loads((REPO / threats.MODEL_PATH).read_text())
        broken = copy.deepcopy(model)
        broken["threats"][0]["benchmark_cases"] = ["BENCH-DOES-NOT-EXIST"]
        report = threats.validate(REPO, broken)
        self.assertTrue(any(f["code"] == "MISSING_BENCHMARK" for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()
