"""End-to-end synthetic pipeline: discovery, three pinned phases, facts, compose, finalize, deliver.

Everything is a labeled synthetic fixture; no network, no live token. The test proves the
plumbing and turn-free operation, not diligence accuracy.
"""
import copy
import json
import re
import shutil
import tempfile
import time
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backend_common import Cache, canonical, write_new
from backend_fixtures import CHAIN, TOKEN, ALICE, BOB, CAROL, hh, header, abi
from broad_collect import Pipeline, brief, summary_lines
from bundle_assemble import DIMENSIONS, deliver, freeze, intake, preflight, read_draft
from compose import compose
from investigation import Investigation
from keccak import selector, topic
from validate_bundle import validate

POOL = "0x5234567890abcdef1234567890abcdef12345678"
QUOTE = "0x6234567890abcdef1234567890abcdef12345678"
NFPM = "0x7234567890abcdef1234567890abcdef12345678"
QUOTER = "0x8234567890abcdef1234567890abcdef12345678"
FACTORY = "0x9234567890abcdef1234567890abcdef12345678"
LOCKER = "0xa234567890abcdef1234567890abcdef12345678"
DEAD = "0x000000000000000000000000000000000000dead"
CREATION_TX = hh("SYNTHETIC creation transaction")
SELL_TX = hh("SYNTHETIC sale transaction")
SWAP_V3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
SUPPLY = 10 ** 27
REGISTRY = {"dexscreener": "synthetic", "explorers": [{"name": "Synthetic explorer", "base": "https://explorer.invalid", "api_v2": True}],
            "uniswap_v3": {"nonfungible_position_manager": NFPM, "quoter_v2": QUOTER}}


def string_abi(text):
    raw = text.encode()
    return "0x" + (32).to_bytes(32, "big").hex() + len(raw).to_bytes(32, "big").hex() + raw.hex() + "00" * ((-len(raw)) % 32)


def word_address(value):
    return "0x" + "0" * 24 + value[2:]


