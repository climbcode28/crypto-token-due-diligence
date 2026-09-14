#!/usr/bin/env python3
"""Standard broad collection in one process: discovery, four pinned RPC phases, source match, facts.

This replaces a dozen hand-written collector plans with explicit reads whose shape is fixed
in presets.py. It composes the existing Collector, session, cache and assembler; it adds no
transport, no fallback provider and no semantic conclusions. Everything it decodes is
written to facts.json with the evidence alias that supports it.
"""
import argparse
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

import presets
from sale_decode import decode_sale
from backend_common import Cache, Invalid, address, canonical, integer, need, quantity, read_json, replace_json, sha, stamp, write_new
from evm_decode import classify_clone
from facts import DEAD, SELECTORS, TRANSFER, account_code_kind, holder_summary, decimal_string, decode_result, summarize_row, transfers
from keccak import selector, topic
from rpc_collect import Collector, HttpTransport, add_provider_arguments, configured_transport, provider_availability, seconds


class StartFailure(Invalid):
    """A start that failed before any block was pinned; carries a structured, actionable diagnostic."""

    def __init__(self, info):
        super().__init__(info.get("message", "start failed"))
        self.info = info


LANE_MINUTES = 4
LANE_CHARGE = 20
PIN_LAG = 3  # blocks behind the reported head: load-balanced public RPCs lag by a block or two
NO_RESPONSE = ("dns_resolution", "timeout", "transport_error")  # failure categories recorded before any host answered


def spawn_prompt(run, lane):
    path = (Path(run).resolve() / "lanes" / lane / "brief.md")
    return f"Read the file {path} and follow it exactly; it is your entire instruction set. Do not read anything else first."


MAX_USER_URLS = 6


def user_urls(values):
    """User-provided links to capture: credential-free http(s) only, deduplicated, at most six."""
    from web_capture import clean_url
    out = []
    for raw in values or []:
        url = str(raw).strip()
        if not url or url in out:
            continue
        clean_url(url)
        out.append(url)
    need(len(out) <= MAX_USER_URLS, f"at most {MAX_USER_URLS} user URLs; put the rest in --focus as text for the lanes to prioritise")
    return out


def user_focus_section(intake, lane):
    """The lane brief's 'What the user asked' section, rendered from intake.json."""
    focus = str((intake or {}).get("focus") or "").strip().replace("{{", "{ {").replace("}}", "} }")
    urls = list((intake or {}).get("user_urls") or [])
    if not focus and not urls:
        return "No additional asks beyond the standard scope."
    lines = []
    if focus:
        lines.append("The user's own words, beyond the address: \"" + focus.replace("\"", "'")[:1200] + "\"")
        lines.append("")
        lines.append("Answer each ask explicitly: in a finding when you observed something (documentary truth-versus-hype "
                     "judgements are `inference` findings citing the captures; lore or claims you could not observe are never Good), "
                     "or as a coverage attempt naming what you tried when it cannot be answered from permitted sources. Repeat the "
                     "answer in one sentence of your final reply.")
    if urls:
        who = ("Capture every one of these first, in your first fetcher batch" if lane == "project"
               else "Capture the ones about pools, holders or trades in your first fetcher batch; the project lane covers the rest")
        lines.append("")
        lines.append(f"User-provided links ({who}):")
        lines += ["- " + u for u in urls]
        lines.append("")
        lines.append("An X/Twitter status page is a JavaScript shell, but the post text usually sits in the `og:description` or "
                     "`twitter:description` meta tag of the captured HTML; read it with `rg -o 'og:description\" content=\"[^\"]*'` on "
                     "the `.raw` file. A page that returns nothing readable is a recorded gap, not an answer.")
    return "\n".join(lines)


def write_brief(run, lane, minutes=LANE_MINUTES, allow_partial=False):
    """Render the lane brief to lanes/<lane>/brief.md so the coordinator spawns with a one-line pointer."""
    text = brief(run, lane, minutes, allow_partial)
    path = Path(run) / "lanes" / lane / "brief.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, text


def charge_lane(session, lane, count=LANE_CHARGE):
    """Pre-charge a lane's web budget exactly as `investigation.py charge` does; returns the count charged."""
    import uuid
    owner = str(uuid.uuid4())
    charged = 0
    session.reserve(owner, count)
    try:
        for _ in range(count):
            if not session.acquire("lane_" + lane, owner=owner, reserved=True):
                break
            charged += 1
    finally:
        session.release(owner)
    return charged


