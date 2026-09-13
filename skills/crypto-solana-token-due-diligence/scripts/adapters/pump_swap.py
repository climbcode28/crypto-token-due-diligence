"""PumpSwap current Pool/GlobalConfig, actual custody and separate pricing reserves."""
from adapters.base import Sample,capability
from adapters.pump_layouts import fixed
from adapters.pump_common import REVISION,SWAP_PROGRAM,ZERO,pda,pool_authority,pool_address,fee_address,decode_fees,selected_fees
from solana_common import need,TOKEN_PROGRAM,TOKEN_2022,base58_bytes
from solana_addresses import associated_token_address,create_program_address
from solana_accounts import decode_holding,ratio

PROGRAM=SWAP_PROGRAM
GLOBAL=pda(PROGRAM,b'global_config')
CAPABILITY=capability('pumpswap',PROGRAM,REVISION,model='fungible_token2022_lp_actual_vaults_with_separate_virtual_quote',
    dependencies=['pool','global_config','mints','vaults','lp_mint','fee_config','program_control'])
CAPABILITY.update(version='1.4.0',allocation_bytes=[261,271,301],reserved_tail_policy='known fields, the creator-fee/holder-reward tail group when the allocation holds it, then an all-zero trailing allocation of any length; a truncated account or any nonzero tail is refused',quote=False,historical_execution='pinned create/swap/withdraw/fee roles; exact transfer reconciliation separate')


def decode_pool(account):
    v=fixed(account,PROGRAM,'Pool')  # allocations observed: 261, 271, 301 bytes
    need(v['creator_fee_bps']<=10000,'invalid Pump creator fee rate')
    need(v['base_mint']!=v['quote_mint'] and v['pool_base_token_account']!=v['pool_quote_token_account'],'PumpSwap asset/vault overlap')
    v.update(mints=[v['base_mint'],v['quote_mint']],vaults=[v['pool_base_token_account'],v['pool_quote_token_account']],config=GLOBAL,
        canonical_creator=v['creator']==pool_authority(v['base_mint']))
    v['canonical_migration_destination']=v['canonical_creator'] and v['index']==0
    return v


def analyze(target,pool,observations,*,lp_accounts=None):
    sample=Sample(target,pool,observations,CAPABILITY);state=decode_pool(sample.account(pool))
    need(target['mint'] in state['mints'],'target not in PumpSwap pool')
    need(create_program_address([b'pool',state['index'].to_bytes(2,'little'),base58_bytes(state['creator'],32),
        *[base58_bytes(m,32) for m in state['mints']],bytes([state['pool_bump']])],PROGRAM)==pool,'PumpSwap pool PDA mismatch')
    need(state['lp_mint']==pda(PROGRAM,b'pool_lp_mint',base58_bytes(pool,32)),'PumpSwap LP mint PDA mismatch')
    sample.result.update(state=state,mints=state['mints']);sample.controls(PROGRAM)
    try:
        config=fixed(sample.account(GLOBAL),PROGRAM,'GlobalConfig');sample.result['global']=config
        need(config['disable_flags']<32,'unknown PumpSwap disable flags')
        need(sum(config[k] for k in ('lp_fee_basis_points','protocol_fee_basis_points','coin_creator_fee_basis_points','buyback_basis_points'))<10000,'invalid PumpSwap global rates')
        need(config['max_configurable_creator_fee_bps']==0 or state['creator_fee_bps']<=config['max_configurable_creator_fee_bps'],'creator fee exceeds the configurable maximum')
        required=[pool,GLOBAL,*state['mints'],*state['vaults']]
        mints=[]
        for mint,vault in zip(state['mints'],state['vaults']):
            program=sample.account(mint)['owner'];mints.append(sample.mint(mint,program))
            need(vault==associated_token_address(pool,mint,program)[0],'PumpSwap vault ATA mismatch')
            sample.vault(vault,mint,program,pool)
        sample.same_bank(required)
        reserves=[int(v['amount_atomic']) for v in sample.result['vaults']]
        effective=reserves[1]+state['virtual_quote_reserves'];need(0<effective<2**128,'invalid effective PumpSwap quote reserve')
        sample.result.update(reserves_atomic=list(map(str,reserves)),effective_pricing_reserves_atomic=[str(reserves[0]),str(effective)],
            reserve_formula='actual vault token balances; pricing quote separately adds signed virtual_quote_reserves',
            stage='current_amm_pool_migration_history_unverified')
        addr=fee_address(PROGRAM);fees=decode_fees(addr,sample.account(addr),PROGRAM);sample.result['fee_config']=fees;sample.same_bank(required+[addr])
        try:
            sample.result['selected_fees']=selected_fees(fees,canonical=state['canonical_creator'],quote=state['quote_mint'],mint_supply=int(mints[0]['supply_atomic']),
                base_reserve=reserves[0],quote_reserve=effective,mode_restricted=state['is_mayhem_mode'] or state['is_cashback_coin'] or state['virtual_quote_reserves']!=0 or config['buyback_basis_points']!=0)
        except ValueError as exc:sample.result['gaps'].append(str(exc))
        sample.result['lp_custody']=custody(sample,state,required,lp_accounts or [])
    except ValueError as exc:sample.result['gaps'].append(str(exc))
    result=sample.finish()
    for role in ('admin','admin_set_coin_creator_authority','boost_authority'):
        value=result.get('global',{}).get(role)
        if value and value!=ZERO:result['controller_roots'].append({'address':value,'role':role,'evidence':sample.used[GLOBAL]['evidence']})
    result['creator_roles']={'pool_creator':state['creator'],'coin_creator':state['coin_creator'],
        'fee_beneficiary':None,'human_identity':None,'scope':'pool derivation and stored coin creator differ; cashback/sharing/setter history required for beneficiary attribution'}
    state['virtual_quote_reserves']=str(state['virtual_quote_reserves'])
    return result


def custody(sample,state,required,addresses):
    need(isinstance(addresses,list) and len(addresses)<=6 and len(set(addresses))==len(addresses),'at most six unique LP holdings')
    lm=sample.mint(state['lp_mint'],TOKEN_2022)
    need(lm['mint_authority']==sample.pool and lm['freeze_authority'] is None,'PumpSwap LP authority mismatch')
    supply=int(lm['supply_atomic']);need(supply<=state['lp_supply'],'LP mint supply exceeds pool accounting supply')
    sample.same_bank(required+[state['lp_mint']]);rows=[];missing=[];total=0
    for address in addresses:
        try:
            h=decode_holding(sample.account(address),mint=state['lp_mint'],token_program=TOKEN_2022)
            need(h['state']!='uninitialized','uninitialized LP holding');sample.same_bank(required+[state['lp_mint'],address])
            total+=int(h['amount_atomic']);rows.append({'address':address,**h,**sample.used[address],
                'mint_supply_share':ratio(int(h['amount_atomic']),supply),'pool_accounting_share':ratio(int(h['amount_atomic']),state['lp_supply'])})
        except ValueError as exc:missing.append({'address':address,'reason':str(exc)})
    need(total<=supply,'LP holdings exceed observed mint supply')
    return {'mint':state['lp_mint'],'mint_supply_atomic':str(supply),'pool_accounting_supply_atomic':str(state['lp_supply']),
        'observed_atomic':str(total),'accounts':rows,'missing':missing,'sample_mint_share':ratio(total,supply),
        'sample_pool_share':ratio(total,state['lp_supply']),'locked_share':None,'enumeration':'explicit_subset_not_exhaustive',
        'accounting_minus_mint_supply_atomic':str(state['lp_supply']-supply),'difference_reason':'burn/initialization/history unresolved; not automatically locked'}
