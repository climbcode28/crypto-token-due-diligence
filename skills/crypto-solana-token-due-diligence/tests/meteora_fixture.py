"""Synthetic accounts at explicit offsets from pinned layouts; no SDK required."""
import struct
from pool_fixture import key,mint,holding,batch
from solana_fixture import account
from solana_common import base58_bytes,TOKEN_2022
from solana_addresses import find_program_address
from solana_discovery import MAINNET
from adapters.binary import discriminator
from adapters import meteora_dlmm as dlmm,meteora_damm_v2 as damm,meteora_common as common

Q=1<<64


def write(raw,offset,value,size=8,signed=False):
    raw[offset:offset+size]=value.to_bytes(size,'little',signed=signed)


def owned(raw,program):return {**account(bytes(raw)),'owner':program}


def clock(slot=100,timestamp=1000):
    return owned(struct.pack('<QqQQq',slot,0,1,1,timestamp),common.SYSVAR)


def fixture(kind='dlmm',collect=0):
    module=dlmm if kind=='dlmm' else damm
    program=module.PROGRAM
    pool,mints,owner=key(60),[key(2),key(3)],key(61)
    authority=pool if kind=='dlmm' else find_program_address([b'pool_authority'],program)[0]
    vaults=[find_program_address([base58_bytes(pool,32),base58_bytes(m,32)] if kind=='dlmm' else [b'token_vault',base58_bytes(m,32),base58_bytes(pool,32)],program)[0] for m in mints]
    a={'pool':pool,'mints':mints,'vaults':vaults,'owner':owner,'authority':authority}
    values={mints[0]:mint(10000000),mints[1]:mint(20000000),
            vaults[0]:holding(mints[0],authority,1000000),vaults[1]:holding(mints[1],authority,2000000),common.CLOCK:clock()}
    if kind=='dlmm':
        raw=bytearray(904);raw[:8]=discriminator('LbPair')
        write(raw,8,100,2);write(raw,10,10,2);write(raw,12,20,2);write(raw,14,5000,2)
        write(raw,20,10000,4);write(raw,24,-10000,4,True);write(raw,28,10000,4,True)
        write(raw,32,1000,2);raw[35]=2;write(raw,80,10,2)
        for offset,k in zip((88,120,152,184),[*mints,*vaults]):raw[offset:offset+32]=base58_bytes(k,32)
        raw[848:880]=base58_bytes(owner,32)
        position=key(62);pos=bytearray(8120);pos[:8]=discriminator('PositionV2');pos[8:40]=base58_bytes(pool,32);pos[40:72]=base58_bytes(owner,32)
        # Three bins crossing zero: (-1,0,1), shares quarter/half/zero.
        for i,share in enumerate([25*Q,50*Q,0]):write(pos,72+16*i,share,16)
        write(pos,7912,-1,4,True);write(pos,7916,1,4,True);write(pos,7992,90)
        write(pos,4584,7);write(pos,4592,11)
        arrays=[]
        for index in (-1,0):
            array=dlmm.bin_array_address(pool,index*70);arrays.append(array)
            b=bytearray(10136);b[:8]=discriminator('BinArray');write(b,8,index,8,True);b[24:56]=base58_bytes(pool,32)
            for bin_id,amounts in [(-1,(1000,0)),(0,(1000,2000)),(1,(0,2000))]:
                if bin_id//70 != index:continue
                start=56+(bin_id%70)*144;write(b,start,amounts[0]);write(b,start+8,amounts[1]);write(b,start+16,Q,16);write(b,start+32,100*Q,16)
            values[array]=owned(b,program)
        a.update(arrays=arrays)
    else:
        raw=bytearray(1112);raw[:8]=discriminator('Pool')
        write(raw,8,2500000);raw[48]=20;raw[50]=10
        for offset,k in zip((168,200,232,264),[*mints,*vaults]):raw[offset:offset+32]=base58_bytes(k,32)
        write(raw,360,2000*Q,16);write(raw,392,100);write(raw,400,200)
        write(raw,424,Q//2 if collect<2 else 0,16);write(raw,440,2*Q if collect<2 else (1<<128)-1,16);write(raw,456,Q,16)
        raw[484]=collect;raw[696]=1
        write(raw,552,100*Q,16);raw[648:680]=base58_bytes(owner,32);write(raw,680,10000);write(raw,688,20000)
        nft=key(63);position=find_program_address([b'position',base58_bytes(nft,32)],program)[0];ha=key(64)
        pos=bytearray(408);pos[:8]=discriminator('Position');pos[8:40]=base58_bytes(pool,32);pos[40:72]=base58_bytes(nft,32)
        write(pos,136,7);write(pos,144,11)
        for offset,liquidity in [(152,500),(168,400),(184,100)]:write(pos,offset,liquidity*Q,16)
        # cliff slot 90: 100; periods every 10 slots release 100 each, three total.
        write(pos,312,90);write(pos,320,10);write(pos,328,100*Q,16);write(pos,344,100*Q,16);write(pos,376,3,2)
        write(pos,392,(1<<2)|(1<<3),4)
        nm=bytearray(__import__('base64').b64decode(mint(1,authority,0)['data'][0]));write(nm,46,1,4);nm[50:82]=base58_bytes(pool,32)
        values[nft]=owned(nm,TOKEN_2022)
        hm=bytearray(__import__('base64').b64decode(holding(nft,owner,1,key(65))['data'][0]));write(hm,121,0)
        values[ha]=owned(hm+b'\2',TOKEN_2022)
        a.update(nft=nft,holding=ha)
    values[pool]=owned(raw,program);values[position]=owned(pos,program)
    a['position']=position;a['lead']={'position':position,'kind':'account','evidence':['position-lead']}
    if 'holding' in a:a['lead']['holding']=a['holding']
    return {'family':'solana','genesis_hash':MAINNET,'mint':mints[0]},a,values
