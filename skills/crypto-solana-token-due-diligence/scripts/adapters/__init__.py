"""Pinned protocol decoders. Imported layouts never establish a deployment identity."""


def pool_adapter(name):
    """Explicit supported implementations only; indexer labels cannot enable adapters."""
    from solana_common import need
    from adapters import raydium_cpmm, raydium_amm_v4, raydium_clmm, orca_whirlpool, meteora_dlmm, meteora_damm_v2, pump_curve, pump_swap
    known = {m.CAPABILITY['id']: m for m in (raydium_cpmm, raydium_amm_v4, raydium_clmm, orca_whirlpool, meteora_dlmm, meteora_damm_v2, pump_curve, pump_swap)}
    need(name in known, 'unsupported pool adapter')
    return known[name]
