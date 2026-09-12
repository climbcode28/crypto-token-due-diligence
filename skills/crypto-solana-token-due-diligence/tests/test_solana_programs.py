import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_programs import decode_program, compare_program_recheck, LOADER_V2
from solana_common import sha
from solana_fixture import KEY, OTHER, account
from program_fixture import program, packet


class ProgramTests(unittest.TestCase):
    def test_programdata_authority_and_complete_bytes(self):
        address, pd, p, d = program()
        result = decode_program(address, p, d)
        self.assertEqual(result["programdata_address"], pd)
        self.assertEqual(result["upgrade_authority"], OTHER)
        self.assertEqual(result["code_sha256"], sha(b"\x7fELFsynthetic bytes"))
        self.assertEqual(result["evidence"], ["program", "programdata"])
        self.assertEqual(decode_program(address, p)["upgradeability"], "unknown")

    def test_metadata_slice_cannot_supply_executable_hash(self):
        address, pd, p, d = program(None, sliced=True)
        result = decode_program(address, p, d)
        self.assertEqual(result["upgradeability"], "authority_revoked")
        self.assertEqual(result["code_capture"], "metadata_only")
        self.assertIsNone(result["code_sha256"])

    def test_wrong_loader_owner_address_or_state_rejected(self):
        address, pd, p, d = program()
        wrong = copy.deepcopy(d)
        wrong["response"]["result"]["value"]["owner"] = OTHER
        with self.assertRaises(ValueError):
            decode_program(address, p, wrong)
        wrong = copy.deepcopy(d)
        wrong["request"]["params"][0] = KEY
        with self.assertRaises(ValueError):
            decode_program(address, p, wrong)
        wrong = copy.deepcopy(p)
        wrong["response"]["result"]["value"]["owner"] = OTHER
        self.assertEqual(decode_program(address, wrong)["upgradeability"], "unknown")
        wrong = copy.deepcopy(p)
        wrong["response"]["result"]["value"]["executable"] = False
        with self.assertRaises(ValueError):
            decode_program(address, wrong)

    def test_changed_authority_and_nonfresh_recheck_cannot_agree(self):
        address, _, p, d = program(start=1)
        _, _, freshp, freshd = program(KEY, start=3)
        first, fresh = decode_program(address, p, d), decode_program(address, freshp, freshd)
        self.assertEqual(compare_program_recheck(first, fresh)["status"], "changed")
        with self.assertRaises(ValueError):
            compare_program_recheck(first, first)

    def test_v2_loader_has_scoped_upgrade_statement(self):
        value = {**account(b"\x7fELFfixture"), "owner": LOADER_V2, "executable": True}
        result = decode_program(KEY, packet(KEY, value))
        self.assertEqual(result["upgradeability"], "no_upgrade_path_in_recognized_loader")
        self.assertNotIn("safe", result)


if __name__ == "__main__":
    unittest.main()
