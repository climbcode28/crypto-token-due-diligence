"""Bounded launch, key continuity and inventory facts; no human identity inference."""
from solana_common import need,pubkey,target_identity,signature,TOKEN_PROGRAM,TOKEN_2022,natural
from solana_wire import validate_response
from solana_transactions import historical_owner,verify_sales,verify_rebuys
from solana_programs import observed_account
from solana_accounts import decode_holding
from adapters.pump_common import CURVE_PROGRAM,SWAP_PROGRAM,curve_address,pool_address

VERSION='1.1.0'


def history_pages(address,packets,*,start_slot,end_slot):
    """At most two 25-entry pages for an exact address, scoped to (start,end]."""
    address=pubkey(address);need(natural(start_slot)<natural(end_slot),'invalid history window')
    need(isinstance(packets,list) and len(packets)<=2,'history cap is two pages')
    result={'address':address,'start_slot':start_slot,'end_slot':end_slot,'window':'(start_slot,end_slot]',
        'pages_attempted':len(packets),'page_limit':packets[0]['request']['params'][1].get('limit') if packets else None,
        'signatures':[],'evidence':[],'window_covered':False,'gaps':[]}
    seen=set();before=None;previous_slot=2**64
    for packet in packets:
        req=packet['request'];need(req['method']=='getSignaturesForAddress' and req['params'][0]==address,'history address mismatch')
        need(req['params'][1].get('before')==before,'history pagination discontinuity')
        need('until' not in req['params'][1],'until cursor cannot establish slot coverage')
        result['evidence'].append(req['id'])
        if packet.get('status')!='ok':result['gaps'].append('signature page failed');break
        checked=validate_response(req,packet['response'])
        if checked['status']!='ok':result['gaps'].append('signature page unavailable');break
        rows=checked['result']
        need(not rows or rows[0]['slot']<=previous_slot,'history page slot order contradicts cursor')
        for row in rows:
            need(row['signature'] not in seen,'duplicate paginated signature');seen.add(row['signature'])
            if start_slot<row['slot']<=end_slot:result['signatures'].append({**row,'evidence_id':req['id']})
        if rows and rows[-1]['slot']<=start_slot:
            result['window_covered']=True;break
        if not rows or len(rows)<req['params'][1]['limit']:
            result['gaps'].append('short/empty index page does not establish archive coverage');break
        before=rows[-1]['signature']
        previous_slot=rows[-1]['slot']
    if not result['window_covered']:result['gaps'].append('bounded pages do not cover declared window')
    result['scope']='provider-indexed exact-address window; owner pages alone do not enumerate token-account activity'
    return result


