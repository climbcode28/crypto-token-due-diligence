"""Legacy AMM v4: preserve vaults, verify OpenBook dependencies, expose version ambiguity."""
from adapters.binary import raw_account, Reader
from adapters.base import Sample, capability, lp_custody
from solana_common import need, b58encode, TOKEN_PROGRAM
from solana_addresses import create_program_address

PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
OPENBOOK = "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX"
REVISION = "c613c87c41edbe21112c9b8341774a70009c6d7b"
CURRENT_REVISION = "d26944bfb76fb5fa8f91e5d440c2050ed358ef81"
CAPABILITY = capability("raydium_amm_v4", PROGRAM, REVISION, model="fungible_lp_openbook_or_vault",
    dependencies=["pool", "mints", "vaults", "lp_mint", "open_orders", "market", "event_queue", "program_control"])
CAPABILITY["source_variants"] = {"legacy_openbook": REVISION, "current_vault_only": CURRENT_REVISION}
CAPABILITY["unsupported_market_programs"] = "Serum and other OpenBook forks require separate pins"


def decode_pool(account):
    raw = raw_account(account, PROGRAM)
    need(not account["executable"] and len(raw) == 752, "AMM v4 pool layout mismatch")
    r = Reader(raw)
    settings = [r.integer(8) for _ in range(16)]
    fees = [r.integer(8) for _ in range(8)]
    pnl = [r.integer(8), r.integer(8)]
    r.take(128)
    keys = [r.key() for _ in range(9)]
    r.take(64); owner = r.key(); supply = r.integer(8)
    need(settings[0] in range(1, 8) and settings[1] <= 255 and max(settings[4:6]) <= 255, "invalid AMM v4 status/nonce/decimals")
    # Retain vault observations even when fee fields are invalid; arithmetic is gated later.
    valid_fees = all(0 <= fees[i] < fees[i+1] for i in range(0, 8, 2))
    need(keys[2] != keys[3], "AMM v4 identical pool mints")
    return {"status": settings[0], "bump": settings[1], "decimals": settings[4:6],
        "authority": create_program_address([b"amm authority", bytes([settings[1]])], PROGRAM),
        "vaults": keys[:2], "mints": keys[2:4], "lp_mint": keys[4], "open_orders": keys[5],
        "market": keys[6], "market_program": keys[7], "target_orders": keys[8], "amm_owner": owner,
        "lp_supply": supply, "pending_pnl": pnl, "fee_fractions": [list(map(str, fees[i:i+2])) for i in range(0, 8, 2)],
        "fees_valid": valid_fees, "legacy_orderbook_enabled": settings[0] in (1, 5)}


def _book(account, length=None):
    raw = raw_account(account, OPENBOOK)
    need(not account["executable"] and raw[:5] == b"serum" and raw[-7:] == b"padding", "OpenBook padding/owner mismatch")
    need(length is None or len(raw) == length, "unsupported OpenBook layout length")
    return raw[5:-7]


def decode_market(address, account, mints):
    r = Reader(_book(account, 388))
    need(r.integer(8) in (3, 131) and r.key() == address, "OpenBook market identity/flags mismatch")
    r.integer(8)
    need([r.key(), r.key()] == mints, "OpenBook market mints mismatch")
    # MarketState event_q is the key at body offset 248.
    return {"event_queue": b58encode(r.raw[248:280])}


def decode_orders(account, market, authority):
    r = Reader(_book(account, 3228))
    need(r.integer(8) == 5 and r.key() == market and r.key() == authority, "OpenOrders relationship/flags mismatch")
    coin_free, coin, pc_free, pc = [r.integer(8) for _ in range(4)]
    need(coin_free <= coin and pc_free <= pc, "OpenOrders free balance exceeds total")
    return [coin, pc]


