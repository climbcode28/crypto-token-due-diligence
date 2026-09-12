"""Exact size policies, scoped offline CPMM estimates and captured public quotes."""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from urllib.parse import urlencode
from solana_common import need,pubkey,target_identity,natural,TOKEN_PROGRAM
from solana_wire import amount
from solana_accounts import decode_mint
from solana_programs import observed_account
from solana_discovery import MAINNET,captured_json
from solana_session import label
from adapters import raydium_cpmm as cp
from adapters.base import Sample
from adapters.meteora_common import point,CLOCK

VERSION='1.0.0'


def decimal(value):
    need(type(value) in (str,int,Decimal) and len(str(value))<=128,'bounded decimal required')
    try:d=Decimal(value)
    except InvalidOperation as exc:raise ValueError('invalid decimal') from exc
    need(d.is_finite() and abs(d.as_tuple().exponent)<=256,'invalid decimal magnitude')
    return Fraction(d)


def size_policy(target,mint_packet,*,user_sizes=None,price=None,now=None):
    target=target_identity(target);value,meta=observed_account(target['mint'],mint_packet)
    need(value is not None and not meta['sliced'],'full mint observation required for quote units')
    decimals=decode_mint(value)['decimals'];scale=10**decimals
    evidence=list(meta['evidence']);gaps=[];values=[]
    if user_sizes is not None:
        need(isinstance(user_sizes,list) and 1<=len(user_sizes)<=3,'one to three explicit token-quantity sizes required')
        basis='user_token_quantities'
        for raw in user_sizes:
            number=decimal(raw)*scale
            need(number.denominator==1 and 0<number<2**64,'user quantity is unrepresentable in atomic token units')
            values.append({'input_atomic':str(number.numerator),'requested_token_quantity':str(raw)})
        if len(values)<3:
            basis='user_token_quantities_then_disclosed_probes'
            probes=[scale,10*scale,100*scale] if 100*scale<2**64 else [1,10,100]
            for units in probes:
                if len(values)==3:break
                if str(units) not in {v['input_atomic'] for v in values}:values.append({'input_atomic':str(units),'illustrative_probe':True})
    else:
        valid_price=False
        if price is not None:
            try:
                need(price['genesis_hash']==target['genesis_hash'] and price['price_denominator_mint']==target['mint'] and price.get('evidence') and not price.get('conflicts'),'price subject/conflicts unresolved')
                need(type(now) in (int,float) and type(price['captured_at']) in (int,float) and 0<=now-price['captured_at']<=300,'captured price is missing/stale')
                usd=decimal(price['price_usd']);need(usd>0,'positive USD price required')
                for e in price['evidence']:label(e)
                evidence+=price['evidence'];valid_price=True
            except (KeyError,ValueError,TypeError) as exc:gaps.append(str(exc))
        if valid_price:
            basis='illustrative_USD_equivalents_floor_to_atomic_units'
            for dollars in (100,1000,10000):
                quantity=Fraction(dollars*scale,1)/usd;units=quantity.numerator//quantity.denominator
                values.append({'input_atomic':str(units) if 0<units<2**64 else None,'illustrative_usd':str(dollars),
                               'gap':None if 0<units<2**64 else 'illustrative quantity outside atomic range'})
        else:
            basis='illustrative_token_quantity_probes'
            probes=[scale,10*scale,100*scale]
            if probes[-1]>=2**64:
                probes=[1,10,100];basis='illustrative_atomic_unit_probes_decimal_range'
            values=[{'input_atomic':str(v)} for v in probes]
    return {'schema_version':1,'target':target,'decimals':decimals,'basis':basis,'sizes':values,
            'evidence':sorted(set(evidence)),'gaps':gaps,'scope':'illustrative sizes; no user position or affordability inferred'}


def _ratio(f):return {'numerator':str(f.numerator),'denominator':str(f.denominator)}


