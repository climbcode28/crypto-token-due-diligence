"""Method-specific read-only wire validation. No protocol recognition or network."""
import base64
import re

from solana_common import need, natural, pubkey, signature, base58_bytes, TOKEN_PROGRAM, TOKEN_2022
from solana_session import label

METHODS = {"getGenesisHash", "getAccountInfo", "getMultipleAccounts", "getBlock", "getBlockTime",
    "getEpochInfo", "getTokenLargestAccounts", "getTokenSupply", "getSignaturesForAddress",
    "getTransaction", "getTokenAccountsByOwner", "getProgramAccounts"}
STATE = {"getAccountInfo", "getMultipleAccounts", "getTokenLargestAccounts", "getTokenSupply", "getTokenAccountsByOwner", "getProgramAccounts"}
SCAN_ROWS = 5000  # A sliced program scan is a bounded census; the byte allowance still caps it.


def amount(value):
    need(isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,38}", value), "canonical atomic amount required")
    return int(value)


def config(value, extra=()):
    need(isinstance(value, dict) and set(value) <= {"commitment", "minContextSlot", *extra}, "unsupported RPC configuration")
    need(value.get("commitment") == "finalized", "explicit finalized commitment required")
    if "minContextSlot" in value:
        natural(value["minContextSlot"])


def account_config(value, extra=()):
    config(value, ("encoding", "dataSlice", *extra))
    need(value.get("encoding") == "base64", "raw base64 required")
    if "dataSlice" in value:
        part = value["dataSlice"]
        need(isinstance(part, dict) and set(part) == {"offset", "length"}, "invalid data slice")
        natural(part["offset"])
        need(0 < natural(part["length"]) <= 1_000_000, "data slice length out of bounds")


def validate_request(request):
    need(isinstance(request, dict) and set(request) == {"jsonrpc", "id", "method", "params"}, "invalid RPC request fields")
    need(request["jsonrpc"] == "2.0", "invalid JSON-RPC version")
    label(request["id"])
    method, params = request["method"], request["params"]
    need(method in METHODS and isinstance(params, list), "unsupported read method")
    if method == "getGenesisHash":
        need(params == [], "genesis takes no parameters")
    elif method in {"getAccountInfo", "getMultipleAccounts"}:
        need(len(params) == 2, "account read requires explicit configuration")
        addresses = params[0] if method == "getMultipleAccounts" else [params[0]]
        need(isinstance(addresses, list) and 1 <= len(addresses) <= 100, "account batch requires 1–100 addresses")
        for address in addresses:
            pubkey(address)
        need(len(set(addresses)) == len(addresses), "duplicate account address")
        account_config(params[1])
    elif method in {"getTokenSupply", "getTokenLargestAccounts"}:
        need(len(params) == 2, "token read requires configuration")
        pubkey(params[0])
        config(params[1])
    elif method == "getBlock":
        need(len(params) == 2, "block read requires configuration")
        natural(params[0])
        need(params[1] == {"commitment": "finalized", "transactionDetails": "none", "rewards": False}, "only bounded block headers supported")
    elif method == "getBlockTime":
        need(len(params) == 1, "block time needs one slot")
        natural(params[0])
    elif method == "getEpochInfo":
        need(len(params) == 1, "epoch requires explicit configuration")
        config(params[0])
    elif method == "getSignaturesForAddress":
        need(len(params) == 2, "signature history needs configuration")
        pubkey(params[0])
        config(params[1], ("limit", "before", "until"))
        need(1 <= natural(params[1].get("limit")) <= 25, "history page must contain 1–25 candidates")
        for key in ("before", "until"):
            if key in params[1]:
                signature(params[1][key])
    elif method == "getTransaction":
        need(len(params) == 2, "transaction needs configuration")
        signature(params[0])
        need(params[1] == {"commitment": "finalized", "encoding": "json", "maxSupportedTransactionVersion": 0}, "only raw legacy/v0 JSON transactions supported")
    elif method == "getTokenAccountsByOwner":
        need(len(params) == 3 and isinstance(params[1], dict) and set(params[1]) == {"mint"}, "owner lookup must be narrowed to an exact mint")
        pubkey(params[0])
        pubkey(params[1]["mint"])
        account_config(params[2])
        need("dataSlice" not in params[2], "owner binding requires complete base accounts")
    elif method == "getProgramAccounts":
        need(len(params) == 2, "program lookup needs configuration")
        pubkey(params[0])
        account_config(params[1], ("filters", "withContext"))
        need(params[1].get("withContext") is True, "program lookup requires context")
        filters = params[1].get("filters")
        need(isinstance(filters, list) and len(filters) == 2, "unbounded program scans prohibited")
        size, match = filters
        need(isinstance(size, dict) and set(size) == {"dataSize"} and 1 <= natural(size["dataSize"]) <= 8192, "bounded dataSize filter required")  # DLMM PositionV2 is 8120 bytes; the byte allowance still caps the scan
        need(isinstance(match, dict) and set(match) == {"memcmp"}, "exact relationship filter required")
        match = match["memcmp"]
        need(isinstance(match, dict) and set(match) == {"offset", "bytes"}, "invalid relationship filter")
        need(natural(match["offset"]) + 32 <= size["dataSize"], "relationship filter outside account")
        pubkey(match["bytes"])
        part = params[1].get("dataSlice")
        if part is not None:
            need(part["offset"] == 0 and match["offset"] + 32 <= part["length"] <= size["dataSize"], "program scan slice must retain the relationship prefix")
    return request


