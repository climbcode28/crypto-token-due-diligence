"""Pump fee tables and program-derived roles; no inferred beneficiary identity."""
from adapters.binary import Reader,raw_account,discriminator
from solana_common import need,base58_bytes
from solana_addresses import find_program_address,create_program_address

REVISION='e0687ae9b7e064a0f54efc7297c65eecfbba3a8f'
CURVE_PROGRAM='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
SWAP_PROGRAM='pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'
FEE_PROGRAM='pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ'
WSOL='So11111111111111111111111111111111111111112'
ZERO='11111111111111111111111111111111'


def pda(program,*seeds):return find_program_address(list(seeds),program)[0]
def curve_address(mint):return pda(CURVE_PROGRAM,b'bonding-curve',base58_bytes(mint,32))
def pool_authority(mint):return pda(CURVE_PROGRAM,b'pool-authority',base58_bytes(mint,32))
def pool_address(mint,quote,*,creator=None,index=0):
    need(type(index) is int and 0<=index<2**16,'invalid Pump pool index')
    return pda(SWAP_PROGRAM,b'pool',index.to_bytes(2,'little'),base58_bytes(creator or pool_authority(mint),32),base58_bytes(mint,32),base58_bytes(quote,32))
def fee_address(program):return pda(FEE_PROGRAM,b'fee_config',base58_bytes(program,32))


def decode_fees(address,account,program):
    raw=raw_account(account,FEE_PROGRAM)
    # extend_fee_config grows the allocation (4,097 bytes live on 2026-09-12); the tables inside stay bounded below.
    need(not account['executable'] and 73<=len(raw)<=16384 and raw[:8]==discriminator('FeeConfig'),'Pump fee configuration layout mismatch')
    r=Reader(raw);r.take(8);bump=r.integer(1);admin=r.key()
    need(create_program_address([b'fee_config',base58_bytes(program,32),bytes([bump])],FEE_PROGRAM)==address,'Pump fee config PDA mismatch')
    def fees(r):
        values=[r.integer(8) for _ in range(3)]
        need(sum(values)<10000,'invalid Pump fee rates')
        return dict(zip(('lp_fee_bps','protocol_fee_bps','creator_fee_bps'),map(str,values)))
    flat=fees(r)
    def tier(r):return {'market_cap_quote_atomic_threshold':str(r.integer(16)),'fees':fees(r)}
    tiers=r.vector(tier,maximum=128);stable=r.vector(tier,maximum=128)  # 25 tiers each observed live on 2026-09-12
    exotic_zero=None
    if len(raw)-r.offset>=24:exotic_zero=not any(raw[r.offset:r.offset+24]);exotic=fees(r)  # exotic_flat_fees, appended by the 2026-09 fee-program upgrade
    else:exotic=None
    need(not any(r.take(len(raw)-r.offset)),'unknown fee configuration extension')
    for rows in (tiers,stable):
        thresholds=[int(v['market_cap_quote_atomic_threshold']) for v in rows]
        need(thresholds==sorted(set(thresholds)),'fee tiers duplicate or unsorted')
    return {'admin':admin,'flat_fees':flat,'fee_tiers':tiers,'stable_fee_tiers':stable,'exotic_flat_fees':exotic,'exotic_flat_fees_zero':exotic_zero,'evidence_scope':'stored tables; routing and deployment correspondence separate'}


def selected_fees(config,*,canonical,quote,mint_supply,base_reserve,quote_reserve,mode_restricted=False):
    need(base_reserve>0 and quote_reserve>=0,'fee market-cap denominator/reserve invalid')
    cap=quote_reserve*mint_supply//base_reserve
    # New stable/boost/mayhem/cashback/buyback behavior needs its specific runtime
    # rules. Do not silently apply the older native-SOL fee-selection document.
    need(quote==WSOL and not mode_restricted,'current special/non-native fee selection unresolved; stored tables retained')
    if not canonical:return {'fees':config['flat_fees'],'selection':'noncanonical_flat','market_cap_quote_atomic':str(cap)}
    tiers=config['fee_tiers'];need(tiers,'native dynamic fee tiers missing')
    selected=tiers[0]
    for tier in tiers:
        if cap>=int(tier['market_cap_quote_atomic_threshold']):selected=tier
    return {'fees':selected['fees'],'selection':'canonical_native_tier','market_cap_quote_atomic':str(cap),
            'threshold_quote_atomic':selected['market_cap_quote_atomic_threshold'],'scope':'stored nominal rates; actual transaction fees require effects'}
