"""Explicit installed offline fact operations; no arbitrary expression/plugin execution."""
import re
from solana_common import need,target_identity,pubkey
from solana_programs import observed_account

VERSION='1.5.0'  # Persisted derivation contract; bumped whenever any operation's output shape or input binding changes.
RUNTIME_VERSION='1.7.0'
# The contract version in which each operation's output last changed. A derivation recorded
# before its operation last changed cannot be recomputed by this engine: read or replay it
# with its frozen engine instead. Operations absent here have not changed since 1.0.0.
# 1.1.0 (2026-09-11 review): controllers root_links; discovery project-link corroboration; holders discovery
# record and rounding; mint/controls Token-2022 metadata fields and authority; pool limitation scope;
# transaction/sales/rebuys route and fee-sink fields; launch history page limits; public quote sources.
# 1.2.0 (2026-09-12): sales/rebuys accept up to ten receipts (maximum_receipts 10, so pool_activity receipts count)
# and verify a same-transaction wrapped-SOL input; pool facts for the Pump adapters carry the creator-fee/holder-reward
# tail fields, absent_fields and exotic flat fees; transaction effects decode PumpSwap trades with router accounts and
# carry rebate_accounts (decoder 1.3.0). controls gained an optional newer_unpinned note in the same release; a controls
# derivation recorded without it still recomputes, so its entry stays at 1.1.0.
# 1.3.0 (2026-09-12, night): sales/rebuys rows carry spending_owner and custody (router custody legs verify with the
# beneficial wallet as seller) and curve trades verify through native or token quote legs.
# 1.4.0 (2026-09-13): pool facts may carry an optional position_census (counted positions, ranking basis, sampled share) bound to
# the census read; a pool derivation recorded without it still recomputes, so its entry stays at 1.2.0.
# 1.5.0 (2026-09-13, later): the pool census note carries a scope line and is no longer bound to the census read (one unpinned
# program scan made every censused pool fact unusable); a resolved concentrated sample with observed positions reports status
# observed (reserves are never inferred there). A pool derivation recorded at 1.4.0 with a bound census read neither
# recomputes nor shares the output: read or replay it with its frozen engine, so the pool entry moves to 1.5.0.
CHANGED_IN={**{op:'1.1.0' for op in ('controllers','discovery_pools','holders','mint','controls','history')},'pool':'1.5.0','transaction':'1.3.0','sales':'1.3.0','rebuys':'1.3.0'}


