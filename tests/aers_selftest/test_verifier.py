"""Verifier reference: asymmetric (Ed25519) attestation, trust-root gating, and
fail-closed binding checks. The core trust invariant — repository-local code
cannot manufacture a production-valid VERIFIED — is tested through attack paths,
not just the happy path."""
import base64, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import verifier, _ed25519 as ed
from aers.util import canonical_json

REPO = Path(__file__).resolve().parents[2]

# RFC 8032 test vector 1 — proves the VERIFICATION path is standard-correct, so a
# real external verifier using an audited Ed25519 signer will be verified here.
RFC_PK = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
RFC_SIG = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")


def _fixture_repo(td: Path):
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


class Ed25519Tests(unittest.TestCase):
    def test_verification_is_rfc8032_correct(self):
        self.assertTrue(ed.checkvalid(RFC_SIG, b"", RFC_PK))
        self.assertFalse(ed.checkvalid(RFC_SIG, b"x", RFC_PK))          # wrong message
        self.assertFalse(ed.checkvalid(bytes(64), b"", RFC_PK))         # zero signature

    def test_signature_requires_the_private_seed(self):
        seed = bytes(range(32))
        pk = ed.publickey(seed)
        sig = ed.signature(b"m", seed, pk)
        self.assertTrue(ed.checkvalid(sig, b"m", pk))
        other = ed.publickey(bytes(range(1, 33)))
        self.assertFalse(ed.checkvalid(sig, b"m", other))  # cannot verify under a key you don't control


class VerifierTests(unittest.TestCase):
    def _handoff_and_attest(self, td):
        repo, author = _fixture_repo(td)
        handoff = verifier.build_handoff(repo, "FEAT-V", "T-1", "HEAD", author, "high-assurance")
        envelope = verifier.make_attestation(handoff, "VERIFIED", ["OK"], "demo-verifier")
        return handoff, envelope

    def test_local_demo_is_valid_but_never_production(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            r = verifier.verify_attestation(envelope, handoff)
            self.assertTrue(r["valid"])
            self.assertFalse(r["production_valid"])
            self.assertIn("DEMO_TRUST_DOMAIN_ONLY", r["reasons"])
            self.assertEqual(verifier.default_trust_store()["production_keys"], {})

    def test_caller_chosen_production_key_cannot_create_production_valid_result(self):
        # An attacker generates their OWN keypair, signs a matching VERIFIED
        # statement, and supplies their public key as a caller-defined production
        # root. This must NOT yield production_valid by default.
        with tempfile.TemporaryDirectory() as td:
            handoff, _ = self._handoff_and_attest(Path(td))
            seed = bytes(range(7, 39))
            pub = ed.publickey(seed).hex()
            envelope = verifier.make_attestation(handoff, "VERIFIED", ["OK"], "attacker",
                                                 signer_seed=seed, keyid="attacker-key")
            store = {"demo_keys": {}, "production_keys": {"attacker-key": pub}}
            r = verifier.verify_attestation(envelope, handoff, trust_store=store)
            self.assertFalse(r["production_valid"])
            self.assertIn("UNTRUSTED_CALLER_ROOT", r["reasons"])

    def test_legit_production_path_requires_external_out_of_repo_store(self):
        # The ONLY way to production_valid: a signature under a key in an external
        # store OUTSIDE the repo (simulating the verifier's own public key handed
        # over out-of-band). Signing still needs the private seed, which is not
        # in the repo — here the test plays the external verifier.
        with tempfile.TemporaryDirectory() as td:
            handoff, _ = self._handoff_and_attest(Path(td))
            seed = bytes(range(9, 41))
            pub = ed.publickey(seed).hex()
            envelope = verifier.make_attestation(handoff, "VERIFIED", ["OK"], "ext-verifier",
                                                 signer_seed=seed, keyid="prod-key", trust_domain="external")
            ext_store = Path(td) / "external-trust.json"  # OUTSIDE the fixture repo
            ext_store.write_text(json.dumps({"production_keys": {"prod-key": pub}}), encoding="utf-8")
            os.environ["AERS_EXTERNAL_TRUST_STORE"] = str(ext_store)
            try:
                r = verifier.verify_attestation(envelope, handoff)  # trust_store=None -> external
                self.assertTrue(r["production_valid"], r["reasons"])
            finally:
                os.environ.pop("AERS_EXTERNAL_TRUST_STORE", None)

    def test_external_store_inside_repo_is_ignored(self):
        # Pointing the external store at an IN-REPO file is not a trust boundary.
        with tempfile.TemporaryDirectory() as td:
            handoff, _ = self._handoff_and_attest(Path(td))
            in_repo = REPO / ".aers-runtime"
            in_repo.mkdir(exist_ok=True)
            store_file = in_repo / "fake-trust.json"
            store_file.write_text(json.dumps({"production_keys": {"x": "00" * 32}}), encoding="utf-8")
            os.environ["AERS_EXTERNAL_TRUST_STORE"] = str(store_file)
            try:
                self.assertEqual(verifier.default_trust_store()["production_keys"], {})
            finally:
                os.environ.pop("AERS_EXTERNAL_TRUST_STORE", None)
                store_file.unlink()

    def test_result_tampering_breaks_signature(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            payload = json.loads(base64.standard_b64decode(envelope["payload"]))
            payload["predicate"]["verdict"] = "REJECTED"
            envelope["payload"] = base64.standard_b64encode(canonical_json(payload).encode()).decode()
            r = verifier.verify_attestation(envelope, handoff)
            self.assertFalse(r["valid"])
            self.assertIn("SIGNATURE_MISMATCH", r["reasons"])

    def test_candidate_substitution_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            r = verifier.verify_attestation(envelope, dict(handoff, candidate_sha="0" * 40))
            self.assertIn("BINDING_MISMATCH:candidate_digest", r["reasons"])
            self.assertFalse(r["valid"])

    def test_policy_substitution_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            r = verifier.verify_attestation(envelope, dict(handoff, policy_digest="deadbeef"))
            self.assertIn("BINDING_MISMATCH:policy_digest", r["reasons"])

    def test_evidence_substitution_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            r = verifier.verify_attestation(envelope, dict(handoff, author_evidence_digest="deadbeef"))
            self.assertIn("BINDING_MISMATCH:evidence_digest", r["reasons"])

    def test_stale_attestation_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            r = verifier.verify_attestation(envelope, handoff, now_iso="2999-01-01T00:00:00Z")
            self.assertIn("ATTESTATION_EXPIRED", r["reasons"])
            self.assertFalse(r["valid"])

    def test_unknown_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            envelope["signatures"][0]["keyid"] = "attacker-key"
            r = verifier.verify_attestation(envelope, handoff)
            self.assertIn("UNKNOWN_SIGNING_KEY", r["reasons"])


if __name__ == "__main__":
    unittest.main()
