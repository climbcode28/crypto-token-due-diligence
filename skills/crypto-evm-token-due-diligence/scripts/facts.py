"""Compact decoded view of collected evidence for the coordinator.

Decoding here is display help bound to the raw artifacts; it does not establish ABI
semantics, source correspondence or economic meaning. Never paste raw collections into
the conversation; read this view instead.
"""
import json
import re
from pathlib import Path

from validate_bundle import read_json
from keccak import topic

INCREASE_LIQUIDITY_TOPIC = topic("IncreaseLiquidity(uint256,uint128,uint256,uint256)")

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEAD = "0x000000000000000000000000000000000000dead"


def account_code_kind(code):
    """Describe runtime shape only; code presence is not beneficial ownership."""
    if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", code):
        return "unknown"
    if code == "0x":
        return "no_code"
    if len(code) == 48 and code[2:8].lower() == "ef0100":
        return "delegated_account"
    return "code_bearing"


def holder_summary(holders, supply):
    """Sum selected unique atomic balances, never rounded shares or indexer balances.

    The bounded RPC sample is not a global ranking or beneficial-owner cluster.
    Missing reads remain missing; zero supply cannot supply a denominator.
    """
    unique = {}
    for row in holders:
        address = str(row.get("address") or "").lower()
        if not address:
            continue
        if address in unique:
            if unique[address].get("raw") != row.get("raw"):
                raise ValueError("Conflicting balances for one address in holder sample")
            continue
        unique[address] = row
    readable = [r for r in unique.values() if type(r.get("raw")) is int and r["raw"] >= 0]

    def percent(raw):
        if type(supply) is not int or supply <= 0:
            return None
        # Half-up, four places, using integers even for 256-bit atomic supplies.
        units = (raw * 1000000 * 2 + supply) // (2 * supply)
        return f"{units // 10000}.{units % 10000:04d}"

    total = sum(r["raw"] for r in readable)
    counts = dict.fromkeys(("no_code", "delegated_account", "code_bearing", "unknown"), 0)
    for row in unique.values():
        kind = row.get("account_kind")
        if kind not in counts:
            size = row.get("code_bytes")
            kind = "no_code" if size == 0 else "code_bearing" if isinstance(size, int) and size > 0 else "unknown"
        counts[kind] += 1
    largest = max(readable, key=lambda r: r["raw"]) if readable else None
    return {"selected_count": len(unique), "read_count": len(readable), "missing_count": len(unique) - len(readable),
            "sum_raw": str(total) if readable else None, "supply_raw": str(supply) if type(supply) is int and supply > 0 else None,
            "pct_supply": percent(total) if readable else None, "account_counts": counts,
            "largest": {"address": largest["address"], "raw": str(largest["raw"]), "pct_supply": percent(largest["raw"])} if largest else None}

