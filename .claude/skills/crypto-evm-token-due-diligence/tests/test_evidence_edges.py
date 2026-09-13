"""Offline evidence semantics: failures remain unknown and sale amounts bind to swaps."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backend_common import Cache
from bundle_assemble import intake, read_draft
from facts import decode_result, holder_summary
from investigation import Investigation
from keccak import selector, topic
from pipeline_note import build_pipeline_note, write_and_compose
from sale_decode import V2_SWAP, V3_SWAP, V4_SWAP, decode_sale
from test_broad_collect import (Pipeline, PipelineRpc, REGISTRY, fake_fetch, CHAIN, TOKEN,
                                POOL, QUOTE, FACTORY, NFPM, ALICE, BOB, abi, word_address)


def words(*values):
    return "0x" + "".join(format(value % 2 ** 256, "064x") for value in values)


def transfer(asset, sender, recipient, amount, index):
    return {"address": asset, "topics": [topic("Transfer(address,address,uint256)"), word_address(sender), word_address(recipient)],
            "data": abi(amount), "logIndex": hex(index)}


class SaleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.details = [{"pair": POOL, "token0": TOKEN, "token1": QUOTE}]
        self.logs = [transfer(TOKEN, ALICE, POOL, 100, 0), transfer(QUOTE, POOL, ALICE, 10, 1),
                     {"address": POOL, "topics": [V3_SWAP, word_address(ALICE), word_address(ALICE)],
                      "data": words(100, -10, 2 ** 96, 1000, 0), "logIndex": "0x2"}]

    def sale(self, logs=None, details=None, pools=None, status=1):
        return decode_sale(TOKEN, {"logs": self.logs if logs is None else logs}, {"status": status, "from": ALICE},
                           {POOL} if pools is None else pools, 0, pool_details=self.details if details is None else details)

    def test_exact_v3_input_and_output_bind_to_same_pool(self):
        sale = self.sale()
        self.assertTrue(sale["verified"])
        self.assertEqual((sale["seller"], sale["amount_raw"]), (ALICE, 100))
        self.assertEqual(sale["received"], [{"asset": QUOTE, "amount_raw": 10}])

    def test_cross_pool_swap_and_wrong_currency_direction_do_not_verify(self):
        other_pool = copy.deepcopy(self.logs)
        other_pool[-1]["address"] = FACTORY
        self.assertFalse(self.sale(other_pool, pools={POOL, FACTORY})["verified"])
        self.assertFalse(self.sale(details=[{"pair": POOL, "token0": QUOTE, "token1": TOKEN}])["verified"])
        self.assertFalse(self.sale(details=[])["verified"])

    def test_large_liquidity_deposit_cannot_replace_actual_sale(self):
        logs = [transfer(TOKEN, BOB, POOL, 1000000, 3)] + self.logs
        sale = self.sale(logs)
        self.assertTrue(sale["verified"])
        self.assertEqual((sale["seller"], sale["amount_raw"]), (ALICE, 100))
        self.assertFalse(self.sale([logs[0], *self.logs[1:]])["verified"])

    def test_duplicate_equal_inputs_and_zero_or_reverted_swaps_are_unknown(self):
        self.assertFalse(self.sale([transfer(TOKEN, BOB, POOL, 100, 3), *self.logs])["verified"])
        self.assertFalse(self.sale(status=0)["verified"])
        logs = copy.deepcopy(self.logs)
        logs[-1]["data"] = words(0, 0, 0, 0, 0)
        self.assertFalse(self.sale(logs)["verified"])
        logs[-1]["data"] = "0x00"
        self.assertFalse(self.sale(logs)["verified"])

    def test_v2_direction_and_unrelated_proceeds(self):
        logs = copy.deepcopy(self.logs)
        logs[-1].update(topics=[V2_SWAP, word_address(ALICE), word_address(ALICE)], data=words(100, 0, 0, 10))
        self.assertTrue(self.sale(logs)["verified"])
        logs[1]["topics"][1] = word_address(BOB)
        sale = self.sale(logs)
        self.assertTrue(sale["verified"])
        self.assertEqual(sale["received"], [])

    def test_v4_binds_pool_id_and_negative_caller_input(self):
        pool_id = "0x" + "ab" * 32
        details = [{"pair": pool_id, "version": "v4", "counter_asset": QUOTE}]
        logs = copy.deepcopy(self.logs)
        logs[-1].update(topics=[V4_SWAP, pool_id, word_address(ALICE)], data=words(-100, 10, 2 ** 96, 1000, 0, 3000))
        sale = self.sale(logs, details=details)
        self.assertTrue(sale["verified"])
        self.assertEqual(sale["pool_id"], pool_id)
        self.assertIn("indexer-linked", sale["pool_identity_basis"])
        logs[-1]["topics"][1] = "0x" + "cd" * 32
        self.assertFalse(self.sale(logs, details=details)["verified"])


class MissingReadRpc(PipelineRpc):
    def __call__(self, request):
        unavailable = (request["method"] == "eth_getStorageAt" and request["params"][0] == FACTORY) or (
            request["method"] == "eth_call" and request["params"][0]["to"] == NFPM
            and request["params"][0]["data"][2:10] == selector("getApproved(uint256)"))
        if unavailable:
            self.calls.append(copy.deepcopy(request))
            return {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32000, "message": "requested data is unavailable"}}
        return super().__call__(request)


class FactSemanticsTests(unittest.TestCase):
    def test_unavailable_authority_and_approval_never_become_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = Investigation.create(root / "session.sqlite", 200, 600, request_ceiling=300, timeout_ceiling=900, limit_basis="analyst_safety")
            cache = Cache(root / "cache.sqlite")
            rpc = MissingReadRpc()
            try:
                intake(root / "draft", {"chain_id": CHAIN, "address": TOKEN}, "Offline missing-read test", "Authority material", True)
                pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "Offline missing-read test", "Authority material", rpc, session, cache,
                                    "synthetic", fetch=fake_fetch, synthetic=True, registry=REGISTRY)
                facts = pipeline.run_all()
                note = build_pipeline_note(facts, read_draft(root / "draft"))
                findings = {f["id"]: f for f in note["findings"]}
                self.assertIn("EIP-1967 implementation unavailable", findings["pipeline-admin-authority"]["text"])
                self.assertIn("approved operator unavailable", findings["pipeline-launch-position-custody"]["text"])
                self.assertNotIn("approved operator none", findings["pipeline-launch-position-custody"]["text"])
                factory = next(s for s in note["scope"] if s["address"] == FACTORY)
                self.assertNotEqual(factory.get("proxy", {}).get("status"), "none_found")
                self.assertEqual(write_and_compose(root)["errors"], [])
                self.assertEqual(len(rpc.calls), 102, "semantic corrections add no requests (102: the pipeline's standard reads including Safe module/guard, custodian getters and the second phase-4 collection)")
            finally:
                cache.close()
                session.close()

    def test_owner_array_shape_and_full_count_survive_bounded_display(self):
        owners = [int(ALICE, 16) + i for i in range(21)]
        decoded = decode_result(selector("getOwners()"), words(32, len(owners), *owners))
        self.assertEqual(decoded["count"], 21)
        self.assertEqual(len(decoded["addresses"]), 20)
        for malformed in (words(64, 1, int(ALICE, 16)), words(32, 2, int(ALICE, 16)), "0x",
                          words(32, 1, int(ALICE, 16)) + "00", words(32, 21, *owners[:20], 2 ** 160)):
            self.assertNotIn("addresses", decode_result(selector("getOwners()"), malformed))

    def test_untyped_getter_counts_and_missing_indexer_fields_keep_their_units(self):
        sample = {"target": {"chain_id": CHAIN, "address": TOKEN},
                  "metadata": {"symbol": "SYNP", "total_supply": 10 ** 18, "decimals": 9},
                  "controls": {"getters": {"launchBlock": {"decoded": {"int": 20000000}, "evidence": "token-launchBlock"}}},
                  "owners": {"factory": {"address": FACTORY, "safe_owners": [ALICE] * 20,
                                            "safe_owner_count": 21, "safe_threshold": 15}},
                  "maturity": {"holders_count": 100, "indexed_pools": 1, "indexed_liquidity_usd": None,
                               "indexed_volume_h24_usd": None, "indexed_txns_h24": {"buys": None, "sells": None}}}
        note = build_pipeline_note(sample, {"scope": [], "evidence": [{"id": "runtime"}, {"id": "token-launchBlock"}, {"id": "metadata-total_supply"}]})
        text = " ".join(f["text"] for f in note["findings"])
        self.assertIn("launchBlock() = 20000000 (raw decoded integer)", text)
        self.assertIn("21 owner addresses", text)
        self.assertNotIn("20 signers", text)
        self.assertIn("transfer count unavailable", text)
        self.assertIn("aggregate liquidity USD unavailable", text)
        self.assertNotIn("0 buys", text)

    def test_integer_holder_aggregation_keeps_missing_and_unique_semantics(self):
        supply = 2 ** 256 - 1
        rows = [{"address": ALICE, "raw": supply // 4, "account_kind": "no_code"},
                {"address": ALICE.upper(), "raw": supply // 4, "account_kind": "no_code"},
                {"address": BOB, "raw": None, "account_kind": "unknown"}]
        summary = holder_summary(rows, supply)
        self.assertEqual((summary["selected_count"], summary["read_count"], summary["missing_count"]), (2, 1, 1))
        self.assertEqual(summary["pct_supply"], "25.0000")


if __name__ == "__main__":
    unittest.main()
