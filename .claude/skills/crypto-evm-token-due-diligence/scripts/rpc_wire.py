"""Shared JSON-RPC wire checks, before caching or treating a response as evidence.

These checks establish shape, not contract semantics or provider honesty. Error and
null responses are valid wire observations but are never reusable successful reads.
This module has no imports from collector/reporting modules and no side effects.
"""
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quantity(value):
    require(isinstance(value, str) and re.fullmatch(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)", value),
            "malformed RPC quantity")
    return int(value, 16)


def data(value, size=None):
    require(isinstance(value, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", value),
            "malformed RPC data")
    require(size is None or len(value) == 2 + size * 2, "malformed RPC data width")


def log_shape(logs):
    require(isinstance(logs, list), "malformed receipt logs")
    seen = set()
    for log in logs:
        require(isinstance(log, dict), "malformed log")
        data(log.get("address"), 20)
        data(log.get("blockHash"), 32)
        data(log.get("transactionHash"), 32)
        for key in ("blockNumber", "transactionIndex", "logIndex"):
            quantity(log.get(key))
        require(log.get("removed") is False, "removed/unconfirmed log")
        require(isinstance(log.get("topics"), list) and len(log["topics"]) <= 4, "malformed log topics")
        for topic in log["topics"]:
            data(topic, 32)
        data(log.get("data"))
        key = (log["blockHash"].lower(), quantity(log["logIndex"]))
        require(key not in seen, "duplicate log")
        seen.add(key)


def validate_response(request, response, legacy=False, redacted=False):
    require(isinstance(request, dict) and request.get("jsonrpc") == "2.0"
            and type(request.get("id")) in (str, int) and isinstance(request.get("params"), list),
            "malformed RPC request")
    require(isinstance(response, dict) and response.get("jsonrpc") == "2.0"
            and type(response.get("id")) is type(request["id"])
            and response.get("id") == request["id"], "RPC envelope/ID mismatch")
    require(("result" in response) != ("error" in response), "RPC result/error mismatch")
    if "error" in response:
        error = response["error"]
        require(isinstance(error, dict) and type(error.get("code")) is int
                and isinstance(error.get("message"), str), "malformed RPC error")
        return False
    result = response["result"]
    if result is None or redacted:
        return False
    method = request["method"]
    if method in ("eth_chainId", "eth_blockNumber", "eth_getBalance"):
        quantity(result)
    elif method in ("eth_getCode", "eth_call", "eth_getStorageAt"):
        data(result, 32 if method == "eth_getStorageAt" else None)
    elif method in ("eth_getBlockByNumber", "eth_getBlockByHash"):
        require(isinstance(result, dict), "malformed RPC header")
        for key in ("number", "timestamp"):
            quantity(result.get(key))
        for key in ("hash", "parentHash", "stateRoot"):
            data(result.get(key), 32)
    elif method in ("eth_getTransactionReceipt", "eth_getTransactionByHash"):
        require(isinstance(result, dict), "malformed RPC transaction")
        data(result.get("transactionHash" if method.endswith("Receipt") else "hash"), 32)
        data(result.get("blockHash"), 32)
        quantity(result.get("blockNumber"))
        if method.endswith("Receipt"):
            if not legacy or "status" in result:
                require(quantity(result.get("status")) in (0, 1), "malformed receipt status")
            if not legacy or "logs" in result:
                require(isinstance(result.get("logs"), list), "malformed receipt logs")
                if not legacy:
                    log_shape(result["logs"])
                    require(all(log["transactionHash"].lower() == result["transactionHash"].lower()
                                and log["blockHash"].lower() == result["blockHash"].lower()
                                and quantity(log["blockNumber"]) == quantity(result["blockNumber"])
                                for log in result["logs"]), "receipt log identity mismatch")
    elif method in ("eth_getLogs", "trace_transaction"):
        require(isinstance(result, (dict, list) if legacy and method == "trace_transaction" else list), "malformed RPC list")
        if method == "eth_getLogs" and not legacy:
            log_shape(result)
    elif method == "debug_traceTransaction":
        require(isinstance(result, (dict, list)), "malformed RPC trace")
    else:
        raise ValueError("unsupported RPC method")
    return True