SELECTORS = {
    "06fdde03": ("name", "string"), "95d89b41": ("symbol", "string"), "313ce567": ("decimals", "uint"),
    "18160ddd": ("totalSupply", "uint"), "8da5cb5b": ("owner", "address"), "5c975abb": ("paused", "bool"),
    "70a08231": ("balanceOf", "uint"), "dd62ed3e": ("allowance", "uint"),
    "0dfe1681": ("token0", "address"), "d21220a7": ("token1", "address"), "ddca3f43": ("fee", "uint"),
    "1a686502": ("liquidity", "uint"), "c45a0155": ("factory", "address"), "d0c93a7c": ("tickSpacing", "int"),
    "3850c7bd": ("slot0", ["uint:sqrtPriceX96", "int:tick", "uint:observationIndex", "uint:observationCardinality",
                           "uint:observationCardinalityNext", "uint:feeProtocol", "bool:unlocked"]),
    "0902f1ac": ("getReserves", ["uint:reserve0", "uint:reserve1", "uint:blockTimestampLast"]),
    "99fbab88": ("positions", ["uint:nonce", "address:operator", "address:token0", "address:token1", "uint:fee",
                               "int:tickLower", "int:tickUpper", "uint:liquidity", "uint:feeGrowthInside0",
                               "uint:feeGrowthInside1", "uint:tokensOwed0", "uint:tokensOwed1"]),
    "6352211e": ("ownerOf", "address"), "081812fc": ("getApproved", "address"), "e985e9c5": ("isApprovedForAll", "bool"),
    "c6a5026a": ("quoteExactInputSingle", ["uint:amountOut", "uint:sqrtPriceX96After", "uint:initializedTicksCrossed", "uint:gasEstimate"]),
    "c815641c": ("getSlot0", ["uint:sqrtPriceX96", "int:tick", "uint:protocolFee", "uint:lpFee"]),
    "fa6793d5": ("getLiquidity", "uint"), "a0e67e2b": ("getOwners", "address[]"), "e75235b8": ("getThreshold", "uint"),
    "a619486e": ("masterCopy", "address"), "d7b96d4e": ("locker", "address"), "3cf28b5a": ("getLaunchedToken", "raw"),
    "5c60da1b": ("implementation", "address"), "f851a440": ("admin", "address"),
}
SLOTS = {
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc": "eip1967.implementation",
    "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103": "eip1967.admin",
    "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50": "eip1967.beacon",
}


def word(result, index):
    start = 2 + 64 * index
    if len(result) < start + 64:
        return None
    return int(result[start:start + 64], 16)


def as_address(value):
    return "0x" + format(value, "040x") if value is not None and value < 2 ** 160 else None


def signed(value, bits=256):
    if value is None:
        return None
    return value - (1 << bits) if value >= 1 << (bits - 1) else value


def decode_string(result):
    try:
        data = bytes.fromhex(result[2:])
        if len(data) >= 64 and int.from_bytes(data[:32], "big") == 32:
            size = int.from_bytes(data[32:64], "big")
            if 64 + size <= len(data):
                return data[64:64 + size].decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return None


