"""Offline historical legacy/v0 effects. Raw keys and successful metadata are mandatory."""
from solana_common import need, natural, pubkey, signature, target_identity, ALPHABET, b58encode, TOKEN_PROGRAM, TOKEN_2022
from solana_wire import validate_response, amount
from solana_swaps import decode as decode_swap,position_instruction
from adapters.pump_instructions import decode as decode_pump
from adapters.pump_common import CURVE_PROGRAM

VERSION='1.4.0'
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
                if addr in balances and balances[addr]['decimals'] is not None:need(balances[addr]['decimals']==raw[9],'checked decimals mismatch')
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
                        elif op==3:
                            # CreateAccountWithSeed: base, seed string, lamports, space, owner; the common temporary-WSOL pattern.
                            seed_length=int.from_bytes(raw[36:44],'little');need(len(raw)==92+seed_length and seed_length<=32 and len(accounts) in (2,3),'invalid create-account-with-seed instruction')
                            effect={'kind':'native_account_create','mint':None,'participants':{'source':accounts[0],'account':accounts[1]},
                                    'amount_atomic':str(int.from_bytes(raw[44+seed_length:52+seed_length],'little')),'space':str(int.from_bytes(raw[52+seed_length:60+seed_length],'little')),
                                    'owning_program':b58encode(raw[60+seed_length:92+seed_length]),'seed_base':b58encode(raw[4:36]),'seed':raw[44:44+seed_length].decode('utf-8',errors='replace')}
                        elif op==8:
                            need(len(raw)==12 and len(accounts)==1,'invalid allocate instruction')
                            effect={'kind':'native_account_allocate','mint':None,'participants':{'account':accounts[0]},'amount_atomic':None,'space':str(int.from_bytes(raw[4:12],'little'))}
                        elif op==1:
                            need(len(raw)==36 and len(accounts)==1,'invalid assign instruction')
                            effect={'kind':'native_account_assign','mint':None,'participants':{'account':accounts[0]},'amount_atomic':None,'owning_program':b58encode(raw[4:36])}
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
                        if effect['kind'] in ('transfer','mint','burn','native_transfer','native_account_create','native_account_allocate','native_account_assign','authority_change','freeze','thaw','token_account_close','sync_native','token_account_initialize'):
                            for role in ('source','destination','account'):
                                if role in effect['participants']:need(effect['participants'][role] in writable,'effect account is readonly in historical message')
                        effect.update(id=ident,program=program,locator=locator,stack_height=raw_ix.get('stackHeight'),transaction_evidence_id=req['id'],slot=tx['slot'])
                        if effect['kind']=='token_account_initialize' and effect['participants']['account'] not in balances:
                            # A temporary account opened in this transaction has no boundary balance; its initialization names
                            # the mint, so a later unchecked transfer from it (a legacy `transfer`) still resolves.
                            balances[effect['participants']['account']]={'mint':effect['mint'],'owner':effect['participants']['owner'],'program':program,'decimals':None,'amount_atomic':None}
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


def _frame(execution,swap):
    """Instruction IDs inside the swap's CPI frame and its direct children (one level deeper).

    An outer swap owns every inner instruction of its group. A nested swap (a router or
    aggregator CPI) owns the instructions after it until the first one at or above its own
    stack height; without recorded heights a nested frame cannot be bounded.
    """
    outer=swap['locator']['outer_index'];group=[i for i in execution['instructions'] if i['locator']['outer_index']==outer and i['locator']['inner_index'] is not None]
    if swap['locator']['inner_index'] is None:
        frame=group;height=swap.get('stack_height') or 1
    else:
        height=swap.get('stack_height');need(height is not None,'nested route without recorded stack heights unresolved')
        frame=[]
        for i in group:
            if i['locator']['inner_index']<=swap['locator']['inner_index']:continue
            need(i.get('stack_height') is not None,'nested route without recorded stack heights unresolved')
            if i['stack_height']<=height:break
            frame.append(i)
    direct={i['id'] for i in frame if i.get('stack_height') is None or i['stack_height']==height+1}
    return {i['id'] for i in frame},direct


