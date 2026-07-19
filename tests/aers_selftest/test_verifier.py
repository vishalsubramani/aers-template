"""Verifier reference: the core trust invariants must hold and fail closed."""
import base64, json, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import verifier
from aers.util import canonical_json

REPO = Path(__file__).resolve().parents[2]


def _fixture_repo(td: Path) -> tuple[Path, Path]:
    repo = td / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "aers.toml").write_text("version = 1\n", encoding="utf-8")
    fdir = repo / ".specify/specs/FEAT-V"
    fdir.mkdir(parents=True)
    (fdir / "feature.contract.json").write_text(json.dumps({"feature_id": "FEAT-V"}), encoding="utf-8")
    (fdir / "tasks.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
    (repo / ".agents/policies").mkdir(parents=True)
    (repo / ".agents/policies/protected-paths.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    author = repo / "author.json"
    author.write_text(json.dumps({"verdict": "AUTHOR_READY"}), encoding="utf-8")
    return repo, author


class VerifierTests(unittest.TestCase):
    def _handoff_and_attest(self, td):
        repo, author = _fixture_repo(td)
        handoff = verifier.build_handoff(repo, "FEAT-V", "T-1", "HEAD", author, "high-assurance")
        envelope = verifier.make_attestation(handoff, "VERIFIED", ["OK"], "demo-verifier")
        return handoff, envelope

    def test_local_cannot_produce_production_valid_verified(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            result = verifier.verify_attestation(envelope, handoff)
            # Signature is valid and bindings hold, but it is DEMO-scoped only.
            self.assertTrue(result["valid"])
            self.assertFalse(result["production_valid"])
            self.assertIn("DEMO_TRUST_DOMAIN_ONLY", result["reasons"])
            # There is no production key material in the repository trust store.
            self.assertEqual(verifier.default_trust_store()["production_keys"], {})

    def test_result_tampering_breaks_signature(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            payload = json.loads(base64.standard_b64decode(envelope["payload"]))
            payload["predicate"]["verdict"] = "REJECTED"  # flip verdict, keep signature
            envelope["payload"] = base64.standard_b64encode(canonical_json(payload).encode()).decode()
            result = verifier.verify_attestation(envelope, handoff)
            self.assertFalse(result["valid"])
            self.assertIn("SIGNATURE_MISMATCH", result["reasons"])

    def test_candidate_substitution_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            substituted = dict(handoff, candidate_sha="0" * 40)
            result = verifier.verify_attestation(envelope, substituted)
            self.assertFalse(result["valid"])
            self.assertIn("BINDING_MISMATCH:candidate_digest", result["reasons"])

    def test_policy_substitution_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            result = verifier.verify_attestation(envelope, dict(handoff, policy_digest="deadbeef"))
            self.assertIn("BINDING_MISMATCH:policy_digest", result["reasons"])

    def test_evidence_substitution_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            result = verifier.verify_attestation(envelope, dict(handoff, author_evidence_digest="deadbeef"))
            self.assertIn("BINDING_MISMATCH:evidence_digest", result["reasons"])

    def test_stale_attestation_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            result = verifier.verify_attestation(envelope, handoff, now_iso="2999-01-01T00:00:00Z")
            self.assertFalse(result["valid"])
            self.assertIn("ATTESTATION_EXPIRED", result["reasons"])

    def test_unknown_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            envelope["signatures"][0]["keyid"] = "attacker-key"
            result = verifier.verify_attestation(envelope, handoff)
            self.assertIn("UNKNOWN_SIGNING_KEY", result["reasons"])

    def test_external_production_key_would_validate_but_is_not_repo_local(self):
        # Sanity: production validity is *possible* with an external key, but the
        # key must be supplied out-of-band; nothing in-repo can sign with it.
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            # The demo signature will NOT match a different production keyid, so
            # even naming a production key does not forge production validity.
            store = {"demo_keys": {}, "production_keys": {verifier.DEMO_KEY_ID: "00" * 32}}
            result = verifier.verify_attestation(envelope, handoff, trust_store=store)
            self.assertFalse(result["production_valid"])  # wrong key bytes -> signature mismatch
            self.assertIn("SIGNATURE_MISMATCH", result["reasons"])


if __name__ == "__main__":
    unittest.main()
