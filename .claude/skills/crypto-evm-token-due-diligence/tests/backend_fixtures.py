"""Synthetic regression case. No actual blockchain data or HTTP calls."""
import copy
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backend_common import canonical, sha, write_new
from detect import TRANSFER, ZERO

TOKEN = "0x1234567890abcdef1234567890abcdef12345678"
ALICE = "0x2234567890abcdef1234567890abcdef12345678"
BOB = "0x3234567890abcdef1234567890abcdef12345678"
CAROL = "0x4234567890abcdef1234567890abcdef12345678"
CHAIN = 31337
SELECTOR = "0x8c0b5e22"  # Synthetic configured predicate; no claim this is a real contract ABI.
SUPPLY = 10**24


def hh(value):
    return "0x" + hashlib.sha256(str(value).encode()).hexdigest()


def abi(value):
    return "0x" + format(value, "064x")


def calldata(account):
    return SELECTOR + "0" * 24 + account[2:]


def header(number):
    return {"number": hex(number), "hash": hh(number), "parentHash": hh(number - 1),
            "stateRoot": hh("state" + str(number)), "timestamp": hex(1704067200 + number)}


TX = hh("SYNTHETIC launch transaction")


def transfer(sender, recipient, amount, index):
    return {"address": TOKEN, "topics": [TRANSFER, "0x" + "0" * 24 + sender[2:],
                                         "0x" + "0" * 24 + recipient[2:]],
            "data": abi(amount), "transactionHash": TX, "blockHash": hh(100),
            "blockNumber": "0x64", "transactionIndex": "0x0", "logIndex": hex(index), "removed": False}


def receipt():
    return {"transactionHash": TX, "blockHash": hh(100), "blockNumber": "0x64", "status": "0x1",
            "from": CAROL, "to": TOKEN,
            "logs": [transfer(ZERO, ALICE, 2 * 10**23, 0), transfer(ZERO, BOB, 3 * 10**23, 1),
                     transfer(ALICE, CAROL, 10**23, 2)]}


def plan():
    return {"schema_version": 1, "target": {"chain_id": CHAIN, "address": TOKEN},
            "pins": [{"id": "launch", "number": 100}, {"id": "current", "number": 101}],
            "queries": [
                {"id": "launch-receipt", "pin_id": "launch", "method": "eth_getTransactionReceipt", "params": [TX]},
                {"id": "launch-supply", "pin_id": "launch", "method": "eth_call", "params": [{"to": TOKEN, "data": "0x18160ddd"}]},
                *[{"id": "code-" + pin, "pin_id": pin, "method": "eth_getCode", "params": [TOKEN]}
                  for pin in ("launch", "current")],
                *[{"id": "fee-" + pin, "pin_id": pin, "method": "eth_call", "params": [{"to": TOKEN, "data": calldata(ALICE)}]}
                  for pin in ("launch", "current")]]}


def case(root):
    return {"schema_version": 1, "collection_sha256": sha((root / "collection.json").read_bytes()),
            "launch": {"definition": "SYNTHETIC direct mint recipients in the declared launch receipt",
                       "receipt_evidence_ids": ["launch-receipt"], "source_addresses": [ZERO],
                       "excluded_recipients": {}, "supply_evidence_id": "launch-supply", "flag_at_bps": 2500},
            "fee_checks": [{"id": "alice-" + pin, "account": ALICE, "contract": TOKEN,
                            "selector": SELECTOR, "semantic_basis": "SYNTHETIC address-to-bool getter; test fixture only",
                            "call_evidence_id": "fee-" + pin, "code_evidence_id": "code-" + pin}
                           for pin in ("launch", "current")]}


class FakeRpc:
    synthetic = True
    namespace = "synthetic-regression-provider"

    def __init__(self):
        self.calls = []
        self.overrides = {}

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        method, params = request["method"], request["params"]
        if method in self.overrides:
            result = self.overrides[method](request)
            if isinstance(result, Exception):
                raise result
        elif method == "eth_chainId":
            result = hex(CHAIN)
        elif method == "eth_getBlockByNumber":
            result = header(int(params[0], 16))
        elif method == "eth_getTransactionReceipt":
            result = receipt()
        elif method == "eth_getTransactionByHash":
            result = {"hash": TX, "blockNumber": "0x64", "blockHash": hh(100), "from": CAROL, "to": TOKEN}
        elif method == "eth_call":
            result = abi(SUPPLY if params[0]["data"] == "0x18160ddd" else int(params[-1], 16) == 100)
        elif method == "eth_getCode":
            result = "0x60006000f3"
        elif method == "eth_getLogs":
            result = []
        elif method in ("trace_transaction", "debug_traceTransaction"):
            result = []
        elif method == "eth_getStorageAt":
            result = abi(0)
        elif method == "eth_getBalance":
            result = "0x0"
        else:
            raise AssertionError("unexpected synthetic RPC request")
        if isinstance(result, dict) and "error" in result:
            return {"jsonrpc": "2.0", "id": request["id"], **result}
        return {"jsonrpc": "2.0", "id": request["id"], "result": copy.deepcopy(result)}


if __name__ == "__main__":
    import argparse
    from backend_common import Cache
    from rpc_collect import Collector
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new synthetic demo directory")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cache = Cache(args.output / "cache.sqlite")
    try:
        root = args.output / "collection"
        Collector(root, cache, FakeRpc(), "synthetic-offline").collect(plan())
        write_new(args.output / "case.json", case(root))
    finally:
        cache.close()
    print("Created SYNTHETIC offline collection and detector case.")
