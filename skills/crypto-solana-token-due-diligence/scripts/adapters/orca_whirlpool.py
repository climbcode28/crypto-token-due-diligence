"""Whirlpool fixed/dynamic arrays and standard or bundled position account evidence."""
import sys
from adapters.base import capability
from adapters.binary import Reader, discriminator, raw_account
from adapters import concentrated
from adapters.concentrated_math import price_tick_consistent, MIN_TICK, MAX_TICK
from solana_common import need, base58_bytes, b58encode, sha
from solana_addresses import find_program_address, create_program_address

PROGRAM='whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc'
REVISION='408c945fef4c49ab70def4303377cfaf8f0f3c99'
MATH='orca'
CAPABILITY=capability('orca_whirlpool',PROGRAM,REVISION,model='concentrated_nft_or_bundle_position',
    dependencies=['pool','mints','vaults','config','position','boundary_tick_arrays','position_mint','position_holding','optional_bundle','program_control'])
CAPABILITY.update(position_variants=['spl_nft','token2022_nft_base_controls','spl_bundle_nft'],
    tick_arrays=['TickArray_9988','DynamicTickArray_148_to_10004'],
    unsupported=['token2022_bundle_nft','unknown_position_layouts','lock_configurations'],adaptive_fee_quotes=False)


def decode_pool(address,account):
    raw=raw_account(account,PROGRAM)
    need(not account['executable'] and len(raw)==653 and raw[:8]==discriminator('Whirlpool'),'Whirlpool layout mismatch')
    r=Reader(raw);r.take(8);config=r.key();bump=r.integer(1);spacing=r.integer(2);seed=r.take(2)
    fee,protocol=r.integer(2),r.integer(2);liquidity,price=r.integer(16),r.integer(16);tick=r.integer(4,signed=True)
    owed=[str(r.integer(8)),str(r.integer(8))]
    mint0,vault0=r.key(),r.key();g0=r.integer(16);mint1,vault1=r.key(),r.key();g1=r.integer(16)
    need(spacing>0 and protocol<=2500 and fee<=60000 and base58_bytes(mint0,32)<base58_bytes(mint1,32),'Whirlpool spacing/fees/mint order invalid')
    need(create_program_address([b'whirlpool',base58_bytes(config,32),base58_bytes(mint0,32),base58_bytes(mint1,32),seed,bytes([bump])],PROGRAM)==address,'Whirlpool PDA mismatch')
    price_tick_consistent(price,tick,MATH)
    return {'config':config,'tick_spacing':spacing,'fee_tier_index':int.from_bytes(seed,'little'),
        'mints':[mint0,mint1],'vaults':[vault0,vault1],'liquidity':liquidity,'sqrt_price_x64':price,'current_tick':tick,
        'fee_rate':str(fee),'fee_rate_denominator':'1000000','protocol_fee_rate':str(protocol),'protocol_denominator':'10000',
        'protocol_fees_owed_atomic':owed,'fee_growth_global_x64':list(map(str,[g0,g1])),
        'reward_and_control_extensions_sha256':sha(raw[269:]),'adaptive_fee_quote_support':False}


def config(sample,state):
    account=sample.account(state['config'])
    need(not account['executable'],'Whirlpool config cannot be executable')
    raw=raw_account(account,PROGRAM)
    need(len(raw)==108 and raw[:8]==discriminator('WhirlpoolsConfig'),'Whirlpool config layout mismatch')
    r=Reader(raw);r.take(8)
    row={'fee_authority':r.key(),'collect_protocol_fees_authority':r.key(),'reward_emissions_super_authority':r.key(),
         'default_protocol_fee_rate':r.integer(2),'feature_flags':r.integer(2),'evidence':sample.used[state['config']]['evidence']}
    need(row['default_protocol_fee_rate']<=2500 and row['feature_flags']<=1,'unsupported Whirlpool config control fields')
    sample.result['fee_config']=row


