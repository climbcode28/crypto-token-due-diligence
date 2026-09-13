"""Current Pump curve/global bytes; completion never proves migration."""
from adapters.base import Sample,capability
from adapters.pump_layouts import fixed
from adapters.pump_common import REVISION,CURVE_PROGRAM,WSOL,ZERO,pda,curve_address,fee_address,decode_fees,selected_fees
from solana_common import need,TOKEN_PROGRAM,TOKEN_2022
from solana_addresses import associated_token_address

PROGRAM=CURVE_PROGRAM
GLOBAL=pda(PROGRAM,b'global')
CAPABILITY=capability('pump_curve',PROGRAM,REVISION,model='bonding_curve_real_and_virtual_separate',
    dependencies=['curve','global','base_mint','base_holding','quote_holding_if_non_native','fee_config','program_control'])
CAPABILITY.update(version='1.4.0',allocation_bytes=[115,124,125,151],reserved_tail_policy='known fields, the creator-fee/holder-reward tail group when the allocation holds it, then an all-zero trailing allocation of any length; a truncated account or any nonzero tail is refused',migration='successful exact migration instruction plus current destination pool required',
    quote=False,historical_execution='typed create/migrate/fee roles; legacy native-quote trades reconciled from lamport balance deltas, v2 token-quote trades verified as ordinary legs')


def decode_pool(account):
    v=fixed(account,PROGRAM,'BondingCurve')  # allocations observed: 115, 124, 125, 151 bytes
    need(v['creator_fee_bps']<=10000,'invalid Pump creator fee rate')
    v.update(quote_mint_stored=v['quote_mint'],quote_mint=WSOL if v['quote_mint']==ZERO else v['quote_mint'])
    zero_completed=v['complete'] and all(v[k]==0 for k in ('virtual_token_reserves','virtual_quote_reserves','real_token_reserves','real_quote_reserves'))
    need((v['virtual_token_reserves']>0 or zero_completed) and v['real_token_reserves']<=v['virtual_token_reserves'],'invalid Pump curve token reserves')
    need(v['real_quote_reserves']<=v['virtual_quote_reserves'],'invalid Pump curve quote reserves')
    need(not v['complete'] or v['real_token_reserves']==0,'completed curve retains real token reserves')
    v['zero_completed_reserves']=zero_completed
    return v


def analyze(target,pool,observations,**unused):
    sample=Sample(target,pool,observations,CAPABILITY)
    need(pool==curve_address(target['mint']),'target/curve PDA mismatch; mint suffix is not recognition')
    state=decode_pool(sample.account(pool));sample.result.update(state=state,stage='completed_curve_migration_unverified' if state['complete'] else 'pre_migration_curve',migration=None)
    sample.controls(PROGRAM)
    try:
        global_state=fixed(sample.account(GLOBAL),PROGRAM,'Global');sample.result['global']=global_state
        need(global_state['fee_basis_points']+global_state['creator_fee_basis_points']+global_state['buyback_basis_points']<10000,'invalid Pump global fees')
        need(global_state['max_configurable_creator_fee_bps']==0 or state['creator_fee_bps']<=global_state['max_configurable_creator_fee_bps'],'creator fee exceeds the configurable maximum')
        mint_account=sample.account(target['mint']);token_program=mint_account['owner'];mint=sample.mint(target['mint'],token_program)
        holding=associated_token_address(pool,target['mint'],token_program)[0]
        vault=sample.vault(holding,target['mint'],token_program,pool)
        required=[pool,GLOBAL,target['mint'],holding]
        need(state['real_token_reserves']<=int(vault['amount_atomic']),'recorded real tokens exceed curve holding')
        if state['quote_mint']==WSOL:
            need(state['real_quote_reserves']<=sample.account(pool)['lamports'],'recorded real native reserve exceeds lamports')
            sample.result['native_lamports']=str(sample.account(pool)['lamports'])
            sample.result['native_non_reserve_lamports']=str(sample.account(pool)['lamports']-state['real_quote_reserves'])
        else:
            quote=state['quote_mint'];qprogram=sample.account(quote)['owner'];sample.mint(quote,qprogram)
            qholding=associated_token_address(pool,quote,qprogram)[0];q=sample.vault(qholding,quote,qprogram,pool)
            required += [quote,qholding]
            need(state['real_quote_reserves']<=int(q['amount_atomic']),'recorded real quote exceeds token holding')
        sample.same_bank(required)
        sample.result.update(reserves_atomic=[str(state['real_token_reserves']),str(state['real_quote_reserves'])],
            virtual_reserves_atomic=[str(state['virtual_token_reserves']),str(state['virtual_quote_reserves'])],
            mints=[target['mint'],state['quote_mint']],reserve_formula='recorded real reserves bounded by observed custody; virtual balances are pricing inputs, not custody')
        addr=fee_address(PROGRAM);fees=decode_fees(addr,sample.account(addr),PROGRAM);sample.result['fee_config']=fees
        sample.same_bank(required+[addr])
        sample.result['selected_fees']=selected_fees(fees,canonical=True,quote=state['quote_mint'],mint_supply=int(mint['supply_atomic']),
            base_reserve=state['virtual_token_reserves'],quote_reserve=state['virtual_quote_reserves'],
            mode_restricted=state['is_mayhem_mode'] or state['is_cashback_coin'] or global_state['buyback_basis_points']!=0)
        sample.result['selected_fees']['applicable_components']=['protocol_fee_bps','creator_fee_bps']
    except ValueError as exc:sample.result['gaps'].append(str(exc))
    result=sample.finish()
    result['controller_roots'] += [{'address':value,'role':role,'evidence':sample.used.get(GLOBAL,{}).get('evidence',[])}
        for role,value in result.get('global',{}).items() if role in ('authority','withdraw_authority','set_creator_authority','admin_set_creator_authority') and value!=ZERO]
    result['creator_role']={'address':state['creator'],'role':'current recorded creator; fee sharing/cashback and setter powers separate',
        'human_identity':None,'evidence':sample.used[pool]['evidence']}
    for k in ('virtual_token_reserves','virtual_quote_reserves','real_token_reserves','real_quote_reserves','token_total_supply'):state[k]=str(state[k])
    return result