def launch_facts(target,executions,*,curve=None,pool=None):
    target=target_identity(target);need(isinstance(executions,list) and len(executions)<=4,'launch receipt cap is four')
    result={'target':target,'initializations':[],'migration':None,'stage':curve.get('stage') if curve else 'launch_unverified','gaps':[],
        'mint_creation_time':None,'prior_launch_count':None,'human_identity':None}
    for execution in executions:
        if execution.get('target')!=target or execution.get('execution_status')!='succeeded' or not execution.get('block_evidence_id'):
            result['gaps'].append('launch receipt missing matching successful historical execution');continue
        effects=execution['effects']
        for e in effects:
            if e['kind']=='launch_initialize' and e['program']==CURVE_PROGRAM and e['mint']==target['mint']:
                matching=[x for x in effects if x['kind']=='mint_initialize' and x['mint']==target['mint'] and x['program']==e['token_program'] and x['locator']['outer_index']==e['locator']['outer_index'] and x['locator']['inner_index'] is not None]
                if len(matching)!=1:result['gaps'].append('launch instruction lacks exact inner mint initialization');continue
                result['initializations'].append({'signature':execution['signature'],'slot':execution['slot'],'block_time':execution['block_time'],
                    'creator_argument':e['participants']['creator_argument'],'payer':e['participants']['payer'],
                    'evidence':[execution['transaction_evidence_id'],execution['block_evidence_id']],
                    'effect_ids':[e['id'],matching[0]['id']],'scope':'successful Pump launch with exact mint initialization; creator argument not human identity'})
            if e['kind']!='launch_migrate' or e['program']!=CURVE_PROGRAM or e['mint']!=target['mint']:continue
            try:
                need(curve and pool and curve['target']==pool['target']==target,'current curve and destination pool required')
                need(curve['pool']==curve_address(target['mint']) and curve['state']['complete'],'curve completion unresolved')
                need(e['curve']==curve['pool'] and e['pool']==pool['pool']==pool_address(target['mint'],e['quote_mint']),'migration destination mismatch')
                state=pool['state'];need(state['mints']==[target['mint'],e['quote_mint']] and curve['state']['quote_mint']==e['quote_mint'],'migration asset mismatch')
                need(state['vaults']==e['vaults'] and state['lp_mint']==e['lp_mint'],'migration vault/LP mismatch')
                need(pool['reserves_atomic'] is not None,'current destination custody not verified')
                need(all(c['context_slot']>=execution['slot'] for row in (curve,pool) for c in row['contexts']),'current stage observations predate migration')
                created=[x for x in effects if x['kind']=='pool_initialize' and x['program']==SWAP_PROGRAM and x['pool']==e['pool'] and
                    x['locator']['outer_index']==e['locator']['outer_index'] and x['locator']['inner_index'] is not None]
                need(len(created)==1,'exact destination pool initialization CPI missing');created=created[0]
                need(created['mint']==target['mint'] and created['quote_mint']==e['quote_mint'] and created['vaults']==e['vaults'] and created['lp_mint']==e['lp_mint'],'migration pool initialization differs')
                need(created['index']==0 and created['participants']['pool_creator']==e['participants']['pool_creator']==state['creator'],'migration pool creator/index mismatch')
                moved=[]
                for mint,vault in zip(state['mints'],state['vaults']):
                    rows=[x for x in effects if x['kind']=='transfer' and x['mint']==mint and x['participants']['destination']==vault and
                        x['locator']['outer_index']==e['locator']['outer_index'] and x['locator']['inner_index'] is not None and int(x['amount_atomic'])>0]
                    need(len(rows)==1,'migration destination funding unresolved');moved+=rows
                result.update(stage='migration_verified_current_pool_observed',migration={'signature':execution['signature'],'slot':execution['slot'],'pool':e['pool'],
                    'mints':state['mints'],'current_reserves_atomic':pool['reserves_atomic'],'effect_ids':[e['id'],created['id']]+[x['id'] for x in moved],
                    'evidence':[execution['transaction_evidence_id'],execution['block_evidence_id'],*curve['evidence'],*pool['evidence']]})
            except (ValueError,KeyError,TypeError) as exc:result['gaps'].append(str(exc))
    if len(result['initializations'])==1:result['mint_creation_time']=result['initializations'][0]['block_time']
    elif len(result['initializations'])>1:result['gaps'].append('multiple contradictory mint initialization receipts')
    return result