def decode_result(selector, result):
    """Best-effort decode by known selector; unknown shapes fall back to raw words."""
    if not isinstance(result, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", result):
        return {"raw": str(result)[:80]}
    name, spec = SELECTORS.get(selector, (None, None))
    words = (len(result) - 2) // 64
    if spec == "string":
        value = decode_string(result)
        return {"string": value} if value is not None else {"raw": result[:80], "words": words}
    if spec == "address[]":
        count = word(result, 1)
        if word(result, 0) != 32 or count is None or len(result) != 2 + 64 * (count + 2):
            return {"raw": result[:80], "words": words}
        if any(word(result, 2 + i) >= 2 ** 160 for i in range(count)):
            return {"raw": result[:80], "words": words}
        addresses = [as_address(word(result, 2 + i)) for i in range(min(count, 20))]
        return {"addresses": addresses, "count": count}
    if isinstance(spec, list):
        out = {}
        for index, item in enumerate(spec):
            kind, label = item.split(":", 1)
            value = word(result, index)
            if value is None:
                break
            # ABI encodes every signed integer as 256-bit two's complement regardless of declared width.
            out[label] = as_address(value) if kind == "address" else bool(value) if kind == "bool" else signed(value) if kind == "int" else value
        return out
    if words == 1:
        value = word(result, 0)
        out = {"int": value}
        if spec == "address" or (spec is None and 2 ** 96 <= value < 2 ** 160):
            out["address"] = as_address(value)
        if spec == "bool" or (spec is None and value in (0, 1)):
            out["bool"] = bool(value)
        if spec == "int":
            out["int"] = signed(value)
        return out
    if words == 0:
        return {"empty": True}
    text = decode_string(result)
    if text is not None:
        return {"string": text}
    return {"raw": result[:80], "words": words}


def decimal_string(raw, decimals):
    if raw is None or decimals is None or not 0 <= decimals <= 36:
        return None
    sign = "-" if raw < 0 else ""
    raw = abs(raw)
    whole, frac = divmod(raw, 10 ** decimals) if decimals else (raw, 0)
    if not decimals or frac == 0:
        return sign + f"{whole:,}"
    fraction = str(frac).rjust(decimals, "0")[:6].rstrip("0")
    if whole == 0 and not fraction:
        return sign + "<0.000001"
    return sign + f"{whole:,}" + ("." + fraction if fraction else "")


def transfers(receipt):
    rows = []
    for log in receipt.get("logs", []):
        topics = log.get("topics") or []
        if len(topics) == 3 and topics[0].lower() == TRANSFER and re.fullmatch(r"0x[0-9a-fA-F]{64}", log.get("data", "")):
            rows.append({"asset": log["address"].lower(), "from": "0x" + topics[1][-40:].lower(), "to": "0x" + topics[2][-40:].lower(),
                         "amount_raw": int(log["data"], 16), "log_index": int(log["logIndex"], 16)})
    return rows


def summarize_row(root, ev, names=None, decimals=None):
    """One compact line of facts for an evidence row, reading its artifact."""
    query = ev.get("query", {})
    method = query.get("method") or query.get("operation")
    alias = (ev.get("collection_provenance") or {}).get("evidence_id") or ev["id"]
    item = {"alias": alias, "id": ev["id"], "address": ev["address"], "pin": ev.get("pin_id"), "kind": ev["kind"],
            "method": method, "status": ev.get("observation_status", "ok")}
    if ev["kind"] != "rpc":
        item["operation"] = method
        for key in ("url", "source_urls"):
            if key in query:
                item[key] = query[key]
        return item
    try:
        obj = read_json(Path(root) / ev["artifact"])
    except (OSError, ValueError):
        item["status"] = "artifact_unreadable"
        return item
    response = obj.get("response", {})
    if "error" in response:
        item["status"] = "rpc_error"
        item["error"] = str(response["error"].get("message", ""))[:80]
        return item
    result = response.get("result")
    if result is None:
        item["status"] = "null_result"
        return item
    params = query.get("params", [])
    if method == "eth_call":
        data = params[0].get("data", "")
        selector = data[2:10].lower()
        label = (names or {}).get(selector) or SELECTORS.get(selector, (selector, None))[0]
        item["call"] = label
        if len(data) > 10:
            item["args"] = [as_address(int(data[10 + 64 * i:10 + 64 * (i + 1)], 16)) or int(data[10 + 64 * i:10 + 64 * (i + 1)], 16)
                            for i in range((len(data) - 10) // 64)][:4]
        item["decoded"] = decode_result(selector, result)
        if label in ("balanceOf", "totalSupply") and decimals is not None and isinstance(item["decoded"].get("int"), int):
            item["decoded"]["decimal"] = decimal_string(item["decoded"]["int"], decimals)
    elif method == "eth_getCode":
        raw = bytes.fromhex(result[2:])
        item["code_bytes"] = len(raw)
        if raw:
            from keccak import keccak256_hex
            item["keccak256"] = keccak256_hex(raw)
    elif method == "eth_getStorageAt":
        item["slot"] = SLOTS.get(str(params[1]).lower(), str(params[1])[:18])
        value = int(result, 16)
        item["decoded"] = {"int": value, "address": as_address(value) if value else None}
    elif method == "eth_getBlockByNumber":
        item["decoded"] = {"number": int(result["number"], 16), "hash": result["hash"], "timestamp": int(result["timestamp"], 16)}
    elif method == "eth_getTransactionReceipt":
        item["decoded"] = {"status": int(result.get("status", "0x0"), 16), "block": int(result["blockNumber"], 16),
                           "from": result.get("from"), "to": result.get("to"), "logs": len(result.get("logs", [])),
                           "transfers": transfers(result)[:12]}
    elif method == "eth_getTransactionByHash":
        item["decoded"] = {"block": int(result["blockNumber"], 16), "from": result.get("from"), "to": result.get("to"),
                           "value": int(result.get("value", "0x0"), 16), "input_selector": (result.get("input") or "")[:10]}
    elif method == "eth_getLogs":
        ids = []
        for log in result or []:
            topics = (log.get("topics") or []) if isinstance(log, dict) else []
            if topics and str(topics[0]).lower() == INCREASE_LIQUIDITY_TOPIC and len(topics) > 1:
                try:
                    ids.append(int(topics[1], 16))
                except (TypeError, ValueError):
                    pass
        # Position ids from IncreaseLiquidity events are the input of the positions preset the queue names next.
        item["decoded"] = {"logs": len(result or []), "token_ids": sorted(set(ids))[:20], "token_ids_total": len(set(ids))}
    elif method == "eth_chainId":
        item["decoded"] = {"chain_id": int(result, 16)}
    elif method == "eth_getBalance":
        item["decoded"] = {"int": int(result, 16), "decimal": decimal_string(int(result, 16), 18)}
    return item


def facts_view(root, draft, names=None):
    root = Path(root)
    target = draft["target"]
    decimals = None
    for ev in draft["evidence"]:
        if ev["kind"] == "rpc" and ev["address"] == target["address"] and ev["query"].get("method") == "eth_call" \
                and ev["query"]["params"][0].get("data", "").lower() == "0x313ce567" and ev.get("observation_status", "ok") == "ok":
            try:
                value = int(read_json(root / ev["artifact"])["response"]["result"], 16)
                decimals = value if 0 <= value <= 36 else None
            except (OSError, ValueError, KeyError, TypeError):
                pass
    rows = [summarize_row(root, ev, names, decimals) for ev in draft["evidence"]]
    counts = {}
    for row in rows:
        counts[row["alias"]] = counts.get(row["alias"], 0) + 1
    for row in rows:
        row["ambiguous"] = counts[row["alias"]] > 1
    by_address = {}
    for row in rows:
        by_address.setdefault(row["address"], []).append(row)
    scope_ids = {s["address"]: s["id"] for s in draft.get("scope", [])}
    return {"target": target, "decimals": decimals,
            "pins": [{"id": p["id"], "number": p["number"], "timestamp_utc": p["timestamp_utc"]} for p in draft["pins"]],
            "scope": scope_ids, "rows_by_address": by_address, "findings": [f["id"] for f in draft.get("findings", [])],
            "coverage": {c["dimension"]: c["status"] for c in draft.get("coverage_records", [])}}


def render_text(view, limit=400):
    lines = ["target chain " + str(view["target"]["chain_id"]) + " " + view["target"]["address"] + " decimals=" + str(view["decimals"])]
    lines += ["pins: " + "; ".join(f"{p['id'][:24]}… #{p['number']} {p['timestamp_utc']}" for p in view["pins"])]
    lines += ["coverage: " + ", ".join(f"{k}={v}" for k, v in view["coverage"].items())]
    count = 0
    for addr, rows in view["rows_by_address"].items():
        label = view["scope"].get(addr, "")
        lines.append("## " + addr + (" (" + label + ")" if label else "") + f" [{len(rows)} rows]")
        for row in rows:
            if count >= limit:
                lines.append("… truncated; raise --limit for more rows")
                return "\n".join(lines)
            count += 1
            detail = row.get("decoded") or {k: row[k] for k in ("code_bytes", "keccak256", "url", "operation") if k in row}
            call = (row.get("call") + str(row.get("args", "")) + " ") if row.get("call") else ""
            pin = (row.get("pin") or "chain")[:22]
            name = row["alias"] + (f" (ambiguous alias; cite id {row['id']})" if row.get("ambiguous") and not row["alias"].startswith("sys-") else "")
            lines.append(f"- {name}: {row['method']} {call}@{pin} {row['status']} {json.dumps(detail, default=str)[:220]}")
    return "\n".join(lines)
