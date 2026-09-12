"""Deterministic collector-plan builders for the standard broad pipeline and its presets.

Every plan is explicit reads only; addresses from the chain registry are candidates that
the pipeline verifies with code reads at the pin before treating them as infrastructure.
"""
import json
from pathlib import Path

from backend_common import address, integer, need
from keccak import selector

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "chain-registry.json"
DEAD = "0x000000000000000000000000000000000000dead"
SLOTS = {
    "eip1967-implementation": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
    "eip1967-admin": "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
    "eip1967-beacon": "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
}
METADATA_SIGS = {"name": "name()", "symbol": "symbol()", "decimals": "decimals()", "total_supply": "totalSupply()"}
# Zero-argument getters whose names commonly expose control or launch structure. A revert
# is a cheap recorded attempt; a value is a lead until source correspondence is established.
CONTROL_GETTERS = ["owner()", "paused()", "getOwner()", "admin()", "implementation()", "factory()", "deployer()",
                   "launchFactory()", "liquidityPool()", "pairToken()", "poolFee()", "treasury()", "feeRecipient()",
                   "taxWallet()", "maxTxBps()", "maxWalletBps()", "launchBlock()", "tradingEnabled()", "locker()"]
V3_POOL_GETTERS = ["token0()", "token1()", "fee()", "liquidity()", "slot0()", "factory()", "tickSpacing()"]
V2_POOL_GETTERS = ["token0()", "token1()", "getReserves()", "totalSupply()", "factory()"]
NFPM_GETTERS = {"positions": "positions(uint256)", "ownerOf": "ownerOf(uint256)", "getApproved": "getApproved(uint256)"}
SAFE_GETTERS = ["getOwners()", "getThreshold()", "masterCopy()"]


def registry(chain_id):
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return data["chains"].get(str(integer(chain_id, "chain ID", 1)), {})


def word_address(value):
    return "0" * 24 + address(value)[2:]


def word_uint(value, bits=256):
    integer(value, "ABI integer")
    need(value < 2 ** bits, "ABI integer overflow")
    return format(value, "064x")


def encode(signature, *words):
    return "0x" + selector(signature) + "".join(words)


def call(qid, pin, to, data, priority=50):
    return {"id": qid, "pin_id": pin, "method": "eth_call", "params": [{"to": address(to), "data": data}], "priority": priority}


def code(qid, pin, target, priority=40):
    return {"id": qid, "pin_id": pin, "method": "eth_getCode", "params": [address(target)], "priority": priority}


def storage(qid, pin, target, slot, priority=50):
    return {"id": qid, "pin_id": pin, "method": "eth_getStorageAt", "params": [address(target), slot], "priority": priority}


def label(text):
    cleaned = "".join(c if c.isalnum() or c in "-_" else "-" for c in text)[:60].strip("-")
    need(bool(cleaned), "empty query label")
    return cleaned


def plan(target, pins, queries):
    seen = set()
    for q in queries:
        need(q["id"] not in seen, "duplicate preset query id " + q["id"])
        seen.add(q["id"])
    return {"schema_version": 1, "target": {"chain_id": target["chain_id"], "address": address(target["address"])},
            "pins": [{"id": pid, "number": number} for pid, number in pins.items()], "queries": queries}


def getter_queries(prefix, pin, contract, signatures, priority=50):
    rows = []
    for signature in signatures:
        name = signature.split("(", 1)[0]
        rows.append(call(label(prefix + "-" + name), pin, contract, encode(signature), priority))
    return rows


def token_phase1(target, pin, abi_view_getters=None, extra_getters=None, control_getters=None):
    """Runtime, metadata, control getters and proxy slots at the current pin."""
    token = target["address"]
    queries = [code("runtime", pin, token, 10)]
    queries += [call("metadata-" + field, pin, token, encode(sig), 10) for field, sig in METADATA_SIGS.items()]
    probes = CONTROL_GETTERS if control_getters is None else control_getters
    getters = list(dict.fromkeys([*(abi_view_getters or []), *probes, *(extra_getters or [])]))
    queries += getter_queries("token", pin, token, getters, 30)
    queries += [storage("token-" + name, pin, token, slot, 30) for name, slot in SLOTS.items()]
    return queries