def creator_activity(target,attributions,executions,*,histories=None,sales=None,rebuys=None):
    target=target_identity(target);need(isinstance(attributions,list) and len(attributions)<=2,'creator/treasury scope capped at two keys')
    need(isinstance(executions,list) and len(executions)<=8,'creator receipt sample capped at eight')
    signatures=[signature(e['signature']) for e in executions];need(len(signatures)==len(set(signatures)),'duplicate creator execution')
    rows=[];seen=set();sales=sales or {'target':target,'receipts':[]};need(sales['target']==target,'sales target mismatch')
    rebuys=rebuys or {'target':target,'receipts':[]};need(rebuys['target']==target,'rebuy target mismatch')
    for attribution in attributions:
        key=pubkey(attribution['address']);need(key not in seen,'duplicate attributed key');seen.add(key)
        need(attribution['mint']==target['mint'] and attribution['role'] in ('creator','treasury') and attribution.get('evidence'),'exact-mint attribution evidence required')
        row={'address':key,'attribution':attribution,'window_samples':[h for h in (histories or []) if h['address']==key],
             'movements':[],'verified_sales':[],'verified_rebuys':[],'protocol_operations':[],'gaps':[], 'human_identity':None,'personal_cash_out':None,
             'total_creator_sales':None,'total_prior_launches':None,'inventory_reconciliation':None}
        for execution in executions:
            if execution.get('target')!=target or execution.get('execution_status')!='succeeded' or not execution.get('block_evidence_id'):
                row['gaps'].append('sampled receipt unavailable/failed; no activity absence inferred');continue
            for sale in sales['receipts']:
                if sale.get('status')=='verified_sale' and sale.get('seller')==key and sale['signature']==execution['signature']:
                    checked=verify_sales(target,[{'pool':sale['pool'],'execution':execution}])['receipts'][0]
                    need(checked==sale,'sale does not recompute from attributed receipt')
                    row['verified_sales'].append(sale)
            for buy in rebuys['receipts']:
                if buy.get('status')=='verified_rebuy' and buy.get('buyer')==key and buy['signature']==execution['signature']:
                    checked=verify_rebuys(target,[{'pool':buy['pool'],'execution':execution}])['receipts'][0]
                    need(checked==buy,'rebuy does not recompute from attributed receipt');row['verified_rebuys'].append(buy)
            for e in execution['effects']:
                if e['kind'] in ('creator_fee_claim','position_liquidity_remove','protocol_trade_instruction'):
                    if key in e['participants'].values():row['protocol_operations'].append({'kind':e['kind'],'signature':execution['signature'],'effect_id':e['id'],'scope':'observed operation; amount/beneficiary needs movements'})
                if e.get('mint')!=target['mint'] or e['kind'] not in ('transfer','mint','burn'):continue
                roles={}
                for name in ('source','destination'):
                    account=e['participants'].get(name)
                    if account:
                        try:roles[name]=historical_owner(execution,account,target['mint'])
                        except ValueError:row['gaps'].append('movement ownership unresolved: '+e['id'])
                if key not in roles.values():continue
                classification='allocation_mint' if e['kind']=='mint' else 'burn' if e['kind']=='burn' else 'internal_transfer' if roles.get('source')==roles.get('destination')==key else 'transfer_out' if roles.get('source')==key else 'transfer_in'
                # A buy/sell intention is not enough to relabel a transfer as proceeds.
                matching=[s for s in row['verified_sales'] if e['id'] in s['effect_ids']]
                if matching and roles.get('source')==key:classification='verified_sale_input'
                if any(e['id'] in r['effect_ids'] for r in row['verified_rebuys']) and roles.get('destination')==key:classification='verified_rebuy_output'
                if classification=='transfer_in' and e['locator']['inner_index'] is not None:
                    ops=[x for x in execution['effects'] if x['kind'] in ('creator_fee_claim','position_liquidity_remove') and key in x['participants'].values() and
                        x['locator']['outer_index']==e['locator']['outer_index'] and x['locator']['inner_index'] is None]
                    if len(ops)==1:classification='fee_operation_receipt' if ops[0]['kind']=='creator_fee_claim' else 'liquidity_withdrawal_receipt'
                row['movements'].append({'kind':classification,'amount_atomic':e['amount_atomic'],'signature':execution['signature'],
                    'effect_id':e['id'],'account_owners':roles,'accounts':e['participants'],'evidence':[execution['transaction_evidence_id'],execution['block_evidence_id']]})
        row['observed_sale_receipts']=len(row['verified_sales']);row['sampled_receipts']=len(executions)
        row['gaps'].append('complete key history, cost basis, beneficiary and inventory conservation not established by receipt subset')
        rows.append(row)
    return {'target':target,'keys':rows,'scope':'bounded attributed-key observations; transfers/exchange labels/shared funding do not establish personal cash-out or identity'}


def prior_launches(address,executions):
    address=pubkey(address);need(isinstance(executions,list) and len(executions)<=8,'prior launch sample capped at eight')
    rows=[]
    for ex in executions:
        from solana_discovery import MAINNET
        if ex.get('target',{}).get('genesis_hash')!=MAINNET:continue
        if ex.get('execution_status')!='succeeded' or not ex.get('block_evidence_id'):continue
        for e in ex['effects']:
            if e['kind']=='launch_initialize' and e['program']==CURVE_PROGRAM and address in e['participants'].values():
                rows.append({'mint':e['mint'],'signature':ex['signature'],'effect_id':e['id'],'relationship':
                    'signer_continuity' if address in ex.get('signers',[]) else 'recorded_creator_argument',
                    'evidence':[ex['transaction_evidence_id'],ex['block_evidence_id']]})
    return {'address':address,'sampled_receipts':len(executions),'observed_launch_links':rows,'total_prior_launches':None,
            'project_affiliation':None,'common_control':None,'human_identity':None,'scope':'observed key continuity only; missing/failed history never proves no prior launches'}


