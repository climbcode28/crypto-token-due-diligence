"""DAMM v2 range/compounding principal and observed vesting; no DAMM v1/DBC aliases."""
import sys
from solana_common import need, pubkey, base58_bytes, b58encode, TOKEN_2022
from solana_addresses import find_program_address
from solana_accounts import decode_holding, ratio
from adapters.base import capability
from adapters.binary import raw_account, discriminator
from adapters import meteora_common as common

PROGRAM = 'cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG'
REVISION = 'a85c926607433f23f0ea60f4ca7b1ae92f4156cb'
CAPABILITY = capability('meteora_damm_v2',PROGRAM,REVISION,model='pool_range_or_compounding_position_liquidity',
    dependencies=['pool_with_embedded_fees','mints','vaults','position','position_nft','Clock_for_vesting'])
CAPABILITY.update(locks=['inner_vesting','explicit_external_vesting','permanent_locked_state'],
    unsupported=['DAMM_v1','DBC','DLMM','executable_exit','unobserved_external_vestings'])


def number(raw, offset, size=8):
    return int.from_bytes(raw[offset:offset+size],'little')


def layout(value, name, length):
    raw = raw_account(value,PROGRAM)
    need(not value['executable'] and len(raw) == length and raw[:8] == discriminator(name),'unsupported DAMM v2 '+name+' layout')
    return raw


def decode_pool(address, value):
    raw = layout(value,'Pool',1112)
    mints=[b58encode(raw[o:o+32]) for o in (168,200)]
    vaults=[b58encode(raw[o:o+32]) for o in (232,264)]
    need(mints[0] != mints[1], 'duplicate DAMM v2 mints')
    for mint,vault in zip(mints,vaults):
        need(vault == find_program_address([b'token_vault',base58_bytes(mint,32),base58_bytes(address,32)],PROGRAM)[0], 'DAMM v2 vault PDA mismatch')
    cfg={'base_fee_mode':raw[16], 'cliff_fee_numerator':str(number(raw,8)),
         'protocol_fee_percent':raw[48], 'referral_fee_percent':raw[50], 'compounding_fee_bps':number(raw,54,2),
         'dynamic_fee_initialized':raw[56], 'max_volatility_accumulator':number(raw,64,4),
         'variable_fee_control':number(raw,68,4), 'bin_step':number(raw,72,2),
         'filter_period':number(raw,74,2), 'decay_period':number(raw,76,2), 'reduction_factor':number(raw,78,2),
         'last_update_timestamp':str(number(raw,80)), 'bin_step_x64':str(number(raw,88,16)),
         'sqrt_price_reference':str(number(raw,104,16)), 'volatility_accumulator':str(number(raw,120,16)),
         'volatility_reference':str(number(raw,136,16)), 'init_sqrt_price':str(number(raw,152,16)),
         'fee_denominator':'1000000000', 'fee_version':raw[486], 'collect_fee_mode':raw[484]}
    mode=cfg['base_fee_mode']
    if mode in (0,1):
        cfg.update(number_of_period=number(raw,22,2), period_frequency=str(number(raw,24)), reduction_factor_base=str(number(raw,32)))
    elif mode == 2:
        cfg.update(fee_increment_bps=number(raw,22,2), max_limiter_duration=number(raw,24,4), max_fee_bps=number(raw,28,4), reference_amount=str(number(raw,32)))
    elif mode in (3,4):
        cfg.update(number_of_period=number(raw,22,2),sqrt_price_step_bps=number(raw,24,4),scheduler_expiration_duration=number(raw,28,4),reduction_factor_base=str(number(raw,32)))
    gaps=[]
    cap=500000000 if raw[486] == 0 else 990000000
    cfg['max_fee_numerator']=str(cap)
    if not (mode <= 4 and int(cfg['cliff_fee_numerator']) <= cap and raw[486] <= 1 and raw[484] <= 2 and
            cfg['protocol_fee_percent'] <= 100 and cfg['referral_fee_percent'] <= 100 and cfg['compounding_fee_bps'] <= 10000 and
            (raw[484] == 2 or cfg['compounding_fee_bps'] == 0) and cfg['dynamic_fee_initialized'] in (0,1)):
        gaps.append('unsupported_DAMM_v2_fee_configuration')
    if cfg['dynamic_fee_initialized'] and not (cfg['bin_step'] > 0 and int(cfg['bin_step_x64']) > 0 and
            cfg['filter_period'] <= cfg['decay_period'] and cfg['reduction_factor'] <= 10000 and
            int(cfg['volatility_accumulator']) <= cfg['max_volatility_accumulator'] and int(cfg['sqrt_price_reference']) > 0):
        gaps.append('invalid_DAMM_v2_dynamic_fee_configuration')
    if raw[480] > 1 or raw[481] > 1 or raw[485] > 1 or raw[696] > 1 or raw[487] or any(raw[697:728]):
        gaps.append('unsupported_DAMM_v2_version_or_controls')
    if any(raw[17:22]) or any(raw[40:48]) or raw[49] or any(raw[51:54]) or any(raw[57:64]):
        gaps.append('unknown_DAMM_v2_fee_layout_padding')
    return {'mints':mints,'vaults':vaults,'authority':find_program_address([b'pool_authority'],PROGRAM)[0],
        'token_programs':common.token_programs(raw[482:484]), 'configuration':cfg,'configuration_gaps':gaps,
        'liquidity':number(raw,360,16), 'protocol_fees':[number(raw,392),number(raw,400)],
        'sqrt_min_price':number(raw,424,16), 'sqrt_max_price':number(raw,440,16), 'sqrt_price':number(raw,456,16),
        'activation_point':str(number(raw,472)), 'activation_type':raw[480], 'status':raw[481],
        'collect_fee_mode':raw[484], 'layout_version':raw[696], 'token_amounts':[number(raw,680),number(raw,688)],
        'permanent_lock_liquidity':number(raw,552,16), 'creator':b58encode(raw[648:680]),
        'fee_growth':[number(raw,488,32),number(raw,520,32)],
        'configuration_scope':'current embedded fees; initialization config address is not stored in pool'}


