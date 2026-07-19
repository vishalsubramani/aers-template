"""Isolation truth model: asserted is never mistaken for proven; fail closed."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import isolation


class IsolationTests(unittest.TestCase):
    def test_asserted_flag_is_only_asserted(self):
        state = isolation.assess_isolation({"AERS_NETWORK_ISOLATED": "1", "AERS_DISABLE_ISOLATION_PROBE": "1"})
        self.assertEqual(state["state"], isolation.ASSERTED_ISOLATED)

    def test_no_mechanism_is_unknown(self):
        state = isolation.assess_isolation({"AERS_DISABLE_ISOLATION_PROBE": "1"})
        self.assertEqual(state["state"], isolation.UNKNOWN)

    def test_external_attestation_recognized(self):
        state = isolation.assess_isolation({"AERS_ISOLATION_ATTESTATION": "signed-token-xyz",
                                            "AERS_DISABLE_ISOLATION_PROBE": "1"})
        self.assertEqual(state["state"], isolation.EXTERNALLY_ATTESTED_ISOLATED)

    def test_r2_fails_closed_on_asserted(self):
        decision = isolation.gate_author_ready("R2", env={"AERS_NETWORK_ISOLATED": "1", "AERS_DISABLE_ISOLATION_PROBE": "1"})
        self.assertFalse(decision["allowed"])
        self.assertIn("ISOLATION_INSUFFICIENT", decision["reason"])

    def test_r3_requires_proven(self):
        # Even external attestation is insufficient for R3; it needs PROVEN.
        self.assertFalse(isolation.accepts_for_author_ready(isolation.EXTERNALLY_ATTESTED_ISOLATED, "R3"))
        self.assertTrue(isolation.accepts_for_author_ready(isolation.PROVEN_ISOLATED, "R3"))

    def test_r1_accepts_asserted(self):
        self.assertTrue(isolation.accepts_for_author_ready(isolation.ASSERTED_ISOLATED, "R1"))

    def test_production_verified_never_rests_on_asserted(self):
        self.assertGreater(isolation.STRENGTH[isolation.PRODUCTION_VERIFIED_MIN_STATE],
                           isolation.STRENGTH[isolation.ASSERTED_ISOLATED])


if __name__ == "__main__":
    unittest.main()