MAX_TRADE_RECEIPTS=10  # start's two automatic receipts plus up to four per pool_activity preset, two presets at most


def _verify_trades(target,candidates,*,buy=False):
    """At most MAX_TRADE_RECEIPTS specific historical receipts; candidate pool labels cannot verify sales."""
    target=target_identity(target)
    need(isinstance(candidates,list) and len(candidates)<=MAX_TRADE_RECEIPTS,'ordinary-sale sample capped at '+str(MAX_TRADE_RECEIPTS)+' receipts')
    rows=[];seen=set()
    for candidate in candidates:
        execution=candidate['execution'];pool=pubkey(candidate['pool'])
        sig=signature(execution['signature'])
        if sig in seen:
            rows.append({'signature':sig,'pool':pool,'status':'unverified','gaps':['duplicate receipt: the same signature was supplied twice']});continue
        seen.add(sig)
        row={'signature':sig,'pool':pool,'status':'unverified','seller':None,'spending_owner':None,'custody':None,'input_atomic':None,'output_atomic':None,
             'counter_mint':None,'effect_ids':[],'native_proceeds':None,'profit':None,'route':None,'protocol_fees_atomic':None,
             'counter_asset_realization':None,'gaps':[]}
        rows.append(row)
        try:
            need(execution['target']==target and execution['execution_status']=='succeeded' and execution['block_evidence_id'],'sale needs matching target and bound successful execution')
            effects=execution['effects'];all_swaps=[e for e in effects if e['kind']=='swap_instruction']
            swaps=[e for e in all_swaps if e['pool']==pool]
            trades=[e for e in effects if e['kind']=='protocol_trade_instruction' and e.get('curve')==pool]
            if not swaps and len(trades)==1:
                if trades[0].get('quote_native'):_verify_native_curve_trade(target,execution,trades[0],buy,row,all_swaps);continue
                swap=_curve_leg(trades[0]);all_swaps=all_swaps+[swap];swaps=[swap]  # a token-quote curve trade is an ordinary leg
            need(len(swaps)==1,'ordinary sale requires exactly one supported swap at the exact pool')
            swap=swaps[0];frame,direct=_frame(execution,swap)
            route='direct' if swap['locator']['inner_index'] is None and len(all_swaps)==1 else 'aggregated'
            transfers=[e for e in effects if e['kind']=='transfer' and e['id'] in direct]
            inp=[e for e in transfers if e['participants']['source']==swap['input_account'] and e['participants']['destination'] in swap['vaults'] and (e['mint']!=target['mint'] if buy else e['mint']==target['mint'])]
            out=[e for e in transfers if e['participants']['destination']==swap['output_account'] and e['participants']['source'] in swap['vaults'] and (e['mint']==target['mint'] if buy else e['mint']!=target['mint'])]
            need(len(inp)==len(out)==1,'exact target input/counter-asset output not observed in swap')
            inp,out=inp[0],out[0]
            sinks=set(swap.get('fee_accounts') or [])
            # Protocol/creator fees leave the same vault (sells) or the trader's input account (buys)
            # only to the adapter-declared sinks; any other flow keeps the receipt ambiguous.
            fees=[e for e in transfers if e['id'] not in (inp['id'],out['id']) and e['participants']['destination'] in sinks and e['participants']['source'] in (*swap['vaults'],swap['input_account'])]
            need(not any(e['participants'].get('destination') in swap.get('rebate_accounts',[]) for e in transfers),'trader cashback rebate makes net proceeds ambiguous')
            need(len(transfers)==2+len(fees),'swap token flow count ambiguous')
            need(inp['participants']['destination']!=out['participants']['source'],'same swap vault cannot supply both sides')
            need(not swap['mints'] or set(swap['mints'])=={inp['mint'],out['mint']},'swap role mint mismatch')
            before=execution['pre_token_balances'];after=execution['post_token_balances']
            for e in (inp,out):
                need(e['program'] in (TOKEN_PROGRAM,TOKEN_2022),'unsupported token program in swap leg')
                if e['program']==TOKEN_2022:
                    # Accepted only when both boundary balances equal the checked amount: a withheld
                    # transfer fee or a hook-driven movement would break that equality or add a flow.
                    need(e['decimals'] is not None and all(e['participants'][r] in before and e['participants'][r] in after for r in ('source','destination')),'Token-2022 leg needs transfer_checked with both boundary balances to exclude fee/hook effects')
            need(all(i['recognized'] for i in execution['instructions'] if i['program'] in (TOKEN_PROGRAM,TOKEN_2022) and i['id'] in frame),'unrecognized token effect inside swap')
            relevant={swap['input_account'],swap['output_account'],*swap['vaults']}
            other_vaults={v for x in all_swaps if x['id']!=swap['id'] for v in x['vaults']}
            # Router custody: the leg's input account may be filled by exactly one transfer from a non-vault account before
            # the leg (the wallet's tokens entering the router) and its output account drained by exactly one transfer to a
            # non-vault account after it (proceeds leaving to the wallet), each at the leg's exact amount. Each side is
            # otherwise a hop between decoded swap vaults; the wallet behind a custody side is the beneficial trader and
            # the router authority only the spending owner. Anything else touching the leg's accounts refuses it below.
            all_vaults={v for x in all_swaps for v in x['vaults']}
            custody_in=[e for e in effects if e['kind']=='transfer' and e['id']!=inp['id'] and e['mint']==inp['mint'] and e['participants'].get('destination')==swap['input_account']
                and e['participants'].get('source') not in all_vaults and effects.index(e)<effects.index(inp) and e['amount_atomic']==inp['amount_atomic']]
            custody_out=[e for e in effects if e['kind']=='transfer' and e['id']!=out['id'] and e['mint']==out['mint'] and e['participants'].get('source')==swap['output_account']
                and e['participants'].get('destination') not in all_vaults and effects.index(e)>effects.index(out) and e['amount_atomic']==out['amount_atomic']]
            fed=custody_in[0] if len(custody_in)==1 else None;drained=custody_out[0] if len(custody_out)==1 else None
            custody_ids={e['id'] for e in (fed,drained) if e}
            hops=set()
            for e in effects:
                if e['id'] in (inp['id'],out['id'],*[f['id'] for f in fees]) or e['id'] in custody_ids:continue
                if e['kind'] in ('transfer','mint','burn','authority_change') and set(e['participants'].values())&relevant:
                    p=e['participants']
                    # In an aggregated route the leg's counter-asset may feed the next hop, or the
                    # leg's input may come from the previous hop; those exact hops are the only tolerated touches.
                    onward=e['kind']=='transfer' and route=='aggregated' and p.get('source')==swap['output_account'] and p.get('destination') in other_vaults and effects.index(e)>effects.index(out)
                    inbound=e['kind']=='transfer' and route=='aggregated' and p.get('destination')==swap['input_account'] and p.get('source') in other_vaults and effects.index(e)<effects.index(inp)
                    # A hop back into the leg's input account after the leg is a round trip, not a sale.
                    need(onward or inbound,'unrelated balance/authority changes touch sale accounts')
                    hops.add(swap['output_account'] if onward else swap['input_account'])
            seller=historical_owner(execution,swap['input_account'],inp['mint'])
            recipient=historical_owner(execution,swap['output_account'],out['mint'])
            need(seller==recipient,'swap counter-asset recipient differs from observed source owner')
            beneficial,spending=seller,None;custody=bool(fed or drained)
            if custody:
                # A custody side pairs with a custody or hop side opposite it; a router that keeps the proceeds or sells
                # its own inventory to a wallet is not a wallet's sale.
                need(fed or swap['input_account'] in hops,'router custody output without a wallet or hop input')
                need(drained or swap['output_account'] in hops,'router custody input without a wallet or hop output')
                if seller in execution['signers']:
                    # The trader owns and signed for the leg's own accounts; a same-amount transfer that funds the input
                    # or forwards the output is a router serving the trader, not a change of beneficial owner. The
                    # funding/forwarding accounts are recorded under `custody`; the trader stays the seller.
                    beneficial,spending=seller,None
                else:
                    # The leg's own accounts are owned by a router, not the trader: the beneficial wallet is the far end
                    # of the custody transfer, inferred through one more hop than a plain leg's owner, so it must have
                    # signed this transaction; a program-owned account or another router layer is not a wallet's sale.
                    wallets={historical_owner(execution,fed['participants']['source'],inp['mint']) if fed else None,historical_owner(execution,drained['participants']['destination'],out['mint']) if drained else None}-{None}
                    need(len(wallets)==1 and seller not in wallets,'router custody flows do not belong to one distinct wallet')
                    beneficial,spending=wallets.pop(),seller
                    need(beneficial in execution['signers'],'router custody wallet did not sign the transaction')
            for e in effects:
                if e['participants'].get('account')==swap['output_account']:
                    if e['kind']=='token_account_initialize':need(effects.index(e)<effects.index(out),'output account initialized after swap')
                    if e['kind']=='token_account_close':need(effects.index(e)>effects.index(out),'output account closed before swap')
            # A wrapped-SOL input account the trader funds in this transaction (a system transfer, then sync_native,
            # both before the leg) legitimately moves by the wrap minus the leg; funding by anyone else before the sync
            # stays ambiguous, and a later, unsynced lamport transfer cannot have funded the leg.
            wrap=0
            if inp['mint']==WSOL:
                synced=[e for e in effects if e['kind']=='sync_native' and e['participants'].get('account')==swap['input_account'] and effects.index(e)<effects.index(inp)]
                funding=[e for e in effects if synced and e['kind']=='native_transfer' and e['participants'].get('destination')==swap['input_account'] and effects.index(e)<effects.index(synced[-1])]
                if funding and all(e['participants'].get('source')==seller for e in funding):wrap=sum(int(e['amount_atomic']) for e in funding)
            # Every account the leg touches must move by exactly the net of the leg's own flows
            # (trade legs plus declared fee flows); a vault paying a fee moves by output plus fee.
            expected={swap['input_account']:wrap} if wrap else {}
            if fed:expected[swap['input_account']]=expected.get(swap['input_account'],0)+int(fed['amount_atomic'])
            if drained:expected[swap['output_account']]=expected.get(swap['output_account'],0)-int(drained['amount_atomic'])
            for e in (inp,out,*fees):
                expected[e['participants']['source']]=expected.get(e['participants']['source'],0)-int(e['amount_atomic'])
                expected[e['participants']['destination']]=expected.get(e['participants']['destination'],0)+int(e['amount_atomic'])
            for account,delta in expected.items():
                if account in hops:continue  # Realized by another hop; the vault side pins the leg amount.
                if account in before and account in after:
                    need(int(after[account]['amount_atomic'])-int(before[account]['amount_atomic'])==delta,'instruction amount and historical token delta disagree')
                else:
                    # A trader account created or closed in this transaction has one boundary
                    # only; verified initialization/closure plus the vault delta pin the amount.
                    need(account in (swap['input_account'],swap['output_account']),'missing vault boundary balance')
                    historical_owner(execution,account,inp['mint'] if account==swap['input_account'] else out['mint'])
            amount_in,amount_out=int(inp['amount_atomic']),int(out['amount_atomic'])
            need(amount_in>0 and amount_out>0,'sale amounts must be positive')
            specified,threshold=int(swap['specified_amount_atomic']),int(swap['threshold_atomic'])
            if swap['mode']=='exact_in':need(amount_in==specified and amount_out>=threshold,'swap exact-input/threshold contradiction')
            elif swap['mode']=='exact_out':need(amount_out==specified and amount_in<=threshold,'swap exact-output/threshold contradiction')
            elif swap['mode']=='exact_out_max_first':need(amount_out==threshold and amount_in<=specified,'swap maximum-input contradiction')
            elif swap['mode']=='exact_in_fee_inclusive':
                # The specified amount is spent fees inclusive: the leg plus the fees drawn from the input account.
                paid=amount_in+sum(int(f['amount_atomic']) for f in fees if f['participants']['source']==swap['input_account'])
                need(paid==specified and amount_out>=threshold,'swap spendable-input/threshold contradiction')
            else:need(False,'partial-fill ordinary-sale classification unsupported')
            converted=swap['output_account'] in hops
            row.update(status='verified_rebuy' if buy else 'verified_sale',seller=beneficial,spending_owner=spending,input_atomic=str(amount_in),output_atomic=str(amount_out),counter_mint=inp['mint'] if buy else out['mint'],
                custody={'router_authority':spending,'input_source':fed['participants']['source'] if fed else None,'output_destination':drained['participants']['destination'] if drained else None,
                    'effect_ids':[e['id'] for e in (fed,drained) if e]} if custody else None,
                effect_ids=[swap['id'],inp['id'],out['id'],*[f['id'] for f in fees]],transaction_evidence_id=execution['transaction_evidence_id'],block_evidence_id=execution['block_evidence_id'],slot=execution['slot'],
                route=route,protocol_fees_atomic=[{'effect_id':f['id'],'mint':f['mint'],'amount_atomic':f['amount_atomic'],'destination':f['participants']['destination']} for f in fees],
                counter_asset_realization='converted_within_route' if converted else 'forwarded_to_beneficial_owner' if drained else 'retained_in_recipient_account',
                token_programs=sorted({inp['program'],out['program']}),
                evidence_scope='one successful supported swap leg at the exact pool with same-owner source/output and matched vault deltas; beneficial ownership/profit unknown')
            if out['mint']==WSOL and not buy and not converted:
                # Through custody the wallet's own WSOL account receives and closes the proceeds; otherwise the leg's output account does.
                try:row['native_proceeds']=_native_proceeds(execution,beneficial,drained['participants']['destination'] if drained else swap['output_account'],amount_out)
                except ValueError as exc:row['gaps'].append(str(exc))
        except (ValueError,KeyError,TypeError) as exc:row['gaps'].append(str(exc))
    return {'schema_version':1,'target':target,'requested_receipts':len(candidates),'maximum_receipts':MAX_TRADE_RECEIPTS,
            'verified_receipts':sum(r['status'] in ('verified_sale','verified_rebuy') for r in rows),'receipts':rows,
            'indexed_activity_count':None,'scope':'bounded trade sample; indexed activity and observed restrictions remain independent'}