def prepare_lanes(run, session, minutes=LANE_MINUTES, count=LANE_CHARGE):
    """Charge both lanes and write both briefs; the printed spawn lines are the coordinator's next action."""
    lanes = {}
    for lane in ("liquidity", "project"):
        entry = {"charged": 0, "brief": None, "prompt": spawn_prompt(run, lane)}
        try:
            entry["charged"] = charge_lane(session, lane, count) if session is not None else 0
        except (ValueError, Invalid) as exc:
            entry["charge_error"] = str(exc)[:120]
        try:
            from web_capture import prepare_budget
            prepare_budget(Path(run) / "lanes" / lane, entry["charged"],
                           min(session.deadline, time.time() + (minutes + 2) * 60) if session is not None else time.time())
            path, _ = write_brief(run, lane, minutes)
            entry["brief"] = str(path.resolve())
        except (Invalid, ValueError, OSError) as exc:
            entry["brief_error"] = str(exc)[:160]
        lanes[lane] = entry
    (Path(run) / "lanes" / "spawn.json").write_text(json.dumps(lanes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lanes


def spawn_lines(lanes):
    lines = ["lanes: " + "; ".join(f"{lane} charged {e['charged']} web requests, brief {e.get('brief') or e.get('brief_error')}" for lane, e in lanes.items())]
    lines.append("NEXT, before reading facts or anything else: spawn BOTH lanes now, in one message, each with exactly this prompt:")
    for lane, e in lanes.items():
        lines.append(f"  {lane} lane -> {e['prompt']}")
    return lines


def pipeline_note_result(run):
    """Write and compose the pipeline's factual note; never fatal for the run."""
    try:
        from pipeline_note import write_and_compose
        return write_and_compose(run)
    except (Invalid, ValueError, OSError, KeyError, TypeError) as exc:
        return {"status": "skipped", "reason": str(exc)[:200]}


def archive_failed_attempt(run):
    """Archive a failed start without resetting its shared attempt ledger or deadline."""
    import shutil
    run = Path(run)
    previous = [p for p in run.iterdir() if p.name.startswith("failed-attempt-")]
    dest = run / f"failed-attempt-{len(previous) + 1}"
    dest.mkdir()
    for child in list(run.iterdir()):
        if child != dest and not child.name.startswith("failed-attempt-"):
            if child.name in ("session.sqlite", "cache.sqlite"):
                shutil.copy2(child, dest / child.name)
            else:
                child.rename(dest / child.name)
    return dest

PIPELINE_VERSION = "1.0.2"
POSITION_TOPICS = {topic("Transfer(address,address,uint256)"), topic("IncreaseLiquidity(uint256,uint128,uint256,uint256)")}
SWAP_TOPICS = {topic("Swap(address,address,int256,int256,uint160,uint128,int24)"),  # Uniswap v3
               topic("Swap(address,uint256,uint256,uint256,uint256,address)"),  # Uniswap v2
               topic("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)")}  # Uniswap v4 PoolManager
TOP_HOLDER_READS = 10
ZERO = "0x" + "0" * 40


GETTER_PRIORITY = ("owner", "admin", "pause", "fee", "tax", "limit", "max", "block", "enabled", "trading", "factory",
                   "pool", "locker", "treasury", "recipient", "wallet", "blacklist", "whitelist", "exempt", "deployer", "launch")
SMALL_ADDRESS_FLOOR = 2 ** 32
ADDRESS_FLOOR = 2 ** 96  # a random 160-bit address is below this with probability ~2^-64; token amounts rarely exceed it
AMOUNT_WORDS = {"amount", "amounts", "limit", "bps", "block", "supply", "max", "min", "rate", "time", "count", "cap",
                "threshold", "percent", "share", "shares", "decimals", "price", "tick", "spacing", "balance", "total", "duration", "end", "start"}
ADDRESS_NAMES = {sig.split("(")[0].lower() for sig in ("owner()", "getOwner()", "admin()", "implementation()", "factory()", "deployer()",
                                                        "launchFactory()", "liquidityPool()", "pairToken()", "treasury()", "feeRecipient()",
                                                        "taxWallet()", "locker()", "positionManager()", "dexFactory()", "router()", "pool()",
                                                        "feeTo()", "minter()", "timelock()", "priceOracle()", "oracle()", "vault()", "beneficiary()")}


def mapping(value):
    return value if isinstance(value, dict) else {}


def sequence(value):
    return value if isinstance(value, list) else []


def flag_value(value):
    """GoPlus encodes booleans as "0"/"1" strings; anything else is unknown."""
    return {"0": False, "1": True}.get(str(value)) if value not in (None, "") else None


def nonnegative(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def observed_sum(values):
    values = list(values)
    return sum(values) if values and all(nonnegative(v) is not None for v in values) else None


def name_words(name):
    return [w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+", name)]


def looks_like_address(value, name=""):
    """Accept getter words that are plausibly addresses: right magnitude, and not an amount-like name.

    Word matching is on whole camelCase words, and names in the control-getter list are never filtered.
    """
    if value is None or value >= 2 ** 160 or value < ADDRESS_FLOOR:
        return False
    if name.lower() in ADDRESS_NAMES:
        return True
    return not any(word in AMOUNT_WORDS for word in name_words(name))


class Pipeline:
    def __init__(self, run, target, question, materiality, transport, session, cache, endpoint_label="research-rpc",
                 fetch=None, quote_sizes=(100, 10000, 100000), pools=(), holders=None, explorer="auto", web=True, synthetic=False, registry=None):
        self.run = Path(run)
        self.target = {"chain_id": integer(target["chain_id"], "chain ID", 1), "address": address(target["address"])}
        self.question, self.materiality = question, materiality
        self.transport, self.session, self.cache, self.endpoint_label = transport, session, cache, endpoint_label
        self.fetch = fetch  # callable(items, out) -> records; default web_capture.capture
        self.quote_sizes, self.extra_pools, self.holders = list(quote_sizes), [address(p) for p in pools], holders or {}
        self.explorer, self.web, self.synthetic = explorer, web, synthetic
        self.registry = registry if registry is not None else presets.registry(self.target["chain_id"])
        self.discovery = {"dexscreener": {"status": "not_attempted"}, "sourcify": {"status": "not_attempted"}, "explorer": {"status": "not_attempted"}, "geckoterminal": {"status": "not_attempted"}, "goplus": {"status": "not_attempted"}}
        self.pairs, self.links, self.abi, self.source_body = [], {"websites": [], "socials": []}, None, None
        self.collections, self.names, self.log = [], {}, []
        self.decoded = {}  # alias -> (row, decoded dict)
        self.pin = None
        self.creation = {}
        self.indexed_holders, self.indexed_transfers, self.sell_candidates, self.indexed_trades = [], [], [], []
        self.goplus = {"status": "not_attempted"}
        self.counters, self.creator_activity, self.pins_seen = {}, {}, {}
        self.explorer_base = None

    # ----- helpers --------------------------------------------------------------------
    def mark(self, phase):
        if self.session is not None:
            try:
                self.session.mark(phase)
            except (ValueError, Invalid):
                pass
        self.log.append({"phase": phase, "at": stamp()})

    def remaining_timeout(self, cap=90):
        if self.session is None:
            return cap
        return max(5.0, min(cap, self.session.remaining_seconds() - 20))

    def collect(self, name, plan, max_requests, timeout=None):
        root = self.run / name
        collector = Collector(root, self.cache, self.transport, self.endpoint_label, max_requests=max_requests,
                              timeout=timeout or self.remaining_timeout(), session=self.session)
        result = collector.collect(plan)
        self.collections.append({"name": name, "status": result["status"], "attempts": result["statistics"]["network_attempts"],
                                 "elapsed_seconds": result["telemetry"]["elapsed_seconds"], "limit_reached": result["execution"]["limit_reached"]})
        if result["status"] in ("complete", "partial"):
            for row in result["evidence"]:
                if row["id"].startswith("sys-"):
                    continue
                artifact = read_json(root / row["artifact"])
                response = artifact.get("response", {})
                result_value = response.get("result") if "error" not in response else None
                self.decoded[row["id"]] = (row, result_value, row["observation_status"])
            if result["pins"]:
                self.pin = self.pin or result["pins"][0]
                for pin in result["pins"]:
                    self.pins_seen[pin["number"]] = pin.get("timestamp_utc")
        return result

    def value(self, alias):
        entry = self.decoded.get(alias)
        return entry[1] if entry and entry[2] == "ok" else None

    def status(self, alias):
        entry = self.decoded.get(alias)
        return entry[2] if entry else "missing"

    def reverted(self, base, names):
        return [name for name in names if self.status(base + "-" + name) == "reverted"]

    def word_value(self, alias):
        raw = self.value(alias)
        return int(raw, 16) if isinstance(raw, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", raw) else None

    def address_value(self, alias):
        value = self.word_value(alias)
        if value is None or value == 0 or value >= 2 ** 160 or value < SMALL_ADDRESS_FLOOR:
            return None
        return "0x" + format(value, "040x")

    def control_getters(self):
        """Probe only getters the verified ABI exposes; without an ABI, probe the common list."""
        if isinstance(self.abi, list) and self.abi:
            names = {item.get("name") for item in self.abi if isinstance(item, dict) and item.get("type") == "function" and not item.get("inputs")}
            return [sig for sig in presets.CONTROL_GETTERS if sig.split("(")[0] in names]
        return list(presets.CONTROL_GETTERS)

    # ----- discovery ------------------------------------------------------------------
    def discover(self, budget_ops):
        out = self.run / "discovery"
        out.mkdir(parents=True, exist_ok=True)
        items = []
        slug = self.registry.get("dexscreener")
        if slug:
            items.append({"id": "dexscreener-pairs", "url": f"https://api.dexscreener.com/token-pairs/v1/{slug}/{self.target['address']}", "purpose": "Exact-address pool discovery"})
        else:
            self.discovery["dexscreener"] = {"status": "unsupported_chain_slug"}
        items.append({"id": "sourcify-correspondence", "purpose": "Verified source, ABI and compiler output",
                      "url": f"https://sourcify.dev/server/v2/contract/{self.target['chain_id']}/{self.target['address']}?fields=compilation,sources,runtimeBytecode,stdJsonInput,stdJsonOutput,abi,deployment"})
        explorer = None
        if self.explorer != "none":
            for candidate in self.registry.get("explorers", []):
                if candidate.get("api_v2") and (self.explorer == "auto" or self.explorer in candidate["name"].lower()):
                    explorer = candidate
                    break
        if explorer:
            base = explorer["base"].rstrip("/")
            self.explorer_base = base
            items.append({"id": "explorer-address", "url": f"{base}/api/v2/addresses/{self.target['address']}", "purpose": "Creation transaction and creator"})
            items.append({"id": "explorer-token", "url": f"{base}/api/v2/tokens/{self.target['address']}", "purpose": "Holder count and supply"})
            items.append({"id": "explorer-counters", "url": f"{base}/api/v2/tokens/{self.target['address']}/counters", "purpose": "Indexed holder and transfer counts"})
            items.append({"id": "explorer-holders", "url": f"{base}/api/v2/tokens/{self.target['address']}/holders", "purpose": "Top indexed holders (page one)"})
            items.append({"id": "explorer-transfers", "url": f"{base}/api/v2/tokens/{self.target['address']}/transfers", "purpose": "Most recent indexed transfers (sale candidates)"})
        elif self.explorer != "none":
            self.discovery["explorer"] = {"status": "no_json_explorer_in_registry", "alternates": [e["name"] for e in self.registry.get("explorers", [])]}
        if self.session is not None and self.fetch is not None:
            granted = []
            for item in items:
                if self.session.acquire("discovery_web"):
                    granted.append(item)
                else:
                    self.discovery["budget"] = "exhausted before discovery of " + item["id"]
            items = granted
            if not items:
                write_new(self.run / "discovery.json", {"schema_version": 1, "target": self.target, "captured_at_utc": stamp(),
                                                         "discovery": self.discovery, "pairs": [], "links": self.links, "abi_getters": []})
                return
        if self.fetch is None:
            from web_capture import capture
            records = capture(items, out, timeout=15, session=self.session, operation="discovery_web")
        else:
            records = self.fetch(items, out)
        by_id = {r["id"]: r for r in records}
        by_id = self.retry_explorer_address(by_id, out)
        for key, rid in (("dexscreener", "dexscreener-pairs"), ("sourcify", "sourcify-correspondence"), ("explorer", "explorer-address")):
            record = by_id.get(rid)
            if record is None:
                continue
            ok = record.get("http_status") == 200 and not record.get("failure_category")
            prior = self.discovery.get(key) if isinstance(self.discovery.get(key), dict) else {}  # the explorer retry's record survives
            self.discovery[key] = {**prior, "status": "ok" if ok else (record.get("failure_category") or "http_" + str(record.get("http_status"))),
                                   "url": record["url"], "captured_at_utc": record["captured_at_utc"], "bytes": record.get("bytes", 0)}
            if key == "explorer" and explorer:
                self.discovery[key]["name"] = explorer["name"]
                if not ok:
                    self.discovery[key]["alternates"] = [e["name"] for e in self.registry.get("explorers", []) if e is not explorer]
            if not ok or not record.get("raw"):
                continue
            try:
                body = json.loads((out / record["raw"]).read_bytes().decode("utf-8"))
            except (ValueError, OSError):
                self.discovery[key]["status"] = "unparseable"
                continue
            if key == "dexscreener":
                self.parse_pairs(body)
            elif key == "sourcify":
                self.source_body = body
                self.abi = body.get("abi") if isinstance(body, dict) else None
                self.discovery[key]["compiler"] = mapping(mapping(body).get("compilation")).get("compilerVersion")
                self.discovery[key]["contract"] = mapping(mapping(body).get("compilation")).get("fullyQualifiedName")
                deployment = mapping(mapping(body).get("deployment"))
                tx = str(deployment.get("transactionHash") or "").lower()
                deployer = str(deployment.get("deployer") or "").lower()
                block = str(deployment.get("blockNumber") or "")
                if re.fullmatch(r"0x[0-9a-f]{64}", tx):
                    # Sourcify's deployment record names the creation transaction independently of the explorer.
                    self.sourcify_deployment = {"tx": tx, "deployer": deployer if re.fullmatch(r"0x[0-9a-f]{40}", deployer) and int(deployer, 16) else None}
                    self.discovery[key]["deployment_tx"] = tx
                    if block.isdigit():
                        self.discovery[key]["deployment_block"] = int(block)
            elif key == "explorer" and isinstance(body, dict):
                tx = str(body.get("creation_transaction_hash") or body.get("creation_tx_hash") or "").lower()
                creator = str(body.get("creator_address_hash") or "").lower()
                self.creation = {"tx": tx if re.fullmatch(r"0x[0-9a-f]{64}", tx) else None,
                                 "creator": creator if re.fullmatch(r"0x[0-9a-f]{40}", creator) and int(creator, 16) else None,
                                 "is_verified": body.get("is_verified") if isinstance(body.get("is_verified"), bool) else None,
                                 "proxy_type": str(body.get("proxy_type"))[:40] if body.get("proxy_type") else None}
                if self.creation["tx"]:
                    self.creation["tx_source"] = "explorer_address" + ("_retry" if self.discovery[key].get("retried") else "")
                self.discovery[key].update(self.creation)
        deployment = getattr(self, "sourcify_deployment", None)
        if deployment and not self.creation.get("tx"):
            # The explorer did not name the creation transaction (a failed page or an unindexed contract): Sourcify's
            # deployment record supplies it, so the creation receipt, the launch signer, the launch-window scan and the
            # position custodian probe survive an explorer outage. The explorer's creator field stays unknown.
            self.creation = {**self.creation, "tx": deployment["tx"], "tx_source": "sourcify_deployment", "deployer": deployment["deployer"]}
            self.discovery.setdefault("explorer", {})["creation_from"] = "sourcify_deployment"
        elif deployment and self.creation.get("tx") and deployment["tx"] != self.creation["tx"]:
            self.creation["deployment_tx_conflict"] = deployment["tx"]  # two sources disagree: recorded, never silently resolved
        token_record = by_id.get("explorer-token")
        if token_record and token_record.get("http_status") == 200 and token_record.get("raw"):
            try:
                body = json.loads((out / token_record["raw"]).read_bytes().decode("utf-8"))
                self.discovery["explorer"]["holders"] = mapping(body).get("holders")
            except (ValueError, OSError):
                pass
        self.parse_explorer_extras(by_id, out)
        self.capture_indexed_trades(out)
        self.capture_goplus(out)
        write_new(self.run / "discovery.json", {"schema_version": 1, "target": self.target, "captured_at_utc": stamp(),
                                                 "discovery": self.discovery, "pairs": self.pairs, "links": self.links,
                                                 "abi_getters": self.abi_getters()})

    def capture_goplus(self, out):
        """GoPlus token security (keyless): listed holders and LP holders with lock flags, contract flags and control
        checks for the exact token. Third-party claims; LP holders are cross-checked against the positions the pipeline
        read and holders against its balance sample when the facts are assembled."""
        self.goplus = {"status": "not_attempted"}
        item = {"id": "goplus-token-security", "url": f"https://api.gopluslabs.io/api/v1/token_security/{self.target['chain_id']}?contract_addresses={self.target['address']}",
                "purpose": "Third-party token security: holders, LP holders with lock flags, control checks"}
        if self.session is not None and self.fetch is not None and not self.session.acquire("discovery_web"):
            self.goplus = {"status": "budget_exhausted", "url": item["url"]}
            self.discovery["goplus"] = {"status": "budget_exhausted"}
            return
        if self.fetch is None:
            from web_capture import capture
            records = capture([item], out, timeout=15, session=self.session, operation="discovery_web")
        else:
            records = self.fetch([item], out)
        record = next((r for r in records if r["id"] == item["id"]), None)
        if record is None:
            self.goplus = {"status": "not_captured", "url": item["url"]}
            self.discovery["goplus"] = {"status": "not_captured"}
            return
        ok = record.get("http_status") == 200 and not record.get("failure_category")
        status = "ok" if ok else (record.get("failure_category") or "http_" + str(record.get("http_status")))
        self.goplus = {"status": status, "url": record["url"], "captured_at_utc": record.get("captured_at_utc"), "bytes": record.get("bytes", 0), "evidence": "doc-goplus-token-security"}
        self.discovery["goplus"] = {"status": status, "url": record["url"]}
        if not ok or not record.get("raw"):
            return
        try:
            body = json.loads((out / record["raw"]).read_bytes().decode("utf-8"))
        except (ValueError, OSError):
            self.goplus["status"] = self.discovery["goplus"]["status"] = "unparseable"
            return
        body = mapping(body)
        if body.get("code") != 1 or not isinstance(body.get("result"), dict):
            self.goplus["status"] = self.discovery["goplus"]["status"] = "api_" + str(body.get("code")) + ":" + str(body.get("message"))[:40]
            return
        entry = mapping(body["result"].get(self.target["address"].lower()) or body["result"].get(self.target["address"]))
        if not entry:
            self.goplus["status"] = self.discovery["goplus"]["status"] = "token_not_listed"
            return
        def flag(name):
            return flag_value(entry.get(name))
        def pct(value):
            try:
                return round(float(value) * 100, 4) if value not in (None, "") else None
            except (TypeError, ValueError):
                return None
        def addr(value):
            value = str(value or "").lower()
            return value if re.fullmatch(r"0x[0-9a-f]{40}", value) else None
        holders, lp_holders = [], []
        for row in sequence(entry.get("holders"))[:20]:
            row = mapping(row)
            if addr(row.get("address")):
                holders.append({"address": addr(row.get("address")), "tag": str(row.get("tag") or "")[:40], "is_contract": flag_value(row.get("is_contract")),
                                "is_locked": flag_value(row.get("is_locked")), "share_pct": pct(row.get("percent")), "balance": str(row.get("balance") or "")[:40]})
        for row in sequence(entry.get("lp_holders"))[:20]:
            row = mapping(row)
            if addr(row.get("address")):
                nfts = []
                for nft in sequence(row.get("NFT_list"))[:20]:
                    nft = mapping(nft)
                    if str(nft.get("NFT_id") or "").isdigit() and int(nft["NFT_id"]) not in {n["id"] for n in nfts}:
                        amount = str(nft.get("amount") or "")[:40]
                        # Empty means a zero amount; an unknown amount is not empty, and an out-of-range position still holds principal.
                        nfts.append({"id": int(nft["NFT_id"]), "share_pct": pct(nft.get("NFT_percentage")), "amount": amount, "amount_known": amount != "",
                                     "in_effect": flag_value(nft.get("in_effect")), "empty": amount == "0"})
                lp_holders.append({"address": addr(row.get("address")), "tag": str(row.get("tag") or "")[:40], "is_contract": flag_value(row.get("is_contract")),
                                   "is_locked": flag_value(row.get("is_locked")), "share_pct": pct(row.get("percent")), "value": str(row.get("value") or "")[:40],
                                   "nft_ids": sorted(n["id"] for n in nfts), "nfts": nfts,
                                   "locked_detail": [{k: str(mapping(d).get(k) or "")[:40] for k in ("end_time", "amount", "opt_token")} for d in sequence(row.get("locked_detail"))[:4]]})
        dex = [{"pair": addr(mapping(d).get("pair")), "type": str(mapping(d).get("liquidity_type") or "")[:20], "name": str(mapping(d).get("name") or "")[:30],
                "fee": str(mapping(d).get("pool_fee") or "")[:12], "liquidity": str(mapping(d).get("liquidity") or "")[:40]} for d in sequence(entry.get("dex"))[:10] if addr(mapping(d).get("pair"))]
        self.goplus.update(holder_count=int(entry["holder_count"]) if str(entry.get("holder_count") or "").isdigit() else None,
                           lp_holder_count=int(entry["lp_holder_count"]) if str(entry.get("lp_holder_count") or "").isdigit() else None,
                           holders=holders, lp_holders=lp_holders, dex=dex,
                           flags={name: flag(name) for name in ("is_honeypot", "is_mintable", "is_proxy", "is_open_source", "transfer_pausable", "is_blacklisted", "is_whitelisted",
                                                                "hidden_owner", "can_take_back_ownership", "selfdestruct", "external_call", "is_anti_whale", "slippage_modifiable", "trading_cooldown")},
                           buy_tax=str(entry.get("buy_tax") or "")[:12], sell_tax=str(entry.get("sell_tax") or "")[:12],
                           owner_address=addr(entry.get("owner_address")), creator_address=addr(entry.get("creator_address")),
                           scope="third-party token-security claims captured from GoPlus; LP holders and holders are verified only where the pipeline read the same position or balance")

    def capture_indexed_trades(self, out):
        """Indexer-listed recent trades at the canonical pool (GeckoTerminal) name sale candidates when the explorer's
        recent-transfer page holds no wallet-to-pool transfer; the receipt, never the listing, establishes the sale."""
        network = self.registry.get("geckoterminal")
        pool = next((p["pair"] for p in self.pairs if not p.get("is_pool_id")), None)
        self.indexed_trades = []
        if not network or not pool:
            self.discovery["geckoterminal"] = {"status": "no_geckoterminal_network_in_registry" if not network else "no_address_pool_indexed"}
            return
        item = {"id": "geckoterminal-trades", "url": f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool}/trades",
                "purpose": "Indexer-listed recent trades at the canonical pool (sale candidates)"}
        if self.session is not None and self.fetch is not None and not self.session.acquire("discovery_web"):
            self.discovery["geckoterminal"] = {"status": "budget_exhausted", "url": item["url"]}
            return
        if self.fetch is None:
            from web_capture import capture
            records = capture([item], out, timeout=15, session=self.session, operation="discovery_web")
        else:
            records = self.fetch([item], out)
        record = next((r for r in records if r["id"] == item["id"]), None)
        if record is None:
            self.discovery["geckoterminal"] = {"status": "not_captured", "url": item["url"]}
            return
        ok = record.get("http_status") == 200 and not record.get("failure_category")
        self.discovery["geckoterminal"] = {"status": "ok" if ok else (record.get("failure_category") or "http_" + str(record.get("http_status"))),
                                           "url": record["url"], "captured_at_utc": record.get("captured_at_utc"), "bytes": record.get("bytes", 0), "pool": pool}
        if not ok or not record.get("raw"):
            return
        try:
            body = json.loads((out / record["raw"]).read_bytes().decode("utf-8"))
        except (ValueError, OSError):
            self.discovery["geckoterminal"]["status"] = "unparseable"
            return
        rows = mapping(body).get("data")
        for row in (rows if isinstance(rows, list) else [])[:300]:
            a = mapping(mapping(row).get("attributes"))
            tx = str(a.get("tx_hash") or "").lower()
            kind = a.get("kind")
            if not re.fullmatch(r"0x[0-9a-f]{64}", tx) or kind not in ("buy", "sell") or any(t["tx"] == tx for t in self.indexed_trades):
                continue
            trader = str(a.get("tx_from_address") or "").lower()
            self.indexed_trades.append({"tx": tx, "kind": kind, "block": a.get("block_number") if isinstance(a.get("block_number"), int) else None,
                                        "trader": trader if re.fullmatch(r"0x[0-9a-f]{40}", trader) else None})
        self.indexed_trades.sort(key=lambda t: -(t["block"] or 0))
        sells = [t["tx"] for t in self.indexed_trades if t["kind"] == "sell"]
        # Listed sells fill the remaining candidate slots; when the explorer filled both, its second (smaller) transfer
        # yields to the most recent listed sell, because a wallet-to-pool transfer can also be a liquidity add.
        for tx in sells:
            if tx not in self.sell_candidates and len(self.sell_candidates) < 2:
                self.sell_candidates.append(tx)
        if sells and not any(tx in sells for tx in self.sell_candidates) and len(self.sell_candidates) == 2:
            self.sell_candidates[1] = sells[0]
        self.discovery["geckoterminal"].update(trades=len(self.indexed_trades), sells=len(sells), sale_candidates=list(self.sell_candidates))

    def explorer_json(self, by_id, out, rid):
        record = by_id.get(rid)
        if not record or record.get("http_status") != 200 or record.get("failure_category") or not record.get("raw"):
            return None
        try:
            return json.loads((out / record["raw"]).read_bytes().decode("utf-8"))
        except (ValueError, OSError):
            return None

    @staticmethod
    def party(item):
        item = item if isinstance(item, dict) else {}
        addr = str(item.get("hash") or "").lower()
        return {"address": addr if re.fullmatch(r"0x[0-9a-f]{40}", addr) else None, "is_contract": item.get("is_contract"),
                "name": item.get("name"), "is_verified": item.get("is_verified")}

    RETRYABLE = ("server_error", "timeout", "throttled")  # the fetcher's own failure categories for a 5xx, a timeout and a 429

    def retry_explorer_address(self, by_id, out):
        """One more attempt at the explorer's address page after a two-second pause when it failed transiently (a 5xx, a
        timeout or a rate limit): the creation transaction hangs on this one request. The live fetcher already gives the
        first attempt its own quick transient retry; this attempt is exactly one charged request. A 404, an access denial
        or a run whose every capture got no response (the host denied the network) is never retried."""
        record = by_id.get("explorer-address")
        if record is None or not getattr(self, "explorer_base", None):
            return by_id
        ok = record.get("http_status") == 200 and not record.get("failure_category")
        status = record.get("failure_category") or "http_" + str(record.get("http_status"))
        if ok or status not in self.RETRYABLE:
            return by_id
        attempted = [r for r in by_id.values() if r.get("url")]
        if attempted and all(r.get("failure_category") in NO_RESPONSE for r in attempted):
            return by_id  # nothing answered anywhere: head_failure names the denial; a retry would only spend its timeout
        if self.session is not None and self.fetch is not None and not self.session.acquire("discovery_web"):
            self.discovery.setdefault("explorer", {})["retry"] = "budget_exhausted"
            return by_id
        if not self.synthetic:
            time.sleep(2)
        item = {"id": "explorer-address-retry", "url": record["url"], "purpose": "Creation transaction and creator (one retry after a transient failure)"}
        if self.fetch is None:
            from web_capture import capture
            records = capture([item], out, timeout=15, session=self.session, operation="discovery_web", retries=0)
        else:
            records = self.fetch([item], out)
        again = next((r for r in records if r["id"] == item["id"]), None)
        if again is None:
            self.discovery.setdefault("explorer", {})["retry"] = "not_captured"
            return by_id
        again_ok = again.get("http_status") == 200 and not again.get("failure_category")
        self.discovery.setdefault("explorer", {})["retry"] = "ok" if again_ok else (again.get("failure_category") or "http_" + str(again.get("http_status")))
        self.discovery["explorer"]["first_attempt"] = status
        if again_ok:
            self.discovery["explorer"]["retried"] = True
            return {**by_id, "explorer-address": {**again, "id": "explorer-address"}}
        return by_id

    def parse_explorer_extras(self, by_id, out):
        """Counters, the top indexed holders and the most recent indexed transfers (Blockscout API v2 shapes)."""
        counters = self.explorer_json(by_id, out, "explorer-counters")
        if isinstance(counters, dict):
            for key, field in (("token_holders_count", "holders_count"), ("transfers_count", "transfers_count")):
                value = counters.get(key)
                if isinstance(value, (str, int)) and str(value).isdigit():
                    self.counters[field] = int(value)
                    self.discovery.setdefault("explorer", {})[field] = int(value)
        holders = self.explorer_json(by_id, out, "explorer-holders")
        items = holders.get("items") if isinstance(holders, dict) else holders
        for item in sequence(items)[:50]:
            if not isinstance(item, dict):
                continue
            who = self.party(item.get("address"))
            value = str(item.get("value") or "")
            if who["address"] and value.isdigit():
                self.indexed_holders.append({**who, "value_raw": int(value)})
        if self.indexed_holders:
            self.discovery.setdefault("explorer", {})["top_holders_captured"] = len(self.indexed_holders)
        transfers = self.explorer_json(by_id, out, "explorer-transfers")
        items = transfers.get("items") if isinstance(transfers, dict) else transfers
        pools = self.pool_destinations(self.pairs)
        for item in sequence(items)[:50]:
            if not isinstance(item, dict):
                continue
            tx = str(item.get("transaction_hash") or item.get("tx_hash") or "").lower()
            if not re.fullmatch(r"0x[0-9a-f]{64}", tx):
                continue
            src, dst = self.party(item.get("from")), self.party(item.get("to"))
            total = item.get("total") if isinstance(item.get("total"), dict) else {}
            value = str(total.get("value") or "")
            row = {"tx": tx, "block": item.get("block_number"), "from": src["address"], "to": dst["address"],
                   "from_is_contract": src["is_contract"], "to_is_contract": dst["is_contract"], "value_raw": int(value) if value.isdigit() else None,
                   "method": item.get("method"), "timestamp": item.get("timestamp")}
            self.indexed_transfers.append(row)
        # A transfer of the token into a pool from a non-pool, non-contract wallet is a sale candidate; prefer the largest two.
        candidates = [r for r in self.indexed_transfers if r["to"] in pools and r["from"] not in pools and r["from_is_contract"] is False]
        candidates.sort(key=lambda r: -(r["value_raw"] or 0))
        for row in candidates:
            if row["tx"] not in self.sell_candidates and len(self.sell_candidates) < 2:
                self.sell_candidates.append(row["tx"])
        if self.indexed_transfers:
            self.discovery.setdefault("explorer", {})["recent_transfers_captured"] = len(self.indexed_transfers)
            self.discovery["explorer"]["sale_candidates"] = list(self.sell_candidates)

    def capture_creator_activity(self, signer):
        """Second bounded explorer pass once the launch signer is known: its transactions and token transfers."""
        if not self.explorer_base or not signer or not self.web:
            return
        out = self.run / "discovery"
        items = [{"id": "explorer-signer-transactions", "url": f"{self.explorer_base}/api/v2/addresses/{signer}/transactions", "purpose": "Launch signer transactions (other launches, admin calls)", "address": signer},
                 {"id": "explorer-signer-token-transfers", "url": f"{self.explorer_base}/api/v2/addresses/{signer}/token-transfers", "purpose": "Launch signer token transfers (early sales, proceeds)", "address": signer}]
        if self.session is not None and self.fetch is not None:
            items = [item for item in items if self.session.acquire("discovery_web")]
        if not items:
            return
        try:
            if self.fetch is None:
                from web_capture import capture
                records = capture(items, out, timeout=15, session=self.session, operation="discovery_web")
            else:
                records = self.fetch(items, out)
        except (Invalid, ValueError, OSError) as exc:
            self.creator_activity = {"status": "capture_failed", "reason": str(exc)[:120]}
            return
        by_id = {r["id"]: r for r in records}
        activity = {"signer": signer}
        txs = self.explorer_json(by_id, out, "explorer-signer-transactions")
        tx_observed = isinstance(txs, list) or isinstance(mapping(txs).get("items"), list)
        items_tx = sequence(txs.get("items") if isinstance(txs, dict) else txs)
        factory = self.creation.get("factory") or self.creation.get("creator")
        launches, contracts_created = [], 0
        for item in items_tx[:50]:
            if not isinstance(item, dict):
                continue
            to = self.party(item.get("to"))["address"]
            if item.get("created_contract"):
                contracts_created += 1
            if to and factory and to == factory:
                launches.append(str(item.get("hash") or "")[:66])
        activity.update(transactions_captured=len(items_tx) if tx_observed else None,
                        transactions_more=bool(isinstance(txs, dict) and txs.get("next_page_params")) if tx_observed else None,
                        calls_to_launch_factory=len(launches) if tx_observed else None, contracts_created=contracts_created if tx_observed else None)
        tt = self.explorer_json(by_id, out, "explorer-signer-token-transfers")
        tt_observed = isinstance(tt, list) or isinstance(mapping(tt).get("items"), list)
        items_tt = sequence(tt.get("items") if isinstance(tt, dict) else tt)
        outbound, inbound, other_tokens = 0, 0, set()
        for item in items_tt[:50]:
            if not isinstance(item, dict):
                continue
            token = str(mapping(item.get("token")).get("address") or mapping(item.get("token")).get("address_hash") or "").lower()
            src = self.party(item.get("from"))["address"]
            if token != self.target["address"]:
                if re.fullmatch(r"0x[0-9a-f]{40}", token):
                    other_tokens.add(token)
                continue
            if src == signer:
                outbound += 1
            elif self.party(item.get("to"))["address"] == signer:
                inbound += 1
        activity.update(token_transfers_captured=len(items_tt) if tt_observed else None,
                        token_transfers_more=bool(isinstance(tt, dict) and tt.get("next_page_params")) if tt_observed else None,
                        target_outbound=outbound if tt_observed else None, target_inbound=inbound if tt_observed else None,
                        other_tokens_touched=len(other_tokens) if tt_observed else None,
                        status="ok" if tx_observed and tt_observed else "partial" if tx_observed or tt_observed else "unavailable")
        self.creator_activity = activity

    def parse_pairs(self, body):
        rows = body if isinstance(body, list) else sequence(mapping(body).get("pairs"))
        seen = set()
        for pair in rows:
            try:
                base, quote = pair["baseToken"]["address"].lower(), pair["quoteToken"]["address"].lower()
            except (KeyError, TypeError, AttributeError):
                continue
            if self.target["address"] not in (base, quote):
                continue
            if pair.get("chainId") and pair["chainId"] != self.registry.get("dexscreener"):
                continue
            key = str(pair.get("pairAddress", "")).lower()
            if not re.fullmatch(r"0x[0-9a-f]{40}|0x[0-9a-f]{64}", key) or key in seen:
                continue
            if not re.fullmatch(r"0x[0-9a-f]{40}", base) or not re.fullmatch(r"0x[0-9a-f]{40}", quote) or int(base, 16) == 0 or int(quote, 16) == 0:
                continue
            seen.add(key)
            labels = [str(x).lower() for x in sequence(pair.get("labels"))]
            version = "v4" if "v4" in labels else "v3" if "v3" in labels else "v2" if ("v2" in labels or not labels) else "unknown"
            other = quote if base == self.target["address"] else base
            other_meta = pair["quoteToken"] if base == self.target["address"] else pair["baseToken"]
            self.pairs.append({"pair": key, "is_pool_id": len(key) == 66, "dex": pair.get("dexId"), "version": version, "labels": labels,
                               "counter_asset": other, "counter_symbol": other_meta.get("symbol"), "target_is_base": base == self.target["address"],
                               "liquidity_usd": nonnegative(mapping(pair.get("liquidity")).get("usd")),
                               "volume_h24": nonnegative(mapping(pair.get("volume")).get("h24")),
                               "txns_h24": {k: nonnegative(mapping(mapping(pair.get("txns")).get("h24")).get(k)) for k in ("buys", "sells")},
                               "price_usd": pair.get("priceUsd"), "fdv": nonnegative(pair.get("fdv")),
                               "market_cap": nonnegative(pair.get("marketCap")), "created_at_ms": nonnegative(pair.get("pairCreatedAt")), "url": pair.get("url")})
            info = mapping(pair.get("info"))
            for site in sequence(info.get("websites")):
                if isinstance(mapping(site).get("url"), str) and site["url"] not in self.links["websites"]:
                    self.links["websites"].append(site["url"])
            for social in sequence(info.get("socials")):
                if isinstance(mapping(social).get("url"), str) and social["url"] not in self.links["socials"]:
                    self.links["socials"].append(social["url"])
        self.pairs.sort(key=lambda p: -(p["liquidity_usd"] or 0))
        self.discovery["dexscreener"]["pairs"] = len(self.pairs)

    def abi_getters(self, cap=40):
        if not isinstance(self.abi, list):
            return []
        skip = {sig.split("(")[0] for sig in presets.CONTROL_GETTERS} | {"name", "symbol", "decimals", "totalSupply"}
        found = []
        for item in self.abi:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            if item.get("type") == "function" and item.get("stateMutability") in ("view", "pure") and not item.get("inputs") and item.get("name") not in skip \
                    and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item["name"]) and len(item.get("outputs") or []) <= 3:
                found.append(item["name"] + "()")
        found.sort(key=lambda sig: (not any(k in sig.lower() for k in GETTER_PRIORITY), sig))
        return found[:cap]

    # ----- phases -----------------------------------------------------------------------
    def head_failure(self, discovery, chain, stage):
        """Explain a failed chain/head read precisely: transport failure and chain mismatch are different problems."""
        row = discovery.evidence[-1] if discovery.evidence else {}
        acquisition = row.get("acquisition", {})
        if chain is not None:
            try:
                served = quantity(chain)
            except (Invalid, ValueError, TypeError):
                served = None
            return {"stage": stage, "category": "chain_mismatch", "rpc_chain_id": served, "requested_chain_id": self.target["chain_id"],
                    "message": f"The RPC endpoint answered eth_chainId with chain {served}, not the requested chain {self.target['chain_id']}.",
                    "next_step": f"Point the RPC URL variable (ROBINHOOD_DRPC_URL or --rpc-url-env) at an endpoint for chain {self.target['chain_id']} "
                                 "and re-run the identical start command; this run directory accepts the restart."}
        category = acquisition.get("failure_category") or row.get("observation_status") or "unknown"
        statuses = {k: v.get("status") for k, v in self.discovery.items() if isinstance(v, dict)}
        # Only a capture that was actually sent records its url; registry gaps (no slug, no JSON explorer) never reach the network.
        attempted = {k: statuses[k] for k, v in self.discovery.items() if isinstance(v, dict) and v.get("url")}
        if stage == "chain_check" and self.web and attempted and category in NO_RESPONSE and all(v in NO_RESPONSE for v in attempted.values()):
            # Nothing answered anywhere: web discovery hosts and the RPC endpoint all failed before any response.
            # That is the host denying outbound network to this command, not a provider or chain problem.
            return {"stage": stage, "category": "network_unavailable", "transport_category": category, "discovery": statuses,
                    "http_status": acquisition.get("http_status"), "rpc_error_code": acquisition.get("rpc_error_code"), "evidence": row.get("artifact"),
                    "message": "No host answered: web discovery (" + ", ".join(sorted(attempted)) + ") and the RPC endpoint all failed before any response "
                               + f"({category}). The host denied outbound network to this command; the endpoint and the chain were not verified.",
                    "next_step": "Request network permission for the start command itself, then re-run the identical start command once in the same run "
                                 "directory (it accepts the restart and keeps its session ledger). Do not switch providers, try other environment "
                                 "variable names or read helper source."}
        return {"stage": stage, "category": category, "http_status": acquisition.get("http_status"), "rpc_error_code": acquisition.get("rpc_error_code"),
                "evidence": row.get("artifact"),
                "message": "The RPC endpoint could not be reached or did not answer " + ("eth_chainId" if stage == "chain_check" else "eth_blockNumber")
                           + f" ({category}). This is a transport failure, not a chain mismatch; the endpoint was not verified.",
                "next_step": "Re-run the identical start command once; this run directory accepts the restart. If the runtime explicitly reports a "
                             "sandbox network denial, retry with authorized network access. Do not read helper "
                             "source or try other environment variable names; the URL in the private env is used as configured."}

    def head(self):
        discovery = Collector(self.run / "head", self.cache, self.transport, self.endpoint_label, max_requests=3,
                              timeout=self.remaining_timeout(30), session=self.session)
        discovery.root.mkdir(parents=True)
        discovery.target = self.target
        discovery.deadline = time.monotonic() + self.remaining_timeout(30)
        if isinstance(self.transport, HttpTransport):
            self.transport.deadline = discovery.deadline
        chain = discovery.request("chain", "eth_chainId", [], cached=False)
        if chain is None or quantity(chain) != self.target["chain_id"]:
            raise StartFailure(self.head_failure(discovery, chain, "chain_check"))
        head = discovery.request("head", "eth_blockNumber", [], cached=False)
        if head is None:
            raise StartFailure(self.head_failure(discovery, None, "head_block"))
        pinned = max(1, quantity(head) - PIN_LAG)
        write_new(self.run / "head" / "head.json", {"chain_id": quantity(chain), "head": quantity(head), "pinned": pinned, "pin_lag": PIN_LAG, "captured_at_utc": stamp()})
        return pinned

    def phase1(self, head):
        getters = self.abi_getters()
        for sig in [*getters, *presets.CONTROL_GETTERS, *presets.METADATA_SIGS.values(), *presets.V3_POOL_GETTERS, *presets.V2_POOL_GETTERS, *presets.SAFE_GETTERS]:
            self.names[selector(sig)] = sig.split("(")[0]
        queries = presets.token_phase1(self.target, "current", getters, control_getters=self.control_getters())
        plan = presets.plan(self.target, {"current": head}, queries)
        write_new(self.run / "phase1-plan.json", plan)
        return self.collect("phase1", plan, max_requests=len(queries) + 4)

    def phase1_facts(self):
        controls = {"owner": None, "paused": None, "eip1967": {}, "getters": {}, "reverted_getters": [], "failed_getters": []}
        candidates = {}
        for alias, (row, value, status) in self.decoded.items():
            if not alias.startswith("token-"):
                continue
            name = alias[len("token-"):]
            if status != "ok":
                if not name.startswith("eip1967-"):
                    # A revert is the chain's answer (no such function or guarded); a transport/RPC failure is a gap.
                    controls["reverted_getters" if status == "reverted" else "failed_getters"].append(name)
                continue
            if name.startswith("eip1967-"):
                word = int(value, 16)
                controls["eip1967"][name[len("eip1967-"):]] = ("0x" + format(word, "040x")) if 0 < word < 2 ** 160 else None
                if 0 < word < 2 ** 160:
                    candidates["proxy-" + name[len("eip1967-"):]] = "0x" + format(word, "040x")
                continue
            decoded = decode_result(row["query"]["params"][0]["data"][2:10].lower(), value)
            controls["getters"][name] = {"decoded": decoded, "evidence": alias}
            if name == "owner":
                controls["owner"] = decoded.get("address")
            if name == "paused":
                controls["paused"] = decoded.get("bool")
            candidate = decoded.get("address")
            if candidate and candidate not in (self.target["address"], DEAD) and looks_like_address(int(candidate, 16), name):
                candidates[name] = candidate
            elif candidate and not looks_like_address(int(candidate, 16), name):
                decoded.pop("address", None)
        runtime = self.value("runtime")
        clone = classify_clone(runtime) if isinstance(runtime, str) else {"status": "unavailable"}
        if clone.get("implementation"):
            candidates["clone-implementation"] = clone["implementation"]
        controls["clone"] = clone
        controls["code_bytes"] = len(bytes.fromhex(runtime[2:])) if isinstance(runtime, str) else None
        metadata = {}
        for field in ("name", "symbol", "decimals", "total_supply"):
            raw = self.value("metadata-" + field)
            decoded = decode_result(selector(presets.METADATA_SIGS[field]), raw) if raw else {}
            metadata[field] = decoded.get("string") if field in ("name", "symbol") else decoded.get("int")
        if metadata["decimals"] is not None and not 0 <= metadata["decimals"] <= 36:
            metadata["decimals_raw"] = metadata["decimals"]
            metadata["decimals"] = None  # nonstandard; keep raw for review, never exponentiate it
        return controls, candidates, metadata

    def phase2(self, head, candidates, metadata):
        pin = "current"
        queries = []
        pools = []
        for index, pair in enumerate(self.pairs[:6]):
            prefix = "pool" + str(index + 1)
            if pair["is_pool_id"] or pair["version"] == "v4":
                state_view = (self.registry.get("uniswap_v4") or {}).get("state_view")
                if state_view and pair["is_pool_id"]:
                    queries += presets.v4_queries(prefix, pin, state_view, pair["pair"])
                    pools.append({**pair, "prefix": prefix, "read": "v4_state_view", "state_view": state_view})
                else:
                    pools.append({**pair, "prefix": prefix, "read": "unsupported_v4_without_state_view"})
                continue
            queries += presets.pool_queries(prefix, pin, pair["pair"], "v2" if pair["version"] == "v2" else "v3")
            pools.append({**pair, "prefix": prefix, "read": pair["version"]})
        for extra in self.extra_pools:
            if extra not in {p["pair"] for p in pools}:
                prefix = "pool" + str(len(pools) + 1)
                queries += presets.pool_queries(prefix, pin, extra, "v3")
                pools.append({"pair": extra, "is_pool_id": False, "dex": "user-supplied", "version": "v3", "prefix": prefix, "read": "v3", "counter_asset": None})
        holders = {"dead": DEAD}
        for pool in pools:
            if not pool["is_pool_id"]:
                holders[pool["prefix"]] = pool["pair"]
        if self.creation.get("creator"):
            holders["creator"] = self.creation["creator"]
        for name, holder in self.holders.items():
            holders[presets.label(name)] = holder
        for name, contract in list(candidates.items())[:10]:
            holders["arch-" + presets.label(name)] = contract
        queries += presets.balance_queries("bal", pin, self.target["address"], holders)
        architecture = {presets.label(name): contract for name, contract in list(candidates.items())[:10]}
        nfpm = (self.registry.get("uniswap_v3") or {}).get("nonfungible_position_manager")
        if nfpm:
            architecture["nfpm"] = nfpm
        counter_assets = {p["counter_asset"] for p in pools if p.get("counter_asset")}
        for asset in list(counter_assets)[:3]:
            architecture["quote-" + asset[2:10]] = asset
            queries += presets.getter_queries("quote-" + asset[2:10], pin, asset, ["decimals()", "symbol()"])
        # Counter-asset reserves held by each address-based pool: the depth behind the quotes, at the pin.
        for pool in pools:
            if not pool["is_pool_id"] and pool.get("counter_asset") and pool["counter_asset"] in set(list(counter_assets)[:3]):
                queries += presets.balance_queries("cbal", pin, pool["counter_asset"], {pool["prefix"]: pool["pair"]})
        # Top indexed holders (explorer page one) become pinned balance reads plus a code check each.
        known = {self.target["address"], DEAD, *holders.values()}
        self.holder_exclusions = sorted(known)
        top = []
        for entry in self.indexed_holders:
            if entry["address"] in known or len(top) >= TOP_HOLDER_READS:
                continue
            known.add(entry["address"])
            top.append(entry)
        self.top_holder_reads = {}
        for n, entry in enumerate(top, 1):
            name = presets.label(f"{n}-{entry['address'][2:8]}")
            self.top_holder_reads[name] = entry
            queries += presets.balance_queries("hold", pin, self.target["address"], {name: entry["address"]})
            queries.append(presets.code("hold-" + name + "-runtime", pin, entry["address"]))
        queries += presets.architecture_queries("arch", pin, architecture)
        pins = {"current": head}
        receipt_block = None
        transactions = {}
        if self.creation.get("tx"):
            receipt_block = self.lookup_block(self.creation["tx"])
            if receipt_block:
                transactions[self.creation["tx"]] = receipt_block
        for tx in self.sell_candidates[:2]:
            if tx not in transactions:
                block = self.lookup_block(tx)
                if block:
                    transactions[tx] = block
        self.sale_txs = [tx for tx in transactions if tx != self.creation.get("tx")]
        if transactions:
            extra_pins, receipt_rows = presets.receipt_queries(transactions)
            pins.update(extra_pins)
            queries += receipt_rows
        plan = presets.plan(self.target, pins, queries)
        write_new(self.run / "phase2-plan.json", plan)
        result = self.collect("phase2", plan, max_requests=len(queries) + 2 * len(pins) + 2)
        return result, pools, holders, architecture

    def lookup_block(self, tx_hash):
        """Uncached discovery read; not imported as pinned evidence (a receipt needs its own pin)."""
        need(isinstance(tx_hash, str) and re.fullmatch(r"0x[0-9a-f]{64}", tx_hash), "transaction hash must be 32 lowercase hex bytes")
        root = self.run / ("lookup-" + tx_hash[2:10])
        n = 2
        while root.exists():  # a hash looked up earlier in this run (a sale candidate) gets its own directory; evidence is never overwritten
            root = self.run / ("lookup-" + tx_hash[2:10] + "-" + str(n))
            n += 1
        collector = Collector(root, self.cache, self.transport, self.endpoint_label, max_requests=2, timeout=self.remaining_timeout(20), session=self.session)
        collector.root.mkdir(parents=True)
        collector.target = self.target
        collector.deadline = time.monotonic() + self.remaining_timeout(20)
        receipt = collector.request("receipt", "eth_getTransactionReceipt", [tx_hash], cached=False)
        if isinstance(receipt, dict) and receipt.get("blockNumber"):
            return quantity(receipt["blockNumber"])
        return None

    def phase2_facts(self, pools, holders, architecture, metadata):
        decimals = metadata.get("decimals")
        supply = metadata.get("total_supply")
        out_pools = []
        for pool in pools:
            prefix = pool["prefix"]
            entry = {k: pool.get(k) for k in ("pair", "is_pool_id", "dex", "version", "labels", "counter_asset", "counter_symbol", "target_is_base",
                                              "liquidity_usd", "volume_h24", "txns_h24", "price_usd", "fdv", "market_cap", "created_at_ms", "url", "read", "prefix")}
            entry["evidence"] = {}
            if pool["read"] == "v4_state_view":
                slot0 = self.value(prefix + "-getSlot0")
                if slot0:
                    entry["slot0"] = decode_result(selector("getSlot0(bytes32)"), slot0)
                    entry["fee"] = entry["slot0"].get("lpFee")
                    entry["evidence"]["slot0"] = prefix + "-getSlot0"
                liquidity = self.word_value(prefix + "-getLiquidity")
                entry["liquidity"], entry["evidence"]["liquidity"] = liquidity, prefix + "-getLiquidity"
            elif pool["read"] in ("v2", "v3", "unknown"):
                for name in ("token0", "token1", "factory"):
                    entry[name] = self.address_value(prefix + "-" + name)
                    entry["evidence"][name] = prefix + "-" + name
                if pool["read"] == "v2":
                    reserves = self.value(prefix + "-getReserves")
                    if reserves:
                        entry["reserves"] = decode_result(selector("getReserves()"), reserves)
                        entry["evidence"]["reserves"] = prefix + "-getReserves"
                    entry["lp_total_supply"] = self.word_value(prefix + "-totalSupply")
                else:
                    entry["fee"] = self.word_value(prefix + "-fee")
                    entry["liquidity"] = self.word_value(prefix + "-liquidity")
                    slot0 = self.value(prefix + "-slot0")
                    if slot0:
                        entry["slot0"] = decode_result(selector("slot0()"), slot0)
                    entry["tick_spacing"] = self.word_value(prefix + "-tickSpacing")
                    entry["evidence"].update({"fee": prefix + "-fee", "liquidity": prefix + "-liquidity", "slot0": prefix + "-slot0"})
                balance = self.word_value("bal-" + prefix)
                entry["target_balance_raw"] = balance
                entry["target_balance"] = decimal_string(balance, decimals)
                entry["target_balance_pct_supply"] = round(balance / supply * 100, 4) if balance is not None and supply else None
                entry["evidence"]["target_balance"] = "bal-" + prefix
                counter = self.word_value("cbal-" + prefix)
                if counter is not None and pool.get("counter_asset"):
                    counter_decimals = self.word_value("quote-" + pool["counter_asset"][2:10] + "-decimals")
                    entry["counter_balance_raw"] = counter
                    entry["counter_balance"] = decimal_string(counter, counter_decimals) if counter_decimals is not None else None
                    entry["evidence"]["counter_balance"] = "cbal-" + prefix
                code = self.value(prefix + "-runtime")
                entry["code_bytes"] = len(bytes.fromhex(code[2:])) if isinstance(code, str) else None
                entry["target_in_pool"] = self.target["address"] in (entry.get("token0"), entry.get("token1")) if entry.get("token0") else None
            out_pools.append(entry)
        balances = {}
        for name, holder in holders.items():
            raw = self.word_value("bal-" + presets.label(name))
            balances[name] = {"address": holder, "raw": raw, "decimal": decimal_string(raw, decimals),
                              "pct_supply": round(raw / supply * 100, 4) if raw is not None and supply else None, "evidence": "bal-" + presets.label(name)}
        arch = []
        owners = {}
        for name, contract in architecture.items():
            base = presets.label("arch-" + name)
            code = self.value(base + "-runtime")
            owner = self.address_value(base + "-owner")
            impl = self.word_value(base + "-eip1967-implementation")
            item = {"label": name, "address": contract, "code_bytes": len(bytes.fromhex(code[2:])) if isinstance(code, str) else None,
                    "owner": owner, "eip1967_implementation": ("0x" + format(impl, "040x")) if impl and impl < 2 ** 160 else None,
                    "eip1967_implementation_raw": impl, "implementation_status": self.status(base + "-eip1967-implementation"),
                    "reverted": self.reverted(base, ("owner",)),
                    "evidence": {"runtime": base + "-runtime", "owner": base + "-owner", "implementation_slot": base + "-eip1967-implementation"}}
            if name.startswith("quote-"):
                item["decimals"] = self.word_value(name + "-decimals")
                sym = self.value(name + "-symbol")
                item["symbol"] = decode_result("95d89b41", sym).get("string") if sym else None
            arch.append(item)
            if owner and owner not in (self.target["address"], DEAD):
                owners[name] = owner
        top_holders = []
        for name, entry in getattr(self, "top_holder_reads", {}).items():
            raw = self.word_value("hold-" + name)
            code = self.value("hold-" + name + "-runtime")
            top_holders.append({"address": entry["address"], "indexer_value_raw": entry.get("value_raw"), "indexer_is_contract": entry.get("is_contract"),
                                "indexer_name": entry.get("name"), "raw": raw, "decimal": decimal_string(raw, decimals),
                                "pct_supply": round(raw / supply * 100, 4) if raw is not None and supply else None,
                                "code_bytes": len(bytes.fromhex(code[2:])) if isinstance(code, str) else None,
                                "account_kind": account_code_kind(code),
                                "evidence": {"balance": "hold-" + name, "runtime": "hold-" + name + "-runtime"}})
        self.top_holders = top_holders
        pool_addresses = self.pool_destinations(out_pools)
        receipts = []
        position_ids = []
        nfpm = (self.registry.get("uniswap_v3") or {}).get("nonfungible_position_manager")
        for alias, (row, value, status) in list(self.decoded.items()):
            if alias.startswith("receipt-") and status == "ok" and isinstance(value, dict):
                item = {"tx": row["tx_hash"], "status": quantity(value.get("status", "0x0")), "block": quantity(value["blockNumber"]),
                        "from": (value.get("from") or "").lower() or None, "to": (value.get("to") or "").lower() or None,
                        "logs": len(value.get("logs", [])), "transfers": transfers(value)[:20], "evidence": alias}
                item["role"] = "creation" if item["tx"] == self.creation.get("tx") else "sale_candidate" if item["tx"] in getattr(self, "sale_txs", []) else "other"
                if item["role"] == "creation" and item["from"]:
                    self.creation["signer"] = item["from"]
                    self.creation["block"] = item["block"]
                    self.creation["factory"] = item["to"]
                if item["role"] == "sale_candidate":
                    item["sale"] = self.decode_sale(value, item, pool_addresses, decimals, out_pools)
                own_ids = []
                for log in value.get("logs", []):
                    if nfpm and log["address"].lower() == nfpm and log["topics"] and log["topics"][0].lower() in POSITION_TOPICS:
                        idx = 3 if log["topics"][0].lower() == topic("Transfer(address,address,uint256)") else 1
                        if len(log["topics"]) > idx:
                            own_ids.append(int(log["topics"][idx], 16))
                item["nfpm_position_ids"] = sorted(set(own_ids))
                position_ids.extend(own_ids)
                receipts.append(item)
        receipts.sort(key=lambda r: (r.get("role") != "creation", r["block"]))
        return out_pools, balances, arch, owners, receipts, sorted(set(position_ids))

    def phase3(self, head, pools, metadata, owners, position_ids):
        pin = "current"
        queries = []
        decimals = metadata.get("decimals")
        quoter = (self.registry.get("uniswap_v3") or {}).get("quoter_v2")
        canonical = next((p for p in pools if p["read"] == "v3" and p.get("fee") and p.get("counter_asset") and p.get("target_in_pool")), None)
        quotes_meta = None
        if quoter and canonical and decimals is not None:
            amounts = [{"label": str(size), "raw": size * 10 ** decimals} for size in self.quote_sizes]
            queries += presets.quote_queries("quote", pin, quoter, self.target["address"], canonical["counter_asset"], canonical["fee"], amounts)
            quotes_meta = {"quoter": quoter, "pool": canonical["pair"], "fee": canonical["fee"], "token_out": canonical["counter_asset"], "sizes": self.quote_sizes}
        nfpm = (self.registry.get("uniswap_v3") or {}).get("nonfungible_position_manager")
        if nfpm and position_ids:
            queries += presets.position_queries("pos", pin, nfpm, position_ids[:6])
        for name, owner in list(owners.items())[:4]:
            base = presets.label("owner-" + name)
            queries.append(presets.code(base + "-runtime", pin, owner))
            queries += presets.safe_queries(base, pin, owner)
            queries.append(presets.call(base + "-owner", pin, owner, presets.encode("owner()")))
        if not queries:
            return None, quotes_meta
        plan = presets.plan(self.target, {"current": head}, queries)
        write_new(self.run / "phase3-plan.json", plan)
        return self.collect("phase3", plan, max_requests=len(queries) + 4), quotes_meta

    def phase3_facts(self, quotes_meta, pools, metadata, owners, position_ids):
        decimals = metadata.get("decimals")
        quotes = []
        if quotes_meta:
            quote_decimals = None
            for alias, (row, value, status) in self.decoded.items():
                if alias.startswith("quote-") and alias.endswith("-decimals") and status == "ok" and row["address"] == quotes_meta["token_out"]:
                    quote_decimals = int(value, 16)
            baseline = None
            for size in quotes_meta["sizes"]:
                alias = "quote-" + str(size)
                raw = self.value(alias)
                item = {"size_tokens": size, "amount_in_raw": size * 10 ** decimals, "evidence": alias, "status": self.decoded.get(alias, (None, None, "missing"))[2]}
                if raw:
                    decoded = decode_result("c6a5026a", raw)
                    out = decoded.get("amountOut")
                    item.update(amount_out_raw=out, amount_out=decimal_string(out, quote_decimals) if quote_decimals is not None else None,
                                quote_decimals=quote_decimals, ticks_crossed=decoded.get("initializedTicksCrossed"))
                    per_token = out / size if out is not None else None
                    if per_token is not None and baseline is None:
                        baseline = per_token
                    item["impact_vs_smallest_pct"] = round((per_token / baseline - 1) * 100, 4) if per_token is not None and baseline else None
                quotes.append(item)
        positions = []
        nfpm = (self.registry.get("uniswap_v3") or {}).get("nonfungible_position_manager")
        for token_id in position_ids[:6]:
            base = presets.label("pos-" + str(token_id))
            raw = self.value(base + "-positions")
            item = {"id": token_id, "manager": nfpm, "owner": self.address_value(base + "-ownerOf"), "approved": self.address_value(base + "-getApproved"),
                    "approved_raw": self.word_value(base + "-getApproved"),
                    "evidence": {"positions": base + "-positions", "owner": base + "-ownerOf", "approved": base + "-getApproved"}}
            if raw:
                decoded = decode_result("99fbab88", raw)
                item.update({k: decoded.get(k) for k in ("token0", "token1", "fee", "tickLower", "tickUpper", "liquidity", "tokensOwed0", "tokensOwed1")})
                pool = next((p for p in pools if p.get("token0") and {p["token0"], p["token1"]} == {decoded.get("token0"), decoded.get("token1")} and p.get("fee") == decoded.get("fee")), None)
                if pool and pool.get("liquidity") and pool.get("slot0"):
                    tick = pool["slot0"].get("tick")
                    lower, upper = decoded.get("tickLower"), decoded.get("tickUpper")
                    in_range = lower is not None and upper is not None and tick is not None and lower <= tick < upper
                    item["pool"] = pool["pair"]
                    item["in_range"] = in_range
                    item["pct_of_pool_active_liquidity"] = round(decoded["liquidity"] / pool["liquidity"] * 100, 4) if in_range and decoded.get("liquidity") is not None else 0.0 if decoded.get("liquidity") is not None else None
            positions.append(item)
        owner_details = {}
        for name, owner in list(owners.items())[:4]:
            base = presets.label("owner-" + name)
            code = self.value(base + "-runtime")
            owners_raw = self.value(base + "-getOwners")
            modules_page = decode_module_page(self.value(base + "-getModulesPaginated"))
            owner_details[name] = {"address": owner, "code_bytes": len(bytes.fromhex(code[2:])) if isinstance(code, str) else None,
                                   "safe_owners": decode_result("a0e67e2b", owners_raw).get("addresses") if owners_raw else None,
                                   "safe_owner_count": decode_result("a0e67e2b", owners_raw).get("count") if owners_raw else None,
                                   "safe_threshold": self.word_value(base + "-getThreshold"), "owner": self.address_value(base + "-owner"),
                                   # Modules and the guard are the Safe powers a signer count does not show: a module moves assets without signatures.
                                   "safe_modules": modules_page["modules"] if modules_page else None,
                                   "safe_modules_truncated": bool(modules_page and modules_page["next"] != presets.SAFE_SENTINEL),
                                   "safe_guard": self.address_value(base + "-guard"), "safe_guard_read": self.status(base + "-guard") == "ok",
                                   "reverted": self.reverted(base, ("getOwners", "getThreshold", "owner", "getModulesPaginated")),
                                   "evidence": {"runtime": base + "-runtime", "getOwners": base + "-getOwners", "getThreshold": base + "-getThreshold", "owner": base + "-owner",
                                                "getModulesPaginated": base + "-getModulesPaginated", "guard": base + "-guard"}}
        return quotes, positions, owner_details

    def phase4(self, head, receipts, positions, owner_details, architecture_addresses):
        """Code reads for actors discovered late (creator, recipients, position owners) so notes can name them."""
        actors = {}
        if self.creation.get("creator"):
            actors["creator"] = self.creation["creator"]
        for receipt in receipts:
            for key in ("from", "to"):
                if receipt.get(key):
                    actors[presets.label("tx-" + key + "-" + receipt[key][2:8])] = receipt[key]
            for transfer in receipt.get("transfers", [])[:6]:
                for key in ("from", "to"):
                    if int(transfer[key], 16) >= SMALL_ADDRESS_FLOOR:
                        actors[presets.label("xfer-" + key + "-" + transfer[key][2:8])] = transfer[key]
        for position in positions:
            for key in ("owner", "approved"):
                if position.get(key):
                    actors[presets.label("pos-" + key + "-" + position[key][2:8])] = position[key]
        for name, detail in owner_details.items():
            for owner in detail.get("safe_owners") or []:
                if owner:
                    actors[presets.label("signer-" + owner[2:8])] = owner
        # A position custodian keeps its actor row even when the token also names it as an architecture contract:
        # its withdrawal terms are read here, not left to a coordinator preset.
        custodians = {}
        for position in positions:
            if position.get("owner") and position["owner"] not in (self.target["address"], DEAD):
                custodians.setdefault(presets.label("pos-owner-" + position["owner"][2:8]), position["owner"])
        known = {self.target["address"], DEAD, *architecture_addresses} - set(custodians.values())
        actors = {k: v for k, v in actors.items() if v not in known}
        # Position custodians lead the bounded list: a receipt-heavy run (three receipts with six transfers each) must never
        # push a custodian past the ten-actor cap, or its withdrawal getters would go unread (a live PONS run did exactly that).
        custodian_addrs = set(custodians.values())
        actors = {**{k: v for k, v in actors.items() if v in custodian_addrs}, **actors}
        seen = set()
        unique = {}
        for name, addr in actors.items():
            if addr not in seen:
                seen.add(addr)
                unique[name] = addr
        unique = dict(list(unique.items())[:10])
        if not unique:
            return None, {}
        queries = [presets.code("actor-" + presets.label(name), "current", addr) for name, addr in unique.items()]
        plan = presets.plan(self.target, {"current": head}, queries)
        write_new(self.run / "phase4-plan.json", plan)
        result = self.collect("phase4", plan, max_requests=len(queries) + 4)
        details = {}
        for name, addr in unique.items():
            code = self.value("actor-" + presets.label(name))
            details[name] = {"address": addr, "code_bytes": len(bytes.fromhex(code[2:])) if isinstance(code, str) else None,
                             "evidence": "actor-" + presets.label(name)}
        # A position custodian is matched by address (its actor row may carry a receipt or transfer label); one with code
        # answers its withdrawal getters in a second bounded collection, an EOA owner has none to answer.
        probe = {name: addr for name, addr in unique.items() if addr in custodian_addrs and (details[name]["code_bytes"] or 0) > 0}
        for name, addr in unique.items():
            if addr in custodian_addrs:
                details[name]["role"] = "position_custodian" if name in probe else "position_owner_without_code"
        if probe:
            getter_ids, queries = {}, []
            for name, addr in probe.items():
                rows = presets.getter_queries("actor-" + presets.label(name), "current", addr, presets.LOCKER_GETTERS)
                getter_ids[name] = {sig.split("(")[0]: row["id"] for sig, row in zip(presets.LOCKER_GETTERS, rows)}
                queries += rows
            plan = presets.plan(self.target, {"current": head}, queries)
            write_new(self.run / "phase4b-plan.json", plan)
            getters_result = self.collect("phase4b", plan, max_requests=len(queries) + 4)
            for name in probe:
                details[name]["getters_read"] = getters_result["status"] in ("complete", "partial")
                getters = {}
                for sig in presets.LOCKER_GETTERS:
                    label = sig.split("(")[0]
                    raw = self.value(getter_ids[name][label])
                    if raw is not None:
                        getters[label] = {"decoded": decode_result(selector(sig), raw), "evidence": getter_ids[name][label]}
                details[name].update(getters=getters, reverted=[label for label, alias in getter_ids[name].items() if self.status(alias) == "reverted"])
        return result, details

    def pool_destinations(self, pools):
        """Addresses that receive tokens in a sale: v2/v3 pool contracts, plus the v4 PoolManager when v4 pools are indexed."""
        out = {p["pair"] for p in pools if not p.get("is_pool_id")}
        if any(p.get("is_pool_id") or p.get("version") == "v4" for p in pools):
            manager = (self.registry.get("uniswap_v4") or {}).get("pool_manager")
            if manager:
                out.add(manager)
        return out

    def decode_sale(self, receipt, item, pool_addresses, decimals, pool_details=None):
        return decode_sale(self.target["address"], receipt, item, pool_addresses, decimals, pool_details=pool_details)

    # ----- assembly ---------------------------------------------------------------------
    def assemble(self):
        from bundle_assemble import add_artifact, import_collection, source_match, read_draft
        draft = self.run / "draft"
        imported = []
        for entry in self.collections:
            if entry["status"] in ("complete", "partial"):
                import_collection(draft, self.run / entry["name"], self.synthetic)
                imported.append(entry["name"])
        registered_docs = []
        try:
            from web_capture import register
            records = []
            for path in sorted((self.run / "discovery").glob("*.json")):
                record = read_json(path)
                if record.get("id") in ("sourcify-correspondence",) or "url" not in record:
                    continue
                record["_dir"] = str(self.run / "discovery")
                records.append(record)
            if records and imported:
                registered_docs = register(draft, records)
        except (Invalid, ValueError, OSError, KeyError) as exc:
            registered_docs = ["registration_failed: " + str(exc)[:120]]
        source = {"status": self.discovery["sourcify"].get("status", "not_attempted")}
        if self.pin is not None and self.source_body and isinstance(self.source_body, dict) and self.discovery["sourcify"].get("status") == "ok":
            try:
                d = read_draft(draft)
                pin = next(p for p in d["pins"] if p["number"] == self.pin["number"])
                runtime = next(e for e in d["evidence"] if e["address"] == self.target["address"] and e["query"].get("method") == "eth_getCode" and e["pin_id"] == pin["id"])
                raw_path = self.run / "discovery" / "sourcify-correspondence.raw"
                descriptor = {"id": "sourcify-correspondence", "kind": "document", "target": dict(self.target), "chain_id": self.target["chain_id"],
                              "address": self.target["address"], "pin_id": pin["id"], "tx_hash": None, "captured_at_utc": self.discovery["sourcify"]["captured_at_utc"],
                              "endpoint_label": "sourcify-dev", "query": {"operation": "sourcify_v2_contract_lookup", "url": self.discovery["sourcify"]["url"],
                                                                          "source_urls": [self.discovery["sourcify"]["url"]], "capture_mode": "downloaded_response"},
                              "decoding_basis": "Sourcify-published compilation and sources; correspondence established only by the bound comparison artifact",
                              "coverage": "Single bounded public API capture", "observation_status": "ok"}
                add_artifact(draft, raw_path, descriptor)
                if self.source_body.get("sources") and self.source_body.get("stdJsonInput"):
                    try:
                        row = source_match(draft, runtime["id"], "sourcify-correspondence", "token-match")
                        comparison = read_json(draft / row["artifact"])
                        source.update(status=comparison["status"], compiler=comparison.get("compiler_version"), contract=comparison.get("contract_identifier"),
                                      evidence=["sourcify-correspondence", "token-match"])
                    except (Invalid, ValueError, KeyError) as exc:
                        source.update(status="unsupported_correspondence", reason=str(exc)[:200], evidence=["sourcify-correspondence"])
                else:
                    source.update(status="sources_unavailable", evidence=["sourcify-correspondence"])
            except (StopIteration, Invalid, ValueError, OSError, KeyError) as exc:
                source.update(status="registration_failed", reason=str(exc)[:200])
        return imported, source, registered_docs

    def maturity(self, receipts):
        """Age, indexed adoption counts and aggregate indexed market figures, each labeled with its source."""
        creation = next((r for r in receipts if r.get("role") == "creation"), None)
        out = {}
        if creation and self.pin:
            launch_ts = self.pins_seen.get(creation["block"])
            out.update(launch_block=creation["block"], launch_time_utc=launch_ts)
            try:
                from datetime import datetime, timezone
                a = datetime.strptime(launch_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                b = datetime.strptime(self.pin["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                out["age_days"] = round((b - a).total_seconds() / 86400, 1)
            except (TypeError, ValueError):
                pass
        if self.counters:
            out.update({k: v for k, v in self.counters.items()})
            out["counts_source"] = "explorer indexer (document evidence), not an RPC read"
        if self.pairs:
            out.update(indexed_pools=len(self.pairs),
                       indexed_liquidity_usd=observed_sum(p.get("liquidity_usd") for p in self.pairs),
                       indexed_volume_h24_usd=observed_sum(p.get("volume_h24") for p in self.pairs),
                       indexed_txns_h24={"buys": observed_sum(mapping(p.get("txns_h24")).get("buys") for p in self.pairs),
                                         "sells": observed_sum(mapping(p.get("txns_h24")).get("sells") for p in self.pairs)},
                       indexed_market_cap_usd=next((p.get("market_cap") for p in self.pairs if p.get("market_cap")), None),
                       market_source="Dexscreener API (document evidence), not an RPC read")
        return out

    def work_plan(self, hints):
        from bundle_assemble import SURFACES
        surfaces = [{"dimension": d, "state": "pending", "next_check": SURFACES[d] + (": review facts.json observations" if hints.get(d) == "observations" else ": no observations yet; lane or preset needed"),
                     "requests": 4 if hints.get(d) == "observations" else 8} for d in SURFACES]
        return {"surfaces": surfaces, "overhead_requests": 12, "contingency_requests": 12, "seconds_required": 420}

    def run_all(self):
        started = time.monotonic()
        self.mark("intake")
        if self.web:
            self.discover(budget_ops=8)
        else:
            self.discovery = {k: {"status": "skipped"} for k in self.discovery}
            self.goplus = {"status": "skipped"}
            write_new(self.run / "discovery.json", {"schema_version": 1, "target": self.target, "discovery": self.discovery, "pairs": [], "links": self.links, "abi_getters": []})
        self.mark("discovery")
        head = self.head()
        self.phase1(head)
        controls, candidates, metadata = self.phase1_facts()
        self.mark("phase1")
        result2, pools, holders, architecture = self.phase2(head, candidates, metadata)
        pools_out, balances, arch, owners, receipts, position_ids = self.phase2_facts(pools, holders, architecture, metadata)
        self.mark("phase2")
        if self.creation.get("signer"):
            self.capture_creator_activity(self.creation["signer"])
        result3, quotes_meta = self.phase3(head, pools_out, metadata, owners, position_ids)
        quotes, positions, owner_details = self.phase3_facts(quotes_meta, pools_out, metadata, owners, position_ids)
        self.mark("phase3")
        _, actors = self.phase4(head, receipts, positions, owner_details, {a["address"] for a in arch} | {p["pair"] for p in pools_out if not p.get("is_pool_id")})
        self.mark("phase4")
        imported, source, registered_docs = self.assemble()
        write_new(self.run / "getter-names.json", self.names)
        sales = [r["sale"] for r in receipts if r.get("role") == "sale_candidate" and r.get("sale")]
        maturity = self.maturity(receipts)
        hints = {
            "token_controls": "observations", "development_disclosure": "observations" if source.get("status") in ("matched", "mismatch") or maturity else "none",
            "canonical_lp_principal_custody": "observations" if positions or any(p.get("liquidity") for p in pools_out) else "none",
            "side_pool_removal_risk": "observations" if len(pools_out) > 1 else "none",
            "sellability_exit_depth": "observations" if quotes or sales else "none",
            "current_concentration": "observations" if balances or self.top_holders else "none",
            "historical_launch_integrity": "observations" if any(r.get("role") == "creation" for r in receipts) else "none",
            "admin_treasury_reward_custody": "observations" if arch or owner_details else "none",
            "reward_accounting_liveness": "none", "utility_redemption_rights": "none",
            "external_dependencies": "observations" if any(a["label"].startswith("quote-") for a in arch) else "none",
        }
        facts = {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "target": self.target,
                 "pin": {k: self.pin[k] for k in ("number", "hash", "timestamp_utc")} if self.pin else None,
                 "metadata": metadata, "controls": controls, "source": source, "discovery": self.discovery, "links": self.links,
                 "pools": pools_out, "quotes": quotes, "balances": balances, "architecture": arch, "owners": owner_details,
                 "receipts": receipts, "positions": positions, "creation": self.creation, "actors": actors,
                 "top_holders": self.top_holders, "sales": sales, "creator_activity": self.creator_activity, "maturity": maturity,
                 "holder_summary": holder_summary(self.top_holders, metadata.get("total_supply")),
                 "holder_selection": {"limit": TOP_HOLDER_READS, "excluded_addresses": getattr(self, "holder_exclusions", []),
                                      "basis": "First indexed page, excluding target, dead and separately requested balances; no global or beneficial-owner ranking"},
                 "indexed": {"counters": self.counters, "top_holders_captured": len(self.indexed_holders), "recent_transfers_captured": len(self.indexed_transfers),
                             "sale_candidates": list(self.sell_candidates), "indexed_trades_captured": len(self.indexed_trades),
                             "indexed_sells": [t["tx"] for t in self.indexed_trades if t["kind"] == "sell"][:10],
                             "indexed_trades_sample": self.indexed_trades[:10]},
                 "coverage_hint": hints, "collections": self.collections, "imported": imported, "document_evidence": registered_docs,
                 "session": self.session.status() if self.session is not None else None,
                 "elapsed_seconds": round(time.monotonic() - started, 3), "phases": self.log,
                 "limits": ["Decoded values are display help bound to the linked evidence; semantics, source correspondence and economic meaning require review.",
                            "Registry addresses are candidates verified only by the code reads recorded here."]}
        facts["goplus"] = goplus_facts(self.goplus, positions, self.top_holders, balances, pools_out)
        facts["recommended_presets"] = recommended_presets(facts)
        write_new(self.run / "facts.json", facts)
        write_new(self.run / "work-plan.json", self.work_plan(hints))  # the validator's plan shape, nothing else
        write_new(self.run / "recommended-presets.json", facts["recommended_presets"])
        if self.session is not None:
            try:
                plan = self.work_plan(hints)
                review = self.session.review(plan)
                facts["review"] = {"action": review["action"], "projected_total_attempts": review["projected_total_attempts"]}
                if review["action"] == "replan":
                    # The standard pipeline consumed the opening allowance; presets and lanes still need
                    # room. This is a recorded same-session revision inside the immutable ceilings, and
                    # it is printed in the pipeline summary so the coordinator sees it.
                    status = self.session.replan(plan, "Standard pipeline consumed the opening operational allowance; extend within the finite ceilings for lane charges and presets")
                    facts["review"].update(replanned=True, request_limit=status["request_limit"], remaining_requests=status["remaining_requests"],
                                           note="Operational allowance revised inside the immutable ceilings; ceilings unchanged")
            except (ValueError, Invalid) as exc:
                facts["review"] = {"action": "unavailable", "reason": str(exc)[:120]}
        self.mark("facts")
        return facts


def goplus_facts(goplus, positions, top_holders, balances, pools):
    """The captured GoPlus claims with pipeline cross-checks: an LP holder is verified when one of its NFT ids is a position
    the pipeline read (with our owner and share), a holder when its balance sits in the balance sample."""
    out = dict(goplus)
    if goplus.get("status") != "ok":
        return out
    read_positions = {p["id"]: p for p in positions or [] if p.get("id") is not None}
    canonical = next((p["pair"] for p in pools or [] if p.get("read") == "v3" and p.get("target_in_pool")), None)
    sampled = {h["address"].lower(): h for h in top_holders or [] if h.get("address")}
    sampled.update({b["address"].lower(): {"pct_supply": b.get("pct_supply")} for b in (balances or {}).values() if b.get("address")})
    for row in out.get("lp_holders", []):
        matched = [pid for pid in row.get("nft_ids", []) if pid in read_positions]
        row["verified_positions"] = [{"id": pid, "owner": read_positions[pid].get("owner"), "pct_of_pool_active_liquidity": read_positions[pid].get("pct_of_pool_active_liquidity")} for pid in matched]
        row["verified"] = bool(matched)
    for row in out.get("holders", []):
        hit = sampled.get(row["address"])
        row["verified"] = hit is not None
        row["sample_pct_supply"] = hit.get("pct_supply") if hit else None
    out["canonical_pool"] = canonical
    out["canonical_pool_listed"] = bool(canonical) and any(d.get("pair") == canonical for d in out.get("dex", []))
    out["lp_holders_verified"] = sum(1 for r in out.get("lp_holders", []) if r["verified"])
    out["holders_verified"] = sum(1 for r in out.get("holders", []) if r["verified"])
    # Unread listed positions are offered largest share first, in-range positions before out-of-range ones (out-of-range
    # principal still needs custody), and a position with a zero amount is never worth a read.
    unread = {}
    for r in out.get("lp_holders", []):
        for n in r.get("nfts") or [{"id": pid, "share_pct": None, "empty": False, "in_effect": None} for pid in r.get("nft_ids", [])]:
            if n["id"] not in read_positions and not n.get("empty"):
                share = n.get("share_pct") if n.get("share_pct") is not None else -1.0
                key = (0 if n.get("in_effect") is not False else 1, -share)
                unread[n["id"]] = min(unread.get(n["id"], key), key)
    out["unread_lp_nft_ids"] = [pid for pid, _ in sorted(unread.items(), key=lambda kv: (kv[1], kv[0]))][:12]
    return out


def decode_module_page(raw):
    """(address[] modules, address next) from Safe.getModulesPaginated; None unless the ABI shape is exact."""
    if not isinstance(raw, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{64})+", raw):
        return None
    words = [int(raw[2 + 64 * i:66 + 64 * i], 16) for i in range((len(raw) - 2) // 64)]
    if len(words) < 3 or words[0] != 64 or words[1] >= 2 ** 160:
        return None
    count = words[2]
    if count > 10 or len(words) != 3 + count or any(w == 0 or w >= 2 ** 160 for w in words[3:]):
        return None
    return {"modules": ["0x" + format(w, "040x") for w in words[3:]], "next": "0x" + format(words[1], "040x")}


def recommended_presets(facts):
    """Presets derived from the facts, run by start itself (run_recommended) and printed for the coordinator when one was
    deferred. Empty when the standard reads covered the routes: Safe modules and guard, locker getters, position custody and
    sale receipts are read by the pipeline itself. Each row carries the exact `command` and the same request as `params`."""
    out = []
    pin = (facts.get("pin") or {}).get("number")
    pools = facts.get("pools") or []
    unread = (facts.get("goplus") or {}).get("unread_lp_nft_ids") or []
    if unread:
        ids = unread[:6]
        out.append({"preset": "positions", "dimension": "canonical_lp_principal_custody",
                    "command": f'collect --run "$RUN" --preset positions --ids {",".join(str(i) for i in ids)}', "params": {"preset": "positions", "ids": ids},
                    "reason": f"GoPlus lists {len(unread)} LP position ids the pipeline has not read; reading them verifies the listed LP holders' custody and shares on chain"})
    canonical = next((p for p in pools if p.get("read") == "v3" and p.get("target_in_pool")), None)
    nfpm = next((a["address"] for a in facts.get("architecture") or [] if a.get("label") == "nfpm"), None)
    positions = [p for p in facts.get("positions") or [] if canonical and p.get("pool") == canonical["pair"]]
    covered = round(sum(p.get("pct_of_pool_active_liquidity") or 0 for p in positions), 4)
    if canonical and nfpm and pin and covered < 80:
        span = 9999
        creation_block = (facts.get("creation") or {}).get("block")
        windows = []
        if isinstance(creation_block, int) and creation_block <= pin:
            windows.append(("launch window", creation_block, min(pin, creation_block + span)))  # launch-locked positions are added near launch
        if not windows or windows[0][2] < max(0, pin - span):
            windows.append(("recent window", max(0, pin - span), pin))
        for label, frm, to in windows[:2]:
            increase = topic("IncreaseLiquidity(uint256,uint128,uint256,uint256)")
            out.append({"preset": "logs", "dimension": "canonical_lp_principal_custody",
                        "command": f'collect --run "$RUN" --preset logs --contract {nfpm} --topic {increase} --from-block {frm} --to-block {to}',
                        "params": {"preset": "logs", "contract": nfpm, "topic": increase, "from_block": frm, "to_block": to, "window": label},
                        "then": 'collect --run "$RUN" --preset positions --ids <the token_ids the logs rows print; keep the ids whose positions read back at the canonical pool>',
                        "reason": f"identified positions cover {covered}% of the canonical pool's active liquidity; {label} of {to - frm + 1} blocks (eth_getLogs ranges are capped at {span + 1}), a sample of liquidity adds, never an enumeration"})
    verified = any(s.get("verified") for s in facts.get("sales") or [])
    probed = {r.get("tx") for r in facts.get("receipts") or []} | set((facts.get("indexed") or {}).get("sale_candidates") or [])
    pending = [tx for tx in (facts.get("indexed") or {}).get("indexed_sells") or [] if tx not in probed][:2]
    if not verified and pending:
        out.append({"preset": "receipts", "dimension": "sellability_exit_depth",
                    "command": f'collect --run "$RUN" --preset receipts --tx {",".join(pending)}', "params": {"preset": "receipts", "tx": pending},
                    "reason": "no sale verified yet; these indexer-listed sells at the canonical pool were not probed"})
    return out[:4]


def summary_lines(facts):
    lines = [f"pipeline {PIPELINE_VERSION} elapsed {facts['elapsed_seconds']}s; collections: " + ", ".join(f"{c['name']}={c['status']}({c['attempts']} req, {c['elapsed_seconds']}s)" for c in facts["collections"])]
    if facts["pin"]:
        lines.append(f"pin #{facts['pin']['number']} {facts['pin']['timestamp_utc']} {facts['pin']['hash']}")
    m = facts["metadata"]
    lines.append(f"token {m.get('name')} ({m.get('symbol')}) decimals={m.get('decimals')} totalSupply={decimal_string(m.get('total_supply'), m.get('decimals'))} code_bytes={facts['controls'].get('code_bytes')} clone={facts['controls'].get('clone', {}).get('status')}")
    getters_seen = facts['controls'].get('getters', {})
    owner_note = facts['controls'].get('owner') if 'owner' in getters_seen else ("reverted" if "owner" in (facts['controls'].get('reverted_getters') or []) else "not in verified ABI (not probed)")
    paused_note = facts['controls'].get('paused') if 'paused' in getters_seen else ("reverted" if "paused" in (facts['controls'].get('reverted_getters') or []) else "not in verified ABI (not probed)")
    lines.append(f"owner={owner_note} paused={paused_note} eip1967={facts['controls'].get('eip1967')} reverted_getters={facts['controls'].get('reverted_getters')}"
                 + (f" failed_getters={facts['controls'].get('failed_getters')}" if facts['controls'].get('failed_getters') else ""))
    getters = {k: v['decoded'] for k, v in facts['controls'].get('getters', {}).items() if k not in ('owner', 'paused')}
    if getters:
        lines.append("getters: " + json.dumps(getters, default=str)[:900])
    lines.append(f"source: {facts['source']}")
    lines.append(f"discovery: {json.dumps(facts['discovery'], default=str)[:600]}")
    creation = facts.get("creation") or {}
    creation_explorer = facts.get("discovery", {}).get("explorer") if isinstance(facts.get("discovery", {}).get("explorer"), dict) else {}
    if creation.get("tx") or creation.get("deployment_tx_conflict"):
        lines.append(f"creation: tx={creation.get('tx')} source={creation.get('tx_source')} creator={creation.get('creator')} signer={creation.get('signer')}"
                     + (f" deployer={creation['deployer']} (Sourcify" + ("; the explorer's creator is unknown)" if not creation.get("creator") else ")") if creation.get("deployer") else "")
                     + (f" explorer_first_attempt={creation_explorer.get('first_attempt')} retry={creation_explorer.get('retry')}" if creation_explorer.get("retry") else "")
                     + (f" | conflict: Sourcify's deployment record names {creation['deployment_tx_conflict']}; unresolved" if creation.get("deployment_tx_conflict") else ""))
    if facts["links"]["websites"] or facts["links"]["socials"]:
        lines.append("links: " + json.dumps(facts["links"])[:400])
    lines.append("evidence aliases: token reads are token-<getter>, runtime, metadata-<field>, token-eip1967-<slot>; rows below start with their alias prefix")
    for p in facts["pools"]:
        prefix = p.get("prefix") or "pool"
        lines.append(f"pool [{prefix}-*] {p['pair'][:14]} {p.get('dex')} {p.get('version')} counter={p.get('counter_symbol')} liqUSD={p.get('liquidity_usd')} fee={p.get('fee')} liquidity={p.get('liquidity')} tick={(p.get('slot0') or {}).get('tick')} target_balance={p.get('target_balance')} ({p.get('target_balance_pct_supply')}%) in_pool={p.get('target_in_pool')} [bal-{prefix}]")
    for q in facts["quotes"]:
        lines.append(f"quote [{q.get('evidence')}] {q['size_tokens']} -> {q.get('amount_out')} ({q.get('status')}) impact={q.get('impact_vs_smallest_pct')}%")
    for name, b in facts["balances"].items():
        if b["raw"] is not None:
            lines.append(f"balance [{b.get('evidence')}] {name} {b['address'][:12]} = {b['decimal']} ({b['pct_supply']}%)")
    for a in facts["architecture"]:
        ev = a.get("evidence", {})
        owner_note = "reverted (no owner() at the pin)" if "owner" in (a.get("reverted") or []) else a.get("owner")
        lines.append(f"arch [{ev.get('runtime')}, {ev.get('owner')}, {ev.get('implementation_slot')}] {a['label']} {a['address']} code={a['code_bytes']} owner={owner_note} impl_slot={a.get('eip1967_implementation')}" + (f" symbol={a.get('symbol')} decimals={a.get('decimals')}" if a['label'].startswith('quote-') else ""))
    for name, o in facts["owners"].items():
        ev = o.get("evidence", {})
        rev = o.get("reverted") or []
        safe_note = "reverted (signers unresolved)" if "getOwners" in rev else o.get("safe_owners")
        owner_note = "reverted (owner unresolved)" if "owner" in rev else o.get("owner")
        if o.get("safe_owners"):
            modules_note = "reverted" if "getModulesPaginated" in rev else (str(o.get("safe_modules")) + ("+more" if o.get("safe_modules_truncated") else ""))
            guard_note = (o.get("safe_guard") or "zero (no guard)") if o.get("safe_guard_read") else "unread"
        else:
            modules_note = guard_note = "n/a (not a resolved Safe)"
        lines.append(f"owner-of [{ev.get('runtime')}, {ev.get('getOwners')}, {ev.get('getThreshold')}, {ev.get('getModulesPaginated')}, {ev.get('guard')}] {name}: {o['address']} code={o['code_bytes']} safe_owners={safe_note} threshold={o.get('safe_threshold')} owner={owner_note} modules={modules_note} guard={guard_note}")
    for r in facts["receipts"]:
        lines.append(f"receipt [{r.get('evidence')}] {r['tx'][:14]} status={r['status']} block={r['block']} from={r['from']} transfers={len(r['transfers'])} nfpm_positions={r.get('nfpm_position_ids')}")
    for p in facts["positions"]:
        ev = p.get("evidence", {})
        lines.append(f"position [{ev.get('positions')}, {ev.get('owner')}, {ev.get('approved')}] {p['id']} owner={p.get('owner')} approved={p.get('approved')} liquidity={p.get('liquidity')} range=[{p.get('tickLower')},{p.get('tickUpper')}] in_range={p.get('in_range')} pct_active={p.get('pct_of_pool_active_liquidity')}")
    for name, a in facts.get("actors", {}).items():
        lines.append(f"actor {name} {a['address']} code_bytes={a['code_bytes']} evidence={a['evidence']}")
        if a.get("role") == "position_custodian":
            answered = {k: v["decoded"] for k, v in (a.get("getters") or {}).items()}
            lines.append(f"custodian-getters [{', '.join(v['evidence'] for v in (a.get('getters') or {}).values()) or 'none answered'}] {a['address']} answered={json.dumps(answered, default=str)[:600]} reverted={a.get('reverted')}")
    for p in facts.get("pools", []):
        if p.get("counter_balance") is not None:
            lines.append(f"pool-depth [{p['evidence'].get('counter_balance')}] {p.get('prefix')} holds {p.get('counter_balance')} {p.get('counter_symbol')} and {p.get('target_balance')} target at the pin")
    for h in facts.get("top_holders", []):
        ev = h.get("evidence", {})
        lines.append(f"top-holder [{ev.get('balance')}, {ev.get('runtime')}] {h['address']} = {h.get('decimal')} ({h.get('pct_supply')}%) code_bytes={h.get('code_bytes')} indexer_tag={h.get('indexer_name')}")
    if facts.get("top_holders"):
        lines.append("holder-summary (selected unique addresses; not beneficial owners): " + json.dumps(holder_summary(facts["top_holders"], m.get("total_supply")), sort_keys=True))
    for s in facts.get("sales", []):
        if s.get("verified"):
            lines.append(f"sale-verified seller={s['seller']} sold {s.get('amount')} into {s['pool'][:12]} received={[(r['asset'][:10], r['amount_raw']) for r in s.get('received', [])]} (receipt alias in receipts above)")
        else:
            lines.append(f"sale-candidate not verified: {s.get('reason')}")
    if facts.get("creator_activity"):
        lines.append("creator-activity: " + json.dumps(facts["creator_activity"])[:400])
    if facts.get("maturity"):
        lines.append("maturity: " + json.dumps(facts["maturity"], default=str)[:500])
    if facts.get("document_evidence"):
        lines.append("document evidence: " + ", ".join(facts["document_evidence"]))
    lines.append("coverage_hint: " + ", ".join(f"{k}={v}" for k, v in facts["coverage_hint"].items()))
    g = facts.get("goplus") or {}
    if g.get("status") == "ok":
        lp = "; ".join(f"{r['address'][:12]} {r.get('share_pct')}% locked={r.get('is_locked')} contract={r.get('is_contract')} nfts={r.get('nft_ids')} verified={r.get('verified')}" for r in g.get("lp_holders", [])[:6])
        flags = {k: v for k, v in (g.get("flags") or {}).items() if v is not None}
        lines.append(f"goplus [{g.get('evidence')}] holders={g.get('holder_count')} lp_holders={g.get('lp_holder_count')} verified_lp={g.get('lp_holders_verified')}/{len(g.get('lp_holders', []))} verified_holders={g.get('holders_verified')}/{len(g.get('holders', []))} buy_tax={g.get('buy_tax')} sell_tax={g.get('sell_tax')} flags={json.dumps(flags)} unread_lp_nft_ids={g.get('unread_lp_nft_ids')}")
        if lp:
            lines.append("goplus-lp-holders: " + lp)
    elif g.get("status"):
        lines.append(f"goplus: {g.get('status')} (third-party token security not available for this run)")
    for r in facts.get("presets_run") or []:
        head = f"preset-run {r['preset']} {r['status']}" + (f" [{r['collection']}] attempts={r.get('attempts')} elapsed={r.get('elapsed_seconds')}s" if r.get("collection") else "")
        lines.append(head + f" | {r['command']}" + (f" | chained from the {r['chained_from']}" if r.get("chained_from") else "") + (f" | trimmed from {r['trimmed_from']} ids to fit the remaining requests" if r.get("trimmed_from") else "")
                     + (f" | {r['reason']}" if r.get("reason") else ""))
    recommended = facts.get("recommended_presets") or []
    for n, r in enumerate(recommended, 1):
        lines.append(f"recommended preset {n} [{r['dimension']}]: {r['command']} | {r['reason']}" + (f" | then: {r['then']}" if r.get("then") else ""))
    if not recommended:
        lines.append("recommended presets: none remain; start ran its queue itself" if facts.get("presets_run") else
                     "recommended presets: none; the standard reads covered custody, Safe modules/guard, custodian getters and sale receipts")
    if facts.get("review"):
        lines.append("budget review: " + json.dumps(facts["review"]))
    return lines


def brief(run, lane, minutes, allow_partial=False):
    run = Path(run)
    facts = read_json(run / "facts.json") if (run / "facts.json").is_file() else None
    need(facts is not None or allow_partial, "facts.json is not ready; wait for the pipeline (about 15-90 s) or pass --allow-partial to brief from discovery only")
    discovery = read_json(run / "discovery.json") if (run / "discovery.json").is_file() else {"pairs": [], "links": {"websites": [], "socials": []}, "discovery": {}}
    template = (Path(__file__).resolve().parents[1] / "assets" / ("lane-brief-" + lane + ".md")).read_text(encoding="utf-8")
    target = (facts or discovery)["target"]
    pools = "\n".join(f"- {p['pair']} ({p.get('dex')} {p.get('version')}, counter {p.get('counter_symbol')}, indexed liquidity USD {p.get('liquidity_usd')}, url {p.get('url')})" for p in discovery.get("pairs", [])[:8]) or "- none indexed by Dexscreener"
    links = "\n".join("- " + u for u in [*discovery.get("links", {}).get("websites", []), *discovery.get("links", {}).get("socials", [])]) or "- none from Dexscreener; find target-linked channels through the pool/explorer pages"
    pin = facts["pin"] if facts and facts.get("pin") else {"number": "pending", "timestamp_utc": "pending", "hash": "pending"}
    facts_lines = "\n".join(summary_lines(facts)) if facts else "facts.json not ready yet; rely on discovery.json and the run's own captures"
    intake = read_json(run / "intake.json") if (run / "intake.json").is_file() else {}
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) + timedelta(minutes=minutes + 2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    skill_dir = str(Path(__file__).resolve().parents[1])
    filled = template
    for key, value in (("RUN", str(run.resolve())), ("SKILL_DIR", skill_dir), ("CHAIN_ID", str(target["chain_id"])), ("ADDRESS", target["address"]),
                       ("PIN_NUMBER", str(pin["number"])), ("PIN_TIME", str(pin["timestamp_utc"])), ("POOLS", pools), ("LINKS", links),
                       ("FACTS", facts_lines), ("CUTOFF_UTC", cutoff), ("MINUTES", str(minutes)),
                       ("CREATION_TX", str((facts or {}).get("creation", {}).get("tx") or "unknown")), ("CREATOR", str((facts or {}).get("creation", {}).get("creator") or ((facts or {}).get("creation", {}).get("deployer") and (facts["creation"]["deployer"] + " (deployer per Sourcify's deployment record; the explorer's creator is unknown)")) or "unknown")),
                       ("EXPLORERS", ", ".join(e["name"] + " " + e["base"] for e in presets.registry(target["chain_id"]).get("explorers", [])) or "none registered"),
                       ("USER_FOCUS", user_focus_section(intake, lane))):
        filled = filled.replace("{{" + key + "}}", value)
    return filled


PRESET_FIELDS = ("prefix", "tx", "ids", "manager", "contract", "signatures", "asset", "holders", "contracts", "topic", "from_block", "to_block", "version", "max_requests")


def preset_args(params):
    """The argparse-shaped request for a recommended row's `params` (the same request its printed command makes)."""
    from types import SimpleNamespace
    args = SimpleNamespace(preset=params["preset"], **{k: None for k in PRESET_FIELDS})
    if params["preset"] == "positions":
        args.ids = ",".join(str(i) for i in params["ids"])
    elif params["preset"] == "logs":
        args.contract, args.topic, args.from_block, args.to_block = params["contract"], params["topic"], params["from_block"], params["to_block"]
    elif params["preset"] == "receipts":
        args.tx = ",".join(params["tx"])
    else:
        raise Invalid("unsupported recommended preset " + str(params["preset"]))
    return args


def build_preset(pipeline, facts, args):
    """The pinned plan for one preset request: (collection name, plan, query count, pins)."""
    target = facts["target"]
    head = facts["pin"]["number"]
    pin = "current"
    pins = {"current": head}
    prefix = presets.label(args.prefix or args.preset)
    required = {"receipts": "tx", "positions": "ids", "getters": "signatures", "balances": "holders", "architecture": "contracts", "logs": "contract", "pool": "contract"}
    need(getattr(args, required[args.preset]) is not None, "--" + required[args.preset].replace("_", "-") + " is required for preset " + args.preset)
    if args.preset in ("getters", "logs", "pool"):
        need(args.contract is not None, "--contract is required for preset " + args.preset)
    if args.preset == "logs":
        need(args.from_block is not None and args.to_block is not None, "--from-block and --to-block are required for preset logs")
    if args.preset == "receipts":
        transactions = {}
        for tx in args.tx.split(","):
            tx = tx.strip().lower()
            need(re.fullmatch(r"0x[0-9a-fA-F]{64}", tx), "transaction hash must be 32 bytes")
            need(pipeline.session is None or pipeline.session.status()["remaining_requests"] >= 1, "request budget exhausted before the receipt lookup for " + tx)
            block = pipeline.lookup_block(tx)
            need(block is not None, "receipt not found for " + tx)
            transactions[tx] = block
        pins, queries = presets.receipt_queries(transactions)
    elif args.preset == "positions":
        ids = [integer(int(x), "token id") for x in args.ids.split(",")]
        queries = presets.position_queries(prefix, pin, args.manager or (pipeline.registry.get("uniswap_v3") or {}).get("nonfungible_position_manager"), ids)
    elif args.preset == "getters":
        signatures = [s.strip() for s in args.signatures.split(",") if s.strip()]
        queries = [presets.code(prefix + "-runtime", pin, args.contract)] + presets.getter_queries(prefix, pin, args.contract, signatures)
        for sig in signatures:
            pipeline.names[selector(sig)] = sig.split("(")[0]
    elif args.preset == "balances":
        holders = dict(item.split("=", 1) for item in args.holders.split(","))
        queries = presets.balance_queries(prefix, pin, args.asset or target["address"], holders)
    elif args.preset == "architecture":
        contracts = dict(item.split("=", 1) for item in args.contracts.split(","))
        queries = presets.architecture_queries(prefix, pin, contracts)
    elif args.preset == "logs":
        topics = [args.topic] if args.topic else []
        queries = [presets.range_log_query(prefix + "-logs", pin, args.contract, topics, args.from_block, args.to_block)]
    elif args.preset == "pool":
        queries = presets.pool_queries(prefix, pin, args.contract, args.version or "v3")
        queries += presets.balance_queries(prefix + "-bal", pin, target["address"], {"pool": args.contract})
    else:
        raise Invalid("unsupported preset")
    plan = presets.plan(target, pins, queries)
    name = "preset-" + prefix + "-" + sha(json.dumps(plan, sort_keys=True).encode())[:8]
    return name, plan, len(queries), pins, prefix


def collect_preset(run, pipeline, session, facts, name, plan, max_requests, prefix):
    """One pinned preset collection imported into the draft: the same path for a coordinator `collect` and for start's own queue."""
    from bundle_assemble import import_collection
    write_new(run / (name + "-plan.json"), plan)
    result = pipeline.collect(name, plan, max_requests=max_requests)
    if result["status"] in ("complete", "partial"):
        import_collection(run / "draft", run / name, bool(getattr(pipeline, "synthetic", False)))
    names = read_json(run / "getter-names.json") if (run / "getter-names.json").is_file() else {}
    names.update(pipeline.names)
    (run / "getter-names.json").write_text(json.dumps(names, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    decimals = facts.get("metadata", {}).get("decimals")
    rows = [summarize_row(run / name, row, names, decimals) for row in result["evidence"] if not row["id"].startswith("sys-")]
    if session.schema >= 3:
        session.mark("preset_" + re.sub(r"[^A-Za-z0-9_]", "_", prefix)[:20])
    return {"collection": name, "status": result["status"], "attempts": result["statistics"]["network_attempts"],
            "elapsed_seconds": result["telemetry"]["elapsed_seconds"], "imported": result["status"] in ("complete", "partial"), "rows": rows}


QUEUE_HEADROOM = 150  # seconds that must remain before the deadline for start to run a recommended preset itself (the SKILL's rule for presets)


def preset_estimate(params):
    """Requests a recommended row will spend, counted before anything is sent: its queries, one pin header and recheck per pin,
    the chain check, and for receipts the uncached block lookup each hash needs first."""
    if params["preset"] == "positions":
        return 1 + 3 * len(params["ids"]) + 4
    if params["preset"] == "logs":
        return 1 + 4
    if params["preset"] == "receipts":
        return 5 * len(params["tx"]) + 2
    raise Invalid("unsupported recommended preset " + str(params.get("preset")))


def run_recommended(run, pipeline, session, facts, headroom=QUEUE_HEADROOM, reserve=0):
    """Start's own execution of the recommended queue under the run's session, pin and provider: each row is the same
    pinned collection its printed command would make, so a derived follow-up never waits for a coordinator turn or a
    second paid-use approval. A row is deferred (left in the printed queue) when fewer than `headroom` seconds remain or
    the leftover requests, less `reserve`, would not cover it; a logs row's `then` step is chained: up to six of the
    position ids the scan printed that the pipeline has not read are read next. Returns (rows run or deferred, remaining)."""
    ran = []
    queue = list(facts.get("recommended_presets") or [])
    read_ids = {p.get("id") for p in facts.get("positions") or []}
    while queue:
        row = queue.pop(0)
        params = row.get("params")
        entry = {"preset": row["preset"], "dimension": row.get("dimension"), "command": row["command"], "params": params, "collection": None, "status": None, "attempts": 0, "elapsed_seconds": None}
        if row.get("chained_from"):
            entry["chained_from"] = row["chained_from"]
        if not params:
            ran.append({**entry, "status": "deferred", "reason": "the row carries no structured request; run its command"})
            continue
        # The time and budget checks precede any send: a receipts row's block lookups are themselves charged requests.
        try:
            estimate = preset_estimate(params)
        except (Invalid, KeyError, TypeError) as exc:
            ran.append({**entry, "status": "failed", "reason": str(exc)[:160]})
            continue
        status = session.status()
        if status["remaining_seconds"] < headroom:
            ran.append({**entry, "status": "deferred", "reason": f"fewer than {headroom} s remained before the deadline; run its command only if time allows"})
            continue
        left = max(0, status["remaining_requests"] - reserve)
        if left < estimate and params["preset"] == "positions" and (left - 5) // 3 >= 1:
            # A positions row is trimmed to the ids the remaining requests can cover; the rest are printed as a deferred row.
            fit = (left - 5) // 3
            rest = {**params, "ids": params["ids"][fit:]}
            ran.append({**entry, "params": rest, "command": f'collect --run "$RUN" --preset positions --ids {",".join(str(i) for i in rest["ids"])}', "status": "deferred",
                        "reason": f"{len(rest['ids'])} of {len(params['ids'])} ids did not fit the {left} requests that remained after the lane charges"})
            params = {**params, "ids": params["ids"][:fit]}
            entry.update(params=params, command=f'collect --run "$RUN" --preset positions --ids {",".join(str(i) for i in params["ids"])}', trimmed_from=len(rest["ids"]) + fit)
            estimate = preset_estimate(params)
        if left < estimate:
            ran.append({**entry, "status": "deferred", "reason": f"about {estimate} requests needed, {left} remain after the lane charges"})
            continue
        try:
            args = preset_args(params)
            name, plan, count, pins, prefix = build_preset(pipeline, facts, args)
        except (Invalid, ValueError, KeyError, TypeError) as exc:
            ran.append({**entry, "status": "failed", "reason": str(exc)[:160]})
            continue
        needed = count + 2 * len(pins) + 2
        try:
            result = collect_preset(run, pipeline, session, facts, name, plan, needed, prefix)
        except (Invalid, ValueError, OSError, KeyError, TypeError) as exc:
            ran.append({**entry, "status": "failed", "reason": str(exc)[:160]})
            continue
        ran.append({**entry, "collection": result["collection"], "status": result["status"], "attempts": result["attempts"], "elapsed_seconds": result["elapsed_seconds"],
                    "rows": [{k: r.get(k) for k in ("alias", "status", "decoded")} for r in result["rows"]][:40]})
        if params["preset"] == "positions":
            read_ids.update(params["ids"])
        elif params["preset"] == "logs" and result["status"] in ("complete", "partial"):
            printed = [i for r in result["rows"] for i in ((r.get("decoded") or {}).get("token_ids") or [])]
            ids = [i for i in dict.fromkeys(printed) if i not in read_ids][:6]
            if ids:
                queue.insert(0, {"preset": "positions", "dimension": row.get("dimension"), "params": {"preset": "positions", "ids": ids},
                                 "command": f'collect --run "$RUN" --preset positions --ids {",".join(str(i) for i in ids)}', "chained_from": params.get("window", "log scan"),
                                 "reason": f"positions the {params.get('window', 'log')} scan printed ({len(set(printed))} ids); the ones that read back at the canonical pool join the custody cross-check"})
    return ran, queue


def remaining_recommendations(run, facts, ran):
    """The queue after start ran its rows: re-derived from the facts with the positions the presets read merged in, minus
    every row start ran (a scan that did not close its gap is the named limit, not a loop) and plus the deferred rows."""
    from bundle_assemble import read_draft
    from pipeline_note import positions_from_draft
    merged = dict(facts)
    try:
        later = positions_from_draft(run, read_draft(run / "draft"), facts)
    except (Invalid, ValueError, OSError, KeyError, TypeError):
        later = []
    if later:
        merged["positions"] = list(facts.get("positions") or []) + later
        if (facts.get("goplus") or {}).get("status") == "ok":
            merged["goplus"] = goplus_facts(facts["goplus"], merged["positions"], facts.get("top_holders"), facts.get("balances"), facts.get("pools"))
    # A scan or receipts row that ran (whatever it closed) is done for its kind and surface, and a position id that was read
    # (or reverted) is never offered again: a partial read or an open coverage gap is the named limit, never re-queued with a
    # narrower command. Position ids nothing has read yet (the listed ids beyond a six-id row) are new work and stay offered.
    ran_rows = [r for r in ran if r["status"] != "deferred"]
    done = {(r["preset"], r["dimension"]) for r in ran_rows if r["preset"] != "positions"}
    read_ids = {i for r in ran_rows if (r.get("params") or {}).get("preset") == "positions" for i in r["params"]["ids"]}
    fresh = [r for r in recommended_presets(merged) if (r["preset"], r["dimension"]) not in done
             and not (r["preset"] == "positions" and set((r.get("params") or {}).get("ids") or []) & read_ids)]
    commands = {r["command"] for r in fresh}
    for r in ran:
        if r["status"] == "deferred" and r["command"] not in commands:
            fresh.append({k: r[k] for k in ("preset", "dimension", "command", "params") if k in r} | {"reason": r.get("reason", "deferred by start")})
    return fresh[:4]


def provider_note(route):
    """One printed line when the configured dRPC URL has no key and the chain's built-in public endpoint is used instead."""
    if route.get("endpoint_source") == "builtin_public_key_missing":
        print(json.dumps({"provider_note": "the configured dRPC URL has no DRPC_API_KEY, so the chain's built-in public endpoint is used; add the key to the private env file to use dRPC"}))


def preset_collect(args):
    from investigation import Investigation
    run = Path(args.run)
    facts = read_json(run / "facts.json")
    target = facts["target"]
    args.chain_id = target["chain_id"]
    session = Investigation(run / "session.sqlite")
    cache = Cache(run / "cache.sqlite")
    try:
        route = provider_availability(args)
        if route["status"] != "ready":
            print(json.dumps(route, sort_keys=True))
            return 3
        provider_note(route)
        transport = configured_transport(args)
        pipeline = Pipeline(run, target, facts.get("question", ""), "", transport, session, cache, args.endpoint_label)
        pipeline.pin = facts["pin"]
        name, plan, count, pins, prefix = build_preset(pipeline, facts, args)
        result = collect_preset(run, pipeline, session, facts, name, plan, args.max_requests or (count + 2 * len(pins) + 2), prefix)
        print(json.dumps({**result, "session": session.status()}, sort_keys=True, default=str)[:20000])
        status_code = 0 if result["status"] == "complete" else 2
    finally:
        cache.close()
        session.close()
    if (run / "facts.json").is_file():
        print("pipeline note: " + json.dumps(pipeline_note_result(run), sort_keys=True, default=str)[:1500])
    return status_code


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    start = sub.add_parser("start", help="fresh run: session, intake draft, discovery, four pinned phases, source match, facts.json")
    start.add_argument("--chain-id", type=int, required=True)
    start.add_argument("--address", required=True)
    start.add_argument("--run", type=Path, required=True, help="new investigation directory")
    start.add_argument("--question", required=True)
    start.add_argument("--focus", default="", help="the user's extra asks beyond the address, verbatim; rendered into both lane briefs")
    start.add_argument("--url", action="append", default=[], help="a link the user gave (repeatable, at most six); lanes capture these first")
    start.add_argument("--materiality", default="All privileged authority and principal-removal powers are material; exit sizes are illustrative")
    start.add_argument("--max-requests", type=int, default=360)  # the standard reads plus start's own preset queue; the 400 ceiling stays
    start.add_argument("--timeout", type=float, default=600)
    start.add_argument("--request-ceiling", type=int, default=400)
    start.add_argument("--timeout-ceiling", type=float, default=1500)
    start.add_argument("--pools", default="", help="comma-separated extra exact pool addresses")
    start.add_argument("--holders", default="", help="label=address,... extra balances to read")
    start.add_argument("--quote-sizes", default="100,10000,100000")
    start.add_argument("--explorer", default="auto", help="auto | none | substring of a registry explorer name")
    start.add_argument("--no-web", action="store_true")
    start.add_argument("--no-lanes", action="store_true", help="focused question: do not charge lanes or write lane briefs")
    start.add_argument("--fixture", type=Path, help="synthetic RPC fixture for offline tests")
    start.set_defaults(help_phases="four pinned RPC phases")
    start.add_argument("--allow-synthetic", action="store_true")
    add_provider_arguments(start)
    collect = sub.add_parser("collect", help="one extra pinned collection from a preset; imports into the draft")
    collect.add_argument("--run", type=Path, required=True)
    collect.add_argument("--preset", required=True, choices=("receipts", "positions", "getters", "balances", "architecture", "logs", "pool"))
    collect.add_argument("--prefix")
    collect.add_argument("--tx")
    collect.add_argument("--ids")
    collect.add_argument("--manager")
    collect.add_argument("--contract")
    collect.add_argument("--signatures")
    collect.add_argument("--asset")
    collect.add_argument("--holders")
    collect.add_argument("--contracts")
    collect.add_argument("--topic")
    collect.add_argument("--from-block", type=int)
    collect.add_argument("--to-block", type=int)
    collect.add_argument("--version")
    collect.add_argument("--max-requests", type=int)
    add_provider_arguments(collect)
    brief_cmd = sub.add_parser("brief", help="print a self-contained lane brief")
    brief_cmd.add_argument("--run", type=Path, required=True)
    brief_cmd.add_argument("--lane", required=True, choices=("liquidity", "project"))
    brief_cmd.add_argument("--minutes", type=int, default=4)
    brief_cmd.add_argument("--allow-partial", action="store_true", help="print a brief before facts.json exists (lanes then cite only their own captures)")
    status = sub.add_parser("status", help="session, phases and facts summary")
    status.add_argument("--run", type=Path, required=True)
    args = p.parse_args()
    start_owned = False
    try:
        if args.action == "brief":
            path, text = write_brief(args.run, args.lane, args.minutes, args.allow_partial)
            print(text)
            print("\nbrief written to " + str(path.resolve()) + "\nspawn prompt -> " + spawn_prompt(args.run, args.lane))
            return 0
        if args.action == "status":
            from investigation import Investigation
            session = Investigation(args.run / "session.sqlite")
            try:
                out = {"session": session.status()}
            finally:
                session.close()
            if (args.run / "facts.json").is_file():
                out["facts"] = summary_lines(read_json(args.run / "facts.json"))
            print(json.dumps(out, sort_keys=True, indent=1, default=str))
            return 0
        if args.action == "collect":
            return preset_collect(args)
        from bundle_assemble import intake
        from investigation import Investigation
        target = {"chain_id": args.chain_id, "address": address(args.address)}
        need(not args.run.exists() or (args.run / "start-failed.json").is_file(),
             "run directory must be new; every investigation is fresh (only a directory whose start failed before pinning accepts a restart)")
        restart = args.run.exists()
        if restart:
            failure = read_json(args.run / "start-failed.json")
            need(failure.get("stage") in ("chain_check", "head_block") and not (args.run / "facts.json").exists()
                 and not (args.run / "phase1").exists(), "restart is only allowed before pinned collection")
            old_intake = read_json(args.run / "intake.json") if (args.run / "intake.json").is_file() else {}
            need(not old_intake or old_intake.get("target") == target, "restart target must match the failed investigation")
        if args.fixture:
            need(args.allow_synthetic, "fixture requires --allow-synthetic")
            from bootstrap import FixtureTransport
            transport = FixtureTransport(args.fixture)
        else:
            route = provider_availability(args)
            if route["status"] != "ready":
                print(json.dumps(route, sort_keys=True))
                return 3
            provider_note(route)
            transport = configured_transport(args)
        if restart:
            archive_failed_attempt(args.run)
        args.run.mkdir(parents=True, exist_ok=True)
        start_owned = True
        for sub in ("notes", "lanes/liquidity", "lanes/project"):
            (args.run / sub).mkdir(parents=True)
        session = Investigation(args.run / "session.sqlite") if restart and (args.run / "session.sqlite").is_file() else \
            Investigation.create(args.run / "session.sqlite", args.max_requests, args.timeout, request_ceiling=args.request_ceiling,
                                 timeout_ceiling=args.timeout_ceiling, limit_basis="analyst_safety")
        cache = Cache(args.run / "cache.sqlite")
        try:
            intake(args.run / "draft", target, args.question, args.materiality, bool(args.fixture))
            write_new(args.run / "intake.json", {"target": target, "question": args.question, "materiality": args.materiality,
                                                 "focus": args.focus.strip(), "user_urls": user_urls(args.url),
                                                 "quote_sizes": args.quote_sizes, "started_at_utc": stamp(), "pipeline_version": PIPELINE_VERSION})
            holders = dict(item.split("=", 1) for item in args.holders.split(",") if "=" in item)
            pipeline = Pipeline(args.run, target, args.question, args.materiality, transport, session, cache, args.endpoint_label,
                                quote_sizes=[int(x) for x in args.quote_sizes.split(",") if x.strip()],
                                pools=[x for x in args.pools.split(",") if x.strip()], holders=holders, explorer=args.explorer,
                                web=not args.no_web, synthetic=bool(args.fixture))
            facts = pipeline.run_all()
            lanes = None if args.no_lanes else prepare_lanes(args.run, session)
            if lanes and facts.get("recommended_presets"):
                # The lanes are charged first; start then runs its own queue on what is left, so a derived follow-up never
                # costs a coordinator turn or a second paid-use approval. The facts carry every outcome.
                ran, _ = run_recommended(args.run, pipeline, session, facts)
                facts["presets_run"] = ran
                facts["recommended_presets"] = remaining_recommendations(args.run, facts, ran)
                facts["session"] = session.status()
                replace_json(args.run / "facts.json", facts)
                replace_json(args.run / "recommended-presets.json", facts["recommended_presets"])
        finally:
            cache.close()
            session.close()
        for line in summary_lines(facts):
            print(line)
        print("pipeline note: " + json.dumps(pipeline_note_result(args.run), sort_keys=True, default=str)[:1500])
        if lanes:
            for line in spawn_lines(lanes):
                print(line)
        phase1 = next((c for c in facts["collections"] if c["name"] == "phase1"), None)
        return 0 if phase1 and phase1["status"] in ("complete", "partial") else 2
    except (Invalid, ValueError, OSError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, (Invalid, ValueError)) else type(exc).__name__
        if args.action == "start" and start_owned and isinstance(exc, StartFailure):
            info = exc.info
            info = {"status": "start_failed", "run": str(args.run.resolve()), "restart_allowed": True, **info}
            (args.run / "start-failed.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(info, sort_keys=True))
        print("Pipeline failed: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