def adjusted_orders(account, address, balances):
    raw = _book(account)
    r = Reader(raw)
    flags, head, count, sequence = [r.integer(8) for _ in range(4)]
    capacity = (len(raw)-32)//88
    need(flags == 17 and capacity > 0 and 0 <= head < capacity and count <= min(capacity, 4096), "invalid or oversized event queue")
    values = list(balances)
    applied = 0
    for i in range(count):
        event = raw[32+((head+i) % capacity)*88:32+((head+i) % capacity+1)*88]
        flags = event[0]
        need(flags in (1, 5, 9, 13, 2, 6, 18, 22), "unsupported OpenBook event flags")
        need(event[1] < 128, "invalid event owner slot")
        need(not flags & 1 or event[2] <= 7, "unsupported OpenBook event fee tier")
        if b58encode(event[48:80]) != address or not (flags & 1 and flags & 8):
            continue
        received, paid = int.from_bytes(event[8:16], "little"), int.from_bytes(event[16:24], "little")
        incoming, outgoing = (0, 1) if flags & 4 else (1, 0)
        values[incoming] += received
        values[outgoing] -= paid
        need(all(0 <= v < 2**64 for v in values), "event-adjusted OpenOrders overflow/underflow")
        applied += 1
    return values, {"count": count, "capacity": capacity, "sequence": str(sequence), "applied_maker_fills": applied}


def analyze(target, pool, observations, *, lp_accounts=None):
    sample = Sample(target, pool, observations, CAPABILITY)
    state = decode_pool(sample.account(pool))
    need(target["mint"] in state["mints"], "target mint not in AMM v4 pool")
    sample.result.update(state=state, mints=state["mints"])
    sample.controls(PROGRAM)
    for i in range(2):
        try:
            sample.vault(state["vaults"][i], state["mints"][i], TOKEN_PROGRAM, state["authority"])
        except ValueError as exc:
            sample.result["gaps"].append(str(exc))
    try:
        need(len(sample.result["vaults"]) == 2, "both verified vaults required")
        need(state["fees_valid"], "invalid AMM v4 fee configuration")
        for i in range(2):
            sample.mint(state["mints"][i], TOKEN_PROGRAM, state["decimals"][i])
        required = [pool, *state["mints"], *state["vaults"]]
        gross = [int(v["amount_atomic"]) for v in sample.result["vaults"]]
        vault_only = [v-p for v, p in zip(gross, state["pending_pnl"])]
        vault_valid = all(0 <= v < 2**64 for v in vault_only)
        variants = {"current_vault_only": list(map(str, vault_only)) if vault_valid else None}
        if state["legacy_orderbook_enabled"]:
            need(state["market_program"] == OPENBOOK, "unsupported legacy market program")
            market = decode_market(state["market"], sample.account(state["market"]), state["mints"])
            balances = decode_orders(sample.account(state["open_orders"]), state["market"], state["authority"])
            adjusted, queue = adjusted_orders(sample.account(market["event_queue"]), state["open_orders"], balances)
            sample.result.update(open_orders_base_atomic=list(map(str, balances)),
                open_orders_adjusted_atomic=list(map(str, adjusted)), event_queue=queue)
            required += [state["market"], state["open_orders"], market["event_queue"]]
            legacy = [v+o for v, o in zip(vault_only, adjusted)]
            need(all(0 <= v < 2**64 for v in legacy), "AMM v4 reserve overflow/underflow")
            variants["legacy_openbook"] = list(map(str, legacy))
        else:
            need(vault_valid, "pending PnL exceeds vault balance")
            variants["legacy_orderbook_disabled"] = list(map(str, vault_only))
        sample.same_bank(required)
        sample.result["reserve_variants_atomic"] = variants
        if vault_valid and all(v is not None for v in variants.values()) and len({tuple(v) for v in variants.values()}) == 1:
            sample.result["reserves_atomic"] = list(map(str, vault_only))
        else:
            sample.result["gaps"].append("deployed_reserve_variant_unresolved; current source removed OpenBook")
        sample.result["reserve_formula"] = "vault + version-dependent event-adjusted OpenOrders - pending PnL"
        sample.result["lp_custody"] = lp_custody(sample, state["lp_mint"], state["authority"], state["lp_supply"],
            lp_accounts or [], pool_dependencies=required)
    except ValueError as exc:
        sample.result["gaps"].append(str(exc))
    return sample.finish()
