"""Offline historical legacy/v0 effects. Raw keys and successful metadata are mandatory."""
from solana_common import need, natural, pubkey, signature, target_identity, ALPHABET, b58encode, TOKEN_PROGRAM, TOKEN_2022
from solana_wire import validate_response, amount
from solana_swaps import decode as decode_swap,position_instruction
from adapters.pump_instructions import decode as decode_pump

VERSION='1.1.0'
SYSTEM='11111111111111111111111111111111'
WSOL='So11111111111111111111111111111111111111112'


def data_bytes(text):
    need(isinstance(text,str) and len(text)<=14000,'bounded instruction data required')
    number=0
    for c in text:
        need(c in ALPHABET,'invalid instruction base58')
        number=number*58+ALPHABET.index(c)
    raw=bytes(len(text)-len(text.lstrip('1')))+number.to_bytes((number.bit_length()+7)//8,'big')
    need(len(raw)<=10000 and b58encode(raw)==text,'invalid instruction encoding')
    return raw


def index(value,keys):
    need(type(value) is int and 0<=value<len(keys),'instruction/balance account index outside historical keys')
    return keys[value]


def token_balances(rows,keys):
    need(isinstance(rows,list) and len(rows)<=len(keys),'token balance metadata missing')
    result={}
    for r in rows:
        need(isinstance(r,dict),'invalid token balance')
        address=index(r.get('accountIndex'),keys)
        need(address not in result,'duplicate token balance index')
        q=r['uiTokenAmount'];mint=pubkey(r['mint']);atomic=amount(q['amount'])
        need(atomic<2**64 and natural(q['decimals'])<=255,'invalid historical token balance')
        program=pubkey(r['programId']) if r.get('programId') else None
        need(program is None or program in (TOKEN_PROGRAM,TOKEN_2022),'unsupported balance token program')
        result[address]={'mint':mint,'owner':pubkey(r['owner']) if r.get('owner') else None,
                         'program':program,'amount_atomic':str(atomic),'decimals':q['decimals']}
    return result


def token_effect(raw,a,balances,program):
    if not raw:return None
    op=raw[0]
    def need_accounts(count):need(len(a)>=count,'token instruction missing accounts')
    def mint_of(address):
        found=balances.get(address)
        need(found is not None,'unchecked token instruction mint missing from historical metadata')
        return found['mint']
    if op in (3,7,8,12,14,15):
        checked=op in (12,14,15)
        need(len(raw)==(10 if checked else 9),'unsupported token quantity instruction layout')
        need_accounts(4 if op==12 else 3)
        value=str(int.from_bytes(raw[1:9],'little'))
        if op in (3,12):
            source,dest,mint,authority=(a[0],a[2],a[1],a[3]) if checked else (a[0],a[1],mint_of(a[0]),a[2])
            kind='transfer';participants={'source':source,'destination':dest,'authority':authority}
            if dest in balances:need(balances[dest]['mint']==mint,'historical transfer mint mismatch')
            if source in balances:need(balances[source]['mint']==mint,'historical transfer source mint mismatch')
        elif op in (7,14):
            kind='mint';mint=a[0];participants={'destination':a[1],'authority':a[2]}
        else:
            kind='burn';mint=a[1];participants={'source':a[0],'authority':a[2]}
        if checked:
            for addr in participants.values():
                if addr in balances:need(balances[addr]['decimals']==raw[9],'checked decimals mismatch')
        for addr in participants.values():
            if addr in balances:
                need(balances[addr]['program'] in (None,program),'historical token program mismatch')
        for role in ('source','destination'):
            addr=participants.get(role)
            if addr in balances:need(balances[addr]['mint']==mint,'historical mint/burn/transfer account mint mismatch')
        return {'kind':kind,'mint':mint,'participants':participants,'amount_atomic':value,
                'decimals':raw[9] if checked else None,'quantity_scope':'instruction gross amount; transfer-fee/closure reconciliation separate'}
    if op==6:
        need_accounts(2);need(len(raw) in (3,35) and raw[2] in (0,1) and len(raw)==(35 if raw[2] else 3),'invalid SetAuthority layout')
        need(raw[1]<=16,'unsupported authority kind')
        return {'kind':'authority_change','mint':balances.get(a[0],{}).get('mint'),'participants':{'account':a[0],'authority':a[1]},
                'authority_type':raw[1],'new_authority':b58encode(raw[3:35]) if raw[2] else None,'amount_atomic':None}
    if op in (0,20):
        need_accounts(2 if op==0 else 1)
        need(len(raw) in (35,67) and raw[34] in (0,1) and len(raw)==(67 if raw[34] else 35),'invalid mint initialization')
        return {'kind':'mint_initialize','mint':a[0],'participants':{'mint':a[0]},'decimals':raw[1],
                'mint_authority':b58encode(raw[2:34]),'freeze_authority':b58encode(raw[35:]) if raw[34] else None,'amount_atomic':None}
    if op in (1,16,18):
        need_accounts({1:4,16:3,18:2}[op]);need(len(raw)==(1 if op==1 else 33),'invalid token account initialization')
        return {'kind':'token_account_initialize','mint':a[1],'participants':{'account':a[0],'owner':a[2] if op==1 else b58encode(raw[1:33])},'amount_atomic':None}
    if op in (9,17):
        need_accounts(3 if op==9 else 1);need(len(raw)==1,'invalid close/sync instruction')
        return {'kind':'token_account_close' if op==9 else 'sync_native','mint':balances.get(a[0],{}).get('mint'),
                'participants':{'account':a[0],**({'destination':a[1],'authority':a[2]} if op==9 else {})},'amount_atomic':None}
    if op in (10,11):
        need_accounts(3);need(len(raw)==1,'invalid freeze/thaw instruction')
        return {'kind':'freeze' if op==10 else 'thaw','mint':a[1],'participants':{'account':a[0],'authority':a[2]},'amount_atomic':None}
    return None


def decode_transaction(target,packet,block_packet):
    """Typed effects carry exact source IDs/locators; gaps never create persisted effects."""
    target=target_identity(target);req=packet['request']
    need(packet.get('status')=='ok' and req['method']=='getTransaction','successful transaction capture required')
    checked=validate_response(req,packet['response']);sig=signature(req['params'][0])
    result={'schema_version':1,'decoder_version':VERSION,'target':target,'signature':sig,
            'transaction_evidence_id':req['id'],'block_evidence_id':None,'slot':None,'version':None,
            'execution_status':'unknown','effects':[],'instructions':[],'gaps':[],
            'historical_account_keys':[],'network_fee_lamports':None,'net_proceeds':None,
            'scope':'historical RPC execution observation; network identity and digest closure required by bundle'}
    if checked['status']!='ok':
        result['gaps'].append('transaction_'+checked['status']);return result
    tx=checked['result'];result.update(slot=tx['slot'],version=tx['version'])
    try:
        need(block_packet is not None and block_packet.get('status')=='ok','historical block header not captured')
        br=block_packet['request'];bv=validate_response(br,block_packet['response'])
        need(br['method']=='getBlock' and br['params'][0]==tx['slot'] and bv['status']=='ok','transaction/header slot mismatch')
        need(tx['blockTime']==bv['result']['blockTime'],'transaction/header time contradiction')
        result.update(block_evidence_id=br['id'],blockhash=bv['result']['blockhash'],block_time=tx['blockTime'])
        meta=tx['meta'];need(isinstance(meta,dict) and 'err' in meta,'transaction status metadata missing')
        if 'status' in meta:need(meta['status']==({'Ok':None} if meta['err'] is None else {'Err':meta['err']}),'contradictory execution status')
        result['network_fee_lamports']=str(natural(meta['fee']))
        message=tx['transaction']['message'];static=message['accountKeys']
        need(1<=len(static)<=256 and len(set(static))==len(static),'invalid static key list')
        header=message['header'];signed=natural(header['numRequiredSignatures'])
        rs=natural(header['numReadonlySignedAccounts']);ru=natural(header['numReadonlyUnsignedAccounts'])
        need(1<=signed<=len(static) and rs<signed and ru<=len(static)-signed,'invalid historical message header')
        signatures=tx['transaction']['signatures']
        need(len(signatures)==signed and signatures[0]==sig and len(set(signatures))==len(signatures),'signature/header binding mismatch')
        pubkey(message['recentBlockhash'])
        lookups=message.get('addressTableLookups',[])
        need(isinstance(lookups,list) and len(lookups)<=32,'invalid historical lookup descriptors')
        loaded=meta.get('loadedAddresses')
        if tx['version']==0:
            need(isinstance(loaded,dict) and set(loaded)=={'writable','readonly'},'historical loaded addresses missing')
        else:
            need(not lookups and (loaded is None or loaded=={'writable':[],'readonly':[]}),'legacy transaction cannot have loaded keys')
            loaded={'writable':[],'readonly':[]}
        counts={k:0 for k in ('writable','readonly')}
        for lookup in lookups:
            pubkey(lookup['accountKey'])
            for k in counts:
                indices=lookup[k+'Indexes'];need(isinstance(indices,list) and len(indices)<=256 and len(indices)==len(set(indices)),'invalid lookup indexes')
                need(all(type(n) is int and 0<=n<=255 for n in indices),'lookup index outside u8')
                counts[k]+=len(indices)
        for k in counts:
            need(isinstance(loaded[k],list) and len(loaded[k])==counts[k],'incomplete historical loaded keys')
            for key in loaded[k]:pubkey(key)
        keys=static+loaded['writable']+loaded['readonly']
        need(len(keys)<=256 and len(set(keys))==len(keys),'duplicate/oversized full historical key list')
        result.update(historical_account_keys=keys,signers=static[:signed],fee_payer=static[0])
        for name in ('preBalances','postBalances'):
            need(isinstance(meta.get(name),list) and len(meta[name])==len(keys),'complete native balance metadata required')
            for v in meta[name]:natural(v)
        result['native_balances']={k:{'pre':str(meta['preBalances'][i]),'post':str(meta['postBalances'][i]),'delta':str(meta['postBalances'][i]-meta['preBalances'][i])} for i,k in enumerate(keys)}
        if meta['err'] is not None:
            result.update(execution_status='failed',execution_error=meta['err'])
            result['gaps'].append('failed_transaction_has_no_persisted_token_effects');return result
        # Successful execution is distinct from complete effect interpretation.
        result['execution_status']='succeeded'
        pre=token_balances(meta.get('preTokenBalances'),keys);post=token_balances(meta.get('postTokenBalances'),keys)
        balances={**pre,**post}
        for a in pre.keys()&post.keys():
            need(all(pre[a][k]==post[a][k] for k in ('mint','decimals','program')),'account reinitialization/mint metadata ambiguity')
        result.update(pre_token_balances=pre,post_token_balances=post)
        outer=message['instructions'];need(isinstance(outer,list) and len(outer)<=256,'bounded compiled instructions required')
        inner=meta.get('innerInstructions');need(isinstance(inner,list) and len(inner)<=len(outer),'inner instruction metadata missing')
        grouped={}
        for group in inner:
            n=group['index'];need(type(n) is int and 0<=n<len(outer) and n not in grouped,'invalid inner instruction group')
            need(isinstance(group['instructions'],list) and len(group['instructions'])<=256,'inner instruction cap exceeded')
            grouped[n]=group['instructions']
        need(len(outer)+sum(map(len,grouped.values()))<=1024,'instruction sample cap exceeded')
        writable=set(static[:signed-rs]+static[signed:len(static)-ru if ru else len(static)]+loaded['writable'])
        pending=[]
        for n,ix in enumerate(outer):
            for j,raw_ix in [(None,ix),*enumerate(grouped.get(n,[]))]:
                need(isinstance(raw_ix,dict) and 'parsed' not in raw_ix,'compiled historical instruction required')
                program=index(raw_ix['programIdIndex'],keys)
                ai=raw_ix['accounts'];need(isinstance(ai,list) and len(ai)<=256,'bounded instruction account indexes required')
                accounts=[index(i,keys) for i in ai];raw=data_bytes(raw_ix['data'])
                locator={'outer_index':n,'inner_index':j};ident=req['id']+'-ix-'+str(n)+('-inner-'+str(j) if j is not None else '')
                entry={'id':ident,'program':program,'accounts':accounts,'locator':locator,'stack_height':raw_ix.get('stackHeight'),
                       'data':raw_ix['data'],'recognized':False}
                result['instructions'].append(entry)
                effect=None
                try:
                    if program in (TOKEN_PROGRAM,TOKEN_2022):effect=token_effect(raw,accounts,balances,program)
                    elif program==SYSTEM and len(raw)>=4:
                        op=int.from_bytes(raw[:4],'little')
                        if op==2:
                            need(len(raw)==12 and len(accounts)==2,'invalid native transfer')
                            effect={'kind':'native_transfer','mint':None,'participants':{'source':accounts[0],'destination':accounts[1]},'amount_atomic':str(int.from_bytes(raw[4:12],'little'))}
                        elif op==0:
                            need(len(raw)==52 and len(accounts)==2,'invalid create-account instruction')
                            effect={'kind':'native_account_create','mint':None,'participants':{'source':accounts[0],'account':accounts[1]},
                                    'amount_atomic':str(int.from_bytes(raw[4:12],'little')),'space':str(int.from_bytes(raw[12:20],'little')),'owning_program':b58encode(raw[20:52])}
                    else:
                        swap=decode_swap(program,raw,accounts)
                        if swap:effect={'kind':'swap_instruction','mint':None,'participants':{},'amount_atomic':None,**swap}
                        else:effect=position_instruction(program,raw,accounts) or decode_pump(program,raw,accounts)
                    if effect:
                        if effect['kind'] in ('mint','burn','mint_initialize'):need(effect['mint'] in writable,'effect mint is readonly in historical message')
                        if effect['kind'] in ('launch_initialize','launch_migrate','pool_initialize'):
                            for role in ('mint','curve','pool'):
                                if role in effect['participants']:need(effect['participants'][role] in writable,'launch account is readonly')
                        if effect['kind'] in ('position_initialize','position_liquidity_remove'):
                            position=effect['participants'].get('position',effect['participants'].get('holding'))
                            need(position in writable,'position effect account is readonly')
                        if effect['kind'] in ('transfer','mint','burn','native_transfer','native_account_create','authority_change','freeze','thaw','token_account_close','sync_native','token_account_initialize'):
                            for role in ('source','destination','account'):
                                if role in effect['participants']:need(effect['participants'][role] in writable,'effect account is readonly in historical message')
                        effect.update(id=ident,program=program,locator=locator,transaction_evidence_id=req['id'],slot=tx['slot'])
                        pending.append(effect);entry['recognized']=True
                except ValueError as exc:
                    entry['gap']=str(exc);result['gaps'].append(ident+': '+str(exc))
        result['effects']=pending
        result['effect_coverage']='partial' if any(not i['recognized'] for i in result['instructions']) else 'all_returned_instructions'
    except (KeyError,TypeError,ValueError) as exc:
        result['effects']=[];result['gaps'].append(str(exc));result['effect_coverage']='unavailable'
    return result


def historical_owner(execution,address,mint):
    """Ownership at transaction boundaries, or exact in-transaction initialization."""
    effects=execution['effects']
    need(not any(e['kind']=='authority_change' and e['participants'].get('account')==address for e in effects), 'in-transaction ownership changes unresolved')
    pre=execution.get('pre_token_balances',{}).get(address)
    post=execution.get('post_token_balances',{}).get(address)
    owners={r['owner'] for r in (pre,post) if r and r['owner']}
    initialized=[e for e in effects if e['kind']=='token_account_initialize' and e['participants']['account']==address]
    need(len(initialized)<=1,'account reinitialization unresolved')
    need(not (pre and initialized),'account existed before initialization; historical reuse unresolved')
    for e in initialized:
        need(e['mint']==mint,'initialized account mint mismatch');owners.add(e['participants']['owner'])
    need(len(owners)==1 and all(r['mint']==mint for r in (pre,post) if r),'historical token ownership missing/conflicting')
    # A missing side is not automatically a zero balance.
    if pre is None:need(initialized,'opening token balance missing without verified initialization')
    if post is None:need(any(e['kind']=='token_account_close' and e['participants']['account']==address for e in effects),'closing token balance missing without verified closure')
    return next(iter(owners))


def _native_proceeds(execution,owner,output_account,gross):
    effects=execution['effects'];native=execution['native_balances'];fee=int(execution['network_fee_lamports']) if execution['fee_payer']==owner else 0
    closes=[e for e in effects if e['kind']=='token_account_close' and e['participants']['account']==output_account]
    need(len(closes)==1 and closes[0]['participants']['destination']==owner,'WSOL closure destination not reconciled to seller')
    need(owner in native and output_account in native,'seller/native account balances missing')
    need(native[output_account]['post']=='0','closed WSOL account retains lamports')
    initial=int(native[output_account]['pre'])
    funded=0;other_owner_delta=0;owner_funding=0
    for e in effects:
        p=e['participants']
        if e['kind']=='native_account_create':
            value=int(e['amount_atomic'])
            if p['account']==output_account:
                need(initial==0 and e['owning_program']==TOKEN_PROGRAM,'WSOL creation/reinitialization unresolved')
                funded+=value
                if p['source']==owner:owner_funding+=value
            elif p['source']==owner:other_owner_delta-=value
        if e['kind']=='native_transfer':
            value=int(e['amount_atomic'])
            need(output_account not in p.values(),'additional WSOL funding/sync flow unresolved')
            if p['source']==owner:other_owner_delta-=value
            if p['destination']==owner:other_owner_delta+=value
    refund=initial+funded
    expected=gross+refund-owner_funding+other_owner_delta-fee
    actual=int(native[owner]['delta'])
    need(actual==expected,'seller native delta does not reconcile swap/rent/fees/other transfers')
    return {'net_sale_after_seller_network_fee_lamports':str(gross-fee), 'seller_network_fee_lamports':str(fee),
            'gross_sale_lamports':str(gross), 'preexisting_and_funded_account_refund_lamports':str(refund),
            'seller_account_funding_lamports':str(owner_funding),'other_native_delta_lamports':str(other_owner_delta),
            'observed_seller_native_delta_lamports':str(actual),
            'scope':'reconciled sale component; refund includes rent/preexisting WSOL, not sale profit'}


def _verify_trades(target,candidates,*,buy=False):
    """At most two specific historical receipts; candidate pool labels cannot verify sales."""
    target=target_identity(target)
    need(isinstance(candidates,list) and len(candidates)<=2,'ordinary-sale sample capped at two')
    rows=[];seen=set()
    for candidate in candidates:
        execution=candidate['execution'];pool=pubkey(candidate['pool'])
        sig=signature(execution['signature']);need(sig not in seen,'duplicate sale receipt');seen.add(sig)
        row={'signature':sig,'pool':pool,'status':'unverified','seller':None,'input_atomic':None,'output_atomic':None,
             'counter_mint':None,'effect_ids':[],'native_proceeds':None,'profit':None,'gaps':[]}
        rows.append(row)
        try:
            need(execution['target']==target and execution['execution_status']=='succeeded' and execution['block_evidence_id'],'sale needs matching target and bound successful execution')
            swaps=[e for e in execution['effects'] if e['kind']=='swap_instruction']
            need(len(swaps)==1 and swaps[0]['pool']==pool and swaps[0]['locator']['inner_index'] is None,'ordinary sale requires one supported direct swap at exact pool; nested/multi-hop routes unresolved')
            swap=swaps[0];outer=swap['locator']['outer_index']
            transfers=[e for e in execution['effects'] if e['kind']=='transfer' and e['locator']['outer_index']==outer]
            need(len(transfers)==2,'swap token flow count ambiguous')
            inp=[e for e in transfers if e['participants']['source']==swap['input_account'] and e['participants']['destination'] in swap['vaults'] and (e['mint']!=target['mint'] if buy else e['mint']==target['mint'])]
            out=[e for e in transfers if e['participants']['destination']==swap['output_account'] and e['participants']['source'] in swap['vaults'] and (e['mint']==target['mint'] if buy else e['mint']!=target['mint'])]
            need(len(inp)==len(out)==1,'exact target input/counter-asset output not observed in swap')
            inp,out=inp[0],out[0]
            need(inp['locator']['inner_index'] is not None and out['locator']['inner_index'] is not None,'swap effects require actual inner instructions')
            need(inp['participants']['destination']!=out['participants']['source'],'same swap vault cannot supply both sides')
            need(not swap['mints'] or set(swap['mints'])=={inp['mint'],out['mint']},'swap role mint mismatch')
            # Token-2022 fee/hook effects need their full historical extension route.
            need(inp['program']==out['program']==TOKEN_PROGRAM,'Token-2022 historical fee/hook reconciliation unsupported')
            need(all(i['recognized'] for i in execution['instructions'] if i['program'] in (TOKEN_PROGRAM,TOKEN_2022) and i['locator']['outer_index']==outer),'unrecognized token effect inside swap')
            relevant={swap['input_account'],swap['output_account'],*swap['vaults']}
            for e in execution['effects']:
                if e['id'] in (inp['id'],out['id']):continue
                if e['kind'] in ('transfer','mint','burn','authority_change'):
                    need(not (set(e['participants'].values())&relevant),'unrelated balance/authority changes touch sale accounts')
            seller=historical_owner(execution,swap['input_account'],inp['mint'])
            recipient=historical_owner(execution,swap['output_account'],out['mint'])
            need(seller==recipient,'swap counter-asset recipient differs from observed source owner')
            for e in execution['effects']:
                if e['participants'].get('account')==swap['output_account']:
                    if e['kind']=='token_account_initialize':need(execution['effects'].index(e)<execution['effects'].index(out),'output account initialized after swap')
                    if e['kind']=='token_account_close':need(execution['effects'].index(e)>execution['effects'].index(out),'output account closed before swap')
            before=execution['pre_token_balances'];after=execution['post_token_balances']
            for e in (inp,out):
                for role,direction in (('source',-1),('destination',1)):
                    account=e['participants'][role]
                    if account in before and account in after:
                        need(int(after[account]['amount_atomic'])-int(before[account]['amount_atomic'])==direction*int(e['amount_atomic']),'instruction amount and historical token delta disagree')
                    else:
                        need(account==swap['output_account'] and out['mint']==WSOL,'missing transfer boundary balances')
                        historical_owner(execution,account,out['mint'])
            amount_in,amount_out=int(inp['amount_atomic']),int(out['amount_atomic'])
            need(amount_in>0 and amount_out>0,'sale amounts must be positive')
            specified,threshold=int(swap['specified_amount_atomic']),int(swap['threshold_atomic'])
            if swap['mode']=='exact_in':need(amount_in==specified and amount_out>=threshold,'swap exact-input/threshold contradiction')
            elif swap['mode']=='exact_out':need(amount_out==specified and amount_in<=threshold,'swap exact-output/threshold contradiction')
            elif swap['mode']=='exact_out_max_first':need(amount_out==threshold and amount_in<=specified,'swap maximum-input contradiction')
            else:need(False,'partial-fill ordinary-sale classification unsupported')
            row.update(status='verified_rebuy' if buy else 'verified_sale',seller=seller,input_atomic=str(amount_in),output_atomic=str(amount_out),counter_mint=inp['mint'] if buy else out['mint'],
                effect_ids=[swap['id'],inp['id'],out['id']],transaction_evidence_id=execution['transaction_evidence_id'],block_evidence_id=execution['block_evidence_id'],slot=execution['slot'],
                evidence_scope='one successful direct SPL swap with same-owner source/output and matched balance deltas; beneficial ownership/profit unknown')
            if out['mint']==WSOL and not buy:
                try:row['native_proceeds']=_native_proceeds(execution,seller,swap['output_account'],amount_out)
                except ValueError as exc:row['gaps'].append(str(exc))
        except (ValueError,KeyError,TypeError) as exc:row['gaps'].append(str(exc))
    return {'schema_version':1,'target':target,'requested_receipts':len(candidates),'maximum_receipts':2,
            'verified_receipts':sum(r['status'] in ('verified_sale','verified_rebuy') for r in rows),'receipts':rows,
            'indexed_activity_count':None,'scope':'bounded direct trade sample; indexed activity and observed restrictions remain independent'}


def verify_sales(target,candidates):return _verify_trades(target,candidates)


def verify_rebuys(target,candidates):
    result=_verify_trades(target,candidates,buy=True)
    for row in result['receipts']:row['buyer']=row.pop('seller')
    return result