def reconcile_inventory(target,owner,opening,closing,histories,executions):
    """Conservation for explicitly listed unchanged token accounts, not all wallets."""
    target=target_identity(target);owner=pubkey(owner)
    result={'target':target,'owner':owner,'status':'unresolved','opening_atomic':None,'closing_atomic':None,
        'net_flow_atomic':None,'difference_atomic':None,'accounts':sorted(opening),'evidence':[],'gaps':[],
        'scope':'listed token-account subset only; no exhaustive owner inventory, beneficial ownership or profit claim'}
    try:
        need(opening and set(opening)==set(closing) and len(opening)<=20,'identical bounded opening/closing account sets required')
        from solana_session import encoded
        need(len({encoded(p) for p in opening.values()})==len({encoded(p) for p in closing.values()})==1,'each inventory boundary needs one account batch')
        values=[];slots=[]
        for packets in (opening,closing):
            total=0;slot=None
            for address,packet in packets.items():
                value,meta=observed_account(address,packet);need(not meta['sliced'],'full inventory holding required')
                h=decode_holding(value,mint=target['mint'],token_program=TOKEN_PROGRAM)
                need(h['spending_owner']==owner and h['state']!='uninitialized','inventory owner/state mismatch')
                total+=int(h['amount_atomic']);slot=meta['context_slot'];result['evidence']+=meta['evidence']
            values.append(total);slots.append(slot)
        need(slots[0]<slots[1],'inventory boundaries not ordered')
        need(len(histories)==len(opening) and {h['address'] for h in histories}==set(opening),'history required for every listed token account')
        required={}
        for h in histories:
            need(h['start_slot']==slots[0] and h['end_slot']==slots[1] and h['window_covered'] and not h['gaps'],'account history window incomplete')
            result['evidence']+=h['evidence']
            for row in h['signatures']:
                old=required.get(row['signature']);need(old is None or old['slot']==row['slot'] and old['err']==row['err'],'history receipt contradiction')
                required[row['signature']]=row
        need(len(executions)<=8 and len({e['signature'] for e in executions})==len(executions),'bounded unique inventory receipts required')
        by_sig={e['signature']:e for e in executions};need(set(by_sig)==set(required),'all and only indexed window receipts required')
        net=0
        for sig,record in required.items():
            ex=by_sig[sig];need(ex['target']==target and ex['block_evidence_id'] and ex['slot']==record['slot'],'inventory execution binding mismatch')
            result['evidence'] += [ex['transaction_evidence_id'],ex['block_evidence_id']]
            if record['err'] is not None:need(ex['execution_status']=='failed','history/execution status contradiction');continue
            need(ex['execution_status']=='succeeded' and not ex['gaps'] and ex['effect_coverage']=='all_returned_instructions','incomplete successful inventory effects')
            for e in ex['effects']:
                if e['kind'] not in ('transfer','mint','burn') or e.get('mint')!=target['mint']:continue
                for role,direction in (('source',-1),('destination',1)):
                    address=e['participants'].get(role)
                    if address in opening:
                        need(historical_owner(ex,address,target['mint'])==owner,'inventory historical ownership changed')
                        net+=direction*int(e['amount_atomic'])
        difference=values[1]-values[0]-net
        result.update(opening_atomic=str(values[0]),closing_atomic=str(values[1]),net_flow_atomic=str(net),difference_atomic=str(difference),
            status='reconciled' if difference==0 else 'mismatch',start_slot=slots[0],end_slot=slots[1])
        if difference:result['gaps'].append('opening plus interpreted flows does not equal closing inventory')
    except (ValueError,KeyError,TypeError) as exc:result['gaps'].append(str(exc))
    result['evidence']=sorted(set(result['evidence']))
    return result
