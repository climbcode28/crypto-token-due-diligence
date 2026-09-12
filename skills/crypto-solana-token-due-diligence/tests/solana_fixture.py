"""Deterministic synthetic RPC, with no socket or provider dependencies."""
import base64
import json
import threading
import time

from solana_common import b58encode, TOKEN_PROGRAM

KEY = b58encode(bytes([2])*32)
OTHER = b58encode(bytes([3])*32)
GENESIS = b58encode(bytes([4])*32)
SIG = b58encode(bytes([5])*64)
TARGET = {"family": "solana", "mint": KEY, "genesis_hash": GENESIS}


def account(raw=None):
    if raw is None:
        raw = bytes(36)+(2**60+17).to_bytes(8, "little")+bytes([9, 1])+bytes(36)
    return {"owner": TOKEN_PROGRAM, "executable": False, "lamports": 100,
            "space": len(raw), "data": [base64.b64encode(raw).decode(), "base64"]}


def request(method, params, name="r"):
    return {"jsonrpc": "2.0", "id": name, "method": method, "params": params}


def response(req, result):
    return {"jsonrpc": "2.0", "id": req["id"], "result": result}


class Rpc:
    lock = threading.Lock()
    calls = []
    active = peak = 0
    mode = "normal"
    delay = 0
    stamp = int(time.time())

    def __init__(self, url, headers, timeout, max_bytes):
        self.namespace, self.max_bytes = "synthetic", max_bytes
        self.local = threading.local()
        self.last_redacted = False

    def __call__(self, req):
        cls = type(self)
        with cls.lock:
            cls.calls.append(req)
            cls.active += 1
            cls.peak = max(cls.peak, cls.active)
            repeats = sum(c["method"] == req["method"] and c["params"] == req["params"] for c in cls.calls)
        try:
            time.sleep(cls.delay)
            method, params = req["method"], req["params"]
            if cls.mode == "timeout":
                raise TimeoutError("synthetic")
            if method == "getGenesisHash":
                result = OTHER if cls.mode == "wrong_network" else GENESIS
            elif method in ("getAccountInfo", "getMultipleAccounts"):
                value = account()
                if cls.mode == "changed_mint" and "critical" in req["id"]:
                    value["lamports"] += 1
                values = [value for _ in params[0]] if method == "getMultipleAccounts" else value
                if cls.mode == "short_batch" and method == "getMultipleAccounts":
                    values = values[:-1]
                slot = 103 if "critical" in req["id"] else 102 if "holdings" in req["id"] else 100
                result = {"context": {"slot": slot}, "value": values}
            elif method == "getTokenLargestAccounts":
                result = {"context": {"slot": 101}, "value": [{"address": OTHER, "amount": "17", "decimals": 9}]}
            elif method == "getEpochInfo":
                result = {"absoluteSlot": 100, "blockHeight": 80, "epoch": 1, "slotIndex": 10, "slotsInEpoch": 90}
            elif method == "getBlock":
                result = {"blockhash": OTHER if cls.mode == "changed_header" and repeats > 1 else KEY,
                          "previousBlockhash": OTHER, "parentSlot": params[0]-1, "blockTime": cls.stamp}
            elif method == "getTransaction":
                result = {"slot": 25, "blockTime": 123456, "version": 0, "meta": None,
                          "transaction": {"signatures": [params[0]], "message": {"accountKeys": [KEY]}}}
            else:
                raise AssertionError("fixture method not defined")
            value = response(req, result)
            if cls.mode == "wrong_id":
                value["id"] = "wrong"
            self.local.response_bytes = len(json.dumps(value).encode())
            return value
        finally:
            with cls.lock:
                cls.active -= 1
