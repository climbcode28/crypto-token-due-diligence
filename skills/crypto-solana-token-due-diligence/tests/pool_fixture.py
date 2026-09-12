"""Synthetic byte fixtures with independently stated Raydium field offsets."""
import struct
from solana_common import b58encode, base58_bytes, TOKEN_PROGRAM
from solana_addresses import find_program_address
from solana_discovery import MAINNET
from solana_fixture import account, request, response
from solana_presets import settings
from adapters.binary import discriminator
from adapters import raydium_cpmm as cp, raydium_amm_v4 as amm


def key(n): return b58encode(bytes([n])*32)
def mint(supply, authority=None, decimals=6):
    raw = (struct.pack('<I', 1)+base58_bytes(authority, 32)) if authority else bytes(36)
    return account(raw+struct.pack('<QBB', supply, decimals, 1)+bytes(36))

def holding(mint_key, owner, amount, delegate=None):
    raw=base58_bytes(mint_key, 32)+base58_bytes(owner, 32)+struct.pack('<Q', amount)
    raw+=(struct.pack('<I', 1)+base58_bytes(delegate, 32)) if delegate else bytes(36)
    return account(raw+b'\1'+bytes(12)+struct.pack('<Q', amount if delegate else 0)+bytes(36))

def batch(values, name='pool-sample', slot=100):
    addresses=list(values)
    req=request('getMultipleAccounts', [addresses, settings()], name)
    packet={'status':'ok','request':req,'response':response(req, {'context':{'slot':slot},'value':list(values.values())}),
        'started_at':1,'completed_at':1.1}
    return {address:packet for address in addresses}

def fixture(kind='cpmm', status=6):
    program=cp.PROGRAM if kind=='cpmm' else amm.PROGRAM
    pool, mints, owner = key(30), [key(2),key(3)], key(31)
    authority,bump=find_program_address([b'vault_and_lp_mint_auth_seed' if kind=='cpmm' else b'amm authority'],program)
    vaults=[find_program_address([b'pool_vault',base58_bytes(pool,32),base58_bytes(m,32)],program)[0] for m in mints] if kind=='cpmm' else [key(32),key(33)]
    lp=find_program_address([b'pool_lp_mint',base58_bytes(pool,32)],program)[0] if kind=='cpmm' else key(34)
    addresses={'pool':pool,'mints':mints,'vaults':vaults,'lp':lp,'holder':key(35),'authority':authority}
    values={mints[0]:mint(1000000),mints[1]:mint(2000000),vaults[0]:holding(mints[0],authority,10000),vaults[1]:holding(mints[1],authority,20000),lp:mint(900,authority,9),key(35):holding(lp,owner,450,key(36))}
    if kind=='cpmm':
        config,cbump=find_program_address([b'amm_config',b'\0\1'],program)
        keys=[config,owner,*vaults,lp,*mints,TOKEN_PROGRAM,TOKEN_PROGRAM,key(37)]
        raw=discriminator('PoolState')+b''.join(base58_bytes(k,32) for k in keys)
        raw+=bytes([bump,0,9,6,6])+struct.pack('<7Q',1000,100,200,30,40,1,5)+bytes([0,1])+bytes(6)+struct.pack('<2Q',10,20)+bytes(224)
        cfg=discriminator('AmmConfig')+struct.pack('<BBH4Q',cbump,0,1,2500,120000,40000,0)+base58_bytes(owner,32)*2+struct.pack('<Q',500)+bytes(120)
        values[config]={**account(cfg),'owner':program};addresses['config']=config
    else:
        raw=bytearray(752)
        struct.pack_into('<2Q',raw,0,status,bump);struct.pack_into('<2Q',raw,32,6,6)
        struct.pack_into('<8Q',raw,128,5,10000,25,10000,12,100,25,10000)
        struct.pack_into('<2Q',raw,192,100,200)
        oo,market,event=key(38),key(39),key(40)
        keys=[*vaults,*mints,lp,oo,market,amm.OPENBOOK,key(41)]
        raw[336:624]=b''.join(base58_bytes(k,32) for k in keys)
        raw[688:720]=base58_bytes(owner,32);struct.pack_into('<Q',raw,720,1000)
        orders=bytearray(3216);struct.pack_into('<Q',orders,0,5);orders[8:40]=base58_bytes(market,32);orders[40:72]=base58_bytes(authority,32)
        struct.pack_into('<4Q',orders,72,10,300,20,600)
        mk=bytearray(376);struct.pack_into('<Q',mk,0,3);mk[8:40]=base58_bytes(market,32);mk[48:112]=b''.join(base58_bytes(m,32) for m in mints);mk[248:280]=base58_bytes(event,32)
        evt=bytearray(88);evt[0]=13;struct.pack_into('<2Q',evt,8,70,100);evt[48:80]=base58_bytes(oo,32)
        queue=struct.pack('<4Q',17,0,1,3)+evt+bytes(88)
        for addr,data in [(oo,orders),(market,mk),(event,queue)]:values[addr]={**account(b'serum'+data+b'padding'),'owner':amm.OPENBOOK}
        addresses.update(oo=oo,market=market,event=event)
    values[pool]={**account(bytes(raw)),'owner':program}
    return {'family':'solana','genesis_hash':MAINNET,'mint':mints[0]},addresses,values