def estimate(target,adapter_id,pool,observations,input_atomic,*,slippage_bps=50):
    target=target_identity(target);pubkey(pool);quantity=amount(input_atomic)
    need(0<quantity<2**64 and 0<=natural(slippage_bps)<=10000,'invalid quote amount/slippage')
    result={'schema_version':1,'kind':'modeled_quote','adapter':adapter_id,'target':target,'pool':pool,
        'input_mint':target['mint'],'input_atomic':input_atomic,'output_mint':None,'output_atomic':None,
        'minimum_output_atomic':None,'slippage_bps':slippage_bps,'fees':None,'route':[],'contexts':[],
        'evidence':[],'gaps':[],'status':'unknown','execution_observed':False}
    try:
        need(adapter_id=='raydium_cpmm','local quote capability unavailable: complete protocol fee/traversal semantics required; no vault approximation')
        pool_result=cp.analyze(target,pool,observations)
        state=pool_result['state'];fees=pool_result.get('fee_config')
        need(pool_result['reserves_atomic'] is not None and fees is not None,'verified reserves/fees required')
        need(all(p==TOKEN_PROGRAM for p in state['token_programs']),'local Token-2022 execution/transfer fees unsupported')
        need(all(v['state']=='initialized' for v in pool_result['vaults']),'frozen vault blocks local quote')
        need(not state['status_bits']&4,'pool swaps disabled')
        sample=Sample(target,pool,observations,cp.CAPABILITY)
        core=[pool,state['config'],*state['mints'],*state['vaults']]
        for address in core:sample.account(address)
        current=point(sample,core,1)
        need(current>=state['open_time'],'pool is not open at captured Clock')
        side=state['mints'].index(target['mint']);other=1-side
        x,y=[int(pool_result['reserves_atomic'][i]) for i in (side,other)]
        need(x>0 and y>0 and int(pool_result['vaults'][side]['amount_atomic'])+quantity<2**64,'reserve/amount overflow or empty pool')
        trade=int(fees['trade_rate']);creator=int(fees['creator_rate']) if state['creator_fee_enabled'] else 0;den=1000000
        on_input=state['creator_fee_on']==0 or state['creator_fee_on']==side+1
        rate=trade+creator if on_input else trade
        need(rate<den,'combined input fee consumes entire amount')
        need(not on_input or rate>0,'pinned CPMM input fee split has zero denominator')
        total_fee=(quantity*rate+den-1)//den
        creator_fee=(total_fee*creator//rate if rate else 0) if on_input else 0
        trade_fee=total_fee-creator_fee
        net_input=quantity-total_fee;need(net_input>0,'fees round input to zero')
        gross_output=net_input*y//(x+net_input)
        if not on_input:creator_fee=(gross_output*creator+den-1)//den
        output=gross_output if on_input else gross_output-creator_fee
        need(output>0,'output rounds to zero')
        spot=Fraction(quantity*y,x)
        result.update(status='modeled',output_mint=state['mints'][other],output_atomic=str(output),
            minimum_output_atomic=str(output*(10000-slippage_bps)//10000),
            fees={'trade_input_atomic':str(trade_fee),'creator_atomic':str(creator_fee),'creator_mint':state['mints'][side if on_input else other],
                  'protocol_input_atomic':str(trade_fee*int(fees['protocol_share'])//den),'fund_input_atomic':str(trade_fee*int(fees['fund_share'])//den),
                  'scope':'protocol/fund shares are included in trade fee, not additional charges; native fees excluded'},
            modeled_cost_output_units=_ratio(spot-output),price_impact_fraction=_ratio(1-Fraction(output,1)/spot),
            price_impact_definition='1 - modeled_output / pretrade_spot_output; includes swap fees, curve movement and rounding, excludes slippage threshold and native fees',
            route=[{'pool':pool,'program':cp.PROGRAM}],contexts=[{'address':a,**m} for a,m in sample.used.items()],
            evidence=sorted({e for m in sample.used.values() for e in m['evidence']}),
            limitations=['captured state only','no mempool, landing, account-owner or wallet-specific execution guarantee','program upgrades/control changes remain separate'])
    except (ValueError,KeyError,TypeError) as exc:result['gaps'].append(str(exc))
    return result


def quote_url(source,target,output_mint,input_atomic,*,slippage_bps=50):
    target=target_identity(target);pubkey(output_mint)
    need(target['genesis_hash']==MAINNET and output_mint!=target['mint'],'exact mainnet quote pair required')
    need(0<amount(input_atomic)<2**64 and 0<=natural(slippage_bps)<=10000,'invalid quote inputs')
    params={'inputMint':target['mint'],'outputMint':output_mint,'amount':input_atomic,'slippageBps':str(slippage_bps)}
    if source=='jupiter_v2':return 'https://api.jup.ag/swap/v2/order?'+urlencode(params)
    need(source=='raydium_quote','unsupported quote source')
    params['txVersion']='V0'
    return 'https://transaction-v1.raydium.io/compute/swap-base-in?'+urlencode(params)


def public_quote(source,target,record,raw,output_mint,input_atomic,*,slippage_bps=50):
    target=target_identity(target)
    url=quote_url(source,target,output_mint,input_atomic,slippage_bps=slippage_bps)
    body=captured_json(record,raw,expected_url=url);need(isinstance(body,dict),'quote object required')
    result={'schema_version':1,'kind':'api_quote','source':source,'target':target,'input_mint':target['mint'],
        'output_mint':output_mint,'input_atomic':input_atomic,'status':'quoted','route':[],'fees':[],
        'captured_at':record['captured_at'],'evidence':[record['id']],'context_slot':None,'gaps':[],
        'execution_observed':False,'scope':'read-only provider quote; route/depth/price remain provider claims, not on-chain execution'}
    if source=='jupiter_v2':
        need(body.get('transaction') in (None,''),'quote-only response unexpectedly contains transaction bytes')
        need(body.get('swapMode')=='ExactIn','unsupported Jupiter swap mode')
        quoted=body;in_key,out_key='inAmount','outAmount';plan=body.get('routePlan')
        if body.get('errorCode') is not None:
            result['status']='quote_with_execution_error';result['gaps'].append('provider reports execution error: '+str(body['errorCode']))
        result['provider_router']=body.get('router')
        impact=body.get('priceImpact')
        result['price_impact_fraction']=_ratio(decimal(impact)/100) if impact is not None else None
        result['price_impact_definition']='provider priceImpact percentage points / 100; provider reference-price methodology not independently established'
        if body.get('feeBps') is not None:
            need(0<=natural(body['feeBps'])<=10000,'invalid quote fee rate')
            result['fees'].append({'basis_points':body['feeBps'],'mint':pubkey(body['feeMint']),'scope':'provider total rate, do not add again to quoted output'})
    else:
        need(body.get('success') is True and body.get('version')=='V1','Raydium quote error/unsupported envelope')
        quoted=body.get('data');need(isinstance(quoted,dict) and quoted.get('swapType')=='BaseIn','unsupported Raydium quote mode')
        in_key,out_key='inputAmount','outputAmount';plan=quoted.get('routePlan')
        impact=quoted.get('priceImpactPct')
        result['provider_price_impact_raw']=str(impact) if impact is not None else None
        if impact is not None:decimal(impact)
        result['price_impact_fraction']=None
        result['price_impact_definition']='provider priceImpactPct retained verbatim; ratio/percentage convention not assumed across API versions'
    need(quoted.get('inputMint')==target['mint'] and quoted.get('outputMint')==output_mint and quoted.get(in_key)==input_atomic,'quote request/response asset or input mismatch')
    output=amount(quoted[out_key]);minimum=amount(quoted['otherAmountThreshold'])
    need(0<output<2**64 and 0<=minimum<=output and quoted.get('slippageBps')==slippage_bps,'quote output/threshold/slippage mismatch')
    need(isinstance(plan,list) and len(plan)<=12,'bounded route plan required')
    for leg in plan:
        need(isinstance(leg,dict),'invalid route leg')
        info=leg.get('swapInfo') if source=='jupiter_v2' else leg
        need(isinstance(info,dict),'invalid route leg')
        pool=pubkey(info['ammKey' if source=='jupiter_v2' else 'poolId'])
        leg_in,leg_out=pubkey(info['inputMint']),pubkey(info['outputMint']);need(leg_in!=leg_out,'route leg mints overlap')
        r={'pool':pool,'input_mint':leg_in,'output_mint':leg_out,'provider_label':info.get('label')}
        for name in ('inAmount','outAmount'):
            if name in info:need(0<amount(info[name])<2**64,'invalid route leg amount');r[name]=info[name]
        if 'feeAmount' in info:
            fee=amount(info['feeAmount']);need(fee<2**64,'invalid route fee amount')
            result['fees'].append({'pool':pool,'amount_atomic':str(fee),'mint':pubkey(info['feeMint']),'scope':'included provider route fee; not an extra deduction'})
        if source=='jupiter_v2':r.update(percent=leg.get('percent'),bps=leg.get('bps'))
        result['route'].append(r)
    # Every leg must lie on some directed path from the requested input to output.
    reachable={target['mint']};can_finish={output_mint}
    for _ in range(13):
        reachable|={r['output_mint'] for r in result['route'] if r['input_mint'] in reachable}
        can_finish|={r['input_mint'] for r in result['route'] if r['output_mint'] in can_finish}
    if plan:
        need(output_mint in reachable and all(r['input_mint'] in reachable and r['output_mint'] in can_finish for r in result['route']),'quote contains disconnected/wrong-asset route')
    else:result['gaps'].append('provider omitted underlying route; RFQ/route depth not established')
    slot=quoted.get('contextSlot',body.get('contextSlot'))
    if slot is not None:result['context_slot']=natural(slot)
    result.update(output_atomic=str(output),minimum_output_atomic=str(minimum),slippage_bps=slippage_bps,
                  provider_request_id=body.get('requestId',body.get('id')))
    return result
