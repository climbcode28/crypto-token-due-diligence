"""Conservative sale observations from already captured pool identities and receipts."""
import re
from collections import Counter

from facts import decimal_string, signed, transfers
from keccak import topic

V2_SWAP = topic("Swap(address,uint256,uint256,uint256,uint256,address)")
V3_SWAP = topic("Swap(address,address,int256,int256,uint160,uint128,int24)")
V4_SWAP = topic("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)")
ADDRESS = re.compile(r"0x[0-9a-f]{40}")
POOL_ID = re.compile(r"0x[0-9a-f]{64}")


def _swap_amounts(log, target_index):
    """Return target input and other-currency output, rejecting two-sided/zero flows."""
    topics = log.get("topics") or []
    data = log.get("data")
    signature = str(topics[0]).lower() if topics else ""
    words = {V2_SWAP: 4, V3_SWAP: 5, V4_SWAP: 6}.get(signature)
    if len(topics) != 3 or words is None or not isinstance(data, str) or not re.fullmatch(r"0x[0-9a-fA-F]{" + str(words * 64) + r"}", data):
        return None
    values = [int(data[2 + 64 * i:2 + 64 * (i + 1)], 16) for i in range(words)]
    other = 1 - target_index
    if signature == V2_SWAP:
        amount_in, amount_out = values[target_index], values[2 + other]
        if values[other] or values[2 + target_index]:
            return None
    else:
        deltas = [signed(values[0]), signed(values[1])]
        if signature == V4_SWAP:
            if any(not -(2 ** 127) <= value < 2 ** 127 for value in deltas):
                return None
            # PoolManager emits caller deltas: input is negative, output positive.
            amount_in, amount_out = -deltas[target_index], deltas[other]
        else:
            # V3 emits pool deltas: input is positive, output negative.
            amount_in, amount_out = deltas[target_index], -deltas[other]
    return (amount_in, amount_out) if amount_in > 0 and amount_out > 0 else None


def decode_sale(target, receipt, item, pool_addresses, decimals, pool_details=None):
    """Identify a unique input transfer matching a same-pool Swap's target delta.

    This establishes an observed execution for the transfer source only; it does not
    establish general sellability, beneficial ownership or a fee-free transfer path.
    V4's currency association is explicitly bounded to the captured indexer pool key.
    """
    if item["status"] != 1:
        return {"verified": False, "reason": "receipt status is not success"}
    target = target.lower()
    pools = {p.lower() for p in pool_addresses}
    decoded = transfers(receipt)
    moves = [t for t in decoded if t["asset"] == target and t["to"] in pools and t["from"] not in pools
             and int(t["from"], 16) != 0 and t["amount_raw"] > 0]
    matches = []
    swap_count = 0
    for log in receipt.get("logs", []):
        emitter = str(log.get("address", "")).lower()
        topics = log.get("topics") or []
        signature = str(topics[0]).lower() if topics else ""
        if emitter not in pools or signature not in (V2_SWAP, V3_SWAP, V4_SWAP):
            continue
        swap_count += 1
        identities = []
        for detail in pool_details or []:
            pair = str(detail.get("pair", "")).lower()
            if signature == V4_SWAP:
                if not POOL_ID.fullmatch(pair) or len(topics) < 2 or str(topics[1]).lower() != pair:
                    continue
                counter = str(detail.get("counter_asset", "")).lower()
                if not ADDRESS.fullmatch(counter) or counter == target:
                    continue
                currencies = sorted((target, counter))
                basis = "indexer-linked v4 pool ID and currency addresses"
            else:
                if pair != emitter:
                    continue
                currencies = [str(detail.get(k, "")).lower() for k in ("token0", "token1")]
                if not all(ADDRESS.fullmatch(a) for a in currencies) or len(set(currencies)) != 2 or target not in currencies:
                    continue
                basis = "pinned pool token0/token1 reads"
            identities.append((pair, currencies.index(target), currencies[1 - currencies.index(target)], basis))
        identities = list(dict.fromkeys(identities))
        if len(identities) != 1:
            continue
        pair, target_index, output_asset, basis = identities[0]
        amounts = _swap_amounts(log, target_index)
        if amounts is None:
            continue
        amount_in, amount_out = amounts
        candidates = [t for t in moves if t["to"] == emitter and t["amount_raw"] == amount_in]
        if len(candidates) != 1:
            continue
        matches.append((candidates[0], log, pair, output_asset, amount_out, basis))
    # Repeated matching events cannot establish which execution a transfer funded.
    transfer_matches = Counter(m[0]["log_index"] for m in matches)
    unique = [m for m in matches if transfer_matches[m[0]["log_index"]] == 1]
    if not unique:
        return {"verified": False, "reason": "no unambiguous target transfer matched a same-pool Swap input and pool identity",
                "swap_logs": swap_count, "pool_inflows": len(moves)}
    move, log, pair, output_asset, amount_out, basis = max(unique, key=lambda m: m[0]["amount_raw"])
    seller = move["from"]
    received = [t for t in decoded if t["asset"] == output_asset and t["from"] == move["to"] and t["to"] == seller and t["amount_raw"] == amount_out]
    result = {"verified": True, "seller": seller, "pool": move["to"], "amount_raw": move["amount_raw"],
              "amount": decimal_string(move["amount_raw"], decimals),
              "received": [{"asset": t["asset"], "amount_raw": t["amount_raw"]} for t in received[:1]],
              "swap_logs": 1, "seller_is_sender": seller == str(item.get("from") or "").lower(),
              "pool_identity_basis": basis}
    if len(pair) == 66:
        result["pool_id"] = pair
    return result