def vesting(raw):
    need(len(raw) == 80 and not any(raw[66:]),'unsupported vesting layout')
    values={'cliff_point':number(raw,0),'period_frequency':number(raw,8),'cliff_unlock_liquidity':number(raw,16,16),
            'liquidity_per_period':number(raw,32,16),'total_released_liquidity':number(raw,48,16),'number_of_period':number(raw,64,2)}
    total=values['cliff_unlock_liquidity']+values['liquidity_per_period']*values['number_of_period']
    need(values['total_released_liquidity'] <= total < 2**128,'vesting overflow/released exceeds total')
    values['remaining_liquidity']=total-values['total_released_liquidity']
    return values


def release(v, current):
    unlocked=0
    if current >= v['cliff_point']:
        periods=min((current-v['cliff_point'])//v['period_frequency'],v['number_of_period']) if v['period_frequency'] else 0
        unlocked=v['cliff_unlock_liquidity']+periods*v['liquidity_per_period']
    need(unlocked >= v['total_released_liquidity'],'vesting released exceeds captured time schedule')
    return unlocked-v['total_released_liquidity']


def decode_position(address,value,pool,lead=None):
    raw=layout(value,'Position',408)
    nft=b58encode(raw[40:72])
    need(b58encode(raw[8:40]) == pool and address == find_program_address([b'position',base58_bytes(nft,32)],PROGRAM)[0], 'DAMM v2 position pool/PDA mismatch')
    need(number(raw,392,4) <= 255 and not any(raw[396:]),'unsupported position delegate bits or layout')
    unlocked,vested,permanent=[number(raw,o,16) for o in (152,168,184)]
    need(unlocked+vested+permanent < 2**128,'position liquidity overflow')
    inner=vesting(raw[312:392])
    need(inner['remaining_liquidity'] <= vested,'inner vesting exceeds position vested liquidity')
    return {'pool':pool,'position_mint':nft,'liquidity':unlocked+vested+permanent,
        'unlocked_liquidity':unlocked,'vested_liquidity':vested,'permanent_locked_liquidity':permanent,
        'inner_vesting':inner,'delegate_permission':number(raw,392,4),
        'stored_pending_fees_atomic':[str(number(raw,136)),str(number(raw,144))],
        'claimed_fees_atomic':[str(number(raw,200)),str(number(raw,208))],
        'fee_checkpoints':[number(raw,72,32),number(raw,104,32)],
        'current_uncollected_fees_atomic':None, 'rewards':'pending/accruing rewards separate from principal'}


def principal(state, liquidity):
    need(type(liquidity) is int and 0 <= liquidity <= state['liquidity'] < 2**128,'invalid position/pool liquidity')
    if state['collect_fee_mode'] == 2:
        need(state['layout_version'] == 1 and state['liquidity'] >= 100<<64,'compounding requires tracked reserves and dead-liquidity denominator')
        amounts=[liquidity*a//state['liquidity'] for a in state['token_amounts']]
        model='compounding_tracked_reserve_share'
    else:
        low,price,high=state['sqrt_min_price'],state['sqrt_price'],state['sqrt_max_price']
        need(0 < low <= price <= high and low < high < 2**128,'invalid DAMM v2 pool price range')
        amounts=[liquidity*(high-price)//(price*high),liquidity*(price-low)//2**128]
        model='pool_range_with_DAMM_liquidity_scaling'
    need(all(0 <= a < 2**64 for a in amounts),'principal token overflow')
    return {'amounts_atomic':list(map(str,amounts)),'model':model,'rounding':'floor',
            'scope':'gross principal before transfer fees; claimable fees and rewards excluded'}


def custody(sample,position,address,lead,state,core):
    nft=position['position_mint']
    m=sample.mint(nft,TOKEN_2022,0)
    need(m['supply_atomic'] == '1' and m['mint_authority'] == state['authority'] and m['freeze_authority'] == sample.pool,'DAMM v2 NFT issuance/freeze relationship mismatch')
    holding_address=pubkey(lead.get('holding'))
    h=decode_holding(sample.account(holding_address),mint=nft,token_program=TOKEN_2022)
    need(h['amount_atomic'] == '1' and h['state'] != 'uninitialized','position NFT holding amount/state invalid')
    sample.same_bank([*core,address,nft,holding_address])
    eligible=h['delegate'] is not None and h['delegated_amount_atomic'] == '0'
    mask=position['delegate_permission']
    permissions={name:('unrestricted' if mask&(1<<bit) else 'owner_ATA_only' if mask&(1<<(bit+1)) else 'absent')
                 for name,bit in [('remove_liquidity',1),('claim_fees',3),('claim_rewards',5)]}
    return {'holding':holding_address,**h,'mint_controls':m,'representation':'token2022_position_nft',
        'protocol_delegate_eligible':eligible,'delegate_protocol_permissions':permissions,
        'delegate_has_nft_transfer_allowance':h['delegate'] is not None and int(h['delegated_amount_atomic']) >= 1,
        'nft_transfer_executable':None,
        'beneficial_owner':None,'scope':'owner/permissions observed; mint/freeze/extension and program upgrade controls separate'}


def analyze(target,pool,observations,*,positions=None):
    positions=[] if positions is None else positions
    sample,state,core,valid=common.begin(sys.modules[__name__],target,pool,observations,positions)
    total,permanent=0,0
    for lead in positions or []:
        row=common.row(sample,lead)
        try:
            pos=decode_position(lead['position'],sample.account(lead['position']),pool)
            row.update(pos,dependencies=[*core,lead['position']])
            need(valid,'verified embedded fee configuration/mints/vaults required for DAMM v2 principal')
            sample.same_bank(row['dependencies'])
            total+=pos['liquidity'];permanent+=pos['permanent_locked_liquidity']
            value=principal(state,pos['liquidity'])
            pool_amounts=principal(state,state['liquidity'])
            # Real vault balances must back the modeled aggregate, excluding protocol fees.
            for i,vault in enumerate(sample.result['vaults']):
                need(int(pool_amounts['amounts_atomic'][i])+state['protocol_fees'][i] <= int(vault['amount_atomic']), 'modeled DAMM principal exceeds vault backing')
            row.update(principal=value,liquidity_share=ratio(pos['liquidity'],state['liquidity']),
                stored_unlocked_principal=principal(state,pos['unlocked_liquidity']),
                permanent_locked_principal=principal(state,pos['permanent_locked_liquidity']),
                lock_scope='current program rules; transferable position/fee claims and upgrades are separate')
            try:
                row['custody']=custody(sample,pos,lead['position'],lead,state,core)
                row['dependencies'] += [pos['position_mint'],row['custody']['holding']]
                row['controllers']={role:row['custody'][role] for role in ('spending_owner','delegate','close_authority')}
                for key in ('mint_controls',None):
                    control=row['custody'][key] if key else row['custody']
                    if not control['extensions_valid'] or control['unknown_extensions']:row['gaps'].append('position_token_extensions_unresolved')
            except ValueError as exc:
                row['gaps'].append(str(exc))
            try:
                external=lead.get('vestings',[])
                need(isinstance(external,list) and len(external)<=6 and len(set(external))==len(external),'bounded unique external vestings required')
                schedules=[pos['inner_vesting']]
                for vest in external:
                    raw=layout(sample.account(pubkey(vest)),'Vesting',184)
                    need(b58encode(raw[8:40]) == lead['position'] and not any(raw[120:]),'external vesting position/layout mismatch')
                    schedules.append(vesting(raw[40:120]));row['dependencies'].append(vest)
                need(sum(v['remaining_liquidity'] for v in schedules) == pos['vested_liquidity'],'external vesting coverage does not reconcile position vested liquidity')
                current=common.point(sample,row['dependencies'],state['activation_type'])
                row['dependencies'].append(common.CLOCK)
                released=sum(release(v,current) for v in schedules)
                unlocked=pos['unlocked_liquidity']+released
                need(unlocked <= pos['liquidity']-pos['permanent_locked_liquidity'],'vesting release exceeds nonpermanent liquidity')
                row.update(releasable_liquidity=str(released), principal_after_vesting_refresh=principal(state,unlocked),
                    vesting_point=str(current), vesting_coverage='reconciled_captured_position',
                    vesting_action='inner refresh on removal; external schedules require refresh_vesting first',
                    external_vestings=[{k:str(v) for k,v in s.items()} for s in schedules[1:]])
            except ValueError as exc:
                row.update(principal_after_vesting_refresh=None,vesting_coverage='partial')
                row['gaps'].append(str(exc))
        except ValueError as exc:
            row['gaps'].append(str(exc))
    if total > state['liquidity'] or permanent > state['permanent_lock_liquidity']:
        for row in sample.result['positions']:
            row.update(principal=None,stored_unlocked_principal=None,permanent_locked_principal=None,principal_after_vesting_refresh=None,liquidity_share=None)
            row['gaps'].append('sampled_positions_exceed_pool_liquidity_or_permanent_lock_accounting')
    for row in sample.result['positions']:
        for key in ('liquidity','unlocked_liquidity','vested_liquidity','permanent_locked_liquidity'):
            if key in row:row[key]=str(row[key])
        if 'inner_vesting' in row:row['inner_vesting']={k:str(v) for k,v in row['inner_vesting'].items()}
        if 'fee_checkpoints' in row:row['fee_checkpoints']=list(map(str,row['fee_checkpoints']))
    for key in ('liquidity','sqrt_min_price','sqrt_max_price','sqrt_price','permanent_lock_liquidity'):
        state[key]=str(state[key])
    for key in ('fee_growth','token_amounts'):state[key]=list(map(str,state[key]))
    sample.result['gaps'].append('executable_withdrawal_and_dynamic_swap_fees_not_established')
    return common.finish(sample)
