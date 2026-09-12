"""Pinned swap instruction roles, independently scoped from pool-state estimates."""
import hashlib
from solana_common import need, TOKEN_PROGRAM, TOKEN_2022
from adapters import raydium_cpmm as cp, raydium_amm_v4 as amm, raydium_clmm as clmm
from adapters import orca_whirlpool as orca, meteora_dlmm as dlmm, meteora_damm_v2 as damm
from adapters import pump_swap as pump


def tag(name): return hashlib.sha256(('global:'+name).encode()).digest()[:8]


def position_instruction(program,raw,a):
    """Successful position operations; requested liquidity is not token proceeds."""
    effect={'mint':None,'amount_atomic':None,'participants':{},'quantity_scope':'position operation only; actual token amounts require exact token effects'}
    if program==dlmm.PROGRAM and raw[:8]==tag('initialize_position2'):
        need(len(raw)==16 and len(a)==7,'unsupported DLMM position initialization')
        effect.update(kind='position_initialize',pool=a[2],participants={'position':a[1],'owner':a[3]},
            requested_lower_bin=int.from_bytes(raw[8:12],'little',signed=True),requested_width=int.from_bytes(raw[12:16],'little',signed=True))
    elif program==damm.PROGRAM and raw[:8]==tag('create_position'):
        need(len(raw)==8 and len(a)==11,'unsupported DAMM position initialization')
        effect.update(kind='position_initialize',pool=a[3],mint=a[1],participants={'position':a[4],'owner':a[0],'holding':a[2]})
    elif program==orca.PROGRAM and raw[:8]==tag('open_position'):
        need(len(raw)==17 and len(a)==10,'unsupported Whirlpool position initialization')
        effect.update(kind='position_initialize',pool=a[5],mint=a[3],participants={'position':a[2],'owner':a[1],'holding':a[4]},
            requested_lower_tick=int.from_bytes(raw[9:13],'little',signed=True),requested_upper_tick=int.from_bytes(raw[13:17],'little',signed=True))
    elif program==damm.PROGRAM and raw[:8]==tag('remove_liquidity'):
        need(len(raw)==40 and len(a)==15,'unsupported DAMM liquidity removal')
        effect.update(kind='position_liquidity_remove',pool=a[1],participants={'position':a[2],'signer':a[10]},
                      liquidity_units=str(int.from_bytes(raw[8:24],'little')),mints=a[7:9])
    elif program==cp.PROGRAM and raw[:8]==tag('withdraw'):
        need(len(raw)==32 and len(a)==14,'unsupported CPMM withdrawal')
        effect.update(kind='position_liquidity_remove',pool=a[2],mint=a[12],participants={'holding':a[3],'signer':a[0]},
                      lp_units=str(int.from_bytes(raw[8:16],'little')),mints=a[10:12])
    else:return None
    return effect