class PipelineRpc:
    synthetic = True
    namespace = "synthetic-pipeline-provider"

    def __init__(self):
        self.calls = []

    def receipt(self):
        transfer = topic("Transfer(address,address,uint256)")
        return {"transactionHash": CREATION_TX, "blockHash": hh(90), "blockNumber": hex(90), "status": "0x1", "from": CAROL, "to": FACTORY,
                "logs": [{"address": TOKEN, "topics": [transfer, word_address(FACTORY), word_address(CAROL)], "data": abi(10 ** 26),
                          "transactionHash": CREATION_TX, "blockHash": hh(90), "blockNumber": hex(90), "transactionIndex": "0x0", "logIndex": "0x0", "removed": False},
                         {"address": NFPM, "topics": [transfer, "0x" + "0" * 64, word_address(LOCKER), abi(7)], "data": "0x",
                          "transactionHash": CREATION_TX, "blockHash": hh(90), "blockNumber": hex(90), "transactionIndex": "0x0", "logIndex": "0x1", "removed": False}]}

    def sale_receipt(self):
        transfer = topic("Transfer(address,address,uint256)")
        return {"transactionHash": SELL_TX, "blockHash": hh(95), "blockNumber": hex(95), "status": "0x1", "from": ALICE, "to": QUOTER,
                "logs": [{"address": TOKEN, "topics": [transfer, word_address(ALICE), word_address(POOL)], "data": abi(5 * 10 ** 21),
                          "transactionHash": SELL_TX, "blockHash": hh(95), "blockNumber": hex(95), "transactionIndex": "0x0", "logIndex": "0x0", "removed": False},
                         {"address": QUOTE, "topics": [transfer, word_address(POOL), word_address(ALICE)], "data": abi(4 * 10 ** 18),
                          "transactionHash": SELL_TX, "blockHash": hh(95), "blockNumber": hex(95), "transactionIndex": "0x0", "logIndex": "0x1", "removed": False},
                         {"address": POOL, "topics": [SWAP_V3, word_address(QUOTER), word_address(ALICE)], "data": "0x" + "".join(format(w % 2 ** 256, "064x") for w in (5 * 10 ** 21, -4 * 10 ** 18, 2 ** 96, 10 ** 18, 0)),
                          "transactionHash": SELL_TX, "blockHash": hh(95), "blockNumber": hex(95), "transactionIndex": "0x0", "logIndex": "0x2", "removed": False}]}

    def call(self, to, data):
        sel = data[2:10]
        if to == TOKEN:
            table = {selector("name()"): string_abi("Synthetic Pipeline Token"), selector("symbol()"): string_abi("SYNP"),
                     selector("decimals()"): abi(18), selector("totalSupply()"): abi(SUPPLY), selector("owner()"): abi(0),
                     selector("paused()"): abi(0), selector("launchFactory()"): word_address(FACTORY),
                     selector("maxTxAmount()"): abi(2 * 10 ** 25), selector("treasury()"): abi(2 ** 100 + 12345),
                     selector("balanceOf(address)"): None}
            if sel == selector("balanceOf(address)"):
                holder = "0x" + data[-40:]
                return abi({DEAD: 3 * 10 ** 26, POOL: 2 * 10 ** 26, CAROL: 10 ** 25, ALICE: 5 * 10 ** 25, BOB: 10 ** 24}.get(holder, 0))
            if sel in table:
                return table[sel]
            return {"error": {"code": 3, "message": "execution reverted"}}
        if to == POOL:
            table = {selector("token0()"): word_address(TOKEN), selector("token1()"): word_address(QUOTE), selector("fee()"): abi(3000),
                     selector("liquidity()"): abi(10 ** 18), selector("factory()"): word_address(FACTORY), selector("tickSpacing()"): abi(60),
                     selector("slot0()"): "0x" + format(2 ** 96, "064x") + format((-100) % 2 ** 256, "064x") + abi(0)[2:] + abi(1)[2:] + abi(1)[2:] + abi(0)[2:] + abi(1)[2:]}
            return table.get(sel, {"error": {"code": 3, "message": "execution reverted"}})
        if to == QUOTE:
            if sel == selector("balanceOf(address)"):
                return abi(5 * 10 ** 18 if "0x" + data[-40:] == POOL else 0)
            return {selector("decimals()"): abi(18), selector("symbol()"): string_abi("WETH")}.get(sel, {"error": {"code": 3, "message": "execution reverted"}})
        if to == NFPM and sel == selector("positions(uint256)"):
            words = [0, 0, int(TOKEN, 16), int(QUOTE, 16), 3000, (-887220) % 2 ** 256, 887220, 4 * 10 ** 17, 0, 0, 0, 0]
            return "0x" + "".join(format(w, "064x") for w in words)
        if to == NFPM and sel == selector("ownerOf(uint256)"):
            return word_address(LOCKER)
        if to == NFPM and sel == selector("getApproved(uint256)"):
            return abi(0)
        if to == QUOTER and sel == selector("quoteExactInputSingle((address,address,uint256,uint24,uint160))"):
            amount_in = int(data[10 + 128:10 + 192], 16)
            out = amount_in // 1000 - amount_in // 100000  # small size impact
            return "0x" + format(out, "064x") + format(2 ** 96, "064x") + abi(1)[2:] + abi(50000)[2:]
        return {"error": {"code": 3, "message": "execution reverted"}}

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        method, params = request["method"], request["params"]
        if method == "eth_chainId":
            result = hex(CHAIN)
        elif method == "eth_blockNumber":
            result = hex(100)
        elif method == "eth_getBlockByNumber":
            result = header(int(params[0], 16))
        elif method == "eth_getCode":
            result = "0x60006000f3" if params[0] in (TOKEN, POOL, QUOTE, NFPM, QUOTER, FACTORY, LOCKER) else "0x"
        elif method == "eth_call":
            result = self.call(params[0]["to"], params[0]["data"])
        elif method == "eth_getStorageAt":
            result = abi(0)
        elif method == "eth_getTransactionReceipt":
            result = self.receipt() if params[0] == CREATION_TX else self.sale_receipt() if params[0] == SELL_TX else None
        elif method == "eth_getTransactionByHash":
            if params[0] == SELL_TX:
                result = {"hash": SELL_TX, "blockNumber": hex(95), "blockHash": hh(95), "from": ALICE, "to": QUOTER, "input": "0xabcd1234", "value": "0x0"}
            else:
                result = {"hash": CREATION_TX, "blockNumber": hex(90), "blockHash": hh(90), "from": CAROL, "to": FACTORY, "input": "0x1234abcd", "value": "0x0"}
        else:
            raise AssertionError("unexpected synthetic request " + method)
        if isinstance(result, dict) and "error" in result:
            return {"jsonrpc": "2.0", "id": request["id"], **result}
        return {"jsonrpc": "2.0", "id": request["id"], "result": copy.deepcopy(result)}