def pool_queries(prefix, pin, pool, version):
    if version == "v2":
        return [code(prefix + "-runtime", pin, pool)] + getter_queries(prefix, pin, pool, V2_POOL_GETTERS)
    return [code(prefix + "-runtime", pin, pool)] + getter_queries(prefix, pin, pool, V3_POOL_GETTERS)


def v4_queries(prefix, pin, state_view, pool_id_hex):
    need(isinstance(pool_id_hex, str) and len(pool_id_hex) == 66 and pool_id_hex.startswith("0x"), "v4 pool id must be 32 bytes")
    word = pool_id_hex[2:].lower()
    return [code(prefix + "-stateview-runtime", pin, state_view),
            call(prefix + "-getSlot0", pin, state_view, encode("getSlot0(bytes32)", word)),
            call(prefix + "-getLiquidity", pin, state_view, encode("getLiquidity(bytes32)", word))]


def balance_queries(prefix, pin, asset, holders):
    return [call(label(prefix + "-" + name), pin, asset, encode("balanceOf(address)", word_address(holder)))
            for name, holder in holders.items()]


def position_queries(prefix, pin, manager, token_ids, operators=()):
    rows = [code(prefix + "-manager-runtime", pin, manager)]
    for token_id in token_ids:
        integer(token_id, "position token id")
        for name, signature in NFPM_GETTERS.items():
            rows.append(call(label(prefix + "-" + str(token_id) + "-" + name), pin, manager, encode(signature, word_uint(token_id))))
    for owner, operator in operators:
        rows.append(call(label(prefix + "-approvedforall-" + operator[2:10]), pin, manager,
                         encode("isApprovedForAll(address,address)", word_address(owner), word_address(operator))))
    return rows


def quote_queries(prefix, pin, quoter, token_in, token_out, fee, amounts):
    rows = [code(prefix + "-quoter-runtime", pin, quoter)]
    for amount in amounts:
        rows.append(call(label(prefix + "-" + str(amount["label"])), pin, quoter,
                         encode("quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                                word_address(token_in), word_address(token_out), word_uint(amount["raw"]), word_uint(fee, 24), word_uint(0, 160))))
    return rows


def architecture_queries(prefix, pin, contracts):
    """Code, owner and proxy slots for every candidate contract surfaced by getters or discovery."""
    rows = []
    for name, contract in contracts.items():
        base = label(prefix + "-" + name)
        rows.append(code(base + "-runtime", pin, contract))
        rows.append(call(base + "-owner", pin, contract, encode("owner()")))
        rows.append(storage(base + "-eip1967-implementation", pin, contract, SLOTS["eip1967-implementation"]))
    return rows


def safe_queries(prefix, pin, safe):
    return getter_queries(prefix, pin, safe, SAFE_GETTERS)


def receipt_queries(transactions):
    """Receipt and transaction reads, each at its own historical pin {tx_hash: block_number}."""
    pins, rows = {}, []
    for tx, number in transactions.items():
        pid = label("tx-" + str(number))
        pins[pid] = integer(number, "block number", 1)
        short = tx[2:10]
        rows.append({"id": label("receipt-" + short), "pin_id": pid, "method": "eth_getTransactionReceipt", "params": [tx]})
        rows.append({"id": label("tx-" + short), "pin_id": pid, "method": "eth_getTransactionByHash", "params": [tx]})
    return pins, rows


def range_log_query(qid, pin, contract, topics, from_block, to_block):
    need(0 <= from_block <= to_block and to_block - from_block < 10000, "log range must span 1-10000 blocks")
    return {"id": qid, "pin_id": pin, "method": "eth_getLogs",
            "params": [{"address": address(contract), "topics": topics, "from_block": from_block, "to_block": to_block}]}
