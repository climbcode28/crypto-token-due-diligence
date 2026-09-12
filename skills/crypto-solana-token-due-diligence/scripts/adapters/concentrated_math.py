"""Integer Q64 tick tables and principal deltas from pinned protocol definitions.

Tables are protocol constants, not interchangeable approximations. See layout-sources.
Raydium ed7c84a54ced59c55981780546adb0b4583dcf85 and Orca
e528dd23bb41571f92cfdb49a2f15d4fa0b01bec (Apache-2.0).
Orca numeric tables match current 408c945fef4c49ab70def4303377cfaf8f0f3c99.
"""
from solana_common import need
Q64 = 1 << 64
MIN_TICK, MAX_TICK = -443636, 443636
RAY_FACTORS = (18445821805675395072, 18444899583751176192, 18443055278223355904, 18439367220385607680, 18431993317065453568, 18417254355718170624, 18387811781193609216, 18329067761203558400, 18212142134806163456, 17980523815641700352, 17526086738831433728, 16651378430235570176, 15030750278694412288, 12247334978884435968, 8131365268886854656, 3584323654725218816, 696457651848324352, 26294789957507116, 37481735321082)
ORCA_POSITIVE = (79232123823359799118286999567, 79236085330515764027303304731, 79244008939048815603706035061, 79259858533276714757314932305, 79291567232598584799939703904, 79355022692464371645785046466, 79482085999252804386437311141, 79736823300114093921829183326, 80248749790819932309965073892, 81282483887344747381513967011, 83390072131320151908154831281, 87770609709833776024991924138, 97234110755111693312479820773, 119332217159966728226237229890, 179736315981702064433883588727, 407748233172238350107850275304, 2098478828474011932436660412517, 55581415166113811149459800483533, 38992368544603139932233054999993551)
ORCA_NEGATIVE = (18445821805675392311, 18444899583751176498, 18443055278223354162, 18439367220385604838, 18431993317065449817, 18417254355718160513, 18387811781193591352, 18329067761203520168, 18212142134806087854, 17980523815641551639, 17526086738831147013, 16651378430235024244, 15030750278693429944, 12247334978882834399, 8131365268884726200, 3584323654723342297, 696457651847595233, 26294789957452057, 37481735321082)


def sqrt_at_tick(tick, protocol):
    need(type(tick) is int and MIN_TICK <= tick <= MAX_TICK, "tick outside protocol bounds")
    need(protocol in ("raydium", "orca"), "unknown tick math")
    if protocol == "raydium":
        value = Q64
        for i, factor in enumerate(RAY_FACTORS):
            if abs(tick) & (1 << i): value = (value*factor) >> 64
        return ((1 << 128)-1)//value if tick > 0 else value
    bits = 96 if tick >= 0 else 64
    value = 1 << bits
    for i, factor in enumerate(ORCA_POSITIVE if tick >= 0 else ORCA_NEGATIVE):
        if abs(tick) & (1 << i): value = (value*factor) >> bits
    return value >> 32 if tick >= 0 else value


def price_tick_consistent(price, tick, protocol):
    need(type(price) is int and sqrt_at_tick(MIN_TICK, protocol) <= price <= sqrt_at_tick(MAX_TICK, protocol), "sqrt price outside protocol bounds")
    need(protocol != "raydium" or price < sqrt_at_tick(MAX_TICK, protocol), "Raydium maximum sqrt price is exclusive")
    # At a downward tick crossing the current tick can be one below the exact
    # boundary sqrt price. Equal upper price is valid and is not rounded away.
    need(sqrt_at_tick(tick, protocol) <= price <= sqrt_at_tick(min(MAX_TICK, tick+1), protocol), "pool price/current tick inconsistent")


def principal(liquidity, price, lower, upper, protocol):
    need(type(liquidity) is int and 0 <= liquidity < 1 << 128, "invalid position liquidity")
    need(type(lower) is int and type(upper) is int and MIN_TICK <= lower < upper <= MAX_TICK, "invalid position tick range")
    a, b = sqrt_at_tick(lower, protocol), sqrt_at_tick(upper, protocol)
    need(type(price) is int and price > 0, "valid integer sqrt price required")
    current = min(b, max(a, price))
    values = [liquidity*(b-current)*Q64//(current*b), liquidity*(current-a)//Q64]
    need(all(v < 1 << 64 for v in values), "position principal exceeds token amount range")
    return {"amounts_atomic": list(map(str, values)), "rounding": "floor_per_token",
            "sqrt_lower_x64": str(a), "sqrt_upper_x64": str(b),
            "scope": "gross principal at observed price; excludes fees, rewards, transfer fees and execution"}
