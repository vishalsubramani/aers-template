"""Isolation truth model: asserted/forged is never mistaken for proven; only a
cryptographically valid external attestation upgrades the state; fail closed."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import isolation, _ed25519 as ed

NO_PROBE = {"AERS_DISABLE_ISOLATION_PROBE": "1"}


class IsolationTests(unittest.TestCase):
    def test_asserted_flag_is_only_asserted(self):
        state = isolation.assess_isolation({"AERS_NETWORK_ISOLATED": "1", **NO_PROBE})
        self.assertEqual(state["state"], isolation.ASSERTED_ISOLATED)

    def test_no_mechanism_is_unknown(self):
        self.assertEqual(isolation.assess_isolation(dict(NO_PROBE))["state"], isolation.UNKNOWN)

    def test_forged_attestation_is_rejected_not_trusted(self):
        # A bare/garbage token must NOT be accepted as externally attested.
        state = isolation.assess_isolation({"AERS_ISOLATION_ATTESTATION": "anything", **NO_PROBE})
        self.assertNotEqual(state["state"], isolation.EXTERNALLY_ATTESTED_ISOLATED)
        self.assertEqual(state["state"], isolation.UNKNOWN)

    def test_r2_fails_closed_on_forged_token(self):
        decision = isolation.gate_author_ready("R2", env={"AERS_ISOLATION_ATTESTATION": "anything",
                                                          "AERS_NETWORK_ISOLATED": "1", **NO_PROBE})
        self.assertFalse(decision["allowed"])
        self.assertIn("ISOLATION_INSUFFICIENT", decision["reason"])

    def test_valid_signed_attestation_upgrades_state(self):
        seed = bytes(range(20, 52))
        pub = ed.publickey(seed).hex()
        store = {"isolation_keys": {"iso-issuer": pub}}
        payload = {"issuer": "trusted-infra", "mechanism": "gvisor", "expires_at": "2999-01-01T00:00:00Z"}
        token = isolation.make_isolation_token(payload, seed, "iso-issuer")
        state = isolation.assess_isolation({"AERS_ISOLATION_ATTESTATION": token, **NO_PROBE},
                                           trust_store=store)
        self.assertEqual(state["state"], isolation.EXTERNALLY_ATTESTED_ISOLATED)

    def test_expired_signed_attestation_is_rejected(self):
        seed = bytes(range(21, 53))
        pub = ed.publickey(seed).hex()
        store = {"isolation_keys": {"iso-issuer": pub}}
        payload = {"issuer": "infra", "mechanism": "gvisor", "expires_at": "2000-01-01T00:00:00Z"}
        token = isolation.make_isolation_token(payload, seed, "iso-issuer")
        state = isolation.assess_isolation({"AERS_ISOLATION_ATTESTATION": token, **NO_PROBE}, trust_store=store)
        self.assertNotEqual(state["state"], isolation.EXTERNALLY_ATTESTED_ISOLATED)

    def test_tampered_signed_attestation_is_rejected(self):
        seed = bytes(range(22, 54))
        pub = ed.publickey(seed).hex()
        store = {"isolation_keys": {"iso-issuer": pub}}
        payload = {"issuer": "infra", "mechanism": "gvisor", "expires_at": "2999-01-01T00:00:00Z"}
        token = isolation.make_isolation_token(payload, seed, "iso-issuer")
        # verify under a DIFFERENT issuer key set -> unknown issuer / mismatch
        other = {"isolation_keys": {"iso-issuer": ed.publickey(bytes(range(1, 33))).hex()}}
        result = isolation.verify_isolation_attestation(token, other)
        self.assertFalse(result["ok"])

    def test_r2_fails_closed_on_asserted(self):
        decision = isolation.gate_author_ready("R2", env={"AERS_NETWORK_ISOLATED": "1", **NO_PROBE})
        self.assertFalse(decision["allowed"])

    def test_r3_requires_proven(self):
        self.assertFalse(isolation.accepts_for_author_ready(isolation.EXTERNALLY_ATTESTED_ISOLATED, "R3"))
        self.assertTrue(isolation.accepts_for_author_ready(isolation.PROVEN_ISOLATED, "R3"))

    def test_r1_accepts_asserted(self):
        self.assertTrue(isolation.accepts_for_author_ready(isolation.ASSERTED_ISOLATED, "R1"))

    def test_production_verified_never_rests_on_asserted(self):
        self.assertGreater(isolation.STRENGTH[isolation.PRODUCTION_VERIFIED_MIN_STATE],
                           isolation.STRENGTH[isolation.ASSERTED_ISOLATED])


if __name__ == "__main__":
    unittest.main()
