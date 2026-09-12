"""Synthetic Pump bytes at independently enumerated official IDL offsets."""
import struct
from solana_common import base58_bytes,b58encode,TOKEN_PROGRAM,TOKEN_2022
from solana_addresses import find_program_address,associated_token_address
from adapters.binary import discriminator
from adapters import pump_curve as curve,pump_swap as swap
from adapters.pump_common import *
from pool_fixture import key,mint,holding,batch
from solana_fixture import account,request,response
from solana_discovery import MAINNET


def owned(raw,program):return {**account(raw),'owner':program}
def put(raw,offset,k):raw[offset:offset+32]=base58_bytes(k,32)


def fee(program):
    address,bump=find_program_address([b'fee_config',base58_bytes(program,32)],FEE_PROGRAM)
    raw=discriminator('FeeConfig')+bytes([bump])+base58_bytes(key(60),32)+struct.pack('<3Q',20,5,10)
    raw+=struct.pack('<I',2)+(0).to_bytes(16,'little')+struct.pack('<3Q',20,10,20)+(1000000).to_bytes(16,'little')+struct.pack('<3Q',20,5,10)+struct.pack('<I',0)
    return address,owned(raw,FEE_PROGRAM)


def fixture(*,complete=False,non_native=False,virtual=0):
    target={'family':'solana','genesis_hash':MAINNET,'mint':key(2)};m=target['mint'];q=key(3) if non_native else WSOL
    c=curve_address(m);authority=pool_authority(m);pool,bump=find_program_address([b'pool',bytes(2),base58_bytes(authority,32),base58_bytes(m,32),base58_bytes(q,32)],SWAP_PROGRAM)
    vaults=[associated_token_address(pool,x,TOKEN_PROGRAM)[0] for x in (m,q)];lp=pda(SWAP_PROGRAM,b'pool_lp_mint',base58_bytes(pool,32))
    ch=associated_token_address(c,m,TOKEN_PROGRAM)[0];qh=associated_token_address(c,q,TOKEN_PROGRAM)[0]
    addresses={'curve':c,'curve_holding':ch,'quote_holding':qh,'pool':pool,'mints':[m,q],'vaults':vaults,'lp':lp,'holder':key(50),'creator':key(51),'authority':authority}
    values={m:mint(1000000),q:mint(2000000),ch:holding(m,c,0 if complete else 500),qh:holding(q,c,1000),
        vaults[0]:holding(m,pool,10000),vaults[1]:holding(q,pool,20000),lp:{**mint(900,pool,9),'owner':TOKEN_2022},key(50):{**holding(lp,key(52),450,key(53)),'owner':TOKEN_2022}}
    raw=bytearray(115);raw[:8]=discriminator('BondingCurve');struct.pack_into('<5Q',raw,8,1000,2000,0 if complete else 500,1000,1000000);raw[48]=complete;put(raw,49,key(51));put(raw,83,q if non_native else ZERO)
    values[c]={**owned(bytes(raw),CURVE_PROGRAM),'lamports':3000}
    raw=bytearray(1045);raw[:8]=discriminator('Global');raw[8]=1
    for off in (9,41,113,386,418):put(raw,off,key(60))
    struct.pack_into('<Q',raw,105,10);struct.pack_into('<Q',raw,154,20);values[curve.GLOBAL]=owned(bytes(raw),CURVE_PROGRAM)
    raw=bytearray(300);raw[:8]=discriminator('Pool');raw[8]=bump
    for off,k in zip((11,43,75,107,139,171,211),(authority,m,q,lp,*vaults,key(51))):put(raw,off,k)
    struct.pack_into('<Q',raw,203,1000);raw[245:261]=virtual.to_bytes(16,'little',signed=True);values[pool]=owned(bytes(raw),SWAP_PROGRAM)
    raw=bytearray(940);raw[:8]=discriminator('GlobalConfig')
    for off in (8,321,907):put(raw,off,key(60))
    struct.pack_into('<2Q',raw,40,20,5);struct.pack_into('<Q',raw,313,10);values[swap.GLOBAL]=owned(bytes(raw),SWAP_PROGRAM)
    for p in (CURVE_PROGRAM,SWAP_PROGRAM):addr,val=fee(p);values[addr]=val
    return target,addresses,values


def receipt(target,outer,inner,*,slot=95,balances=None):
    """Compile arbitrary exact instructions to a historical raw JSON receipt."""
    payer=key(70);keys=[payer]
    for program,a,raw in [outer,*inner]:
        for k in [program,*a]:
            if k not in keys:keys.append(k)
    def ix(row):
        program,a,raw=row
        return {'programIdIndex':keys.index(program),'accounts':[keys.index(k) for k in a],'data':b58encode(raw)}
    sig=b58encode(bytes([71])*64);req=request('getTransaction',[sig,{'commitment':'finalized','encoding':'json','maxSupportedTransactionVersion':0}],'launch-receipt')
    pre=[];post=[]
    for address,m,owner,x,y in balances or []:
        for out,amount in ((pre,x),(post,y)):
            out.append({'accountIndex':keys.index(address),'mint':m,'owner':owner,'programId':TOKEN_PROGRAM,'uiTokenAmount':{'amount':str(amount),'decimals':6}})
    native=[1000000]*len(keys);after=native.copy();after[0]-=5000
    tx={'slot':slot,'blockTime':1000,'version':'legacy','transaction':{'signatures':[sig],'message':{'accountKeys':keys,'header':{'numRequiredSignatures':1,'numReadonlySignedAccounts':0,'numReadonlyUnsignedAccounts':0},'recentBlockhash':key(72),'instructions':[ix(outer)]}},
        'meta':{'err':None,'fee':5000,'preBalances':native,'postBalances':after,'preTokenBalances':pre,'postTokenBalances':post,'innerInstructions':[{'index':0,'instructions':[ix(i) for i in inner]}]}}
    packet={'status':'ok','request':req,'response':response(req,tx)}
    br=request('getBlock',[slot,{'commitment':'finalized','transactionDetails':'none','rewards':False}],'launch-header')
    block={'status':'ok','request':br,'response':response(br,{'blockhash':key(73),'previousBlockhash':key(74),'parentSlot':slot-1,'blockTime':1000})}
    return packet,block


def migration(target,a):
    from adapters.pump_instructions import tag
    accounts=[key(80+i) for i in range(27)]
    for i,k in {2:target['mint'],3:a['mints'][1],4:a['curve'],9:SWAP_PROGRAM,10:a['pool'],11:a['authority'],15:a['lp'],17:a['vaults'][0],18:a['vaults'][1]}.items():accounts[i]=k
    creation=[key(110+i) for i in range(18)]
    for i,k in {0:a['pool'],2:a['authority'],3:target['mint'],4:a['mints'][1],5:a['lp'],9:a['vaults'][0],10:a['vaults'][1]}.items():creation[i]=k
    create=tag('create_pool')+struct.pack('<HQQ',0,10000,20000)+base58_bytes(a['creator'],32)+bytes(2)
    inner=[(SWAP_PROGRAM,creation,create)];balances=[]
    for i,(m,v) in enumerate(zip(a['mints'],a['vaults'])):
        source=key(140+i);amount=10000*(i+1)
        inner.append((TOKEN_PROGRAM,[source,m,v,a['authority']],struct.pack('<BQB',12,amount,6)))
        balances += [(source,m,a['authority'],amount,0),(v,m,a['pool'],0,amount)]
    return receipt(target,(CURVE_PROGRAM,accounts,tag('migrate_v2')),inner,balances=balances)