def version_tuple(value):
    need(isinstance(value,str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',value) is not None,'invalid operation version')
    return tuple(int(x) for x in value.split('.'))


def recomputable(operation,recorded):
    """'ok' when this engine reproduces the recorded shape; otherwise the reason it cannot."""
    recorded=version_tuple(recorded)
    if recorded>version_tuple(VERSION):return 'derivation recorded by a newer engine; use read/replay'
    if recorded<version_tuple(CHANGED_IN.get(operation,'1.0.0')):return 'operation version differs from installed engine; use read/replay'
    return 'ok'
PUBLICATION_OPS={'public_quote','discovery_pools','repository_metadata','repository_revision','repository_tree'}
EXECUTION_OPS={'transaction','sales','rebuys','launch','creator_activity','inventory','prior_launches'}


def compute(operation,parameters,target,resolve):
    """resolve(id) records every actual direct dependency for exact input closure."""
    target=target_identity(target);p=parameters
    need(isinstance(p,dict),'derivation parameters must be an object')
    def get(name):return resolve(p[name])
    def packets(name='observations'):return {pubkey(address):resolve(eid) for address,eid in p[name].items()}
    if operation=='public_quote':
        from solana_quotes import public_quote
        d=get('capture');return public_quote(p['source'],target,d['record'],d['raw'],p['output_mint'],p['input_atomic'],slippage_bps=p.get('slippage_bps',50))
    if operation in ('discovery_pools','repository_metadata','repository_revision','repository_tree'):
        import solana_discovery as discovery
        d=get('capture')
        if operation=='discovery_pools':return discovery.pools(d['record'],d['raw'],target,source=p.get('source','dexscreener'))
        if operation=='repository_tree':return discovery.repository_tree(d['record'],d['raw'],get('revision'))
        return getattr(discovery,operation)(d['record'],d['raw'],p['repository'])
    if operation=='mint':
        from solana_accounts import decode_mint
        value,meta=observed_account(p.get('address',target['mint']),get('observation'))
        need(not meta['sliced'],'full mint required');return {**decode_mint(value),**meta}
    if operation=='metadata':
        from solana_metadata import decode_metadata
        value,meta=observed_account(p['address'],get('observation'))
        need(value is not None,'metadata account absent');need(not meta['sliced'],'full metadata account required')
        return {**decode_metadata(p['address'],value,target['mint']),**meta}
    if operation=='controls':
        from solana_accounts import controls
        result=controls(get('mint'),target,epoch_packet=get('epoch') if p.get('epoch') else None)
        if p.get('selection_scope'):
            need(p['selection_scope'] in ('latest_retained_account_snapshot','earlier_pinned_snapshot_newer_unpinned'),'unknown control snapshot selection')
            result['selection_scope']=p['selection_scope']
        if p.get('newer_unpinned') is not None:
            # A note about the newer unpinned read, never an input: the fact stays derived from the pinned snapshot only.
            n=p['newer_unpinned'];need(isinstance(n,dict) and set(n)=={'observation','authorities_match','reason'} and isinstance(n['observation'],str) and n['authorities_match'] in (True,False,None) and (n['reason'] is None or isinstance(n['reason'],str)),'invalid newer unpinned snapshot note')
            need(p.get('selection_scope')=='earlier_pinned_snapshot_newer_unpinned','newer unpinned note needs the earlier-pinned selection scope')
            result['newer_unpinned']=n
        return result
    if operation=='holders':
        from solana_accounts import aggregate_holders
        exclusions=p.get('custody_exclusions',{})
        for v in exclusions.values():
            for eid in v['evidence']:resolve(eid)
        return aggregate_holders(get('discovery'),get('sample'),target,custody_exclusions=exclusions)
    if operation=='program':
        from solana_programs import decode_program
        return decode_program(p['address'],get('observation'),get('programdata') if p.get('programdata') else None)
    if operation=='source_assurance':
        from solana_programs import source_assurance
        import json
        from solana_transport import unique_object,invalid_constant
        program=get('program');need(program['address']==p['address'],'source assurance program mismatch')
        publication=third_party=None
        if p.get('publication'):
            rev=get('publication')
            publication={'url':'https://github.com/'+rev['repository']+'/tree/'+rev['revision'],'revision':rev['revision'],'evidence':rev['evidence']}
        if p.get('third_party'):
            captured=get('third_party');claim=json.loads(captured['raw'],object_pairs_hook=unique_object,parse_constant=invalid_constant)
            need(isinstance(claim,dict) and set(claim)<={'program','status','hash_kind','code_sha256'} and {'program','status'}<=set(claim),'unsupported third-party hash statement schema')
            third_party={**claim,'evidence':[captured['record']['id']]}
        return source_assurance(program,publication=publication,third_party=third_party)
    if operation=='controllers':
        from solana_programs import authority_graph
        roots=[]
        for eid in p['root_derivations']:
            value=resolve(eid);roots += value.get('controller_roots',[])
            roots += [{'address':r['controller'],'role':r['role'],'evidence':r['evidence']} for r in value.get('powers',[]) if r['controller']]
            if value.get('mint',{}).get('program'):
                roots.append({'address':value['mint']['program'],'role':'owning_token_program','evidence':value['evidence']})
            if value.get('kind')=='program':
                roots.append({'address':value['address'],'role':'program_behavior','evidence':value['evidence']})
        graph=authority_graph(list(dict.fromkeys(r['address'] for r in roots)),packets(),vault_links=p.get('vault_links'),spending_limits=p.get('spending_limits'))
        graph['root_links']=roots
        return graph
    if operation=='pool':
        from adapters import pool_adapter
        module=pool_adapter(p['adapter']);kwargs={}
        if p['adapter'] in ('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2'):kwargs['positions']=p.get('positions',[])
        elif p['adapter']!='pump_curve':kwargs['lp_accounts']=p.get('lp_accounts',[])
        result=module.analyze(target,p['pool'],packets(),**kwargs)
        census=p.get('census')
        if isinstance(census,dict):
            # The census read (one unpinned program scan) only ranks leads; it is recorded by id inside the note, never
            # bound as an input, so the pool fact stays usable on its pinned batches. Principal and custody come from the
            # sampled positions, which are pinned inputs.
            result['position_census']={**census,'scope':'unpinned ranking read; counts are not principal or custody evidence'}
        return result
    if operation=='transaction':
        from solana_transactions import decode_transaction
        return decode_transaction(target,get('transaction'),get('block'))
    if operation in ('sales','rebuys'):
        from solana_transactions import verify_sales,verify_rebuys
        candidates=[{'pool':row['pool'],'execution':resolve(row['execution'])} for row in p['candidates']]
        return (verify_sales if operation=='sales' else verify_rebuys)(target,candidates)
    if operation=='quote_sizes':
        from solana_quotes import size_policy
        price=get('price') if p.get('price') else None
        if p.get('price_discovery'):
            candidates=get('price_discovery')['candidates'];selected=[v for v in candidates if v['pool']==p['price_pool'] and v['price_denominator_mint']==target['mint']]
            need(len(selected)==1,'one exact-mint captured pool price required');price=selected[0]
        return size_policy(target,get('mint'),user_sizes=p.get('user_sizes'),price=price,now=p.get('now'))
    if operation=='local_quote':
        from solana_quotes import estimate
        return estimate(target,p['adapter'],p['pool'],packets(),p['input_atomic'],slippage_bps=p.get('slippage_bps',50))
    if operation=='history':
        from solana_launch import history_pages
        return history_pages(p['address'],[resolve(eid) for eid in p['pages']],start_slot=p['start_slot'],end_slot=p['end_slot'])
    if operation=='launch':
        from solana_launch import launch_facts
        return launch_facts(target,[resolve(eid) for eid in p['executions']],curve=get('curve') if p.get('curve') else None,pool=get('pool') if p.get('pool') else None)
    if operation=='creator_activity':
        from solana_launch import creator_activity
        for row in p['attributions']:
            for eid in row['evidence']:resolve(eid)
        return creator_activity(target,p['attributions'],[resolve(eid) for eid in p['executions']],histories=[resolve(eid) for eid in p.get('histories',[])],
            sales=get('sales') if p.get('sales') else None,rebuys=get('rebuys') if p.get('rebuys') else None)
    if operation=='inventory':
        from solana_launch import reconcile_inventory
        return reconcile_inventory(target,p['owner'],packets('opening'),packets('closing'),[resolve(eid) for eid in p['histories']],[resolve(eid) for eid in p['executions']])
    if operation=='prior_launches':
        from solana_launch import prior_launches
        return prior_launches(p['address'],[resolve(eid) for eid in p['executions']])
    need(False,'unsupported installed derivation operation: '+str(operation))
