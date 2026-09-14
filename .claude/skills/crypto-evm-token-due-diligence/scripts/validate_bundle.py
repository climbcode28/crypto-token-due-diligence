#!/usr/bin/env python3
"""Offline structural/evidence-binding checks; never contacts or signs for a chain."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from rpc_wire import validate_response
from report_profile import CURRENT_PROFILE, LEGACY_PROFILE, pure_coverage_gap, validate_profile

DIMENSIONS = (
    "token_controls", "canonical_lp_principal_custody", "side_pool_removal_risk",
    "sellability_exit_depth", "current_concentration", "historical_launch_integrity",
    "admin_treasury_reward_custody", "reward_accounting_liveness",
    "utility_redemption_rights", "external_dependencies", "development_disclosure",
)
REPORTING_ENGINE_VERSION = "2.6.3"
SUMMARY_TOPICS = {
    "token_and_liquidity": "Token and liquidity",
    "real_work_vs_marketing": "Real work vs marketing",
    "creator_trading_and_proceeds": "Creator trading and proceeds",
    "prior_launches_and_identity": "Prior launches and identity",
    "adoption_and_maturity": "Adoption and maturity",
    "token_economics": "Token economics",
}
CURRENT_SUMMARY_TOPICS = {"adoption_and_maturity", "token_economics"}
METADATA = {"name": "0x06fdde03", "symbol": "0x95d89b41",
            "decimals": "0x313ce567", "total_supply": "0x18160ddd"}
LIMITS = ("Passing checks internal consistency only; it does not prove RPC honesty, "
          "discovery completeness, source correspondence, economic correctness, or protocol safety.")


class Invalid(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Invalid(message)


def nonempty(value, label):
    need(isinstance(value, str) and bool(value.strip()), f"{label}: required text")
    need(not re.search(r"\b(TODO|TBD|PLACEHOLDER)\b|<[^>]+>", value, re.I),
         f"{label}: unfinished placeholder")
    return value


def integer(value, label, minimum=0):
    need(type(value) is int and value >= minimum, f"{label}: invalid integer")
    return value


def address(value):
    need(isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{40}", value),
         f"malformed address: {value!r}")
    need(int(value, 16) != 0, "zero address cannot identify a target or scope actor")
    return value.lower()


def digest(value, label, prefix=False):
    pattern = r"0x[0-9a-fA-F]{64}" if prefix else r"[0-9a-fA-F]{64}"
    need(isinstance(value, str) and re.fullmatch(pattern, value), f"{label}: malformed hash")
    digits = value[2:] if prefix else value
    need(len(set(digits.lower())) > 1, f"{label}: placeholder hash")
    return value.lower()


def utc(value):
    need(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value),
         "timestamp must be UTC YYYY-MM-DDTHH:MM:SSZ")
    return int(datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


def quantity(value):
    need(isinstance(value, str) and re.fullmatch(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)", value),
         f"invalid RPC quantity: {value!r}")
    return int(value, 16)


def identity(value):
    return integer(value["chain_id"], "chain_id", 1), address(value["address"])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_in(root, name):
    need(isinstance(name, str) and name and not Path(name).is_absolute(), "artifact path must be relative")
    path = (root / name).resolve()
    need(path.is_relative_to(root.resolve()), "artifact path escapes bundle")
    need(path.is_file(), f"missing evidence artifact: {name}")
    return path


def read_json(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def index(items, label):
    need(isinstance(items, list), f"{label}: expected list")
    out = {}
    for item in items:
        key = nonempty(item["id"], f"{label} id")
        need(key not in out, f"duplicate {label} id: {key}")
        out[key] = item
    return out


def refs(ids, entries, label, required=True):
    need(isinstance(ids, list), f"{label}: expected reference list")
    need(not required or bool(ids), f"{label}: missing evidence/references")
    need(len(ids) == len(set(ids)), f"{label}: duplicate references")
    for item in ids:
        need(item in entries, f"{label}: missing reference {item}")


def rpc_unavailable(evidence, response):
    return bool(evidence.get("redacted", False)) or "error" in response or response.get("result") is None


def rpc_result(evidence, objects, eid, method=None):
    need(eid in evidence, f"missing RPC evidence {eid}")
    ev = evidence[eid]
    need(ev["kind"] == "rpc", f"{eid}: raw RPC evidence required")
    obj = objects[eid]
    need(isinstance(obj, dict) and obj["request"] == ev["query"], f"{eid}: query/artifact mismatch")
    if method:
        need(obj["request"]["method"] == method, f"{eid}: expected {method}")
    response = obj["response"]
    need(response.get("jsonrpc") == "2.0", f"{eid}: missing JSON-RPC version")
    need(type(response.get("id")) is type(obj["request"].get("id"))
         and response.get("id") == obj["request"].get("id"), f"{eid}: RPC response ID mismatch")
    need(not rpc_unavailable(ev, response),
         f"{eid}: RPC unavailable/error cannot support resolved evidence")
    return response["result"]


def decode_metadata(field, raw):
    need(isinstance(raw, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", raw), "malformed ABI result")
    data = bytes.fromhex(raw[2:])
    if field in ("decimals", "total_supply"):
        need(len(data) == 32, "nonstandard integer metadata must remain unresolved")
        value = int.from_bytes(data, "big")
        need(field != "decimals" or value <= 255, "decimals outside uint8")
        return value if field == "decimals" else str(value)
    # Only canonical ABI strings are automatically resolved; do not guess bytes32.
    need(len(data) >= 64 and int.from_bytes(data[:32], "big") == 32, "nonstandard string metadata")
    size = int.from_bytes(data[32:64], "big")
    end = 64 + ((size + 31) // 32) * 32
    need(len(data) == end and all(x == 0 for x in data[64 + size:]), "invalid ABI string length/padding")
    return data[64:64 + size].decode("utf-8")


def block_matches(value, pin):
    if isinstance(value, dict):
        return (set(value) == {"blockHash", "requireCanonical"}
                and value.get("blockHash", "").lower() == pin["hash"].lower()
                and value.get("requireCanonical") is True)
    return quantity(value) == pin["number"]


def log_filter(value, pin, addr, eid):
    need(isinstance(value, dict) and set(value) <= {"address", "topics", "blockHash", "fromBlock", "toBlock"},
         f"{eid}: invalid log filter")
    addresses = value["address"] if isinstance(value["address"], list) else [value["address"]]
    addresses = {address(a) for a in addresses}
    need(addr in addresses, f"{eid}: log address mismatch")
    topics = value.get("topics", [])
    need(isinstance(topics, list) and len(topics) <= 4, f"{eid}: invalid log filter topics")
    normalized = []
    for topic in topics:
        alternatives = topic if isinstance(topic, list) else [topic]
        need(all(x is None or (isinstance(x, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", x))
                 for x in alternatives), f"{eid}: invalid log filter topic")
        # Empty OR lists and null options are wildcard positions in EVM filters.
        normalized.append(None if not alternatives or None in alternatives else {x.lower() for x in alternatives})
    if "blockHash" in value:
        need("fromBlock" not in value and "toBlock" not in value, f"{eid}: log filter mixes block hash and range")
        need(digest(value["blockHash"], "log filter hash", True) == pin["hash"].lower(), f"{eid}: log hash mismatch")
        start = end = pin["number"]
    else:
        start, end = quantity(value["fromBlock"]), quantity(value["toBlock"])
        need(start <= end <= pin["number"], f"{eid}: invalid log range")
    return addresses, normalized, start, end


def validate_logs(logs, eid, addresses, topics, start, end, pinned_hashes, transaction_hash=None):
    """Bind returned logs to the request and known headers without claiming completeness."""
    need(isinstance(logs, list), f"{eid}: invalid log response")
    seen = set()
    for log in logs:
        need(isinstance(log, dict), f"{eid}: malformed log")
        returned_address = address(log["address"])
        need(addresses is None or returned_address in addresses, f"{eid}: returned log address mismatch")
        number = quantity(log["blockNumber"])
        block_hash = digest(log["blockHash"], "log block hash", True)
        need(start <= number <= end, f"{eid}: returned log outside query range")
        need(number not in pinned_hashes or block_hash == pinned_hashes[number],
             f"{eid}: returned log conflicts with captured header")
        logged_transaction = digest(log["transactionHash"], "log transaction hash", True)
        need(transaction_hash is None or logged_transaction == transaction_hash,
             f"{eid}: receipt log transaction mismatch")
        quantity(log["transactionIndex"])
        log_index = quantity(log["logIndex"])
        need(log.get("removed") is False, f"{eid}: removed/unconfirmed log cannot support resolved evidence")
        need((block_hash, log_index) not in seen, f"{eid}: duplicate log")
        seen.add((block_hash, log_index))
        returned_topics = log["topics"]
        need(isinstance(returned_topics, list) and len(topics) <= len(returned_topics) <= 4
             and all(isinstance(x, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", x) for x in returned_topics),
             f"{eid}: malformed log topics")
        need(all(options is None or returned_topics[n].lower() in options for n, options in enumerate(topics)),
             f"{eid}: returned log topic mismatch")
        need(isinstance(log["data"], str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", log["data"]),
             f"{eid}: malformed log data")


def validate_summary(summary, findings, ratings, evidence, objects, profile=LEGACY_PROFILE, allow_empty=False):
    """Check label/evidence consistency; prose and source truth still need review."""
    need(isinstance(summary, list) and (bool(summary) or allow_empty), "summary must be a nonempty list")
    seen, adverse = set(), set()
    for item in summary:
        need(isinstance(item, dict) and set(item) == {"finding_id", "topic", "signal"},
             "summary item requires only finding_id, topic and signal")
        fid, signal = item["finding_id"], item["signal"]
        need(isinstance(fid, str) and fid in findings, "summary finding is missing")
        need(fid not in seen, "duplicate summary finding")
        seen.add(fid)
        need(isinstance(item["topic"], str) and item["topic"] in SUMMARY_TOPICS, "invalid summary topic")
        need(signal in ("Good", "Potential Risk", "Bad", "Unverified"), "invalid summary signal")
        if signal == "Unverified" or item["topic"] in CURRENT_SUMMARY_TOPICS:
            need(profile == CURRENT_PROFILE, "new summary signals/topics require the strict profile")
        f = findings[fid]
        if signal == "Unverified":
            need(pure_coverage_gap(f), "Unverified requires a pure coverage gap")
        related = [x for x in ratings.values() if fid in x["finding_ids"] and x["status"] != "not_applicable"]
        need(bool(related), "summary finding must support an applicable rating")
        if signal in ("Good", "Bad"):
            failed = any(evidence[e]["kind"] == "rpc" and rpc_unavailable(evidence[e], objects[e]["response"])
                         for e in f["evidence_ids"])
            need(f["evidence_type"] in ("proven_fact", "strongly_supported") and
                 f["confidence"] in ("high", "medium") and not failed,
                 "summary signal requires resolved evidence")
        if signal == "Bad":
            need(any(x["status"] == "concern" and x["severity"] in ("medium", "high", "critical") and
                     x["confidence"] in ("high", "medium") and x["coverage"] in ("complete", "partial")
                     for x in related), "Bad requires a supported material concern")
        if signal in ("Potential Risk", "Bad") and not pure_coverage_gap(f):
            adverse.add(fid)
    for rating in ratings.values():
        if rating["status"] == "concern" and rating["severity"] in ("high", "critical"):
            need(bool(adverse.intersection(rating["finding_ids"])), "summary omits a high/critical concern")


def validate(root, allow_synthetic=False, rendered=None, required_profile=None):
    root = Path(root).resolve()
    manifest_path, report_path = root / "manifest.json", root / "report.json"
    m, r = read_json(manifest_path), read_json(report_path)
    if required_profile:
        need(m.get("validation_profile", LEGACY_PROFILE) == required_profile, "required report profile missing")
    need(m["schema_version"] == 1 and r["schema_version"] == 1, "unsupported schema version")
    need(type(m["synthetic"]) is bool and m["synthetic"] == r["synthetic"], "synthetic marker mismatch")
    need(allow_synthetic or not m["synthetic"], "synthetic bundle requires --allow-synthetic; never live evidence")
    target = identity(m["target"]["requested"])
    need(target == identity(m["target"]["observed"]), "requested/observed chain or address mismatch")
    need(target == identity(r["target"]), "report refers to wrong target chain/address")
    need(r["manifest_sha256"] == sha(manifest_path.read_bytes()), "report source does not bind this manifest")
    need(m["mode"] in ("broad", "formal_broad"), "broad validator requires broad or formal_broad mode")
    for key in ("question", "materiality"):
        nonempty(m[key], key)
    need(isinstance(m["context"], dict), "context must be an object")
    need(isinstance(m["limitations"], list), "limitations must be a list")
    for item in m["limitations"]:
        nonempty(item, "limitation")

    evidence = index(m["evidence"], "evidence")
    scope = index(m["scope"], "scope")
    need(bool(evidence) and bool(scope), "missing evidence or scope")
    chains, pins, chain_hashes = {}, {}, {}
    for chain in m["chains"]:
        cid = integer(chain["chain_id"], "chain ID", 1)
        need(cid not in chains, "duplicate scope chain")
        nonempty(chain["label"], "chain label")
        chains[cid] = chain
        chain_hashes[cid] = {}
        for pin in chain["pins"]:
            pid = nonempty(pin["id"], "pin id")
            need(pid not in pins, "duplicate pin ID")
            integer(pin["number"], "pin block", 1)
            digest(pin["hash"], "pin block hash", True)
            known_hash = chain_hashes[cid].get(pin["number"])
            need(known_hash is None or known_hash == pin["hash"].lower(), "conflicting pins at the same chain height")
            chain_hashes[cid][pin["number"]] = pin["hash"].lower()
            need(utc(pin["timestamp_utc"]) > 0, "placeholder pin timestamp")
            pins[pid] = (cid, pin)
        need(chain["current_pin"] in pins and pins[chain["current_pin"]][0] == cid,
             "current pin missing or on wrong chain")
    need(target[0] in chains, "target chain missing")
    current_pid = chains[target[0]]["current_pin"]

    objects, observed_headers = {}, {}
    for eid, ev in evidence.items():
        need(identity(ev["target"]) == target, f"{eid}: queried target identity conflicts")
        cid, addr = identity(ev)
        need(cid in chains, f"{eid}: unpinned/inconsistent scope chain")
        chain_level = (m.get("validation_profile") == CURRENT_PROFILE and ev["pin_id"] is None
                       and ev.get("provenance_level") == "chain")
        need(chain_level or ev["pin_id"] in pins and pins[ev["pin_id"]][0] == cid, f"{eid}: pin chain mismatch")
        need(ev["kind"] in ("rpc", "document", "derived", "simulation"), f"{eid}: invalid evidence kind")
        need(type(ev.get("redacted", False)) is bool, f"{eid}: redacted marker must be boolean")
        for key in ("endpoint_label", "decoding_basis", "coverage"):
            nonempty(ev[key], f"{eid} {key}")
        utc(ev["captured_at_utc"])
        if ev.get("tx_hash"):
            digest(ev["tx_hash"], "transaction hash", True)
        need(isinstance(ev["query"], dict) and bool(ev["query"]), f"{eid}: query/provenance missing")
        content = file_in(root, ev["artifact"]).read_bytes()
        need(digest(ev["sha256"], "artifact digest") == sha(content), f"{eid}: evidence hash mismatch")
        if ev["kind"] == "rpc":
            obj = read_json(file_in(root, ev["artifact"]))
            objects[eid] = obj
            need(obj["request"] == ev["query"], f"{eid}: raw query mismatch")
            q = ev["query"]
            need(q["jsonrpc"] == "2.0" and type(q.get("id")) in (str, int) and isinstance(q["params"], list), "malformed RPC request")
            response = obj["response"]
            need(isinstance(response, dict) and response.get("jsonrpc") == "2.0", f"{eid}: invalid RPC response version")
            need(type(response.get("id")) is type(q["id"]) and response.get("id") == q["id"], f"{eid}: response ID mismatch")
            need(("result" in response) != ("error" in response), f"{eid}: RPC requires exactly result or error")
            if "error" in response:
                error = response["error"]
                need(isinstance(error, dict) and type(error.get("code")) is int
                     and isinstance(error.get("message"), str), f"{eid}: malformed RPC error")
            method, params = q["method"], q["params"]
            need(method in {"eth_chainId", "eth_getBlockByNumber", "eth_getBlockByHash", "eth_getCode",
                            "eth_getStorageAt", "eth_call", "eth_getBalance", "eth_getLogs",
                            "eth_getTransactionReceipt", "eth_getTransactionByHash", "debug_traceTransaction",
                            "trace_transaction"}, f"{eid}: unsupported/read-only RPC method")
            need(not chain_level or method == "eth_chainId", "only chain ID RPC may have chain-level provenance")
            pin = pins[ev["pin_id"]][1] if not chain_level else None
            if not rpc_unavailable(ev, response) and method == "eth_chainId":
                need(params == [] and quantity(response["result"]) == cid, "RPC chain ID conflict: contradictory chain observation")
            if not rpc_unavailable(ev, response) and method in ("eth_getBlockByNumber", "eth_getBlockByHash"):
                header = response["result"]
                need(len(params) == 2 and params[1] is False, "header query requires a header-only explicit pin")
                need((method == "eth_getBlockByNumber" and quantity(params[0]) == pin["number"])
                     or (method == "eth_getBlockByHash" and params[0].lower() == pin["hash"].lower()),
                     "header query conflicts with assigned pin")
                need(quantity(header["number"]) == pin["number"], "fake/inconsistent block number: contradictory header")
                need(header["hash"].lower() == pin["hash"].lower(), "fake/inconsistent block hash: contradictory header")
                need(quantity(header["timestamp"]) == utc(pin["timestamp_utc"]), "fake/inconsistent block timestamp: contradictory header")
                header_identity = tuple(header[x].lower() for x in ("hash", "parentHash", "stateRoot"))
                key = (cid, pin["number"])
                need(key not in observed_headers or observed_headers[key] == header_identity, "contradictory header roots/parent")
                observed_headers[key] = header_identity
            if method == "eth_call":
                need(2 <= len(params) <= 4, f"{eid}: invalid eth_call parameter count")
                need(all(x is None or (isinstance(x, dict) and not x) for x in params[2:]),
                     f"{eid}: state/block overrides are counterfactual; preserve as derived scenario evidence")
            if method in ("eth_call", "eth_getCode", "eth_getBalance", "eth_getStorageAt"):
                queried_address = params[0]["to"] if method == "eth_call" else params[0]
                need(address(queried_address) == addr, f"{eid}: query address differs from evidence scope")
                need(block_matches(params[2] if method == "eth_getStorageAt" else params[1], pin),
                     f"{eid}: unpinned or inconsistent query block")
                if not rpc_unavailable(ev, response):
                    result = response["result"]
                    if method == "eth_getBalance":
                        quantity(result)
                    else:
                        pattern = r"0x[0-9a-fA-F]{64}" if method == "eth_getStorageAt" else r"0x(?:[0-9a-fA-F]{2})*"
                        need(isinstance(result, str) and re.fullmatch(pattern, result), f"{eid}: malformed {method} result")
            if method in ("eth_getTransactionReceipt", "eth_getTransactionByHash", "debug_traceTransaction", "trace_transaction"):
                need(ev.get("tx_hash") and params[0].lower() == ev["tx_hash"].lower(), f"{eid}: transaction mismatch")
            if method == "eth_getLogs":
                need(len(params) == 1, f"{eid}: invalid log filter parameter count")
                addresses, topics, start, end = log_filter(params[0], pin, addr, eid)
                if not rpc_unavailable(ev, response):
                    validate_logs(response["result"], eid, addresses, topics, start, end, chain_hashes[cid])
            try:
                validate_response(q, response, legacy=m.get("validation_profile", LEGACY_PROFILE) == LEGACY_PROFILE,
                                  redacted=ev.get("redacted", False))
            except ValueError as exc:
                raise Invalid(f"{eid}: {exc}") from exc

    for cid, chain in chains.items():
        eid = chain["chain_id_evidence"]
        need(evidence[eid]["chain_id"] == cid, "chain verification evidence assigned to wrong chain")
        need(quantity(rpc_result(evidence, objects, eid, "eth_chainId")) == cid, "RPC chain ID conflict")
        for pin in chain["pins"]:
            eid = pin["header_evidence"]
            ev = evidence[eid]
            need(ev["chain_id"] == cid and ev["pin_id"] == pin["id"], "header evidence pin/chain conflict")
            header = rpc_result(evidence, objects, eid)
            method, params = ev["query"]["method"], ev["query"]["params"]
            need(method in ("eth_getBlockByNumber", "eth_getBlockByHash"), "pin lacks captured block header")
            if method == "eth_getBlockByNumber":
                need(quantity(params[0]) == pin["number"], "header query must use explicit block number")
            else:
                need(params[0].lower() == pin["hash"].lower(), "header query hash mismatch")
            need(quantity(header["number"]) == pin["number"], "fake/inconsistent block number")
            need(digest(header["hash"], "header hash", True) == pin["hash"].lower(), "fake/inconsistent block hash")
            need(quantity(header["timestamp"]) == utc(pin["timestamp_utc"]), "fake/inconsistent block timestamp")
            digest(header["parentHash"], "header parent hash", True)
            digest(header["stateRoot"], "header state root", True)

    for eid, ev in evidence.items():
        if ev["kind"] != "rpc" or ev["query"]["method"] not in ("eth_getTransactionReceipt", "eth_getTransactionByHash"):
            continue
        obj = objects[eid]["response"]
        if rpc_unavailable(ev, obj):
            continue  # Unavailability can support an unknown, never resolved execution.
        tx, pin = obj["result"], pins[ev["pin_id"]][1]
        hash_key = "transactionHash" if ev["query"]["method"] == "eth_getTransactionReceipt" else "hash"
        need(tx[hash_key].lower() == ev["tx_hash"].lower(), f"{eid}: captured transaction conflict")
        need(quantity(tx["blockNumber"]) == pin["number"] and tx["blockHash"].lower() == pin["hash"].lower(),
             f"{eid}: transaction requires its own historical pin")
        if ev["query"]["method"] == "eth_getTransactionReceipt" and "logs" in tx:
            validate_logs(tx["logs"], eid, None, [], pin["number"], pin["number"],
                          chain_hashes[ev["chain_id"]], ev["tx_hash"].lower())

    # Trace responses need not carry block identity. Bind successful traces through
    # a mined transaction/receipt already checked against its captured header above.
    transaction_pins = {
        (ev["chain_id"], ev["pin_id"], ev["tx_hash"].lower())
        for eid, ev in evidence.items()
        if ev["kind"] == "rpc"
        and ev["query"]["method"] in ("eth_getTransactionReceipt", "eth_getTransactionByHash")
        and not rpc_unavailable(ev, objects[eid]["response"])
    }
    for eid, ev in evidence.items():
        if ev["kind"] != "rpc" or ev["query"]["method"] not in ("debug_traceTransaction", "trace_transaction"):
            continue
        response = objects[eid]["response"]
        if not rpc_unavailable(ev, response):
            need((ev["chain_id"], ev["pin_id"], ev["tx_hash"].lower()) in transaction_pins,
                 f"{eid}: trace lacks transaction evidence at its chain/pin")

    target_scope = []
    seen_scope = set()
    for sid, item in scope.items():
        pair = identity(item)
        need(pair not in seen_scope, "duplicate address scope; combine roles")
        seen_scope.add(pair)
        need(pair[0] in chains, f"{sid}: inconsistent scope chain")
        need(type(item["material"]) is bool, f"{sid}: material must be boolean")
        need(isinstance(item["roles"], list) and bool(item["roles"]), f"{sid}: missing role")
        for role in item["roles"]:
            nonempty(role, "scope role")
        pid = item["pin_id"]
        need(pid in pins and pins[pid][0] == pair[0], f"{sid}: scope pin on wrong chain")
        refs(item["provenance"], evidence, f"{sid} provenance")
        need(any(identity(evidence[e]) == pair for e in item["provenance"]), f"{sid}: provenance lacks scope identity")
        runtime = item["runtime"]
        status = runtime["status"]
        need(status in ("captured", "no_code", "unavailable"), f"{sid}: runtime status missing")
        if status == "unavailable":
            nonempty(runtime["reason"], f"{sid}: unavailable runtime reason")
            refs(runtime["evidence_ids"], evidence, f"{sid} runtime attempts")
            need(all(identity(evidence[e]) == pair and evidence[e]["pin_id"] == pid
                     for e in runtime["evidence_ids"]), f"{sid}: runtime attempts lack exact scope/pin")
        else:
            eid = runtime["evidence_id"]
            ev = evidence[eid]
            need(identity(ev) == pair and ev["pin_id"] == pid, f"{sid}: runtime identity/pin mismatch")
            code = rpc_result(evidence, objects, eid, "eth_getCode")
            need(isinstance(code, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", code), f"{sid}: malformed runtime")
            need((code == "0x") == (status == "no_code"), f"{sid}: runtime status contradicts bytes")
            need(runtime["sha256"] == sha(bytes.fromhex(code[2:])), f"{sid}: runtime byte hash mismatch")
            if runtime.get("keccak256"):
                digest(runtime["keccak256"], "runtime keccak", True)
        proxy = item["proxy"]
        need(proxy["status"] in ("none_found", "resolved", "unresolved", "not_applicable"), "invalid proxy status")
        nonempty(proxy["basis"], f"{sid} proxy basis")
        refs(proxy["evidence_ids"], evidence, f"{sid} proxy evidence")
        need(any(identity(evidence[e]) == pair and evidence[e]["pin_id"] == pid
                 for e in proxy["evidence_ids"]), f"{sid}: proxy evidence lacks exact scope/pin")
        for key in ("implementation_scope_ids", "authority_scope_ids"):
            refs(proxy[key], scope, f"{sid} {key}", required=False)
            need(all(scope[x]["chain_id"] == pair[0] for x in proxy[key]), "proxy edge crosses chains; model bridge separately")
        need(proxy["status"] != "resolved" or bool(proxy["implementation_scope_ids"]), "resolved proxy lacks implementation scope")
        if pair == target:
            target_scope.append(item)
    need(len(target_scope) == 1 and target_scope[0]["material"] and target_scope[0]["pin_id"] == current_pid,
         "current material target scope missing")

    metadata = m["target"]["metadata"]
    need(set(metadata) == set(METADATA), "metadata fields missing/unsupported")
    for field, selector in METADATA.items():
        item = metadata[field]
        need(item["status"] in ("resolved", "unresolved"), "invalid metadata status")
        refs(item["evidence_ids"], evidence, f"metadata {field}",
             required=not (m.get("validation_profile") == CURRENT_PROFILE and item["status"] == "unresolved"))
        for eid in item["evidence_ids"]:
            ev = evidence[eid]
            need(identity(ev) == target and ev["pin_id"] == current_pid, f"metadata {field}: target/pin mismatch")
        if item["status"] == "unresolved":
            need(item["value"] is None, "unresolved metadata cannot assert a value")
            nonempty(item["reason"], "unresolved metadata reason")
        else:
            eid = item["evidence_ids"][0]
            raw = rpc_result(evidence, objects, eid, "eth_call")
            need(evidence[eid]["query"]["params"][0]["data"].lower() == selector, "metadata selector mismatch")
            decoded = decode_metadata(field, raw)
            need(type(decoded) is type(item["value"]) and decoded == item["value"], f"metadata {field}: decoded value conflicts")
    need(r["metadata"] == metadata, "reported metadata differs from target manifest")

    safety = m["safety"]
    for key in ("no_real_keys", "no_real_signing", "no_broadcast"):
        need(safety[key] is True, f"required safety declaration: {key}")
    sim = safety["simulation"]
    need(type(sim["used"]) is bool, "simulation used must be boolean")
    sim_evidence = [ev for ev in evidence.values() if ev["kind"] == "simulation"]
    need(sim["used"] or not sim_evidence, "undeclared simulation evidence")
    if sim["used"]:
        for key in ("verified_disposable_local_fork", "synthetic_accounts_only", "counterfactual",
                    "no_transaction_forwarding"):
            need(sim[key] is True, f"fork restriction missing: {key}")
        from urllib.parse import urlsplit
        url = urlsplit(sim["endpoint"])
        need(url.scheme in ("http", "https") and url.hostname in ("localhost", "127.0.0.1", "::1")
             and not url.username and not url.password, "fork endpoint must be local without credentials")
        nonempty(sim["process_provenance"], "local fork process provenance")
        nonempty(sim["snapshot_id"], "fork snapshot")
        need(sim["source_pin_id"] in pins, "fork source pin missing")
        local_cid = integer(sim["local_chain_id"], "local chain", 1)
        need(local_cid not in chains, "fork must use a distinct synthetic local chain ID")
        refs(sim["verification_evidence_ids"], evidence, "fork verification evidence")
        need(isinstance(sim["overrides"], list), "fork overrides must be explicit, including empty list")
        need(bool(sim_evidence), "declared simulation lacks artifacts")
    need(r["safety"] == safety, "report safety declarations conflict")

    discoveries = index(m["discoveries"], "discovery")
    for did, discovery in discoveries.items():
        cid = discovery["chain_id"]
        need(cid in chains, "discovery chain not in scope")
        for key in ("universe", "pagination", "inclusion_rules", "exclusions", "materiality", "coverage"):
            nonempty(discovery[key], f"discovery {did} {key}")
        need(isinstance(discovery["block_ranges"], list), "discovery ranges must be a list")
        for start, end in discovery["block_ranges"]:
            need(0 <= integer(start, "range start") <= integer(end, "range end") <= pins[chains[cid]["current_pin"]][1]["number"],
                 "discovery range exceeds pin")
        refs(discovery["evidence_ids"], evidence, "discovery evidence")
        need(all(evidence[e]["chain_id"] == cid for e in discovery["evidence_ids"]), "discovery evidence chain mismatch")

    findings = index(r["findings"], "finding")
    need(bool(findings), "broad report has no findings/unknowns")
    for fid, f in findings.items():
        pair = identity(f)
        need(pair in seen_scope, f"{fid}: finding scope identity missing")
        need(f["pin_id"] in pins and pins[f["pin_id"]][0] == pair[0], f"{fid}: finding pin chain mismatch")
        need(f["evidence_type"] in ("proven_fact", "strongly_supported", "inference", "unknown"), "invalid evidence class")
        need(f["confidence"] in ("high", "medium", "low", "unknown"), "invalid confidence")
        for key in ("proposition", "decoding_basis", "alternatives", "coverage", "stale_when", "time_basis"):
            nonempty(f[key], f"finding {fid} {key}")
        refs(f["evidence_ids"], evidence, f"finding {fid} evidence")
        refs(f["discovery_ids"], discoveries, f"finding {fid} discoveries", required=False)
        need(type(f["discovery_claim"]) is bool, "discovery_claim must be boolean")
        need(not f["discovery_claim"] or bool(f["discovery_ids"]), "discovery claim lacks search universe")
        need(any(identity(evidence[e]) == pair and evidence[e]["pin_id"] == f["pin_id"] for e in f["evidence_ids"]),
             f"{fid}: finding lacks evidence at its exact scope and pin")
        need(f["evidence_type"] != "unknown" or f["confidence"] == "unknown", "unknown finding has resolved confidence")
        need(f["evidence_type"] == "unknown" or f["confidence"] != "unknown", "resolved finding has unknown confidence")

    ratings = index(r["ratings"], "rating")
    need(set(ratings) == set(DIMENSIONS), "all eleven distinct risk dimensions are required")
    for did, rating in ratings.items():
        need(rating["status"] in ("pass", "concern", "unknown", "not_applicable"), f"{did}: invalid rating status")
        need(rating["severity"] in ("critical", "high", "medium", "low", "none", "unknown"), "invalid severity")
        need(rating["likelihood"] in ("observed", "likely", "possible", "unlikely", "unknown", "not_applicable"), "invalid likelihood")
        need(rating["confidence"] in ("high", "medium", "low", "unknown"), "invalid rating confidence")
        need(rating["coverage"] in ("complete", "partial", "unavailable", "not_applicable"), "invalid coverage")
        refs(rating["finding_ids"], findings, f"{did} finding ledger")
        for key in ("rationale", "time_basis"):
            nonempty(rating[key], f"{did} {key}")
        unknown = any(findings[x]["evidence_type"] in ("unknown", "inference")
                      or findings[x]["confidence"] in ("unknown", "low") for x in rating["finding_ids"])
        failed_support = any(evidence[e]["kind"] == "rpc" and rpc_unavailable(evidence[e], objects[e]["response"])
                             for f in rating["finding_ids"] for e in findings[f]["evidence_ids"])
        if rating["status"] == "pass":
            need(not unknown and not failed_support and rating["coverage"] == "complete" and rating["confidence"] in ("high", "medium")
                 and rating["severity"] == "none" and rating["likelihood"] != "unknown",
                 f"{did}: unknown/skipped/partial check presented as a pass")
        if rating["status"] == "unknown":
            need(rating["severity"] == "unknown" and rating["confidence"] == "unknown", "unknown rating must preserve uncertainty")
        if rating["status"] == "not_applicable":
            need(rating["coverage"] == "not_applicable" and not unknown and not failed_support, "not-applicable rating requires resolved evidence")
        if rating["status"] == "concern":
            need(rating["severity"] in ("critical", "high", "medium", "low"), "concern requires explicit severity")
    if "summary" in r:
        validate_summary(r["summary"], findings, ratings, evidence, objects,
                         r.get("validation_profile", LEGACY_PROFILE),
                         allow_empty=r.get("validation_profile") == CURRENT_PROFILE
                         and r.get("completion_review_version") == 2 and r.get("completion_status") == "checkpoint"
                         and r.get("delivery_status") == "internal_checkpoint")
    validate_profile(m, r, evidence, objects, pins, scope, findings, ratings, discoveries, root)
    for key in ("verdict", "conditions", "main_reasons", "strongest_contrary_evidence", "unresolved_questions", "change_evidence"):
        nonempty(r[key], f"report {key}")
    need(not re.search(r"\b(?:unconditionally safe|completely safe|guaranteed safe)\b", r["verdict"], re.I), "unconditional safety verdict")
    if rendered:
        # This is exact deterministic-output validation, not NLP validation of arbitrary reports.
        from render_report import render
        need(Path(rendered).read_text(encoding="utf-8") == render(m, r, sha(report_path.read_bytes())),
             "rendered report differs from bound report source")
    return m, r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--allow-synthetic", action="store_true", help="offline tests only")
    parser.add_argument("--rendered", type=Path)
    parser.add_argument("--profile", choices=(CURRENT_PROFILE, LEGACY_PROFILE), default=CURRENT_PROFILE,
                        help="new reports require the strict profile; select legacy-v1 explicitly for old artifacts")
    args = parser.parse_args()
    try:
        validate(args.bundle, args.allow_synthetic, args.rendered, args.profile)
    except (Invalid, KeyError, TypeError, ValueError, OSError, IndexError, AttributeError, OverflowError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID: bundle identities, pins, evidence bindings, ratings and declarations are consistent.")
    print(LIMITS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
