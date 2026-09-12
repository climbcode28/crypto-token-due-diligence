"""Raydium CPMM 637-byte PoolState and 236-byte fee configuration."""
from adapters.binary import raw_account, discriminator, Reader
from adapters.base import Sample, capability, lp_custody
from solana_common import need, base58_bytes, TOKEN_PROGRAM, TOKEN_2022
from solana_addresses import create_program_address, find_program_address

PROGRAM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
REVISION = "59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92"
CAPABILITY = capability("raydium_cpmm", PROGRAM, REVISION, model="fungible_lp_constant_product",
    dependencies=["pool", "mints", "vaults", "fee_config", "lp_mint", "program_control"])
CAPABILITY.update(version='1.1.0',quote=True, quote_scope='offline exact-input SPL estimate with captured Clock; executable quote not promised',
                  historical_execution='bounded pinned swap roles and matched SPL token effects')


def quote(target,pool,observations,input_atomic,*,slippage_bps=50):
    from solana_quotes import estimate
    return estimate(target,'raydium_cpmm',pool,observations,input_atomic,slippage_bps=slippage_bps)


def decode_pool(account):
    raw = raw_account(account, PROGRAM)
    need(not account["executable"] and len(raw) == 637 and raw[:8] == discriminator("PoolState"), "CPMM pool layout mismatch")
    r = Reader(raw); r.take(8)
    keys = [r.key() for _ in range(10)]
    bump, status, lp_decimals, d0, d1 = [r.integer(1) for _ in range(5)]
    supply, p0, p1, f0, f1, opened, epoch = [r.integer(8) for _ in range(7)]
    mode, enabled = r.integer(1), r.integer(1); r.take(6)
    c0, c1 = r.integer(8), r.integer(8)
    known_tail = not any(r.take(224)) and not any(raw[391:397])
    need(status < 8 and mode < 3 and enabled in (0, 1) and lp_decimals == 9, "unknown CPMM control layout")
    need(base58_bytes(keys[5], 32) < base58_bytes(keys[6], 32), "CPMM mint order mismatch")
    need(all(k in (TOKEN_PROGRAM, TOKEN_2022) for k in keys[7:9]), "unsupported CPMM token program")
    return {"config": keys[0], "creator": keys[1], "vaults": keys[2:4], "lp_mint": keys[4],
        "mints": keys[5:7], "token_programs": keys[7:9], "observation": keys[9], "bump": bump,
        "authority": create_program_address([b"vault_and_lp_mint_auth_seed", bytes([bump])], PROGRAM),
        "status_bits": status, "lp_decimals": lp_decimals, "decimals": [d0, d1], "lp_supply": supply,
        "protocol_fees": [p0, p1], "fund_fees": [f0, f1], "creator_fees": [c0, c1],
        "creator_fee_on": mode, "creator_fee_enabled": bool(enabled), "open_time": opened, "recent_epoch": epoch,
        "known_reserved_layout": known_tail}


def decode_config(address, account):
    raw = raw_account(account, PROGRAM)
    need(not account["executable"] and len(raw) == 236 and raw[:8] == discriminator("AmmConfig"), "CPMM config layout mismatch")
    r = Reader(raw); r.take(8)
    bump, disabled, index = r.integer(1), r.integer(1), r.integer(2)
    trade, protocol, fund, creation = [r.integer(8) for _ in range(4)]
    protocol_owner, fund_owner, creator = r.key(), r.key(), r.integer(8)
    need(not any(r.take(120)), "CPMM configuration has an unsupported reserved layout extension")
    need(disabled in (0, 1) and trade < 1_000_000 and creator < 1_000_000 and protocol+fund <= 1_000_000, "invalid CPMM fee rates")
    need(create_program_address([b"amm_config", index.to_bytes(2, "big"), bytes([bump])], PROGRAM) == address, "CPMM config PDA mismatch")
    return {"trade_rate": str(trade), "protocol_share": str(protocol), "fund_share": str(fund),
        "creator_rate": str(creator), "denominator": "1000000", "create_pool_fee_lamports": str(creation),
        "protocol_owner": protocol_owner, "fund_owner": fund_owner, "disable_create_pool": bool(disabled)}


def analyze(target, pool, observations, *, lp_accounts=None):
    sample = Sample(target, pool, observations, CAPABILITY)
    state = decode_pool(sample.account(pool))
    need(target["mint"] in state["mints"], "target mint not in CPMM pool")
    for i in range(2):
        expected = find_program_address([b"pool_vault", base58_bytes(pool, 32), base58_bytes(state["mints"][i], 32)], PROGRAM)[0]
        need(state["vaults"][i] == expected, "CPMM vault PDA mismatch")
    need(state["lp_mint"] == find_program_address([b"pool_lp_mint", base58_bytes(pool, 32)], PROGRAM)[0], "CPMM LP mint PDA mismatch")
    sample.result.update(state=state, mints=state["mints"])
    sample.controls(PROGRAM)
    for i in range(2):
        try:
            sample.vault(state["vaults"][i], state["mints"][i], state["token_programs"][i], state["authority"])
        except ValueError as exc:
            sample.result["gaps"].append(str(exc))
    try:
        need(len(sample.result["vaults"]) == 2, "both verified vaults required")
        need(state["known_reserved_layout"], "CPMM reserved bytes contain an unsupported layout extension")
        config = decode_config(state["config"], sample.account(state["config"]))
        sample.result["fee_config"] = config
        for i in range(2):
            sample.mint(state["mints"][i], state["token_programs"][i], state["decimals"][i])
        required = [pool, state["config"], *state["mints"], *state["vaults"]]
        sample.same_bank(required)
        gross = [int(v["amount_atomic"]) for v in sample.result["vaults"]]
        fees = [sum(state[k][i] for k in ("protocol_fees", "fund_fees", "creator_fees")) for i in range(2)]
        need(all(f <= g for f, g in zip(fees, gross)), "CPMM fees exceed observed vault")
        sample.result.update(reserves_atomic=[str(g-f) for g, f in zip(gross, fees)],
            reserved_fees_atomic=list(map(str, fees)), reserve_formula="vault_base_amount - protocol - fund - creator fees",
            quote_dependencies="transfer extensions, fee epoch, route and execution remain separate")
        sample.result["lp_custody"] = lp_custody(sample, state["lp_mint"], state["authority"], state["lp_supply"],
            lp_accounts or [], pool_dependencies=required, decimals=state["lp_decimals"])
    except ValueError as exc:
        sample.result["gaps"].append(str(exc))
    return sample.finish()
