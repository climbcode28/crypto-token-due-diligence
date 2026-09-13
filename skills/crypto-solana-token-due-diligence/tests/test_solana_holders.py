from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_accounts import aggregate_holders, ratio
from solana_presets import settings, holding_sample
from solana_fixture import KEY, OTHER, GENESIS, TARGET, request, response
from solana_common import b58encode, TOKEN_2022
from test_solana_accounts import holding, mint, tlv


class HolderTests(unittest.TestCase):
    def packets(self, values=None, supply=2**60+17, program=None):
        addresses = [OTHER, GENESIS, b58encode(bytes([8])*32)]
        req = request("getTokenLargestAccounts", [KEY, {"commitment": "finalized"}], "discovery")
        lead = {"context": {"slot": 100}, "value": [{"address": a, "amount": str(q), "decimals": 9} for a, q in zip(addresses, (2**59, 100, 7))]}
        d = {"request": req, "status": "ok", "response": response(req, lead)}
        plan = holding_sample(KEY, d)[0]
        req = request(plan["method"], plan["params"], "sample")
        values = [holding(2**59), holding(101), holding(7, owner=KEY)] if values is None else values
        m = mint(supply, program=program) if program else mint(supply)
        s = {"request": req, "status": "ok", "response": response(req, {"context": {"slot": 105}, "value": [m]+values})}
        return d, s

    def test_unknown_mint_extension_keeps_sample_status_but_holding_unknowns_demote(self):
        values = [holding(2**59, program=TOKEN_2022), holding(101, program=TOKEN_2022), holding(7, owner=KEY, program=TOKEN_2022)]
        d, s = self.packets(values=values, program=TOKEN_2022)
        s["response"]["result"]["value"][0] = mint(extensions=tlv(60000, b"opaque"), program=TOKEN_2022)
        result = aggregate_holders(d, s, TARGET)
        self.assertEqual(result["status"], "observed")  # the largest-accounts read is the exact top 20; an unknown mint extension is recorded, not a demotion
        self.assertEqual(result["mint"]["unknown_extensions"], [60000])
        self.assertEqual((result["coverage_share"]["rounding"], result["coverage_share"]["places"]), ("half_up", 4))
        values = [holding(2**59, program=TOKEN_2022, extensions=tlv(60001, b"?")), holding(101, program=TOKEN_2022), holding(7, owner=KEY, program=TOKEN_2022)]
        d, s = self.packets(values=values, program=TOKEN_2022)
        self.assertEqual(aggregate_holders(d, s, TARGET)["status"], "partial")

    def test_large_integer_owner_aggregate_rank_and_denominator(self):
        d, s = self.packets()
        result = aggregate_holders(d, s, TARGET)
        self.assertEqual(result["owners"][0]["amount_atomic"], str(2**59+101))
        self.assertEqual(len(result["owners"][0]["accounts"]), 2)
        self.assertEqual(result["coverage_share"]["numerator_atomic"], str(2**59+108))
        self.assertEqual(result["coverage_share"]["denominator_atomic"], str(2**60+17))
        self.assertEqual(result["coverage_share"]["percent_display"], "50.0000")
        self.assertTrue(result["accounts"][1]["balance_changed_since_discovery"])
        self.assertEqual(result["accounts"][1]["rank_at_discovery"], 2)
        self.assertIsNone(result["burned_amount_atomic"])

    def test_null_wrong_mint_and_owner_change_remain_scoped(self):
        d, s = self.packets([None, holding(100, mint=OTHER), holding(7, owner=GENESIS)])
        result = aggregate_holders(d, s, TARGET)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["missing"]), 2)
        self.assertEqual(result["owners"][0]["spending_owner"], GENESIS)
        self.assertEqual(result["observed_base_amount_atomic"], "7")

    def test_duplicates_wrong_denominators_and_unrequested_accounts_rejected(self):
        d, s = self.packets()
        d["response"]["result"]["value"][1]["address"] = OTHER
        with self.assertRaises(ValueError):
            aggregate_holders(d, s, TARGET)
        d, s = self.packets(supply=100)
        with self.assertRaisesRegex(ValueError, "exceed"):
            aggregate_holders(d, s, TARGET)
        d, s = self.packets()
        s["request"]["params"][0][0] = b58encode(bytes([11])*32)
        with self.assertRaisesRegex(ValueError, "denominator"):
            aggregate_holders(d, s, TARGET)

    def test_withheld_exclusions_and_freeze_are_separate_from_owner_balances(self):
        data = tlv(2, (9).to_bytes(8, "little"))
        d, s = self.packets([holding(100, state=2, program=TOKEN_2022, extensions=data),
                            holding(100, program=TOKEN_2022), holding(7, program=TOKEN_2022)], program=TOKEN_2022)
        result = aggregate_holders(d, s, TARGET, custody_exclusions={OTHER: {"reason": "verified pool vault", "evidence": ["pool-proof"]}})
        self.assertEqual(result["known_withheld_amount_atomic"], "9")
        self.assertEqual(result["observed_base_amount_atomic"], "207")
        self.assertEqual(result["custody_excluded_amount_atomic"], "100")
        self.assertEqual(result["owners"][0]["amount_atomic"], "107")
        self.assertEqual(result["accounts"][0]["state"], "frozen")
        self.assertIsNone(result["mint"]["freeze_authority"])

    def test_zero_supply_is_not_an_invented_fraction(self):
        self.assertIsNone(ratio(0, 0))
        self.assertEqual(ratio(1, 3)["percent_display"], "33.3333")


if __name__ == "__main__":
    unittest.main()