def fake_fetch(items, out):
    out = Path(out)
    records = []
    for item in items:
        body = None
        if item["id"] == "dexscreener-pairs":
            body = [{"chainId": "synthetic", "dexId": "uniswap", "labels": ["v3"], "pairAddress": POOL, "url": "https://dexscreener.invalid/pair",
                     "baseToken": {"address": TOKEN, "symbol": "SYNP"}, "quoteToken": {"address": QUOTE, "symbol": "WETH"},
                     "liquidity": {"usd": 12345.0}, "volume": {"h24": 999.0}, "txns": {"h24": {"buys": 10, "sells": 7}}, "priceUsd": "0.5",
                     "fdv": 1, "marketCap": 1, "pairCreatedAt": 1700000000000,
                     "info": {"websites": [{"url": "https://project.invalid"}], "socials": [{"type": "twitter", "url": "https://x.com/synthetic"}]}}]
        elif item["id"] == "sourcify-correspondence":
            body = {"chainId": str(CHAIN), "address": TOKEN, "compilation": {"compilerVersion": "0.8.26", "fullyQualifiedName": "Token.sol:Token"},
                    "abi": [{"type": "function", "name": "launchFactory", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "maxTxAmount", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
                            {"type": "function", "name": "treasury", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "owner", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "paused", "inputs": [], "outputs": [{"type": "bool"}], "stateMutability": "view"},
                            {"type": "function", "name": "transfer", "inputs": [{"type": "address"}], "outputs": [], "stateMutability": "nonpayable"}]}
        elif item["id"] == "explorer-address":
            body = {"is_contract": True, "creation_transaction_hash": CREATION_TX, "creator_address_hash": CAROL, "is_verified": True}
        elif item["id"] == "explorer-token":
            body = {"holders": "1234"}
        elif item["id"] == "explorer-counters":
            body = {"transfers_count": "98765", "token_holders_count": "1234"}
        elif item["id"] == "explorer-holders":
            body = {"items": [{"address": {"hash": DEAD, "is_contract": False, "name": None}, "value": str(3 * 10 ** 26)},
                              {"address": {"hash": POOL, "is_contract": True, "name": "UniswapV3Pool"}, "value": str(2 * 10 ** 26)},
                              {"address": {"hash": ALICE, "is_contract": False, "name": None}, "value": str(5 * 10 ** 25)},
                              {"address": {"hash": BOB, "is_contract": False, "name": None}, "value": str(10 ** 24)}], "next_page_params": None}
        elif item["id"] == "explorer-transfers":
            body = {"items": [{"transaction_hash": SELL_TX, "block_number": 95, "from": {"hash": ALICE, "is_contract": False}, "to": {"hash": POOL, "is_contract": True},
                               "total": {"value": str(5 * 10 ** 21)}, "method": "swap", "timestamp": "2026-01-01T00:00:00Z"},
                              {"transaction_hash": hh("buy"), "block_number": 94, "from": {"hash": POOL, "is_contract": True}, "to": {"hash": BOB, "is_contract": False},
                               "total": {"value": str(10 ** 21)}, "method": "swap"}], "next_page_params": None}
        elif item["id"] == "explorer-signer-transactions":
            body = {"items": [{"hash": CREATION_TX, "block_number": 90, "from": {"hash": CAROL}, "to": {"hash": FACTORY}, "method": "createToken", "created_contract": None},
                              {"hash": hh("other launch"), "block_number": 80, "from": {"hash": CAROL}, "to": {"hash": FACTORY}, "method": "createToken", "created_contract": None}], "next_page_params": None}
        elif item["id"] == "explorer-signer-token-transfers":
            body = {"items": [{"transaction_hash": hh("early sale"), "block_number": 91, "from": {"hash": CAROL}, "to": {"hash": POOL}, "token": {"address": TOKEN}, "total": {"value": "1"}}], "next_page_params": None}
        record = {"id": item["id"], "url": item["url"], "final_url": item["url"], "purpose": item.get("purpose"), "http_status": 200,
                  "captured_at_utc": "2026-01-01T00:00:00Z", "failure_category": None, "content_type": "application/json", "host": "synthetic.invalid",
                  "raw": item["id"] + ".raw", "bytes": 0, "sha256": None}
        raw = json.dumps(body).encode()
        (out / record["raw"]).write_bytes(raw)
        record["bytes"] = len(raw)
        (out / (item["id"] + ".json")).write_text(json.dumps(record))
        records.append(record)
    return records


class BroadCollectTests(unittest.TestCase):
    def run_pipeline(self, root):
        session = Investigation.create(root / "session.sqlite", 200, 600, request_ceiling=300, timeout_ceiling=900, limit_basis="analyst_safety")
        cache = Cache(root / "cache.sqlite")
        rpc = PipelineRpc()
        try:
            intake(root / "draft", {"chain_id": CHAIN, "address": TOKEN}, "Synthetic pipeline question", "All authority material", True)
            pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "Synthetic pipeline question", "All authority material",
                                rpc, session, cache, "synthetic", fetch=fake_fetch, synthetic=True, registry=REGISTRY)
            facts = pipeline.run_all()
            status = session.status()
        finally:
            cache.close()
            session.close()
        return facts, rpc, status

    def test_pipeline_collects_decodes_and_imports_without_model_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            started = time.monotonic()
            facts, rpc, status = self.run_pipeline(root)
            self.assertLess(time.monotonic() - started, 10)
            self.assertEqual(facts["metadata"]["symbol"], "SYNP")
            self.assertEqual(facts["metadata"]["decimals"], 18)
            self.assertEqual(facts["controls"]["owner"], "0x" + "0" * 40)
            self.assertEqual(facts["actors"]["creator"]["address"], CAROL)
            self.assertIn("doc-dexscreener-pairs", facts["document_evidence"])
            self.assertEqual(facts["controls"]["getters"]["launchFactory"]["decoded"]["address"], FACTORY)
            self.assertNotIn("address", facts["controls"]["getters"]["maxTxAmount"]["decoded"], "token amounts are not addresses")
            labels = {a["label"] for a in facts["architecture"]}
            self.assertIn("launchFactory", labels)
            self.assertIn("treasury", labels)
            self.assertNotIn("maxTxAmount", labels)
            self.assertNotIn("launchBlock", facts["controls"]["reverted_getters"], "absent ABI getters are not probed when an ABI exists")
            self.assertEqual(facts["controls"]["reverted_getters"], [])
            self.assertEqual(facts["pools"][0]["pair"], POOL)
            self.assertEqual(facts["pools"][0]["fee"], 3000)
            self.assertEqual(facts["pools"][0]["target_balance_pct_supply"], 20.0)
            self.assertEqual(facts["balances"]["dead"]["pct_supply"], 30.0)
            self.assertEqual(facts["creation"]["tx"], CREATION_TX)
            self.assertEqual(facts["receipts"][0]["nfpm_position_ids"], [7])
            self.assertEqual(facts["positions"][0]["owner"], LOCKER)
            self.assertEqual(facts["positions"][0]["pct_of_pool_active_liquidity"], 40.0)
            self.assertEqual([q["size_tokens"] for q in facts["quotes"]], [100, 10000, 100000])
            self.assertTrue(all(q["amount_out_raw"] for q in facts["quotes"]))
            self.assertEqual(facts["source"]["status"], "sources_unavailable")
            self.assertEqual(facts["discovery"]["explorer"]["holders"], "1234")
            names = {c["name"] for c in facts["collections"]}
            self.assertEqual(names, {"phase1", "phase2", "phase3", "phase4"})
            statuses = {c["name"]: c["status"] for c in facts["collections"]}
            self.assertEqual(statuses["phase1"], "complete", "with a verified ABI only existing getters are probed")
            self.assertEqual({statuses[n] for n in ("phase2", "phase3", "phase4")}, {"complete", "partial"})
            self.assertEqual([p["phase"] for p in status["phases"]], ["intake", "discovery", "phase1", "phase2", "phase3", "phase4", "facts"])
            headers = sum(1 for c in rpc.calls if c["method"] == "eth_getBlockByNumber")
            self.assertLessEqual(headers, 12, "four phases share one pin plus two historical pins (creation, sale)")
            # Depth collected without any coordinator turn: reserves, top holders, a verified sale, creator activity, maturity.
            self.assertEqual(facts["pools"][0]["counter_balance_raw"], 5 * 10 ** 18)
            self.assertEqual(facts["pools"][0]["counter_balance"], "5")
            top = {h["address"]: h for h in facts["top_holders"]}
            self.assertIn(ALICE, top)
            self.assertEqual(top[ALICE]["pct_supply"], 5.0)
            self.assertEqual(top[ALICE]["code_bytes"], 0, "an externally owned account has no code")
            self.assertEqual(top[ALICE]["account_kind"], "no_code")
            self.assertEqual(facts["holder_summary"]["read_count"], len(top))
            self.assertIn(DEAD, facts["holder_selection"]["excluded_addresses"])
            self.assertEqual(len(rpc.calls), 78, "holder arithmetic and delivery preservation add no RPC requests")
            self.assertEqual(status["started_attempts"], 87, "no extra discovery requests or session charges")
            self.assertNotIn(DEAD, top, "already-read balances are not re-read")
            self.assertEqual(facts["indexed"]["counters"], {"holders_count": 1234, "transfers_count": 98765})
            self.assertEqual(facts["indexed"]["sale_candidates"], [SELL_TX])
            self.assertEqual(len(facts["sales"]), 1)
            sale = facts["sales"][0]
            self.assertTrue(sale["verified"], sale)
            self.assertEqual((sale["seller"], sale["pool"], sale["amount_raw"]), (ALICE, POOL, 5 * 10 ** 21))
            self.assertEqual(sale["received"][0]["asset"], QUOTE)
            self.assertEqual([r["role"] for r in facts["receipts"]], ["creation", "sale_candidate"])
            self.assertEqual(facts["creation"]["signer"], CAROL)
            self.assertEqual(facts["creator_activity"]["calls_to_launch_factory"], 2)
            self.assertEqual(facts["creator_activity"]["target_outbound"], 1)
            self.assertEqual(facts["maturity"]["holders_count"], 1234)
            self.assertEqual(facts["maturity"]["launch_block"], 90)
            self.assertIn("age_days", facts["maturity"])
            self.assertIn("sale-verified", summary_lines(facts).__str__())
            self.assertIn("doc-explorer-signer-transactions", facts["document_evidence"])
            draft = read_draft(root / "draft")
            self.assertEqual(len(draft["collections"]), 4)
            self.assertEqual(preflight(root / "draft")["errors"], [])
            summary = " ".join(summary_lines(facts))
            self.assertIn("[pool1-*]", summary)
            self.assertIn("[bal-dead]", summary)
            self.assertIn("[quote-100]", summary)
            text = brief(root, "liquidity", 4)
            self.assertIn(TOKEN, text)
            self.assertIn("notes/liquidity.json", text)
            self.assertNotIn("{{", text)

    def test_compose_note_reaches_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, _, _ = self.run_pipeline(root)
            receipt_alias = facts["receipts"][0]["evidence"]
            (root / "lanes" / "liquidity").mkdir(parents=True)
            fake_fetch([{"id": "explorer-holders", "url": "https://explorer.invalid/holders", "purpose": "holders"}], root / "lanes" / "liquidity")
            lane_note = {"note_schema_version": 1, "lane": "liquidity", "requests_used": 1, "findings": [
                {"id": "holders-table", "dimension": "current_concentration", "topic": "token_economics", "signal": "Good", "claim": "state_observation",
                 "strength": "strongly_supported", "confidence": "medium", "impact": "neutral",
                 "text": "SYNTHETIC: dead address holds 30% and the canonical pool 20% of supply at the pin; the explorer table lists 1,234 holders.",
                 "evidence": ["bal-dead", "bal-pool1", "explorer-holders"]}],
                "coverage": {"current_concentration": {"status": "partial", "gap": "SYNTHETIC: beneficial ownership beyond the explorer table is unknown",
                                                       "priority": "material", "decision_impact": "SYNTHETIC: cannot rank every large holder",
                                                       "attempts": [{"check": "Explorer holder table", "outcome": "Loaded", "evidence": ["explorer-holders"]}],
                                                       "boundary": "unavailable", "basis": "SYNTHETIC: the explorer publishes a capped table only"}}}
            write_new(root / "notes" / "liquidity.json", lane_note)
            result = compose(root / "draft", root / "notes" / "liquidity.json", lane="liquidity")
            self.assertEqual(result["errors"], [], result)
            self.assertEqual(result["registered_captures"], ["doc-liquidity-explorer-holders"])
            checked = {d: {"status": "checked"} for d in ("token_controls", "canonical_lp_principal_custody", "side_pool_removal_risk",
                                                            "sellability_exit_depth", "historical_launch_integrity", "admin_treasury_reward_custody",
                                                            "external_dependencies", "development_disclosure")}
            coordinator = {"note_schema_version": 1, "lane": "coordinator", "findings": [
                {"id": "token-controls", "dimension": "token_controls", "topic": "token_and_liquidity", "signal": "Good", "claim": "state_observation",
                 "strength": "strongly_supported", "confidence": "high", "impact": "benefit",
                 "text": "SYNTHETIC: owner() is zero, paused() is false and the EIP-1967 slots are empty at the pin.",
                 "evidence": ["runtime", "token-owner", "token-paused", "token-eip1967-implementation"]},
                {"id": "locked-position", "dimension": "canonical_lp_principal_custody", "topic": "token_and_liquidity", "signal": "Good", "claim": "state_observation",
                 "strength": "strongly_supported", "confidence": "medium", "impact": "benefit", "subject": POOL,
                 "text": "SYNTHETIC: position 7 owned by the locker supplies 40% of active pool liquidity with no approval set.",
                 "evidence": ["pool1-liquidity", "pos-7-positions", "pos-7-ownerOf", "pos-7-getApproved", "pool1-runtime"]},
                {"id": "single-pool", "dimension": "side_pool_removal_risk", "claim": "state_observation", "strength": "strongly_supported", "confidence": "medium",
                 "impact": "neutral", "subject": POOL, "text": "SYNTHETIC: one indexed pool; no side pools were discovered.", "evidence": ["pool1-token0", "pool1-token1", "doc-dexscreener-pairs"]},
                {"id": "quotes", "dimension": "sellability_exit_depth", "topic": "token_and_liquidity", "signal": "Good", "claim": "state_observation",
                 "strength": "strongly_supported", "confidence": "medium", "impact": "benefit", "subject": QUOTER,
                 "text": "SYNTHETIC: read-only quotes returned for 100, 10,000 and 100,000 tokens with small size impact.",
                 "evidence": ["quote-100", "quote-10000", "quote-100000", "quote-quoter-runtime"]},
                {"id": "launch-receipt", "dimension": "historical_launch_integrity", "topic": "creator_trading_and_proceeds", "signal": "Good",
                 "claim": "historical_execution", "strength": "proven_fact", "confidence": "high", "impact": "neutral",
                 "text": "SYNTHETIC: the creation transaction succeeded and minted the supply to the creator.",
                 "evidence": [receipt_alias], "execution": {"receipt_evidence_id": None, "result": "success", "effects": []}},
                {"id": "factory-owner", "dimension": "admin_treasury_reward_custody", "claim": "state_observation", "strength": "strongly_supported", "confidence": "medium",
                 "impact": "neutral", "subject": FACTORY, "text": "SYNTHETIC: the launch factory has code and no owner() getter.",
                 "evidence": ["arch-launchFactory-runtime", "arch-launchFactory-owner#failed_attempt"]},
                {"id": "quote-asset", "dimension": "external_dependencies", "claim": "state_observation", "strength": "strongly_supported", "confidence": "medium",
                 "impact": "neutral", "subject": QUOTE, "text": "SYNTHETIC: the quote asset has code, 18 decimals and an empty implementation slot.",
                 "evidence": ["arch-quote-" + QUOTE[2:10] + "-runtime", "quote-" + QUOTE[2:10] + "-decimals"]},
                {"id": "source-lookup", "dimension": "development_disclosure", "topic": "real_work_vs_marketing", "signal": "Potential Risk", "claim": "inference",
                 "strength": "inference", "confidence": "medium", "impact": "adverse", "severity": "low",
                 "text": "SYNTHETIC: Sourcify lists a compilation but publishes no sources; correspondence could not be established.",
                 "evidence": ["runtime", "sourcify-correspondence"],
                 "concern": {"basis": "adverse_inference", "mechanism": "Deployed behavior cannot be checked against published source", "consequence": "Holders rely on bytecode inspection only"}},
                {"id": "no-rewards", "dimension": "reward_accounting_liveness", "claim": "state_observation", "strength": "strongly_supported", "confidence": "medium",
                 "impact": "neutral", "text": "SYNTHETIC: no reward or vault contract appears in the architecture reads.", "evidence": ["runtime", "token-launchFactory"]},
                {"id": "no-redemption", "dimension": "utility_redemption_rights", "claim": "state_observation", "strength": "strongly_supported", "confidence": "medium",
                 "impact": "neutral", "text": "SYNTHETIC: the token promises no redemption; none is coded.", "evidence": ["runtime", "metadata-total_supply"]}],
                "coverage": {**checked, "reward_accounting_liveness": {"status": "not_applicable", "outcome": "SYNTHETIC: no reward mechanism exists"},
                             "utility_redemption_rights": {"status": "not_applicable", "outcome": "SYNTHETIC: no redemption right exists"}},
                "decision": {"verdict": {"kind": "findings_with_limits", "scope": "SYNTHETIC general diligence"},
                             "synthesis": {"technical_exposure": "SYNTHETIC technical conclusion.", "credibility_maturity": "SYNTHETIC credibility conclusion.",
                                           "token_economics": "SYNTHETIC economics conclusion.", "research_confidence": "SYNTHETIC confidence conclusion."},
                             "actions": []},
                "text": {"verdict": "SYNTHETIC verdict text.", "main_reasons": "SYNTHETIC reasons.", "strongest_contrary_evidence": "SYNTHETIC contrary.",
                         "unresolved_questions": "SYNTHETIC unresolved.", "change_evidence": "SYNTHETIC change."}}
            receipt_row = next(e for e in read_draft(root / "draft")["evidence"] if (e.get("collection_provenance") or {}).get("evidence_id") == receipt_alias)
            coordinator["findings"][4]["execution"]["receipt_evidence_id"] = receipt_row["id"]
            coordinator["findings"][4]["execution"]["effects"] = [{"kind": "erc20_transfer", "log_index": 0, "asset_scope_id": "target",
                                                                   "from_scope_id": "factory", "to_scope_id": "creator", "amount_raw": str(10 ** 26), "units": "raw_token_units"}]
            coordinator["scope"] = [{"id": "creator", "address": CAROL, "roles": ["creator and initial recipient"]},
                                    {"id": "factory", "address": FACTORY, "roles": ["launch factory"]}]
            coordinator["findings"][4]["evidence"] += ["actor-creator", "arch-launchFactory-runtime"]
            write_new(root / "notes" / "coordinator.json", coordinator)
            result = compose(root / "draft", root / "notes" / "coordinator.json")
            self.assertEqual(result["errors"], [], result)
            self.assertEqual(result["remaining_surfaces"], [])
            out = freeze(root / "draft", root / "report", True)
            _, report = validate(out, True, out / "report.md")
            self.assertEqual(report["completion_status"], "complete")
            delivery = deliver(out, True)
            self.assertEqual(delivery["status"], "ready_for_final_delivery")
            self.assertEqual({r["dimension"] for r in delivery["reading_checklist"]}, set(DIMENSIONS))
            statuses = {r["id"]: r["status"] for r in report["ratings"]}
            self.assertEqual(statuses["token_controls"], "pass")
            self.assertEqual(statuses["current_concentration"], "unknown")
            self.assertEqual(statuses["development_disclosure"], "concern")
            self.assertEqual(statuses["reward_accounting_liveness"], "not_applicable")
            self.assertEqual({s["signal"] for s in report["summary"]}, {"Good", "Potential Risk"})
            self.assertEqual(report["decision_review"]["verdict"]["kind"], "findings_with_limits")
            self.assertIn("SYNTHETIC verdict text.", (out / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