def classify_receipt(target,packet,pool):
    """Cheap pre-spend classification without a header: does the receipt contain a supported swap at
    the exact pool, and does the target mint enter (sell) or leave (buy) the trader account? Never a sale claim."""
    target=target_identity(target);pool=pubkey(pool)
    result={'signature':packet['request']['params'][0] if packet.get('request') else None,'pool':pool,'swap':False,'direction':None,'route':None,'reason':None}
    try:
        need(packet.get('status')=='ok','receipt unavailable: '+str(packet.get('status')))
        checked=validate_response(packet['request'],packet['response']);need(checked['status']=='ok','receipt '+checked['status'])
        tx=checked['result'];meta=tx['meta'];need(isinstance(meta,dict) and meta.get('err') is None,'failed transaction')
        message=tx['transaction']['message'];loaded=meta.get('loadedAddresses') or {'writable':[],'readonly':[]}
        keys=list(message['accountKeys'])+list(loaded.get('writable',[]))+list(loaded.get('readonly',[]))
        mints={}
        for r in (meta.get('preTokenBalances') or [])+(meta.get('postTokenBalances') or []):mints[index(r['accountIndex'],keys)]=pubkey(r['mint'])
        inner={g['index']:g['instructions'] for g in meta.get('innerInstructions') or []}
        for n,ix in enumerate(message['instructions']):
            for j,raw_ix in [(None,ix),*enumerate(inner.get(n,[]))]:
                program=index(raw_ix['programIdIndex'],keys);accounts=[index(i,keys) for i in raw_ix['accounts']]
                try:swap=decode_swap(program,data_bytes(raw_ix['data']),accounts)
                except ValueError:swap=None
                if not swap and program==CURVE_PROGRAM:
                    # A curve trade is a supported swap at the curve: its quote may be native SOL, verified separately.
                    try:trade=decode_pump(program,data_bytes(raw_ix['data']),accounts)
                    except ValueError:trade=None
                    if trade and trade['kind']=='protocol_trade_instruction' and trade['curve']==pool:
                        result.update(swap=True,route='direct' if j is None else 'aggregated',direction='sell' if trade['direction']=='sell_base' else 'buy');return result
                if not swap or swap['pool']!=pool:continue
                source_mint=mints.get(swap['input_account']);dest_mint=mints.get(swap['output_account'])
                result.update(swap=True,route='direct' if j is None else 'aggregated',
                    direction='sell' if source_mint==target['mint'] else 'buy' if dest_mint==target['mint'] else None)
                return result
        result['reason']='no supported swap at the exact pool'
    except (ValueError,KeyError,TypeError) as exc:result['reason']=str(exc) if isinstance(exc,ValueError) else 'malformed receipt'
    return result


