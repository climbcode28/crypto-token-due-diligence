import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_discovery import MAINNET, pools, source_plan, repository_urls, repository_metadata, repository_revision, repository_tree, registry
from solana_common import sha, target_identity
from solana_fixture import TARGET, KEY, OTHER, GENESIS

MAIN_TARGET = {**TARGET, "genesis_hash": MAINNET}


def capture(value, url):
    raw = json.dumps(value, separators=(",", ":")).encode()
    return {"id": "capture", "url": url, "final_url": url, "status": "ok", "http_status": 200,
            "captured_at": 1234, "bytes": len(raw), "sha256": sha(raw)}, raw


def dex_pair():
    return {"chainId": "solana", "pairAddress": GENESIS, "baseToken": {"address": KEY},
            "quoteToken": {"address": OTHER}, "dexId": "raydium", "liquidity": {"usd": 1234.56},
            "priceUsd": "0.00000123456789", "info": {"websites": [{"url": "https://project.example/"}]}}


class DiscoveryTests(unittest.TestCase):
    def test_exact_mint_optional_values_and_project_claim_provenance(self):
        record, raw = capture([dex_pair()], source_plan(MAIN_TARGET)["primary"])
        result = pools(record, raw, MAIN_TARGET)
        row = result["candidates"][0]
        self.assertEqual(row["liquidity_usd"], "1234.56")
        self.assertEqual(row["price_usd"], "0.00000123456789")
        self.assertIsNone(row["volume_h24_usd"])
        self.assertIsNone(row["program"])
        self.assertEqual(result["project_links"][0]["ownership_status"], "indexer_claim_requires_project_verification")

    def test_wrong_mint_network_malformed_and_duplicate_conflicts(self):
        a, b, c, d = dex_pair(), dex_pair(), dex_pair(), dex_pair()
        a["chainId"] = "ethereum"
        b["baseToken"]["address"] = GENESIS
        c["liquidity"] = {"usd": True}
        d["priceUsd"] = "0.5"
        record, raw = capture([a, b, c, dex_pair(), dex_pair(), d], source_plan(MAIN_TARGET)["primary"])
        result = pools(record, raw, MAIN_TARGET)
        self.assertEqual(len(result["rejected"]), 3)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(len(result["duplicates"]), 2)
        self.assertEqual(result["candidates"][0]["conflicts"][0]["fields"], ["price_usd"])

    def test_target_as_quote_does_not_relabel_base_price(self):
        value = dex_pair()
        value["baseToken"], value["quoteToken"] = value["quoteToken"], value["baseToken"]
        record, raw = capture([value], source_plan(MAIN_TARGET)["primary"])
        result = pools(record, raw, MAIN_TARGET)
        self.assertEqual(result["candidates"][0]["price_denominator_mint"], OTHER)
        self.assertEqual(result['project_links'],[])

    def test_blocked_shell_wrong_route_and_changed_bytes_do_not_parse(self):
        record, raw = capture([dex_pair()], source_plan(MAIN_TARGET)["primary"])
        for change in ({"status": "http_403"}, {"shell_suspected": True}, {"sha256": "a"*64},
                       {"url": "https://example.org/wrong"}, {"final_url": "https://unrelated.example/"}):
            with self.assertRaises(ValueError):
                pools({**record, **change}, raw, MAIN_TARGET)
        with self.assertRaises(ValueError):
            pools(record, raw, TARGET)

    def test_alternate_jsonapi_requires_network_pool_and_both_token_relations(self):
        value = {"data": [{"id": "solana_"+GENESIS, "type": "pool", "attributes": {"address": GENESIS, "reserve_in_usd": "12.3"},
            "relationships": {"base_token": {"data": {"id": "solana_"+KEY, "type": "token"}},
                              "quote_token": {"data": {"id": "solana_"+OTHER, "type": "token"}},
                              "dex": {"data": {"id": "orca", "type": "dex"}}}}]}
        record, raw = capture(value, source_plan(MAIN_TARGET)["alternate"])
        self.assertEqual(len(pools(record, raw, MAIN_TARGET, source="geckoterminal")["candidates"]), 1)
        value["data"][0]["relationships"]["quote_token"]["data"]["id"] = "ethereum_"+OTHER
        record, raw = capture(value, source_plan(MAIN_TARGET)["alternate"])
        self.assertEqual(len(pools(record, raw, MAIN_TARGET, source="geckoterminal")["rejected"]), 1)

    def test_repository_revision_binds_distinct_root_tree_sha_and_truncation(self):
        repo, revision, tree = "owner/project", "a"*40, "b"*40
        record, raw = capture({"full_name": repo, "html_url": "https://github.com/"+repo, "archived": False, "fork": False}, repository_urls(repo)["metadata"])
        self.assertIsNone(repository_metadata(record, raw, repo)["license"])
        record, raw = capture({"sha": revision, "commit": {"tree": {"sha": tree}}}, repository_urls(repo)["revision"])
        bound = repository_revision(record, raw, repo)
        value = {"sha": tree, "truncated": True, "tree": [{"path": "src/main.rs", "sha": "c"*40, "type": "blob", "mode": "100644"}]}
        record, raw = capture(value, repository_urls(repo, tree)["tree"])
        result = repository_tree(record, raw, bound)
        self.assertEqual(result["revision"], revision)
        self.assertEqual(result["tree_sha"], tree)
        self.assertEqual(result["status"], "partial")
        value["tree"][0]["path"] = "../escape"
        record, raw = capture(value, repository_urls(repo, tree)["tree"])
        with self.assertRaises(ValueError):
            repository_tree(record, raw, bound)

    def test_registry_is_context_and_future_adapters_are_not_enabled(self):
        network = registry("network")
        self.assertEqual(network["clusters"][0]["genesis_hash"], MAINNET)
        self.assertFalse(network["clusters"][0]["live_provider_tested"])
        self.assertEqual(network["limits"]["enforced_rpc_attempts_per_10s"], 40)
        self.assertTrue(all(not p["enabled"] for p in registry("protocol")["protocols"] if p["status"] == "layout_and_capability_verification_pending"))
        self.assertEqual(set(source_plan(MAIN_TARGET)), {"primary", "alternate"})
        with self.assertRaises(ValueError):
            target_identity({**MAIN_TARGET, "genesis_hash": MAINNET[:32]})


if __name__ == "__main__":
    unittest.main()
