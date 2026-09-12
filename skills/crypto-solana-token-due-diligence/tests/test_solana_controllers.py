import base64
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from adapters import spl_multisig, squads_v4
from solana_programs import authority_graph
from solana_common import TOKEN_PROGRAM, b58encode
from solana_fixture import KEY, OTHER, account
from program_fixture import squads, spending, packet


class ControllerTests(unittest.TestCase):
    def test_full_spl_signers_and_invalid_threshold_display(self):
        raw = bytes([2, 3, 1])+b"".join(bytes([i])*32 for i in range(1, 12))
        result = spl_multisig.decode(KEY, account(raw))
        self.assertEqual(len(result["signers"]), 3)
        self.assertEqual(result["threshold"], 2)
        self.assertEqual(result["subject_linkage"], "requires_observed_authority_edge")
        for bad in (raw[:100], bytes([4])+raw[1:], raw[:3]+bytes(352)):
            with self.assertRaises(ValueError):
                spl_multisig.decode(KEY, account(bad))

    def test_squads_config_bypass_and_variable_option_layout(self):
        for rent in (None, KEY):
            address, value = squads(config_authority=OTHER, rent_collector=rent)
            result = squads_v4.decode(address, value)
            self.assertEqual(result["threshold"], 2)
            self.assertEqual(len(result["members"]), 3)
            self.assertTrue(result["configuration_bypass"])
            self.assertEqual(result["time_lock_seconds"], 3600)
            self.assertEqual(result["rent_collector"], rent)
            self.assertEqual(result["spending_limits"], "not_enumerated")

    def test_wrong_pda_permissions_and_truncated_members_are_not_controllers(self):
        address, value = squads()
        with self.assertRaisesRegex(ValueError, "PDA"):
            squads_v4.decode(KEY, value)
        address, value = squads(masks=(1, 2, 8))
        with self.assertRaises(ValueError):
            squads_v4.decode(address, value)
        address, value = squads()
        raw = base64.b64decode(value["data"][0])[:110]
        with self.assertRaises(ValueError):
            squads_v4.decode(address, {**account(raw), "owner": squads_v4.PROGRAM})

    def test_vault_binding_and_spending_membership_bypass(self):
        address, value = squads()
        multisig = squads_v4.decode(address, value)
        vault = squads_v4.vault_address(address, 2)[0]
        self.assertEqual(squads_v4.verify_vault(vault, multisig, 2)["to"], address)
        with self.assertRaises(ValueError):
            squads_v4.verify_vault(KEY, multisig, 2)
        limit_address, limit_value = spending(multisig)
        result = squads_v4.decode_spending_limit(limit_address, limit_value, multisig)
        self.assertEqual(result["vault"], vault)
        self.assertTrue(result["membership_independent_of_multisig"])
        self.assertNotIn(result["members"][0], [m["key"] for m in multisig["members"]])
        self.assertTrue(result["bypasses_multisig_vote_and_timelock"])
        self.assertEqual(result["destination_restriction"], "any")

    def test_unknown_controller_preserves_observed_edges_and_cycles(self):
        a = {**account(b"custom"), "owner": OTHER}
        b = {**account(b"custom"), "owner": KEY}
        result = authority_graph([KEY], {KEY: packet(KEY, a, "a"), OTHER: packet(OTHER, b, "b")})
        self.assertEqual(len(result["edges"]), 2)
        self.assertTrue(any(g["reason"] == "cycle" for g in result["gaps"]))
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["safe_or_locked_conclusion"])

    def test_graph_bounds_and_squads_configuration_path(self):
        address, value = squads(config_authority=OTHER)
        result = authority_graph([address], {address: packet(address, value)}, max_accounts=2)
        self.assertLessEqual(len(result["nodes"]), 2)
        self.assertLessEqual(result["observed_account_count"], 2)
        self.assertTrue(any(e["role"] == "configuration_bypass" and e["to"] == OTHER for e in result["edges"]))
        self.assertTrue(any(g["reason"] == "account_limit" for g in result["gaps"]))
        result = authority_graph([address], {address: packet(address, value)}, max_depth=0)
        self.assertTrue(any(g["reason"] == "depth_limit" for g in result["gaps"]))

    def test_spending_limit_graph_keeps_bypass_and_incomplete_search(self):
        address, value = squads()
        multisig = squads_v4.decode(address, value)
        limit, limit_value = spending(multisig)
        result = authority_graph([address], {address: packet(address, value, "multisig"), limit: packet(limit, limit_value, "limit")}, spending_limits={address: [limit]})
        self.assertTrue(any(e["role"] == "spending_limit_member" for e in result["edges"]))
        self.assertTrue(any(g["reason"] == "spending_limit_sample_not_exhaustive" for g in result["gaps"]))

    def test_foreign_spending_limit_is_not_a_bypass_for_claimed_parent(self):
        address, value = squads(config_authority=OTHER)
        foreign, foreign_value = squads(create_seed=23)
        limit, limit_value = spending(squads_v4.decode(foreign, foreign_value))
        result = authority_graph([address], {address: packet(address, value, "a"), limit: packet(limit, limit_value, "limit")}, spending_limits={address: [limit]})
        self.assertFalse(any(e["role"] == "spending_limit" for e in result["edges"]))
        self.assertTrue(any(e["role"] == "configuration_bypass" for e in result["edges"]))
        self.assertTrue(any(g["reason"] == "spending_limit_candidate_unverified" for g in result["gaps"]))
        self.assertLessEqual(result["discovered_account_count"], 20)


if __name__ == "__main__":
    unittest.main()