def decode(program,raw,accounts):
    """Return account roles only for the exact known discriminator/argument shape."""
    a=accounts
    family={m.PROGRAM:m.CAPABILITY['id'] for m in (cp,amm,clmm,orca,dlmm,damm,pump)}
    if program not in family:return None
    p=source=dest=trader=None;vaults=[];mints=[];amount=threshold=None;mode=None;fee_accounts=[]
    if program == cp.PROGRAM and raw[:8] in (tag('swap_base_input'),tag('swap_base_output')):
        need(len(raw)==24 and len(a)==13, 'unsupported CPMM swap arguments/accounts')
        p,source,dest,trader=a[3],a[4],a[5],a[0];vaults=a[6:8];mints=a[10:12]
        need(all(t in (TOKEN_PROGRAM,TOKEN_2022) for t in a[8:10]), 'invalid swap token programs')
        mode='exact_in' if raw[:8]==tag('swap_base_input') else 'exact_out_max_first'
    elif program == clmm.PROGRAM and raw[:8] == tag('swap_v2'):
        need(len(raw)==41 and len(a)>=14 and raw[40] in (0,1), 'unsupported CLMM swap arguments/accounts')
        p,source,dest,trader=a[2],a[3],a[4],a[0];vaults=a[5:7];mints=a[11:13]
        mode='exact_in' if raw[40] else 'exact_out'
    elif program == orca.PROGRAM and raw[:8] == tag('swap'):
        # Legacy Whirlpool swap (still the dominant mainnet instruction): amount u64, threshold u64,
        # sqrt_price_limit u128, amount_specified_is_input, a_to_b; no mint accounts, so the
        # verifier binds mints through the transaction's token balances.
        need(len(raw)==42 and len(a)==11 and raw[40] in (0,1) and raw[41] in (0,1), 'unsupported Whirlpool legacy swap layout')
        need(a[0]==TOKEN_PROGRAM, 'legacy Whirlpool swap requires the SPL token program')
        p,trader=a[2],a[1]
        source,dest=(a[3],a[5]) if raw[41] else (a[5],a[3])
        vaults=[a[4],a[6]] if raw[41] else [a[6],a[4]]
        mode='exact_in' if raw[40] else 'exact_out'
    elif program == orca.PROGRAM and raw[:8] == tag('swap_v2'):
        # None remaining-accounts-info only; hook/supplemental-array variants are gaps.
        need(len(raw)==43 and len(a)==15 and raw[40] in (0,1) and raw[41] in (0,1) and raw[42]==0, 'unsupported Whirlpool swap variant')
        p,trader=a[4],a[3]
        source,dest=(a[7],a[9]) if raw[41] else (a[9],a[7])
        vaults,mints=([a[8],a[10]],[a[5],a[6]]) if raw[41] else ([a[10],a[8]],[a[6],a[5]])
        mode='exact_in' if raw[40] else 'exact_out'
    elif program == dlmm.PROGRAM and raw[:8] in (tag('swap'),tag('swap2')):
        # swap2 includes a Borsh vector of remaining-account slices: empty only.
        v2=raw[:8]==tag('swap2')
        need((len(raw)==28 and raw[24:]==bytes(4)) if v2 else len(raw)==24, 'unsupported DLMM swap remaining accounts')
        need(len(a)>=(16 if v2 else 15), 'incomplete DLMM swap accounts')
        p,source,dest,trader=a[0],a[4],a[5],a[10];vaults=a[2:4];mints=a[6:8];mode='exact_in'
        fee_accounts=[a[9]] if a[9]!=dlmm.PROGRAM else []  # optional host_fee_in; the program id stands in when absent
    elif program == damm.PROGRAM and raw[:8] in (tag('swap'),tag('swap2')):
        v2=raw[:8]==tag('swap2')
        need(len(raw)==(25 if v2 else 24) and len(a)==14, 'unsupported DAMM v2 swap accounts/arguments')
        need(not v2 or raw[24] in (0,1,2), 'unknown DAMM swap mode')
        p,source,dest,trader=a[1],a[2],a[3],a[8];vaults=a[4:6];mints=a[6:8]
        mode=('exact_in','partial_fill','exact_out')[raw[24]] if v2 else 'exact_in'
        fee_accounts=[a[11]] if a[11]!=damm.PROGRAM else []  # optional referral_token_account
    elif program==pump.PROGRAM and raw[:8] in (tag('sell'),tag('buy'),tag('buy_exact_quote_in')):
        sell=raw[:8]==tag('sell');exact_quote=raw[:8]==tag('buy_exact_quote_in')
        need(len(a)==(21 if sell else 23) and len(raw)==(24 if sell else 25),'unsupported PumpSwap trade layout')
        if not sell:need(raw[24] in (0,1),'invalid PumpSwap track-volume flag')
        need(all(p in (TOKEN_PROGRAM,TOKEN_2022) for p in a[11:13]),'invalid PumpSwap token programs')
        p,trader=a[0],a[1];source,dest=(a[5],a[6]) if sell else (a[6],a[5]);vaults=a[7:9];mints=a[3:5]
        mode='exact_in' if sell or exact_quote else 'exact_out'
        fee_accounts=[a[10],a[17]]  # protocol_fee_recipient_token_account and coin_creator_vault_ata
    elif program == amm.PROGRAM and raw and raw[0] in (9,11,16,17):
        need(len(raw)==17 and a and a[0]==TOKEN_PROGRAM, 'invalid AMM v4 swap')
        if raw[0] in (16,17):
            need(len(a)==8, 'AMM v4 V2 account count mismatch')
            p,source,dest,trader=a[1],a[5],a[6],a[7];vaults=a[3:5]
        else:
            need(len(a) in (17,18),'AMM v4 legacy account count mismatch')
            p,source,dest,trader=a[1],a[-3],a[-2],a[-1]
            offset=5 if len(a)==18 else 4;vaults=a[offset:offset+2]
        amount=int.from_bytes(raw[1:9],'little');threshold=int.from_bytes(raw[9:17],'little')
        mode='exact_in' if raw[0] in (9,16) else 'exact_out_max_first'
    else:return None
    if amount is None:amount=int.from_bytes(raw[8:16],'little');threshold=int.from_bytes(raw[16:24],'little')
    need(source!=dest and len(set(vaults))==2 and source not in vaults and dest not in vaults,'swap role overlap')
    if mints:need(len(set(mints))==2,'swap mints overlap')
    need(not set(fee_accounts)&{source,dest,*vaults},'fee sink overlaps swap roles')
    return {'adapter':family[program], 'pool':p,'input_account':source,'output_account':dest,'trader':trader,
        'vaults':vaults,'mints':mints,'mode':mode,'specified_amount_atomic':str(amount),'threshold_atomic':str(threshold),'fee_accounts':fee_accounts,
        'role_scope':'pinned successful instruction roles; token flows and seller ownership require separate verification'}
