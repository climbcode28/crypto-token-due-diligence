"""Synthetic historical execution with explicit independently specified balance deltas."""
import struct
from pool_fixture import key
from solana_fixture import request,response
from solana_common import b58encode,base58_bytes,TOKEN_PROGRAM
from solana_discovery import MAINNET
from solana_transactions import WSOL,SYSTEM
from solana_swaps import tag
from adapters import raydium_cpmm as cp


def fixture(version='legacy',wsol=False,closed=False,created=False,tip=0):
    a={'payer':key(9),'owner':key(10),'pool':key(11),'authority':key(12),'config':key(13),
       'source':key(14),'destination':key(15),'input_vault':key(16),'output_vault':key(17),
       'input_mint':key(2),'output_mint':WSOL if wsol else key(3),'oracle':key(18),'tip':key(19)}
    swapkeys=[a[k] for k in ('owner','authority','config','pool','source','destination','input_vault','output_vault')]
    swapkeys += [TOKEN_PROGRAM,TOKEN_PROGRAM,a['input_mint'],a['output_mint'],a['oracle']]
    allkeys=list(dict.fromkeys([a['payer'],a['owner'],*swapkeys,cp.PROGRAM,SYSTEM,a['tip']]))
    loaded=[a['input_vault'],a['output_vault'],a['authority']] if version==0 else []
    keys=[k for k in allkeys if k not in loaded]+loaded
    def ix(program,accounts,data,stack=None):
        out={'programIdIndex':keys.index(program),'accounts':[keys.index(k) for k in accounts],'data':b58encode(data)}
        if stack is not None:out['stackHeight']=stack
        return out
    outer=[]
    if created:
        outer.append(ix(SYSTEM,[a['owner'],a['destination']],struct.pack('<IQQ',0,2039280,165)+base58_bytes(TOKEN_PROGRAM,32)))
        outer.append(ix(TOKEN_PROGRAM,[a['destination'],a['output_mint']],bytes([18])+base58_bytes(a['owner'],32)))
    n=len(outer);outer.append(ix(cp.PROGRAM,swapkeys,tag('swap_base_input')+struct.pack('<QQ',1000,400)))
    inner=[ix(TOKEN_PROGRAM,[a['source'],a['input_mint'],a['input_vault'],a['owner']],struct.pack('<BQB',12,1000,6),2),
           ix(TOKEN_PROGRAM,[a['output_vault'],a['output_mint'],a['destination'],a['authority']],struct.pack('<BQB',12,500,9 if wsol else 6),2)]
    if closed:outer.append(ix(TOKEN_PROGRAM,[a['destination'],a['owner'],a['owner']],b'\11'))
    if tip:outer.append(ix(SYSTEM,[a['owner'],a['tip']],struct.pack('<IQ',2,tip)))
    before={a['source']:10000,a['destination']:0,a['input_vault']:20000,a['output_vault']:30000}
    after={a['source']:9000,a['destination']:500,a['input_vault']:21000,a['output_vault']:29500}
    def balances(values,is_post):
        rows=[]
        for address,value in values.items():
            if address==a['destination'] and (created or (closed and is_post)):continue
            is_input=address in (a['source'],a['input_vault']);mint=a['input_mint'] if is_input else a['output_mint']
            rows.append({'accountIndex':keys.index(address),'mint':mint,'owner':a['owner'] if address in (a['source'],a['destination']) else a['authority'],
                         'programId':TOKEN_PROGRAM,'uiTokenAmount':{'amount':str(value),'decimals':9 if mint==WSOL else 6}})
        return rows
    pre=[2039280]*len(keys);post=pre.copy();pre[keys.index(a['owner'])]=10000000;post[keys.index(a['owner'])]=10000000
    post[keys.index(a['payer'])]-=5000
    if wsol:
        if created:pre[keys.index(a['destination'])]=0;post[keys.index(a['destination'])]=0
        if closed:
            post[keys.index(a['destination'])]=0
            post[keys.index(a['owner'])]+=500+(0 if created else 2039280)
        else:post[keys.index(a['destination'])]+=500
    post[keys.index(a['owner'])]-=tip;post[keys.index(a['tip'])]+=tip
    signatures=[b58encode(bytes([5])*64),b58encode(bytes([6])*64)]
    message={'accountKeys':keys[:-len(loaded)] if loaded else keys,'header':{'numRequiredSignatures':2,'numReadonlySignedAccounts':0,'numReadonlyUnsignedAccounts':0},'recentBlockhash':key(70),'instructions':outer}
    if version==0:message['addressTableLookups']=[{'accountKey':key(80),'writableIndexes':[0,1,2],'readonlyIndexes':[]}]
    tx={'slot':100,'blockTime':1000,'version':version,'transaction':{'signatures':signatures,'message':message},
        'meta':{'err':None,'fee':5000,'preBalances':pre,'postBalances':post,'preTokenBalances':balances(before,False),'postTokenBalances':balances(after,True),
                'innerInstructions':[{'index':n,'instructions':inner}],'loadedAddresses':{'writable':loaded,'readonly':[]}}}
    req=request('getTransaction',[signatures[0],{'commitment':'finalized','encoding':'json','maxSupportedTransactionVersion':0}],'receipt')
    packet={'status':'ok','request':req,'response':response(req,tx)}
    br=request('getBlock',[100,{'commitment':'finalized','transactionDetails':'none','rewards':False}],'receipt-header')
    block={'status':'ok','request':br,'response':response(br,{'blockhash':key(71),'previousBlockhash':key(72),'parentSlot':99,'blockTime':1000})}
    a.update(swap_index=n,keys=keys)
    return {'family':'solana','genesis_hash':MAINNET,'mint':a['input_mint']},a,packet,block
