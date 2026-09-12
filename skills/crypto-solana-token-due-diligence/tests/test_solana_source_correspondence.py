from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_programs import decode_program, source_assurance
from solana_fixture import KEY
from program_fixture import program


class SourceTests(unittest.TestCase):
    def program(self, sliced=False):
        address, _, p, d = program(sliced=sliced)
        return decode_program(address, p, d)

    def test_publication_third_party_and_bytes_are_separate(self):
        value = self.program()
        publication = {"url": "https://github.com/official/project", "revision": "a"*40, "evidence": ["source-capture"]}
        claim = {"program": value["address"], "status": "verified", "evidence": ["remote"],
                 "hash_kind": value["code_hash_kind"], "code_sha256": value["code_sha256"]}
        result = source_assurance(value, publication=publication, third_party=claim)
        self.assertEqual(result["publication"], "published")
        self.assertEqual(result["byte_correspondence"], "remote_hash_matches_captured_bytes")
        self.assertEqual(result["independent_reproduction"], "not_performed")
        self.assertFalse(result["pool_configuration_proven"])
        claim["code_sha256"] = "b"*64
        self.assertEqual(source_assurance(value, third_party=claim)["byte_correspondence"], "mismatch")

    def test_incomplete_bytes_and_unavailable_service_are_not_unpublished(self):
        value = self.program(sliced=True)
        result = source_assurance(value, third_party={"program": value["address"], "status": "unavailable", "evidence": ["outage"]})
        self.assertEqual(result["byte_correspondence"], "incomplete_executable_bytes")
        self.assertEqual(result["publication"], "not_observed")
        self.assertEqual(result["third_party_verification"], "unavailable")

    def test_reproduction_requires_exact_revision_and_matching_artifact_is_not_a_proven_build(self):
        value = self.program()
        publication = {"url": "https://github.com/official/project", "revision": "a"*40, "evidence": ["source-capture"]}
        reproduction = {"program": value["address"], "source_revision": "a"*40, "build_id": "b1", "evidence": ["artifact"], "bytes": b"\x7fELFsynthetic bytes"}
        result = source_assurance(value, publication=publication, reproduction=reproduction)
        self.assertEqual(result["independent_reproduction"], "artifact_match_reproduction_unproven")
        reproduction["source_revision"] = "b"*40
        with self.assertRaises(ValueError):
            source_assurance(value, publication=publication, reproduction=reproduction)

    def test_wrong_subject_and_unsafe_publication_url_rejected(self):
        value = self.program()
        with self.assertRaises(ValueError):
            source_assurance(value, third_party={"program": KEY, "status": "verified", "evidence": ["x"]})
        for url in ("https://user:secret@example.org", "https://example.org?token=secret", "http://example.org"):
            with self.assertRaises(ValueError):
                source_assurance(value, publication={"url": url, "revision": "a"*40})


if __name__ == "__main__":
    unittest.main()
