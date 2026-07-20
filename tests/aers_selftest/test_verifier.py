"""Verifier reference: Ed25519 attestation, root-pinned production trust, full
handoff binding, and strict signature checks. The invariant — repository-local
code cannot manufacture a production-valid VERIFIED — is tested through attack
paths, including an attacker-controlled external trust file."""
import base64, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers_assure import verifier, _ed25519 as ed
from aers.util import canonical_json

REPO = Path(__file__).resolve().parents[2]

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


class Ed25519StrictTests(unittest.TestCase):
    def test_rfc8032_vector_verifies(self):
        self.assertTrue(ed.checkvalid(RFC_SIG, b"", RFC_PK))
        self.assertFalse(ed.checkvalid(RFC_SIG, b"x", RFC_PK))

    def test_malleated_signature_is_rejected(self):
        seed = bytes(range(32))
        pk = ed.publickey(seed)
        sig = ed.signature(b"m", seed, pk)
        S = int.from_bytes(sig[32:], "little")
        malleated = sig[:32] + ((S + ed._l) % (2 ** 256)).to_bytes(32, "little")  # S + L
        self.assertTrue(ed.checkvalid(sig, b"m", pk))
        self.assertFalse(ed.checkvalid(malleated, b"m", pk))  # non-canonical S rejected


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

    def test_attacker_controlled_external_trust_file_is_refused(self):
        # The reviewer's attack: agent writes an external trust file, points the
        # env var at it, and signs with the matching private key. Because the
        # bundle is not signed by a PINNED ROOT, its key is never trusted.
        with tempfile.TemporaryDirectory() as td:
            handoff, _ = self._handoff_and_attest(Path(td))
            seed = bytes(range(7, 39))
            pub = ed.publickey(seed).hex()
            attacker_bundle = Path(td) / "attacker-trust.json"
            # Attacker even self-signs a bundle with their own (unpinned) root.
            attacker_bundle.write_text(json.dumps(
                verifier.sign_trust_bundle({"production_keys": {"atk": pub}}, seed, "atk-root")), encoding="utf-8")
            envelope = verifier.make_attestation(handoff, "VERIFIED", ["OK"], "attacker",
                                                 signer_seed=seed, keyid="atk")
            os.environ["AERS_TRUST_BUNDLE"] = str(attacker_bundle)
            try:
                r = verifier.verify_attestation(envelope, handoff)  # default pinned roots = empty
            finally:
                os.environ.pop("AERS_TRUST_BUNDLE", None)
            self.assertFalse(r["production_valid"])
            self.assertEqual(verifier.default_trust_store()["production_keys"], {})

    def test_caller_chosen_production_key_cannot_create_production_valid_result(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, _ = self._handoff_and_attest(Path(td))
            seed = bytes(range(9, 41))
            pub = ed.publickey(seed).hex()
            envelope = verifier.make_attestation(handoff, "VERIFIED", ["OK"], "attacker",
                                                 signer_seed=seed, keyid="attacker-key")
            store = {"demo_keys": {}, "production_keys": {"attacker-key": pub}}
            r = verifier.verify_attestation(envelope, handoff, trust_store=store)
            self.assertFalse(r["production_valid"])
            self.assertIn("UNTRUSTED_CALLER_ROOT", r["reasons"])

    def test_no_caller_argument_can_inject_a_production_root(self):
        # The public API must expose no way to pass trust roots; production
        # authority comes only from the internal pinned-root constant.
        import inspect
        params = set(inspect.signature(verifier.verify_attestation).parameters)
        self.assertNotIn("pinned_roots", params)
        self.assertNotIn("pinned_roots", set(inspect.signature(verifier.default_trust_store).parameters))

    def test_trust_bundle_loader_refuses_without_audited_backend(self):
        # Production trust must never be established by the unaudited reference
        # verifier. In this env no audited backend is present, so a valid bundle
        # still yields no production keys.
        self.assertFalse(verifier.AUDITED_BACKEND, "test assumes no audited backend here")
        with tempfile.TemporaryDirectory() as td:
            root_seed = bytes(range(1, 33))
            bundle = Path(td) / "bundle.json"
            bundle.write_text(json.dumps(verifier.sign_trust_bundle(
                {"production_keys": {"prod-1": ed.publickey(bytes(range(40, 72))).hex()}}, root_seed, "root-1")),
                encoding="utf-8")
            self.assertEqual(verifier.load_trust_bundle(str(bundle)), {})

    def test_trust_bundle_validation_rejects_cross_protocol_and_malformed(self):
        from datetime import datetime, timezone
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        root_seed = bytes(range(1, 33))
        roots = {"root-1": ed.publickey(root_seed).hex()}
        good = verifier.sign_trust_bundle({"production_keys": {"p": "00" * 32}}, root_seed, "root-1")
        # Valid bundle validates (reference signature is fine for the validator).
        keys, reasons = verifier.validate_trust_bundle(good, roots, now)
        self.assertEqual(reasons, [])
        self.assertIn("p", keys["production_keys"])
        # Cross-protocol: a non-bundle payload type is refused.
        wrong_type = dict(good, payloadType="application/vnd.aers.verification+json")
        self.assertEqual(verifier.validate_trust_bundle(wrong_type, roots, now)[1], ["WRONG_BUNDLE_TYPE"])
        # Unknown root.
        self.assertEqual(verifier.validate_trust_bundle(good, {"other": "00" * 32}, now)[1], ["UNKNOWN_ROOT"])
        # Expired.
        expired = verifier.sign_trust_bundle({"production_keys": {}}, root_seed, "root-1",
                                             expires_at="2000-01-01T00:00:00Z")
        self.assertIn("BUNDLE_EXPIRED", verifier.validate_trust_bundle(expired, roots, now)[1])
        # Wrong audience.
        aud = verifier.sign_trust_bundle({"production_keys": {}}, root_seed, "root-1", audience="someone-else")
        self.assertIn("BUNDLE_AUDIENCE", verifier.validate_trust_bundle(aud, roots, now)[1])
        # Malformed.
        self.assertEqual(verifier.validate_trust_bundle({"payloadType": verifier.BUNDLE_TYPE}, roots, now)[1],
                         ["MALFORMED_BUNDLE"])

    def test_every_handoff_field_substitution_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            for field, bad in [("requested_profile", "lite"), ("feature_id", "FEAT-X"),
                               ("task_id", "T-9"), ("feature_contract_digest", "00" * 32),
                               ("task_contract_digest", "00" * 32), ("repo_identity", "evil"),
                               ("candidate_sha", "0" * 40), ("policy_digest", "deadbeef")]:
                mutated = dict(handoff)
                mutated[field] = bad
                r = verifier.verify_attestation(envelope, mutated)
                self.assertFalse(r["valid"], f"{field} substitution slipped through")

    def test_wrong_payload_type_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            envelope["payloadType"] = "text/plain"
            r = verifier.verify_attestation(envelope, handoff)
            self.assertIn("WRONG_PAYLOAD_TYPE", r["reasons"])

    def test_statement_type_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            payload = json.loads(base64.standard_b64decode(envelope["payload"]))
            payload["predicateType"] = "https://evil/predicate"
            envelope["payload"] = base64.standard_b64encode(canonical_json(payload).encode()).decode()
            r = verifier.verify_attestation(envelope, handoff)
            self.assertFalse(r["valid"])
            self.assertIn("SIGNATURE_MISMATCH", r["reasons"])  # re-encoding breaks the signature

    def test_result_tampering_breaks_signature(self):
        with tempfile.TemporaryDirectory() as td:
            handoff, envelope = self._handoff_and_attest(Path(td))
            payload = json.loads(base64.standard_b64decode(envelope["payload"]))
            payload["predicate"]["verdict"] = "REJECTED"
            envelope["payload"] = base64.standard_b64encode(canonical_json(payload).encode()).decode()
            r = verifier.verify_attestation(envelope, handoff)
            self.assertFalse(r["valid"])
            self.assertIn("SIGNATURE_MISMATCH", r["reasons"])

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
