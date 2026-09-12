import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_addresses import create_program_address, find_program_address, associated_token_address, bytes_are_curve_point, P, ASSOCIATED_PROGRAM
from solana_common import base58_bytes, b58encode, signature, TOKEN_PROGRAM, TOKEN_2022


class AddressTests(unittest.TestCase):
    def test_pinned_official_create_vectors(self):
        fixture = json.loads((Path(__file__).parent/"fixtures/addresses/official-pda-vectors.json").read_text())
        for row in fixture["vectors"]:
            seeds = [bytes.fromhex(value) for value in row["seeds_hex"]]
            if "seed_pubkey" in row:
                seeds.insert(0, base58_bytes(row["seed_pubkey"], 32))
            self.assertEqual(create_program_address(seeds, fixture["program"]), row["address"])
            self.assertFalse(bytes_are_curve_point(base58_bytes(row["address"], 32)))

    def test_decompression_is_not_signature_or_subgroup_validation(self):
        self.assertTrue(bytes_are_curve_point(bytes.fromhex("58"+"66"*31)))
        self.assertTrue(bytes_are_curve_point(bytes(32)))
        self.assertTrue(bytes_are_curve_point((1).to_bytes(32, "little")))
        self.assertTrue(bytes_are_curve_point((P+1).to_bytes(32, "little")))
        self.assertTrue(bytes_are_curve_point((1+2**255).to_bytes(32, "little")))
        with self.assertRaises(ValueError):
            bytes_are_curve_point(bytes(31))

    def test_canonical_signatures_have_distinct_size_and_no_normalization(self):
        for raw in (bytes(64), bytes([255])*64):
            value = b58encode(raw)
            self.assertEqual(signature(value), value)
        for value in (b58encode(bytes(32)), "1"*65, "0"*88, " "+b58encode(bytes(64))):
            with self.assertRaises(ValueError):
                signature(value)

    def test_seed_and_bump_bounds_match_sdk(self):
        program = "BPFLoaderUpgradeab1e11111111111111111111111"
        for seeds in ([bytes(33)], [b"x"]*17, ["text"]):
            with self.assertRaises(ValueError):
                create_program_address(seeds, program)
        with self.assertRaises(ValueError):
            find_program_address([b"x"]*16, program)
        for i in range(20):
            seeds = [b"Lil'", b"Bits", bytes([i])]
            address, bump = find_program_address(seeds, program)
            self.assertEqual(create_program_address(seeds+[bytes([bump])], program), address)
            for skipped in range(255, bump, -1):
                with self.assertRaisesRegex(ValueError, "on curve"):
                    create_program_address(seeds+[bytes([skipped])], program)
        with patch("solana_addresses.bytes_are_curve_point", return_value=True) as check:
            with self.assertRaisesRegex(ValueError, "bounded bump"):
                find_program_address([], program)
            self.assertEqual(check.call_count, 255)

    def test_associated_address_binds_token_program_in_seed_order(self):
        owner, mint = b58encode(bytes([2])*32), b58encode(bytes([3])*32)
        original = associated_token_address(owner, mint, TOKEN_PROGRAM)
        extended = associated_token_address(owner, mint, TOKEN_2022)
        self.assertNotEqual(original[0], extended[0])
        self.assertEqual(original, find_program_address([base58_bytes(owner, 32), base58_bytes(TOKEN_PROGRAM, 32), base58_bytes(mint, 32)], ASSOCIATED_PROGRAM))


if __name__ == "__main__":
    unittest.main()