def account(value, sliced=False):
    if value is None:
        return None
    need(isinstance(value, dict), "account object required")
    pubkey(value["owner"])
    need(type(value["executable"]) is bool, "account executable flag required")
    natural(value["lamports"])
    data = value["data"]
    need(isinstance(data, list) and len(data) == 2 and data[1] == "base64" and isinstance(data[0], str), "base64 account bytes required")
    raw = base64.b64decode(data[0], validate=True)
    need(len(raw) <= 1_000_000, "account bytes exceed bound")
    if "space" in value:
        space = natural(value["space"])
        need(space >= len(raw) if sliced else space == len(raw), "account space mismatch")
    if "rentEpoch" in value:
        natural(value["rentEpoch"])
    return value


def signed_time(value):
    need(value is None or type(value) is int and -(2**63) <= value < 2**63, "invalid block time")


def header(value, slot):
    need(isinstance(value, dict), "block header required")
    pubkey(value["blockhash"])
    pubkey(value["previousBlockhash"])
    parent = natural(value["parentSlot"])
    need(parent < slot or slot == 0 and parent == 0, "invalid parent slot")
    signed_time(value["blockTime"])
    return {k: value[k] for k in ("blockhash", "previousBlockhash", "parentSlot", "blockTime")}


def validate_response(request, response):
    """Return a typed raw observation; errors and nulls never become factual zeroes."""
    validate_request(request)
    need(isinstance(response, dict) and response.get("jsonrpc") == "2.0" and response.get("id") == request["id"], "RPC response ID/version mismatch")
    need(("result" in response) != ("error" in response), "result/error ambiguity")
    if "error" in response:
        error = response["error"]
        need(isinstance(error, dict) and type(error.get("code")) is int and isinstance(error.get("message"), str), "invalid RPC error")
        return {"status": "rpc_error", "result": None}
    value, method, params = response["result"], request["method"], request["params"]
    if value is None:
        return {"status": "null", "result": None}
    output = {"status": "ok", "result": value}
    if method == "getGenesisHash":
        pubkey(value)
    elif method in STATE:
        need(isinstance(value, dict) and isinstance(value.get("context"), dict) and "value" in value, "state context/value required")
        slot = natural(value["context"]["slot"])
        settings = params[-1]
        need(slot >= settings.get("minContextSlot", 0), "context below requested floor")
        output["context_slot"] = slot
        data = value["value"]
        if method in {"getAccountInfo", "getMultipleAccounts"}:
            addresses = params[0] if method == "getMultipleAccounts" else [params[0]]
            values = data if method == "getMultipleAccounts" else [data]
            need(isinstance(values, list) and len(values) == len(addresses), "account array length mismatch")
            for item in values:
                account(item, "dataSlice" in settings)
            output.update(addresses=addresses, address_indices={a: i for i, a in enumerate(addresses)}, missing_indices=[i for i, a in enumerate(values) if a is None])
        elif method in {"getTokenAccountsByOwner", "getProgramAccounts"}:
            sliced = method == "getProgramAccounts" and "dataSlice" in settings
            need(isinstance(data, list) and len(data) <= (SCAN_ROWS if sliced else 100), "owner/program result exceeds bounded sample")
            addresses = []
            for row in data:
                addresses.append(pubkey(row["pubkey"]))
                need(row["account"] is not None, "lookup account missing")
                account(row["account"], sliced)
                raw = base64.b64decode(row["account"]["data"][0], validate=True)
                if method == "getProgramAccounts":
                    size, match = settings["filters"]
                    match = match["memcmp"]
                    expected = settings["dataSlice"]["length"] if sliced else size["dataSize"]
                    need(row["account"]["owner"] == params[0] and len(raw) == expected and raw[match["offset"]:match["offset"]+32] == base58_bytes(match["bytes"], 32), "unrequested program account relationship")
                else:
                    need(row["account"]["owner"] in (TOKEN_PROGRAM, TOKEN_2022) and len(raw) >= 165,
                         "owner lookup did not return a base token account")
                    need(raw[:32] == base58_bytes(params[1]["mint"], 32) and raw[32:64] == base58_bytes(params[0], 32),
                         "unrequested mint or spending owner")
            need(len(addresses) == len(set(addresses)), "duplicate lookup account")
            output.update(addresses=addresses, address_indices={a: i for i, a in enumerate(addresses)})
        else:
            rows = data if method == "getTokenLargestAccounts" else [data]
            need(isinstance(rows, list) and len(rows) <= 20, "largest accounts exceeds sample")
            seen = set()
            for row in rows:
                need(isinstance(row, dict), "token amount row required")
                need(amount(row["amount"]) < 2**64 and natural(row["decimals"]) <= 255, "invalid token quantity")
                if method == "getTokenLargestAccounts":
                    address = pubkey(row["address"])
                    need(address not in seen, "duplicate largest account")
                    seen.add(address)
    elif method == "getBlock":
        header(value, params[0])
    elif method == "getBlockTime":
        signed_time(value)
    elif method == "getEpochInfo":
        for field in ("absoluteSlot", "blockHeight", "epoch", "slotIndex", "slotsInEpoch"):
            natural(value[field])
        need(value["slotIndex"] < value["slotsInEpoch"], "invalid epoch slot index")
        need(value["absoluteSlot"] >= params[0].get("minContextSlot", 0), "epoch below requested floor")
        output["context_slot"] = value["absoluteSlot"]
    elif method == "getSignaturesForAddress":
        need(isinstance(value, list) and len(value) <= params[1]["limit"], "signature page exceeds requested limit")
        seen, previous = set(), 2**64
        for row in value:
            sig, slot = signature(row["signature"]), natural(row["slot"])
            need(sig not in seen and slot <= previous, "duplicate or unordered signature page")
            need("err" in row, "execution status missing")
            signed_time(row["blockTime"])
            seen.add(sig)
            previous = slot
    elif method == "getTransaction":
        natural(value["slot"])
        signed_time(value["blockTime"])
        version = value.get("version")
        if not (version == "legacy" or type(version) is int and version == 0):
            return {"status": "unsupported", "result": value, "reason": "transaction_version"}
        tx = value["transaction"]
        need(isinstance(tx, dict) and isinstance(tx.get("signatures"), list) and params[0] in tx["signatures"], "requested transaction signature missing")
        for sig in tx["signatures"]:
            signature(sig)
        need(isinstance(tx.get("message"), dict) and isinstance(tx["message"].get("accountKeys"), list), "historical transaction keys required")
        for key in tx["message"]["accountKeys"]:
            pubkey(key)
        need("meta" in value, "transaction metadata field missing")
        output["historical_slot"] = value["slot"]
    return output