def decode_position(address,account,pool,lead):
    raw=raw_account(account,PROGRAM)
    need(not account['executable'] and len(raw)==216 and raw[:8]==discriminator('Position'),'unsupported Whirlpool position layout')
    r=Reader(raw);r.take(8);need(r.key()==pool,'Whirlpool position pool mismatch');mint=r.key();liquidity=r.integer(16)
    low,high=r.integer(4,signed=True),r.integer(4,signed=True)
    need(MIN_TICK<=low<high<=MAX_TICK,'Whirlpool position range invalid')
    if lead.get('bundle'):
        index=lead.get('bundle_index');need(type(index)is int and 0<=index<256,'invalid bundle index')
        seeds=[b'bundled_position',base58_bytes(mint,32),str(index).encode()]
    else:seeds=[b'position',base58_bytes(mint,32)]
    need(find_program_address(seeds,PROGRAM)[0]==address,'Whirlpool position PDA mismatch')
    r.take(16);fee0=r.integer(8);r.take(16);fee1=r.integer(8);rewards=[]
    for _ in range(3):r.take(16);rewards.append(str(r.integer(8)))
    return {'position_mint':mint,'lower_tick':low,'upper_tick':high,'liquidity':liquidity,
        'fees_owed_checkpoint_atomic':list(map(str,[fee0,fee1])),'rewards_owed_checkpoint_atomic':rewards,
        'live_uncollected_fees_atomic':None,'live_rewards_atomic':None,'fees_scope':'stored checkpoint, excludes later growth'}


def position_relationship(sample,address,position,lead):
    if not lead.get('bundle'):return []
    bundle=lead['bundle'];account=sample.account(bundle)
    need(not account['executable'],'position bundle cannot be executable')
    raw=raw_account(account,PROGRAM)
    need(len(raw)==136 and raw[:8]==discriminator('PositionBundle'),'unsupported bundle layout')
    mint=position['position_mint']
    need(b58encode(raw[8:40])==mint and find_program_address([b'position_bundle',base58_bytes(mint,32)],PROGRAM)[0]==bundle,'bundle mint/PDA mismatch')
    index=lead['bundle_index']
    need(raw[40+index//8] & (1 << (index%8)), 'position is not active in bundle bitmap')
    need(not any(raw[72:]), 'unknown bundle reserved layout')
    return [bundle]


def tick_array_address(pool,tick,spacing):
    start=(tick//(88*spacing))*(88*spacing)
    return find_program_address([b'tick_array',base58_bytes(pool,32),str(start).encode()],PROGRAM)[0]


def decode_boundary(address,account,pool,tick,spacing):
    raw=raw_account(account,PROGRAM)
    need(not account['executable'] and len(raw)>=12,'incomplete Whirlpool tick array')
    start=int.from_bytes(raw[8:12],'little',signed=True)
    need(start==(tick//(88*spacing))*(88*spacing) and tick%spacing==0 and address==tick_array_address(pool,tick,spacing),'Whirlpool tick array range/PDA mismatch')
    index=(tick-start)//spacing
    if raw[:8]==discriminator('TickArray'):
        need(len(raw)==9988 and b58encode(raw[-32:])==pool,'Whirlpool fixed array layout/pool mismatch')
        body=raw[12+index*113:12+(index+1)*113]
    elif raw[:8]==discriminator('DynamicTickArray'):
        need(148<=len(raw)<=10004 and b58encode(raw[12:44])==pool,'Whirlpool dynamic array layout/pool mismatch')
        bitmap=int.from_bytes(raw[44:60],'little');need(bitmap < 1<<88,'dynamic tick bitmap out of range')
        r=Reader(raw);r.take(60);body=None
        for i in range(88):
            tag=r.integer(1);need(tag in (0,1) and tag==((bitmap>>i)&1),'dynamic tick tag/bitmap mismatch')
            data=bytes([tag])+r.take(112) if tag else bytes(113)
            if i==index:body=data
        need(not any(r.take(len(raw)-r.offset)),'dynamic array has unknown nonzero trailing bytes')
    else:raise ValueError('unsupported Whirlpool tick array discriminator')
    r=Reader(body);initialized=r.integer(1);net=r.integer(16,signed=True);gross=r.integer(16)
    need(initialized in (0,1) and bool(initialized)==bool(gross) and abs(net)<=gross,'Whirlpool boundary liquidity invalid')
    return {'tick':tick,'initialized':bool(initialized),'liquidity_net':str(net),'liquidity_gross':str(gross),
        'fee_growth_outside_x64':[str(r.integer(16)),str(r.integer(16))],'evidence_address':address}


def analyze(target,pool,observations,*,positions):
    return concentrated.analyze(sys.modules[__name__],target,pool,observations,positions)