def _curve_leg(trade):
    """A v2 Pump curve trade with a token quote as a pool leg: the curve's base and quote holdings are its vaults, the
    protocol, buyback and creator quote accounts its fee sinks and the user's volume-accumulator account a rebate."""
    p=trade['participants'];sell=trade['direction']=='sell_base'
    return {'kind':'swap_instruction','adapter':'pump_curve','id':trade['id'],'locator':trade['locator'],'stack_height':trade.get('stack_height'),'pool':trade['curve'],
        'input_account':p['base_account'] if sell else p['quote_account'],'output_account':p['quote_account'] if sell else p['base_account'],'trader':p['user'],
        'vaults':[p['curve_holding'],p['quote_holding']],'mints':[trade['mint'],trade['quote_mint']],'mode':trade['mode'],
        'specified_amount_atomic':trade['specified_atomic'],'threshold_atomic':trade['threshold_atomic'],
        'fee_accounts':[p['quote_fee_account'],p['quote_buyback_account'],p['quote_creator_account']],'rebate_accounts':[p['rebate']]}


def _closed_refund(execution,account):
    """Lamports a closed token account returned: its opening lamports plus every native and wrapped-SOL inflow minus
    every outflow, which the closure sends to its destination."""
    native=execution['native_balances'];need(account in native and native[account]['post']=='0','closed account balances missing or not emptied')
    total=int(native[account]['pre'])
    for e in execution['effects']:
        p=e['participants'];amount=int(e['amount_atomic']) if e.get('amount_atomic') else 0
        if e['kind']=='native_account_create' and p.get('account')==account:total+=amount
        if e['kind']=='native_transfer':total+=amount*((p.get('destination')==account)-(p.get('source')==account))
        if e['kind']=='transfer' and e.get('mint')==WSOL:total+=amount*((p.get('destination')==account)-(p.get('source')==account))
    need(total>=0,'closed account lamport reconstruction negative');return total