def consistency(observations, target):
    """Scan all successful genesis/headers, including observations unused by findings."""
    headers, networks, accounts, times = {}, [], {}, {}
    for row in observations:
        if row.get("status") != "ok":
            continue
        request, response = row["request"], row["response"]
        validated = validate_response(request, response)
        if validated["status"] != "ok":
            continue
        value = validated["result"]
        if request["method"] == "getGenesisHash":
            networks.append(value)
            need(value == target["genesis_hash"], "contradictory network observation")
        elif request["method"] == "getBlock":
            slot = request["params"][0]
            normalized = header(value, slot)
            need(slot not in headers or normalized == headers[slot], "contradictory block observation")
            need(slot not in times or times[slot] == normalized["blockTime"], "contradictory block time observation")
            headers[slot] = normalized
        elif request["method"] == "getBlockTime":
            slot = request["params"][0]
            need(slot not in times or times[slot] == value, "contradictory block time observation")
            need(slot not in headers or headers[slot]["blockTime"] == value, "contradictory block time observation")
            times[slot] = value
        elif request["method"] in ("getAccountInfo", "getMultipleAccounts"):
            values = value["value"] if request["method"] == "getMultipleAccounts" else [value["value"]]
            options = request["params"][1] if len(request["params"]) > 1 and isinstance(request["params"][1], dict) else {}
            data_slice = options.get("dataSlice")
            data_slice = (data_slice.get("offset"), data_slice.get("length")) if isinstance(data_slice, dict) else None
            for address, account_value in zip(validated["addresses"], values):
                # A sliced read and a full read of one account are different observations, not a contradiction.
                key = (validated["context_slot"], address, data_slice)
                need(key not in accounts or accounts[key] == account_value, "contradictory account observation at same context")
                accounts[key] = account_value
    return {"network_observations": len(networks), "header_slots": sorted(headers)}
