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

from backend_common import Cache, read_json, canonical, write_new
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
SAFE = "0xb234567890abcdef1234567890abcdef12345678"
MODULE = "0xc234567890abcdef1234567890abcdef12345678"
GUARD = "0xd234567890abcdef1234567890abcdef12345678"
GUARD_SLOT = "0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8"  # keccak256("guard_manager.guard.address")
DEAD = "0x000000000000000000000000000000000000dead"
CREATION_TX = hh("SYNTHETIC creation transaction")
SELL_TX = hh("SYNTHETIC sale transaction")
SWAP_V3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
SUPPLY = 10 ** 27
REGISTRY = {"dexscreener": "synthetic", "geckoterminal": "synthetic", "explorers": [{"name": "Synthetic explorer", "base": "https://explorer.invalid", "api_v2": True}],
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
                     selector("paused()"): abi(0), selector("launchFactory()"): word_address(FACTORY), selector("locker()"): word_address(LOCKER),
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
        if to == LOCKER:
            table = {selector("owner()"): word_address(SAFE), selector("unlockTime()"): abi(2000000000), selector("beneficiary()"): word_address(SAFE)}
            return table.get(sel, {"error": {"code": 3, "message": "execution reverted"}})
        if to == SAFE:
            table = {selector("getOwners()"): abi(32) + abi(2)[2:] + word_address(ALICE)[2:] + word_address(BOB)[2:], selector("getThreshold()"): abi(2),
                     selector("getModulesPaginated(address,uint256)"): abi(64) + abi(1)[2:] + abi(1)[2:] + word_address(MODULE)[2:]}
            return table.get(sel, {"error": {"code": 3, "message": "execution reverted"}})
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
            result = "0x60006000f3" if params[0] in (TOKEN, POOL, QUOTE, NFPM, QUOTER, FACTORY, LOCKER, SAFE, MODULE, GUARD) else "0x"
        elif method == "eth_call":
            result = self.call(params[0]["to"], params[0]["data"])
        elif method == "eth_getStorageAt":
            result = word_address(GUARD) if params[0] == SAFE and params[1].lower() == GUARD_SLOT else abi(0)
        elif method == "eth_getLogs":
            increase = topic("IncreaseLiquidity(uint256,uint128,uint256,uint256)")
            result = [{"address": NFPM, "topics": [increase, abi(7)], "data": "0x", "blockNumber": hex(90), "blockHash": hh(90), "transactionHash": CREATION_TX, "transactionIndex": "0x0", "logIndex": "0x2", "removed": False},
                      {"address": NFPM, "topics": [increase, abi(15)], "data": "0x", "blockNumber": hex(92), "blockHash": hh(92), "transactionHash": hh("liquidity add"), "transactionIndex": "0x0", "logIndex": "0x0", "removed": False}]
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
                    "deployment": {"transactionHash": CREATION_TX, "blockNumber": "90", "transactionIndex": "0", "deployer": CAROL},
                    "abi": [{"type": "function", "name": "launchFactory", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "maxTxAmount", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
                            {"type": "function", "name": "treasury", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "locker", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "owner", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
                            {"type": "function", "name": "paused", "inputs": [], "outputs": [{"type": "bool"}], "stateMutability": "view"},
                            {"type": "function", "name": "transfer", "inputs": [{"type": "address"}], "outputs": [], "stateMutability": "nonpayable"}]}
        elif item["id"] in ("explorer-address", "explorer-address-retry"):
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
        elif item["id"] == "goplus-token-security":
            body = {"code": 1, "message": "OK", "result": {TOKEN: {"holder_count": "36949", "lp_holder_count": "159", "is_honeypot": "0", "is_mintable": "0", "is_proxy": "0", "is_open_source": "1",
                     "transfer_pausable": "0", "is_blacklisted": "0", "buy_tax": "0", "sell_tax": "0", "owner_address": "", "creator_address": CAROL,
                     "holders": [{"address": ALICE, "tag": "", "is_contract": 0, "is_locked": 0, "percent": "0.05", "balance": "50000"}, {"address": "0x" + "77" * 20, "tag": "", "is_contract": 1, "is_locked": 0, "percent": "0.01", "balance": "10000"}],
                     "lp_holders": [{"address": LOCKER, "tag": "", "is_contract": 1, "is_locked": 0, "percent": "0.594481", "value": "1384506.2", "NFT_list": [{"NFT_id": "7", "amount": "1", "in_effect": "1"}]},
                                    {"address": BOB, "tag": "", "is_contract": 0, "is_locked": 1, "percent": "0.096", "value": "223801.4", "NFT_list": [{"NFT_id": "12", "amount": "1", "in_effect": "1"}], "locked_detail": [{"end_time": "2030-01-01", "opt_token": "x", "amount": "1"}]}],
                     "dex": [{"liquidity_type": "UniV3", "name": "UniswapV3", "liquidity": "3233675.8", "pool_fee": "0.01", "pair": POOL}]}}}
        elif item["id"] == "geckoterminal-trades":
            body = {"data": [{"id": "t1", "type": "trade", "attributes": {"tx_hash": SELL_TX, "kind": "sell", "block_number": 95, "tx_from_address": ALICE}},
                             {"id": "t2", "type": "trade", "attributes": {"tx_hash": "0x" + "ee" * 32, "kind": "buy", "block_number": 96, "tx_from_address": BOB}}]}
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
    def run_pipeline(self, root, rpc=None, queue=False, headroom=None, reserve=0, presets=None, fetch=None):
        session = Investigation.create(root / "session.sqlite", 200, 600, request_ceiling=300, timeout_ceiling=900, limit_basis="analyst_safety")
        cache = Cache(root / "cache.sqlite")
        rpc = rpc or PipelineRpc()
        try:
            intake(root / "draft", {"chain_id": CHAIN, "address": TOKEN}, "Synthetic pipeline question", "All authority material", True)
            pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "Synthetic pipeline question", "All authority material",
                                rpc, session, cache, "synthetic", fetch=fetch or fake_fetch, synthetic=True, registry=REGISTRY)
            facts = pipeline.run_all()
            if queue:  # what main() does after the lane charges: start runs its own queue and rewrites the facts
                from broad_collect import run_recommended, remaining_recommendations
                if presets is not None:
                    facts["recommended_presets"] = presets
                ran, _ = run_recommended(root, pipeline, session, facts, reserve=reserve, **({"headroom": headroom} if headroom is not None else {}))
                facts["presets_run"] = ran
                facts["recommended_presets"] = remaining_recommendations(root, facts, ran)
                (root / "facts.json").write_bytes(canonical(facts))
                (root / "recommended-presets.json").write_bytes(canonical(facts["recommended_presets"]))
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
            self.assertEqual(names, {"phase1", "phase2", "phase3", "phase4", "phase4b"})  # phase4b: custodian getters for owners with code
            statuses = {c["name"]: c["status"] for c in facts["collections"]}
            self.assertEqual(statuses["phase1"], "complete", "with a verified ABI only existing getters are probed")
            self.assertTrue({statuses[n] for n in ("phase2", "phase3", "phase4")} <= {"complete", "partial"}, statuses)  # reverted probes keep a phase partial, never failed
            self.assertEqual([p["phase"] for p in status["phases"]], ["intake", "discovery", "phase1", "phase2", "phase3", "phase4", "facts"])
            headers = sum(1 for c in rpc.calls if c["method"] == "eth_getBlockByNumber")
            self.assertLessEqual(headers, 14, "five collections share one pin plus two historical pins (creation, sale)")
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
            self.assertEqual(len(rpc.calls), 102, "holder arithmetic and delivery preservation add no RPC requests (102 = 78 + locker() and its two architecture reads + seven Safe reads + eleven custodian getters + the second phase-4 collection's pin reads)")
            self.assertEqual(status["started_attempts"], 113, "no extra discovery requests or session charges (113: the 102 pipeline reads plus ten discovery captures and pin charges)")
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
            self.assertEqual(len(draft["collections"]), 5)  # four phases plus the custodian-getter collection
            self.assertEqual(preflight(root / "draft")["errors"], [])
            summary = " ".join(summary_lines(facts))
            self.assertIn("[pool1-*]", summary)
            self.assertIn("[bal-dead]", summary)
            self.assertIn("[quote-100]", summary)
            text = brief(root, "liquidity", 4)
            self.assertIn(TOKEN, text)
            self.assertIn("notes/liquidity.json", text)
            self.assertNotIn("{{", text)

    def test_pipeline_reads_safe_modules_guard_and_custodian_getters_and_recommends_only_what_remains(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root)
            # The locker named by the token is an architecture contract whose owner is a Safe: signers, threshold, module page and guard slot are read.
            safe = facts["owners"]["locker"]
            self.assertEqual((safe["address"], safe["safe_threshold"], safe["safe_owners"]), (SAFE, 2, [ALICE, BOB]))
            self.assertEqual((safe["safe_modules"], safe["safe_guard"], safe["safe_guard_read"]), ([MODULE], GUARD, True))
            self.assertNotIn("getModulesPaginated", safe["reverted"])
            # The position custodian's withdrawal getters are read by the pipeline itself; reverts are recorded answers.
            custodian = next(a for a in facts["actors"].values() if a.get("role") == "position_custodian")
            self.assertEqual(custodian["address"], LOCKER)
            self.assertEqual(custodian["getters"]["unlockTime"]["decoded"]["int"], 2000000000)
            self.assertEqual(custodian["getters"]["beneficiary"]["decoded"]["address"], SAFE)
            self.assertIn("unlockDate", custodian["reverted"])
            summary = "\n".join(summary_lines(facts))
            self.assertIn(f"modules=['{MODULE}'] guard={GUARD}", summary)
            self.assertIn("custodian-getters", summary)
            # One position covers 40% of active liquidity, so a bounded launch-window log scan is the only preset left to recommend.
            queue = facts["recommended_presets"]
            self.assertEqual([q["preset"] for q in queue], ["positions", "logs"])  # GoPlus lists an unread LP position first, then the bounded scan
            self.assertIn("--preset logs --contract " + NFPM + " --topic ", queue[1]["command"])
            self.assertIn("--from-block 90 --to-block " + str(facts["pin"]["number"]), queue[1]["command"])
            self.assertIn("launch window", queue[1]["reason"])
            self.assertIn("token_ids the logs rows print", queue[1]["then"])
            self.assertIn("recommended preset 2 [canonical_lp_principal_custody]", summary)
            self.assertEqual(read_json(root / "recommended-presets.json"), queue)
            self.assertEqual(set(read_json(root / "work-plan.json")), {"surfaces", "overhead_requests", "contingency_requests", "seconds_required"}, "the work plan keeps the validator's shape")
            from pipeline_note import _owners_text, write_and_compose
            self.assertIn("getModulesPaginated() lists 1 module (" + MODULE + "); guard slot " + GUARD, _owners_text(safe))
            write_and_compose(root)
            note = read_json(root / "notes" / "pipeline.json")
            custody = next(f for f in note["findings"] if f["id"] == "pipeline-launch-position-custody")
            self.assertIn("unlockTime() = 2000000000", custody["text"])
            self.assertIn("beneficiary() = " + SAFE, custody["text"])
            self.assertTrue(any(str(e).endswith("-unlockTime") for e in custody["evidence"]), custody["evidence"])

    def test_indexer_listed_sell_is_probed_when_the_explorer_names_no_sale(self):
        def fetch_without_transfers(items, out):
            records = fake_fetch(items, out)
            for r in records:
                if r["id"] == "explorer-transfers" and r.get("raw"):
                    (Path(out) / r["raw"]).write_bytes(json.dumps({"items": []}).encode())
            return records
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            session = Investigation.create(root / "session.sqlite", 200, 600, request_ceiling=300, timeout_ceiling=900, limit_basis="analyst_safety")
            cache = Cache(root / "cache.sqlite")
            try:
                intake(root / "draft", {"chain_id": CHAIN, "address": TOKEN}, "q", "m", True)
                pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "q", "m", PipelineRpc(), session, cache, "synthetic", fetch=fetch_without_transfers, synthetic=True, registry=REGISTRY)
                facts = pipeline.run_all()
            finally:
                cache.close()
                session.close()
            self.assertEqual(facts["indexed"]["recent_transfers_captured"], 0)
            self.assertEqual((facts["discovery"]["geckoterminal"]["status"], facts["discovery"]["geckoterminal"]["sells"]), ("ok", 1))
            self.assertEqual(facts["indexed"]["sale_candidates"], [SELL_TX])
            self.assertEqual(facts["indexed"]["indexed_sells"], [SELL_TX])
            self.assertTrue(any(s.get("verified") for s in facts["sales"]), facts["sales"])
            self.assertNotIn("receipts", [q["preset"] for q in facts["recommended_presets"]])

    def test_indexed_trades_fill_remaining_slots_and_fail_quietly(self):
        from broad_collect import recommended_presets
        def build(tmp, registry, fetch, prefilled=()):
            root = Path(tmp) / "run"
            root.mkdir()
            session = Investigation.create(root / "session.sqlite", 200, 600, request_ceiling=300, timeout_ceiling=900, limit_basis="analyst_safety")
            cache = Cache(root / "cache.sqlite")
            try:
                pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "q", "m", PipelineRpc(), session, cache, "synthetic", fetch=fetch, synthetic=True, registry=registry)
                pipeline.pairs = [{"pair": POOL, "is_pool_id": False, "version": "v3"}]
                pipeline.sell_candidates = list(prefilled)
                (root / "discovery").mkdir()
                pipeline.capture_indexed_trades(root / "discovery")
                return pipeline
            finally:
                cache.close()
                session.close()
        other_sell = "0x" + "cd" * 32
        def feed(items, out):
            path = Path(out) / "trades.json"
            path.write_text(json.dumps({"data": [{"type": "trade", "attributes": {"tx_hash": other_sell, "kind": "sell", "block_number": 99, "tx_from_address": BOB}},
                                                 {"type": "trade", "attributes": {"tx_hash": "0x" + "ab" * 32, "kind": "sell", "block_number": 98}},
                                                 {"type": "trade", "attributes": {"tx_hash": "bad", "kind": "sell", "block_number": 97}}]}))
            return [{"id": items[0]["id"], "url": items[0]["url"], "http_status": 200, "raw": "trades.json", "captured_at_utc": "now", "bytes": path.stat().st_size}]
        with tempfile.TemporaryDirectory() as tmp:
            # The explorer named two transfers; the most recent listed sell replaces the second one.
            pipeline = build(tmp, REGISTRY, feed, prefilled=["0x" + "11" * 32, "0x" + "22" * 32])
            self.assertEqual(pipeline.sell_candidates, ["0x" + "11" * 32, other_sell])
            self.assertEqual((pipeline.discovery["geckoterminal"]["status"], pipeline.discovery["geckoterminal"]["sells"]), ("ok", 2))
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = build(tmp, REGISTRY, lambda items, out: [{"id": items[0]["id"], "url": items[0]["url"], "http_status": 429, "failure_category": "throttled", "captured_at_utc": "now"}])
            self.assertEqual((pipeline.discovery["geckoterminal"]["status"], pipeline.sell_candidates, pipeline.indexed_trades), ("throttled", [], []))
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = build(tmp, {k: v for k, v in REGISTRY.items() if k != "geckoterminal"}, feed)
            self.assertEqual(pipeline.discovery["geckoterminal"]["status"], "no_geckoterminal_network_in_registry")
        # Unprobed listed sells become a receipts recommendation only while no sale is verified.
        facts = {"pin": {"number": 97}, "pools": [], "architecture": [], "positions": [], "sales": [], "receipts": [{"tx": other_sell}],
                 "indexed": {"sale_candidates": [other_sell], "indexed_sells": [other_sell, "0x" + "ab" * 32, "0x" + "ac" * 32, "0x" + "ad" * 32]}}
        queue = recommended_presets(facts)
        self.assertEqual([q["preset"] for q in queue], ["receipts"])
        self.assertIn("--tx 0x" + "ab" * 32 + ",0x" + "ac" * 32, queue[0]["command"])
        self.assertEqual(recommended_presets({**facts, "sales": [{"verified": True}]}), [])

    def test_goplus_claims_are_cross_checked_and_unread_lp_positions_are_recommended_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root)
            g = facts["goplus"]
            self.assertEqual((g["status"], g["holder_count"], g["lp_holder_count"], g["evidence"]), ("ok", 36949, 159, "doc-goplus-token-security"))
            self.assertEqual(g["flags"]["is_honeypot"], False)
            self.assertEqual(g["flags"]["is_open_source"], True)
            self.assertEqual([(r["address"], r["share_pct"], r["is_locked"], r["nft_ids"], r["verified"]) for r in g["lp_holders"]],
                             [(LOCKER, 59.4481, False, [7], True), (BOB, 9.6, True, [12], False)])
            self.assertEqual(g["lp_holders"][0]["verified_positions"][0]["id"], 7)
            self.assertEqual((g["lp_holders_verified"], g["holders_verified"], g["unread_lp_nft_ids"]), (1, 1, [12]))
            self.assertTrue(g["holders"][0]["verified"] and g["holders"][0]["sample_pct_supply"] is not None)
            self.assertIn("doc-goplus-token-security", facts["document_evidence"])
            queue = facts["recommended_presets"]
            self.assertEqual(queue[0]["preset"], "positions")
            self.assertIn("--preset positions --ids 12", queue[0]["command"])
            summary = "\n".join(summary_lines(facts))
            self.assertIn("goplus [doc-goplus-token-security] holders=36949", summary)
            self.assertIn("goplus-lp-holders:", summary)
            from pipeline_note import write_and_compose
            write_and_compose(root)
            note = read_json(root / "notes" / "pipeline.json")
            texts = {f["id"]: f["text"] for f in note["findings"]}
            self.assertIn("GoPlus counts 159 LP holders and lists 2", texts["pipeline-launch-position-custody"])
            self.assertIn("verified as position 7", texts["pipeline-launch-position-custody"])
            self.assertIn("GoPlus corroboration", texts["pipeline-token-controls"])
            self.assertIn("GoPlus lists 36949 holders", texts["pipeline-holder-distribution"])
            self.assertTrue(all("doc-goplus-token-security" in f["evidence"] for f in note["findings"] if f["id"] in ("pipeline-launch-position-custody", "pipeline-token-controls", "pipeline-holder-distribution")))

    def test_goplus_unread_ids_rank_by_share_and_failure_paths_stay_quiet(self):
        from broad_collect import goplus_facts, recommended_presets
        def goplus(lp_holders, **entry):
            return {"status": "ok", "evidence": "doc-goplus-token-security", "holders": [], "lp_holders": lp_holders, "dex": [], "flags": {}, **entry}
        nfts = lambda rows: [{"id": i, "share_pct": share, "amount": amount, "amount_known": amount != "", "in_effect": in_effect, "empty": amount == "0"} for i, share, amount, in_effect in rows]
        g = goplus([{"address": LOCKER, "share_pct": 59.0, "is_locked": False, "is_contract": True, "nft_ids": [7, 30, 40, 41], "nfts": nfts([(7, 50.0, "1", True), (30, 9.0, "1", True), (40, 0.0, "0", True), (41, 20.0, "5", False)])},
                    {"address": BOB, "share_pct": 12.0, "is_locked": True, "is_contract": False, "nft_ids": [12, 13, 14], "nfts": nfts([(12, 11.5, "1", True), (13, 0.5, "1", True), (14, None, "", True)])}])
        out = goplus_facts(g, [{"id": 7, "owner": LOCKER, "pct_of_pool_active_liquidity": 40.0}], [], {}, [{"pair": POOL, "read": "v3", "target_in_pool": True}])
        # Largest in-range share first, an unknown share last among in-range, the out-of-range position after them; the empty position 40 and the read position 7 are excluded.
        self.assertEqual(out["unread_lp_nft_ids"], [12, 30, 13, 14, 41])
        queue = recommended_presets({"pin": {"number": 97}, "pools": [], "architecture": [], "positions": [], "sales": [{"verified": True}], "goplus": out})
        self.assertEqual((queue[0]["preset"], queue[0]["command"].split("--ids ")[1]), ("positions", "12,30,13,14,41"))
        # Failure paths: every status is stated, nothing is queued, the summary names the status, the note says nothing about GoPlus.
        def build(tmp, fetch, web=True):
            root = Path(tmp) / "run"
            root.mkdir()
            session = Investigation.create(root / "session.sqlite", 200, 600, request_ceiling=300, timeout_ceiling=900, limit_basis="analyst_safety")
            cache = Cache(root / "cache.sqlite")
            try:
                pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "q", "m", PipelineRpc(), session, cache, "synthetic", fetch=fetch, synthetic=True, registry=REGISTRY, web=web)
                (root / "discovery").mkdir()
                pipeline.capture_goplus(root / "discovery")
                return pipeline
            finally:
                cache.close()
                session.close()
        def answering(body, http_status=200, failure=None):
            def fetch(items, out):
                path = Path(out) / "goplus.json"
                path.write_text(json.dumps(body))
                record = {"id": items[0]["id"], "url": items[0]["url"], "http_status": http_status, "raw": "goplus.json", "captured_at_utc": "now", "bytes": path.stat().st_size}
                if failure:
                    record["failure_category"] = failure
                return [record]
            return fetch
        cases = [({"code": 1, "message": "OK", "result": {}}, 200, None, "token_not_listed"),
                 ({"code": 4029, "message": "Request limit reached"}, 200, None, "api_4029:Request limit reached"),
                 ({}, 429, "throttled", "throttled"),
                 ({"code": 1, "message": "OK", "result": {TOKEN: {"holder_count": "5"}}}, 200, None, "ok")]
        for body, http_status, failure, expected in cases:
            with tempfile.TemporaryDirectory() as tmp:
                pipeline = build(tmp, answering(body, http_status, failure))
                self.assertEqual(pipeline.goplus["status"], expected, body)
                self.assertEqual(pipeline.discovery["goplus"]["status"], expected)
                facts = {"pin": None, "pools": [], "architecture": [], "positions": [], "sales": [],
                         "goplus": goplus_facts(pipeline.goplus, [], [], {}, []), "coverage_hint": {}, "collections": [], "metadata": {}, "controls": {}, "source": {}, "discovery": {}, "links": {"websites": [], "socials": []}, "quotes": [], "balances": {}, "owners": {}, "receipts": [], "elapsed_seconds": 0}
                self.assertEqual(recommended_presets(facts), [])
                summary = "\n".join(summary_lines(facts))
                self.assertIn("goplus", summary)
                if expected != "ok":
                    self.assertIn(f"goplus: {expected}", summary)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(build(tmp, answering({})).goplus["status"].startswith("api_"), "a body without a code is an API-shape status, never a fact")

    def test_positions_read_by_a_later_preset_verify_goplus_lp_holders_in_the_note(self):
        from pipeline_note import build_pipeline_note, positions_from_draft
        from bundle_assemble import read_draft
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root)
            self.assertEqual(facts["goplus"]["unread_lp_nft_ids"], [12])
            draft = read_draft(root / "draft")
            # A later positions preset read position 12: its ownerOf and positions rows sit in the draft like any evidence row.
            (root / "draft" / "evidence").mkdir(exist_ok=True)
            # Imported preset rows carry a collection prefix on the id and keep the alias in their provenance, like a real draft.
            owner_row = {"id": "c-abc123-positions-12-ownerOf", "kind": "rpc", "address": NFPM, "pin_id": "current", "query": {"method": "eth_call"}, "artifact": "evidence/positions-12-ownerOf.json", "observation_status": "ok",
                         "collection_provenance": {"artifact": "imports/c-abc123/collection.json", "evidence_id": "positions-12-ownerOf", "sha256": "0" * 64}}
            (root / "draft" / owner_row["artifact"]).write_text(json.dumps({"response": {"jsonrpc": "2.0", "id": "x", "result": word_address(BOB)}}))
            words = [0, 0, int(TOKEN, 16), int(QUOTE, 16), 3000, (-887220) % 2 ** 256, 887220, 5 * 10 ** 17, 0, 0, 0, 0]
            pos_row = {**owner_row, "id": "c-abc123-positions-12-positions", "artifact": "evidence/positions-12-positions.json", "collection_provenance": {**owner_row["collection_provenance"], "evidence_id": "positions-12-positions"}}
            (root / "draft" / pos_row["artifact"]).write_text(json.dumps({"response": {"jsonrpc": "2.0", "id": "y", "result": "0x" + "".join(format(w, "064x") for w in words)}}))
            draft["evidence"] += [owner_row, pos_row]
            later = positions_from_draft(root, draft, facts)
            self.assertEqual([(p["id"], p["owner"], p["liquidity"], p["pool"], p["source"]) for p in later], [(12, BOB, 5 * 10 ** 17, POOL, "preset")])
            pool = next(p for p in facts["pools"] if p["pair"] == POOL)
            self.assertEqual((later[0]["in_range"], later[0]["pct_of_pool_active_liquidity"]), (True, round(5 * 10 ** 17 / pool["liquidity"] * 100, 4)), "a full-range preset position gets start's own share arithmetic")
            note = build_pipeline_note(facts, draft, run=root)
            custody = next(f for f in note["findings"] if f["id"] == "pipeline-launch-position-custody")
            self.assertIn("verified as position 12", custody["text"])
            self.assertNotIn("Unread listed position ids", custody["text"])
            # A log scan also read a closed position (no liquidity, a pair no read pool has) whose id sorts first: it is counted, never
            # described as custody, and the finding stays anchored on the pool so the validator keeps it (the AI run dropped it).
            closed_owner = {**owner_row, "id": "c-abc123-positions-5-ownerOf", "artifact": "evidence/positions-5-ownerOf.json", "collection_provenance": {**owner_row["collection_provenance"], "evidence_id": "positions-5-ownerOf"}}
            (root / "draft" / closed_owner["artifact"]).write_text(json.dumps({"response": {"jsonrpc": "2.0", "id": "x", "result": word_address(CAROL)}}))
            closed_words = [0, 0, int(TOKEN, 16), int(ALICE, 16), 500, 0, 100, 0, 0, 0, 0, 0]
            closed_pos = {**owner_row, "id": "c-abc123-positions-5-positions", "artifact": "evidence/positions-5-positions.json", "collection_provenance": {**owner_row["collection_provenance"], "evidence_id": "positions-5-positions"}}
            (root / "draft" / closed_pos["artifact"]).write_text(json.dumps({"response": {"jsonrpc": "2.0", "id": "y", "result": "0x" + "".join(format(w, "064x") for w in closed_words)}}))
            draft["evidence"] += [closed_owner, closed_pos]
            later = positions_from_draft(root, draft, facts)
            self.assertEqual([(p["id"], p["pool"], p["liquidity"]) for p in later], [(5, None, 0), (12, POOL, 5 * 10 ** 17)])
            note = build_pipeline_note(facts, draft, run=root)
            custody = next(f for f in note["findings"] if f["id"] == "pipeline-launch-position-custody")
            self.assertTrue(custody["text"].startswith("Position 7 is owned by"), "start's own canonical-pool position still leads: " + custody["text"][:120])
            self.assertIn("Position 12 is owned by " + BOB, custody["text"])
            self.assertIn("1 further position(s) read (5) hold no liquidity and match no read pool: closed or emptied, not custody.", custody["text"])
            self.assertLess(custody["text"].index("Position 12"), custody["text"].index("1 further position(s)"), "closed positions are counted after the custody descriptions")
            self.assertNotIn("Position 5 is owned", custody["text"])
            self.assertTrue(custody.get("subject"), "anchored on a pool or custodian read at the pin")
            self.assertIn("positions-5-positions", custody["evidence"])
            # With every position closed (a drained pool after a rug) the emptied position and its owner are still the finding, anchored on the pool.
            drained = {**facts, "positions": [{**p, "pool": None, "liquidity": 0, "in_range": None, "pct_of_pool_active_liquidity": None} for p in facts["positions"]]}
            note = build_pipeline_note(drained, {**draft, "evidence": [e for e in draft["evidence"] if "positions-" not in json.dumps(e.get("collection_provenance"))]}, run=root)
            custody = next(f for f in note["findings"] if f["id"] == "pipeline-launch-position-custody")
            self.assertIn("Position 7 is owned by", custody["text"])
            self.assertIn("holds no liquidity (closed or emptied)", custody["text"])
            self.assertTrue(custody.get("subject"))

    def test_start_runs_the_recommended_queue_itself_and_chains_positions_from_the_log_scan(self):
        from pipeline_note import write_and_compose
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, queue=True)
            ran = facts["presets_run"]
            # The GoPlus-listed unread position first, then the launch-window scan, then the ids the scan printed that no read covered (7 was the pipeline's own).
            self.assertEqual([(r["preset"], r["status"]) for r in ran], [("positions", "complete"), ("logs", "complete"), ("positions", "complete")], ran)
            self.assertIn("--ids 12", ran[0]["command"])
            self.assertIn("--ids 15", ran[2]["command"])
            self.assertEqual(ran[2]["chained_from"], "launch window")
            self.assertTrue(all(r["collection"].startswith("preset-") and (root / r["collection"] / "collection.json").is_file() for r in ran), ran)
            self.assertEqual([r["decoded"] for r in ran[1]["rows"] if r["decoded"]], [{"logs": 2, "token_ids": [7, 15], "token_ids_total": 2}])
            self.assertEqual(facts["recommended_presets"], [], "a scan that did not close the coverage gap is the named limit, never re-queued")
            self.assertEqual(read_json(root / "recommended-presets.json"), [])
            self.assertEqual([p["phase"] for p in status["phases"]][-3:], ["preset_positions", "preset_logs", "preset_positions"])
            self.assertEqual(len(rpc.calls), 102 + 16, "three preset collections at the run's pin: each costs its chain check, pin header and recheck (3) plus its queries; the position manager's code read is a cache hit, so a one-position read is three calls and the scan one")
            summary = "\n".join(summary_lines(facts))
            self.assertIn("preset-run positions complete [preset-positions-", summary)
            self.assertIn("recommended presets: none remain; start ran its queue itself", summary)
            self.assertEqual(len(read_draft(root / "draft")["collections"]), 8)
            write_and_compose(root)
            custody = next(f for f in read_json(root / "notes" / "pipeline.json")["findings"] if f["id"] == "pipeline-launch-position-custody")
            self.assertIn("verified as position 12", custody["text"])
            self.assertNotIn("Unread listed position ids", custody["text"])
        # Without enough time before the deadline every row is deferred: the printed queue keeps the rows and says why.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, queue=True, headroom=10 ** 6)
            self.assertEqual([(r["preset"], r["status"]) for r in facts["presets_run"]], [("positions", "deferred"), ("logs", "deferred")])
            self.assertEqual([q["command"] for q in facts["recommended_presets"]], [r["command"] for r in facts["presets_run"]])
            self.assertTrue(all("params" in q for q in facts["recommended_presets"]), "a re-derived row keeps its structured request")
            self.assertEqual(len(rpc.calls), 102, "a deferred row costs nothing")
        # Too few requests after the lane charges defers every row before anything is sent, with the estimate named.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, queue=True, reserve=10 ** 6)
            self.assertEqual([r["status"] for r in facts["presets_run"]], ["deferred", "deferred"])
            self.assertIn("about 8 requests needed", facts["presets_run"][0]["reason"])
            self.assertEqual(len(rpc.calls), 102)
        # Listed ids beyond a six-id row stay offered after the queue; an id that was read or reverted is never offered again.
        from broad_collect import remaining_recommendations
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root)
            ran = [{"preset": "positions", "dimension": "canonical_lp_principal_custody", "status": "partial", "command": "c1", "params": {"preset": "positions", "ids": [1, 2, 3, 4, 5, 6]}}]
            listed = {**facts, "goplus": {**facts["goplus"], "unread_lp_nft_ids": [7, 8, 9, 10]}}
            self.assertEqual([q["params"]["ids"] for q in remaining_recommendations(root, listed, ran) if q["preset"] == "positions"], [[7, 8, 9, 10]])
            overlapping = {**facts, "goplus": {**facts["goplus"], "unread_lp_nft_ids": [3, 4, 7]}}
            self.assertEqual([q for q in remaining_recommendations(root, overlapping, ran) if q["preset"] == "positions"], [], "a reverted or partially read id is the named limit, not a narrower re-queue")
        # A positions row is trimmed to the ids the remaining requests can cover; the rest stay printed as a deferred row.
        three = [{"preset": "positions", "dimension": "canonical_lp_principal_custody", "command": 'collect --run "$RUN" --preset positions --ids 12,15,16',
                  "params": {"preset": "positions", "ids": [12, 15, 16]}, "reason": "synthetic"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, queue=True, presets=three, reserve=200 - 113 - 11)  # eleven requests left: two ids fit
            ran = facts["presets_run"]
            self.assertEqual([(r["preset"], r["status"], r["params"]["ids"]) for r in ran], [("positions", "deferred", [16]), ("positions", "complete", [12, 15])])
            self.assertEqual((ran[1]["trimmed_from"], ran[1]["command"]), (3, 'collect --run "$RUN" --preset positions --ids 12,15'))
            self.assertIn("1 of 3 ids did not fit the 11 requests", ran[0]["reason"])
            self.assertEqual([q["params"]["ids"] for q in facts["recommended_presets"] if q["preset"] == "positions"], [[16]])
            self.assertIn("trimmed from 3 ids to fit the remaining requests", "\n".join(summary_lines(facts)))
            self.assertLessEqual(len(rpc.calls), 102 + 11)
        # A receipts row is deferred before its block lookups are charged, and runs as a pinned receipt collection otherwise.
        receipts = [{"preset": "receipts", "dimension": "sellability_exit_depth", "command": 'collect --run "$RUN" --preset receipts --tx ' + SELL_TX,
                     "params": {"preset": "receipts", "tx": [SELL_TX]}, "reason": "synthetic"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, queue=True, headroom=10 ** 6, presets=receipts)
            self.assertEqual([(r["preset"], r["status"]) for r in facts["presets_run"]], [("receipts", "deferred")])
            self.assertEqual(len(rpc.calls), 102, "no block lookup is charged for a deferred receipts row")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, queue=True, presets=receipts)
            run = facts["presets_run"][0]
            self.assertEqual((run["preset"], run["status"], run["collection"].startswith("preset-receipts-")), ("receipts", "complete", True), run)
            self.assertEqual([c["method"] for c in rpc.calls[102:]].count("eth_getTransactionReceipt"), 1, "the uncached block lookup; the pinned receipt read is a cache hit from the pipeline's own sale probe")
            self.assertEqual([q["preset"] for q in facts["recommended_presets"]], ["positions", "logs"], "the rows the override left unrun are re-derived; the receipts row is not")

    def test_position_custodian_is_matched_by_address_when_a_receipt_names_it_first(self):
        class LockerToRpc(PipelineRpc):
            def sale_receipt(self):
                return {**super().sale_receipt(), "to": LOCKER}
            def __call__(self, request):
                response = super().__call__(request)
                if request["method"] == "eth_getTransactionByHash" and request["params"][0] == SELL_TX:
                    response["result"]["to"] = LOCKER
                return response
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, rpc=LockerToRpc())
            custodians = [a for a in facts["actors"].values() if a.get("role") == "position_custodian"]
            self.assertEqual([a["address"] for a in custodians], [LOCKER])
            self.assertEqual(custodians[0]["getters"]["unlockTime"]["decoded"]["int"], 2000000000)

    def test_creation_transaction_survives_an_explorer_outage(self):
        def failing(fail_ids, status=500, category="server_error", rewrite=None):
            def fetch(items, out):
                records = fake_fetch([i for i in items if i["id"] not in fail_ids], out)
                for i in items:
                    if i["id"] in fail_ids:
                        records.append({"id": i["id"], "url": i["url"], "final_url": i["url"], "purpose": i.get("purpose"), "http_status": status, "captured_at_utc": "2026-01-01T00:00:00Z",
                                        "failure_category": category, "content_type": "text/plain", "host": "synthetic.invalid", "raw": None, "bytes": 0, "sha256": None})
                if rewrite:
                    rewrite(out)
                return records
            return fetch
        # Healthy explorer: the creation comes from its address page, nothing is retried, and the request count is unchanged.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root)
            self.assertEqual((facts["creation"]["tx"], facts["creation"]["tx_source"], facts["creation"]["creator"]), (CREATION_TX, "explorer_address", CAROL))
            self.assertNotIn("retry", facts["discovery"]["explorer"])
            self.assertEqual(status["started_attempts"], 113)
        # A transient 500 on the address page: one retry after the pause recovers the creation and the run proceeds unchanged.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, fetch=failing({"explorer-address"}))
            ex = facts["discovery"]["explorer"]
            self.assertEqual((ex["status"], ex["first_attempt"], ex["retry"], ex.get("retried")), ("ok", "server_error", "ok", True))
            self.assertEqual((facts["creation"]["tx"], facts["creation"]["tx_source"], facts["creation"]["creator"]), (CREATION_TX, "explorer_address_retry", CAROL))
            self.assertEqual(status["started_attempts"], 114, "the retry is one charged discovery request")
            self.assertEqual(len(rpc.calls), 102)
        # The explorer down for both attempts: Sourcify's deployment record names the creation transaction, so the creation receipt,
        # the launch signer, the custodian probe and the launch-window scan all survive; the explorer's creator field stays unknown.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, fetch=failing({"explorer-address", "explorer-address-retry"}))
            ex = facts["discovery"]["explorer"]
            self.assertEqual((ex["status"], ex["retry"], ex["creation_from"], ex.get("retried")), ("server_error", "server_error", "sourcify_deployment", None))
            c = facts["creation"]
            self.assertEqual((c["tx"], c["tx_source"], c.get("creator"), c["deployer"], c["signer"]), (CREATION_TX, "sourcify_deployment", None, CAROL, CAROL))
            self.assertEqual(facts["discovery"]["sourcify"]["deployment_block"], 90)
            self.assertEqual(status["started_attempts"], 113, "one retry; no explorer creator balance to read")
            self.assertEqual([r["role"] for r in facts["receipts"]][:1], ["creation"])
            summary = "\n".join(summary_lines(facts))
            self.assertIn(f"creation: tx={CREATION_TX} source=sourcify_deployment creator=None signer={CAROL} deployer={CAROL} (Sourcify", summary)
            self.assertIn(CAROL + " (deployer per Sourcify's deployment record", brief(root, "project", 4))
            from pipeline_note import write_and_compose
            write_and_compose(root)
            launch = next(f for f in read_json(root / "notes" / "pipeline.json")["findings"] if f["id"] == "pipeline-launch-execution")
            self.assertIn("named by Sourcify's deployment record because the explorer named none; the explorer's creator field is unknown", launch["text"])
            self.assertIn("sourcify-correspondence", launch["evidence"], "the Sourcify capture is cited by its registered evidence id")
            self.assertEqual([p["id"] for p in facts["positions"]], [7])
            self.assertEqual([a["address"] for a in facts["actors"].values() if a.get("role") == "position_custodian"], [LOCKER])
            self.assertIn("phase4b", {col["name"] for col in facts["collections"]})
            self.assertTrue(any("launch window" in q["reason"] for q in facts["recommended_presets"] if q["preset"] == "logs"))
            self.assertEqual(facts["discovery"]["sourcify"]["deployment_tx"], CREATION_TX)
        # A rate limit is transient too (the fetcher reports it as throttled); a 404 or a DNS failure is not, so no retry is spent and Sourcify supplies the creation.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, fetch=failing({"explorer-address"}, status=429, category="throttled"))
            self.assertEqual((facts["discovery"]["explorer"]["first_attempt"], facts["discovery"]["explorer"]["retry"], facts["creation"]["tx_source"]), ("throttled", "ok", "explorer_address_retry"))
        for code, category in ((404, "not_found"), (None, "dns_resolution")):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "run"
                root.mkdir()
                facts, rpc, status = self.run_pipeline(root, fetch=failing({"explorer-address"}, status=code, category=category))
                self.assertNotIn("retry", facts["discovery"]["explorer"])
                self.assertEqual((facts["discovery"]["explorer"]["status"], facts["creation"]["tx_source"]), (category, "sourcify_deployment"))
                self.assertEqual(status["started_attempts"], 112, "no retry is spent, and without the explorer's creator field its balance is not read")
        # The retry helper alone: a refused discovery budget is recorded, and a run whose every capture got no response is never retried.
        from types import SimpleNamespace
        from broad_collect import Pipeline
        class NoBudget:
            def acquire(self, kind):
                return False
        failed = {"id": "explorer-address", "url": "https://explorer.invalid/x", "http_status": 500, "failure_category": "server_error"}
        with tempfile.TemporaryDirectory() as tmp:
            stub = SimpleNamespace(session=NoBudget(), fetch=fake_fetch, explorer_base="https://explorer.invalid", discovery={}, synthetic=True, RETRYABLE=Pipeline.RETRYABLE)
            self.assertEqual(Pipeline.retry_explorer_address(stub, {"explorer-address": failed}, Path(tmp))["explorer-address"], failed)
            self.assertEqual(stub.discovery["explorer"]["retry"], "budget_exhausted")
            calls = []
            stub = SimpleNamespace(session=None, fetch=lambda items, out: calls.append(items) or fake_fetch(items, out), explorer_base="https://explorer.invalid", discovery={}, synthetic=True, RETRYABLE=Pipeline.RETRYABLE)
            denied = {k: {"id": k, "url": f"https://{k}.invalid/x", "http_status": None, "failure_category": "dns_resolution"} for k in ("dexscreener-pairs", "sourcify-correspondence")}
            Pipeline.retry_explorer_address(stub, {**denied, "explorer-address": {**failed, "failure_category": "timeout", "http_status": None}}, Path(tmp))
            self.assertEqual((calls, stub.discovery, sorted(Path(tmp).iterdir())), ([], {}, []), "every capture failed before any response: the denial is diagnosed, nothing is retried or written")
        # Two sources naming different transactions is recorded, never silently resolved.
        def other_deployment(out):
            path = out / "sourcify-correspondence.raw"
            body = json.loads(path.read_bytes())
            body["deployment"]["transactionHash"] = hh("another deployment")
            path.write_bytes(json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, fetch=failing(set(), rewrite=other_deployment))
            self.assertEqual((facts["creation"]["tx"], facts["creation"]["tx_source"], facts["creation"]["deployment_tx_conflict"]), (CREATION_TX, "explorer_address", hh("another deployment")))
            self.assertIn("| conflict: Sourcify's deployment record names " + hh("another deployment") + "; unresolved", "\n".join(summary_lines(facts)))
            from pipeline_note import write_and_compose
            write_and_compose(root)
            launch = next(f for f in read_json(root / "notes" / "pipeline.json")["findings"] if f["id"] == "pipeline-launch-execution")
            self.assertIn("Sourcify's deployment record names a different transaction", launch["text"])

    def test_position_custodian_keeps_its_actor_row_in_a_receipt_heavy_run(self):
        transfer = topic("Transfer(address,address,uint256)")
        def parties(first, count, tx, block, start):
            return [{"address": TOKEN, "topics": [transfer, word_address("0x" + format(first + n, "02x") * 20), word_address(POOL)], "data": abi(10 ** 18),
                     "transactionHash": tx, "blockHash": hh(block), "blockNumber": hex(block), "transactionIndex": "0x0", "logIndex": hex(start + n), "removed": False} for n in range(count)]
        class BusyRpc(PipelineRpc):
            def receipt(self):
                receipt = super().receipt()  # six parties between the launch transfer and the position mint: the locker is not among the receipt's first six transfer parties
                return {**receipt, "logs": receipt["logs"][:1] + parties(0xb0, 6, CREATION_TX, 90, 2) + receipt["logs"][1:]}
            def sale_receipt(self):
                receipt = super().sale_receipt()  # six more parties after the sale's own transfers keep the sale reconcilable
                return {**receipt, "logs": receipt["logs"] + parties(0xa0, 6, SELL_TX, 95, 3)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            facts, rpc, status = self.run_pipeline(root, rpc=BusyRpc())
            # Ten more transfer parties (architecture addresses are filtered first) would push the locker past the ten-actor cap; the custodian leads the list instead.
            custodians = [a for a in facts["actors"].values() if a.get("role") == "position_custodian"]
            self.assertEqual([a["address"] for a in custodians], [LOCKER])
            self.assertEqual(custodians[0]["getters"]["unlockTime"]["decoded"]["int"], 2000000000)
            self.assertIn("phase4b", {c["name"] for c in facts["collections"]})
            self.assertEqual(len(facts["actors"]), 10, "ten other parties fill the cap; the custodian still leads")
            self.assertTrue(facts["sales"][0]["verified"], "the extra transfer logs do not disturb the sale reconciliation")

    def test_logs_rows_print_position_ids_for_the_positions_preset(self):
        from facts import summarize_row, INCREASE_LIQUIDITY_TOPIC
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evidence").mkdir()
            logs = [{"topics": [INCREASE_LIQUIDITY_TOPIC, abi(7)]}, {"topics": [INCREASE_LIQUIDITY_TOPIC, abi(9)]}, {"topics": [INCREASE_LIQUIDITY_TOPIC, abi(7)]}, {"topics": ["0x" + "ab" * 32]}]
            (root / "evidence" / "scan.json").write_text(json.dumps({"response": {"jsonrpc": "2.0", "id": "scan", "result": logs}}))
            row = {"id": "scan-logs", "address": NFPM, "kind": "rpc", "query": {"method": "eth_getLogs"}, "artifact": "evidence/scan.json", "observation_status": "ok"}
            self.assertEqual(summarize_row(root, row)["decoded"], {"logs": 4, "token_ids": [7, 9], "token_ids_total": 2})

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