def _verify_native_curve_trade(target,execution,trade,buy,row,other_swaps=()):
    """A Pump curve trade with a SOL quote pays or receives lamports through program-internal moves, so the quote leg is
    reconciled from the lamport balance deltas of the curve, the fee recipients and the trader (with the trader's own
    explicit native flows netted out); the base leg is one SPL transfer between the trader's account and the curve
    holding, reconciled against both accounts' historical balances."""
    p=trade['participants'];sell=trade['direction']=='sell_base';mint=target['mint'];user=p['user'];curve=trade['curve']
    need(sell!=buy,'curve trade direction does not match the requested verification')
    frame,direct=_frame(execution,trade);effects=execution['effects']
    legs=[e for e in effects if e['kind']=='transfer' and e['id'] in direct and e['mint']==mint and
        ((e['participants']['source'],e['participants']['destination'])==((p['base_account'],p['curve_holding']) if sell else (p['curve_holding'],p['base_account'])))]
    need(len(legs)==1,'exact curve base leg not observed');leg=legs[0];amount=int(leg['amount_atomic'])
    need(len([e for e in effects if e['kind']=='transfer' and e['id'] in direct])==1,'curve trade token flow count ambiguous')
    need(leg['program'] in (TOKEN_PROGRAM,TOKEN_2022),'unsupported token program in curve leg');need(amount>0,'curve base amount absent')
    need(trade['mode']=='exact_in_fee_inclusive' or amount==int(trade['specified_atomic']),'curve base amount and instruction disagree')
    need(historical_owner(execution,p['base_account'],mint)==user,'curve trade base account is not the user\'s')
    before=execution['pre_token_balances'];after=execution['post_token_balances']
    for account,sign in ((leg['participants']['source'],-1),(leg['participants']['destination'],1)):
        if account in before and account in after:need(int(after[account]['amount_atomic'])-int(before[account]['amount_atomic'])==sign*amount,'curve base amount and historical token delta disagree')
        else:need(account==p['base_account'],'missing curve holding boundary balance')  # the trader's account may be created or closed in this transaction; the holding's delta pins the amount
    native=execution['native_balances'];threshold=int(trade['threshold_atomic'])
    need(all(x in native for x in (user,curve,p['fee_recipient'])),'curve trade native balances missing')
    delta=lambda addr:int(native[addr]['delta']) if addr in native else 0
    fee=int(execution['network_fee_lamports']) if execution['fee_payer']==user else 0
    other=0  # the trader's explicit native flows outside the trade frame: rent for accounts they create, tips, wraps and closures
    for e in effects:
        q=e['participants']
        if e['kind']=='native_account_create' and q.get('source')==user:other-=int(e['amount_atomic'])
        if e['kind']=='native_transfer' and e['id'] not in direct:
            if q.get('source')==user:other-=int(e['amount_atomic'])
            if q.get('destination')==user:other+=int(e['amount_atomic'])
        if e['kind']=='token_account_close' and q.get('destination')==user:other+=_closed_refund(execution,q['account'])
    sinks={x for x in (p['fee_recipient'],p.get('buyback'),p.get('creator_vault')) if x};creator_vault=p.get('creator_vault')
    other_swaps=[x for x in other_swaps if x['id']!=trade['id']]
    route='direct' if trade['locator']['inner_index'] is None and not other_swaps else 'aggregated'
    if sell:
        need(not [e for e in effects if e['kind']=='native_transfer' and e['id'] in direct],'explicit native transfers inside a curve sale are unexpected')
        paid={sink:delta(sink) for sink in sinks};need(all(v>=0 for v in paid.values()) and delta(curve)<0,'curve sale lamport flows do not reconcile');gross=-delta(curve)-sum(paid.values())
        need(gross>0 and gross>=threshold,'curve sale proceeds below the instruction minimum or absent')
        residual=delta(user)-(gross-fee+other)
        need(residual==0,'seller native delta does not reconcile curve proceeds, fees and other flows (residual '+str(residual)+' lamports; a trader cashback rebate or another program-internal lamport move is not itemized)')
        # Proceeds the trader wrapped after the trade and fed into another decoded leg were converted within the route,
        # not kept as lamports; the wallet's own lamport gain is still reconciled above.
        wsol_accounts={acc for table in (before,after) for acc,rec in table.items() if rec.get('mint')==WSOL}|{e['participants']['account'] for e in effects if e['kind']=='token_account_initialize' and e.get('mint')==WSOL}
        rewrapped={e['participants']['destination'] for e in effects if e['kind']=='native_transfer' and e['id'] not in direct and e['participants'].get('source')==user
            and e['participants'].get('destination') in wsol_accounts and effects.index(e)>effects.index(leg)}
        converted=any(x['input_account'] in rewrapped for x in other_swaps)
        fees=[{'effect_id':None,'mint':None,'amount_atomic':str(paid[sink]),'destination':sink} for sink in (p['fee_recipient'],p.get('buyback'),creator_vault) if sink]
        row.update(status='verified_sale',seller=user,input_atomic=str(amount),output_atomic=str(gross),counter_mint=None,quote='native_sol',
            effect_ids=[trade['id'],leg['id']],transaction_evidence_id=execution['transaction_evidence_id'],block_evidence_id=execution['block_evidence_id'],slot=execution['slot'],
            route=route,protocol_fees_atomic=fees,counter_asset_realization='converted_within_route' if converted else 'native_lamports_to_wallet',token_programs=[leg['program']],
            native_proceeds={'net_sale_after_seller_network_fee_lamports':str(gross-fee),'seller_network_fee_lamports':str(fee),'gross_sale_lamports':str(gross),
                'other_native_delta_lamports':str(other),'observed_seller_native_delta_lamports':str(delta(user)),
                'scope':'reconciled curve sale; protocol and creator fees left the curve to their recipients'+('; the trader re-wrapped proceeds into a later leg of this route' if converted else '')},
            evidence_scope='one Pump curve sale with native quote reconciled from lamport balance deltas; beneficial ownership/profit unknown')
    else:
        need(trade['mode']!='exact_in_fee_inclusive','exact-quote-in curve buy with a native quote is not yet supported')
        pays=[e for e in effects if e['kind']=='native_transfer' and e['id'] in direct and e['participants']['source']==user]
        need(pays and all(e['participants']['destination'] in sinks|{curve} for e in pays),'curve buy native flows leave the trade accounts')
        paid=lambda to:sum(int(e['amount_atomic']) for e in pays if e['participants']['destination']==to)
        quote=paid(curve);charges=sum(paid(sink) for sink in sinks)
        need(quote>0 and quote+charges<=threshold,'curve buy cost above the instruction maximum or absent')
        need(delta(curve)==quote,'curve lamport delta does not match the buy payment')
        residual=delta(user)-(-(quote+charges)-fee+other)
        need(residual==0,'buyer native delta does not reconcile curve payment, fees and other flows (residual '+str(residual)+' lamports; a trader cashback rebate or another program-internal lamport move is not itemized)')
        fees=[{'effect_id':e['id'],'mint':None,'amount_atomic':e['amount_atomic'],'destination':e['participants']['destination']} for e in pays if e['participants']['destination']!=curve]
        row.update(status='verified_rebuy',seller=user,input_atomic=str(quote),output_atomic=str(amount),counter_mint=None,quote='native_sol',
            effect_ids=[trade['id'],leg['id'],*[e['id'] for e in pays]],transaction_evidence_id=execution['transaction_evidence_id'],block_evidence_id=execution['block_evidence_id'],slot=execution['slot'],
            route=route,protocol_fees_atomic=fees,counter_asset_realization='retained_in_recipient_account',token_programs=[leg['program']],
            evidence_scope='one Pump curve buy with native quote reconciled from explicit lamport transfers; beneficial ownership/profit unknown')


def verify_sales(target,candidates):return _verify_trades(target,candidates)


def verify_rebuys(target,candidates):
    result=_verify_trades(target,candidates,buy=True)
    for row in result['receipts']:row['buyer']=row.pop('seller',None)  # a duplicate-signature row carries only its gap
    return result
