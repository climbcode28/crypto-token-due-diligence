"""Synthetic fixed-offset position fixtures; published lengths are checked independently."""
import struct
from solana_common import base58_bytes,TOKEN_2022
from solana_addresses import find_program_address
from solana_fixture import account
from solana_discovery import MAINNET
from adapters.binary import discriminator
from adapters.concentrated_math import sqrt_at_tick
from adapters import raydium_clmm as ray, orca_whirlpool as orca
from pool_fixture import key,mint,holding,batch


def fixture(kind='raydium',*,tick=0,lower=-100,upper=100,liquidity=1_000_000,bundle=False,dynamic=False,token22=False):
    module=ray if kind=='raydium' else orca;program=module.PROGRAM
    mints=[key(2),key(3)];config=key(50);nft=key(51);owner=key(52);holder=key(53)
    seeds=[b'pool' if kind=='raydium' else b'whirlpool',base58_bytes(config,32),base58_bytes(mints[0],32),base58_bytes(mints[1],32)]
    if kind=='orca':seeds.append(b'\1\0')
    pool,bump=find_program_address(seeds,program)
    vaults=[find_program_address([b'pool_vault',base58_bytes(pool,32),base58_bytes(m,32)],program)[0] for m in mints] if kind=='raydium' else [key(54),key(55)]
    position,pbump=find_program_address([b'bundled_position',base58_bytes(nft,32),b'7'] if bundle else [b'position',base58_bytes(nft,32)],program)
    lead={'position':position,'holding':holder,'kind':'indexer','evidence':['position-lead']}
    values={mints[0]:mint(10**14),mints[1]:mint(10**14),nft:mint(1,None,0),holder:holding(nft,owner,1,key(56)),vaults[0]:holding(mints[0],pool,10**12),vaults[1]:holding(mints[1],pool,10**12)}
    if token22:
        import base64
        original=base64.b64decode(values[nft]['data'][0]);values[nft]={**account(original+bytes(83)+b'\1'+struct.pack('<HH',9,0)),'owner':TOKEN_2022}
        original=base64.b64decode(values[holder]['data'][0]);values[holder]={**account(original+b'\2'+struct.pack('<HH',13,0)),'owner':TOKEN_2022}
    if kind=='raydium':
        raw=bytearray(1544);raw[:8]=discriminator('PoolState');raw[8]=bump
        raw[9:233]=b''.join(base58_bytes(k,32) for k in [config,owner,*mints,*vaults,key(57)])
        raw[233:235]=bytes([6,6]);struct.pack_into('<H',raw,235,1);raw[237:253]=(2_000_000).to_bytes(16,'little');raw[253:269]=sqrt_at_tick(tick,kind).to_bytes(16,'little');struct.pack_into('<i',raw,269,tick)
        cfg=bytearray(117);cfg[:8]=discriminator('AmmConfig');cfg[11:43]=base58_bytes(owner,32);struct.pack_into('<IIHI',cfg,43,100000,2500,1,100000);cfg[61:93]=base58_bytes(owner,32)
        pos=bytearray(281);pos[:8]=discriminator('PersonalPositionState');pos[8]=pbump;pos[9:73]=base58_bytes(nft,32)+base58_bytes(pool,32);struct.pack_into('<ii',pos,73,lower,upper);pos[81:97]=liquidity.to_bytes(16,'little');struct.pack_into('<2Q',pos,129,17,23)
    else:
        raw=bytearray(653);raw[:8]=discriminator('Whirlpool');raw[8:40]=base58_bytes(config,32);raw[40]=bump;struct.pack_into('<4H',raw,41,1,1,2500,1000);raw[49:65]=(2_000_000).to_bytes(16,'little');raw[65:81]=sqrt_at_tick(tick,kind).to_bytes(16,'little');struct.pack_into('<i',raw,81,tick)
        raw[101:165]=base58_bytes(mints[0],32)+base58_bytes(vaults[0],32);raw[181:245]=base58_bytes(mints[1],32)+base58_bytes(vaults[1],32)
        cfg=discriminator('WhirlpoolsConfig')+base58_bytes(owner,32)*3+struct.pack('<HH',1000,0)
        pos=bytearray(216);pos[:8]=discriminator('Position');pos[8:72]=base58_bytes(pool,32)+base58_bytes(nft,32);pos[72:88]=liquidity.to_bytes(16,'little');struct.pack_into('<ii',pos,88,lower,upper);struct.pack_into('<Q',pos,112,17);struct.pack_into('<Q',pos,136,23)
        if bundle:
            bundle_address=find_program_address([b'position_bundle',base58_bytes(nft,32)],program)[0]
            data=bytearray(136);data[:8]=discriminator('PositionBundle');data[8:40]=base58_bytes(nft,32);data[40]=128
            values[bundle_address]={**account(data),'owner':program};lead.update(bundle=bundle_address,bundle_index=7)
    values[pool]={**account(raw),'owner':program};values[config]={**account(cfg),'owner':program};values[position]={**account(pos),'owner':program}
    arrays={}
    count=60 if kind=='raydium' else 88
    for boundary in [lower,upper]:arrays.setdefault((boundary//count)*count,[]).append(boundary)
    array_addresses=[]
    for start,boundaries in arrays.items():
        addr=module.tick_array_address(pool,start,1);array_addresses.append(addr)
        if kind=='raydium':
            data=bytearray(10240);data[:8]=discriminator('TickArrayState');data[8:40]=base58_bytes(pool,32);struct.pack_into('<i',data,40,start)
            for boundary in boundaries:
                at=44+(boundary-start)*168;struct.pack_into('<i',data,at,boundary);data[at+20:at+36]=liquidity.to_bytes(16,'little')
        elif not dynamic:
            data=bytearray(9988);data[:8]=discriminator('TickArray');struct.pack_into('<i',data,8,start);data[-32:]=base58_bytes(pool,32)
            for boundary in boundaries:
                at=12+(boundary-start)*113;data[at]=bool(liquidity);data[at+17:at+33]=liquidity.to_bytes(16,'little')
        else:
            bitmap=sum(1<<(b-start) for b in boundaries) if liquidity else 0
            data=bytearray(discriminator('DynamicTickArray')+struct.pack('<i',start)+base58_bytes(pool,32)+bitmap.to_bytes(16,'little'))
            for i in range(88):
                if start+i in boundaries and liquidity:data+=b'\1'+bytes(16)+liquidity.to_bytes(16,'little')+bytes(80)
                else:data+=b'\0'
        values[addr]={**account(data),'owner':program}
    return {'family':'solana','genesis_hash':MAINNET,'mint':mints[0]}, {'pool':pool,'position':position,'nft':nft,'holding':holder,'owner':owner,'arrays':array_addresses,'config':config,'lead':lead},values
