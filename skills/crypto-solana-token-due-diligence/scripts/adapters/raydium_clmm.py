"""Pinned Raydium CLMM pool/personal-position/tick-array account observations."""
import sys
from adapters.base import capability
from adapters.binary import Reader, discriminator, raw_account
from adapters import concentrated
from adapters.concentrated_math import price_tick_consistent, MIN_TICK, MAX_TICK
from solana_common import need, base58_bytes, b58encode, sha
from solana_addresses import find_program_address, create_program_address

PROGRAM = 'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK'
REVISION = 'ed7c84a54ced59c55981780546adb0b4583dcf85'
MATH = 'raydium'
CAPABILITY = capability('raydium_clmm',PROGRAM,REVISION,model='concentrated_personal_position',
    dependencies=['pool','mints','vaults','config','position','boundary_tick_arrays','position_mint','position_holding','program_control'])
CAPABILITY.update(position_variants=['spl_nft','token2022_nft_base_controls'],tick_arrays=['TickArrayState_10240'],
    unsupported=['limit_order_positions','unknown_position_layouts','locker_programs'],dynamic_fee_quotes=False)


def decode_pool(address, account):
    raw=raw_account(account,PROGRAM)
    need(not account['executable'] and len(raw)==1544 and raw[:8]==discriminator('PoolState'), 'CLMM pool layout mismatch')
    r=Reader(raw);r.take(8);bump=r.integer(1);keys=[r.key() for _ in range(7)]
    decimals=[r.integer(1),r.integer(1)];spacing=r.integer(2);liquidity=r.integer(16);price=r.integer(16);tick=r.integer(4,signed=True)
    need(0<spacing<=1000 and base58_bytes(keys[2],32)<base58_bytes(keys[3],32),'CLMM spacing/mint order invalid')
    seed=raw[391:393]
    need(raw[389]<64 and raw[390]<3, 'unsupported CLMM pool status/fee mode')
    seeds=[b'pool',base58_bytes(keys[0],32),base58_bytes(keys[2],32),base58_bytes(keys[3],32),seed if any(seed) else b'',bytes([bump])]
    need(create_program_address(seeds,PROGRAM)==address,'CLMM pool PDA mismatch')
    for mint,vault in zip(keys[2:4],keys[4:6]):
        need(find_program_address([b'pool_vault',base58_bytes(address,32),base58_bytes(mint,32)],PROGRAM)[0]==vault,'CLMM vault PDA mismatch')
    price_tick_consistent(price,tick,MATH)
    return {'config':keys[0],'creator':keys[1],'mints':keys[2:4],'vaults':keys[4:6],'observation':keys[6],
        'decimals':decimals,'tick_spacing':spacing,'liquidity':liquidity,'sqrt_price_x64':price,'current_tick':tick,
        'status_bits':raw[389],'fee_on':raw[390],'permissioned_seed_index':int.from_bytes(seed,'little'),
        'fee_growth_global_x64':[str(int.from_bytes(raw[a:a+16],'little')) for a in (277,293)],
        'dynamic_fee_metadata_sha256':sha(raw[1096:1176]),'dynamic_fee_quote_support':False}


def config(sample,state):
    account=sample.account(state['config'])
    need(not account['executable'],'CLMM config cannot be executable')
    raw=raw_account(account,PROGRAM)
    need(len(raw)==117 and raw[:8]==discriminator('AmmConfig'),'CLMM config layout mismatch')
    r=Reader(raw);r.take(8);bump,index=r.integer(1),r.integer(2);owner=r.key()
    protocol,trade,spacing,fund=r.integer(4),r.integer(4),r.integer(2),r.integer(4)
    r.take(4);fund_owner=r.key()
    need(spacing==state['tick_spacing'] and trade<1_000_000 and protocol+fund<=1_000_000,'CLMM config spacing/fees invalid')
    sample.result['fee_config']={'owner':owner,'fund_owner':fund_owner,'trade_rate':str(trade),'protocol_share':str(protocol),'fund_share':str(fund),'denominator':'1000000','evidence':sample.used[state['config']]['evidence']}


def decode_position(address, account, pool, lead):
    raw=raw_account(account,PROGRAM)
    need(not account['executable'] and len(raw)==281 and raw[:8]==discriminator('PersonalPositionState'),'unsupported CLMM position layout')
    r=Reader(raw);r.take(8);bump=r.integer(1);mint=r.key()
    need(r.key()==pool,'CLMM position pool mismatch')
    need(not lead.get('bundle'),'bundled CLMM position unsupported')
    need(create_program_address([b'position',base58_bytes(mint,32),bytes([bump])],PROGRAM)==address,'CLMM position PDA mismatch')
    low,high=r.integer(4,signed=True),r.integer(4,signed=True);liquidity=r.integer(16)
    need(MIN_TICK<=low<high<=MAX_TICK,'CLMM position range invalid')
    r.take(32);fees=[str(r.integer(8)),str(r.integer(8))]
    rewards=[]
    for _ in range(3):r.take(16);rewards.append(str(r.integer(8)))
    return {'position_mint':mint,'lower_tick':low,'upper_tick':high,'liquidity':liquidity,
        'fees_owed_checkpoint_atomic':fees,'rewards_owed_checkpoint_atomic':rewards,
        'live_uncollected_fees_atomic':None,'live_rewards_atomic':None,'fees_scope':'stored checkpoint, excludes later growth'}


def position_relationship(sample,address,position,lead):
    return []  # Stored bump/PDA and pool relationship already validated in decode_position.


def tick_array_address(pool,tick,spacing):
    start=(tick//(60*spacing))*(60*spacing)
    return find_program_address([b'tick_array',base58_bytes(pool,32),start.to_bytes(4,'big',signed=True)],PROGRAM)[0]


def decode_boundary(address,account,pool,tick,spacing):
    raw=raw_account(account,PROGRAM)
    need(not account['executable'] and len(raw)==10240 and raw[:8]==discriminator('TickArrayState'),'CLMM tick array layout mismatch')
    need(b58encode(raw[8:40])==pool,'CLMM tick array pool mismatch')
    start=int.from_bytes(raw[40:44],'little',signed=True)
    need(start==(tick//(60*spacing))*(60*spacing) and address==tick_array_address(pool,tick,spacing),'CLMM tick array range/PDA mismatch')
    need(tick % spacing==0,'CLMM boundary not spaced')
    offset=44+((tick-start)//spacing)*168
    r=Reader(raw[offset:offset+168]);stored=r.integer(4,signed=True);net=r.integer(16,signed=True);gross=r.integer(16)
    need((stored==tick or gross==0 and stored==0) and abs(net)<=gross,'CLMM tick state/liquidity mismatch')
    fees=[str(r.integer(16)),str(r.integer(16))]
    return {'tick':tick,'liquidity_net':str(net),'liquidity_gross':str(gross),'fee_growth_outside_x64':fees,
        'limit_order_quantities_uninterpreted':True,'evidence_address':address}


def analyze(target,pool,observations,*,positions):
    return concentrated.analyze(sys.modules[__name__],target,pool,observations,positions)
