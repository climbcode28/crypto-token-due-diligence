"""Bind existing independently checked protocol bytes to v2 contexts."""
from profile_fixture import Bundle,BASE,utc
from solana_presets import settings
from solana_derivations import compute


def rich(root,kind):
    if kind in ('raydium_cpmm','raydium_amm_v4'):
        from pool_fixture import fixture
        target,a,values=fixture('cpmm' if kind=='raydium_cpmm' else 'amm')
    elif kind in ('raydium_clmm','orca_whirlpool'):
        from concentrated_fixture import fixture
        target,a,values=fixture('raydium' if kind=='raydium_clmm' else 'orca')
    elif kind in ('meteora_dlmm','meteora_damm_v2'):
        from meteora_fixture import fixture
        target,a,values=fixture('dlmm' if kind=='meteora_dlmm' else 'damm')
    else:
        from pump_fixture import fixture
        target,a,values=fixture()
    b=Bundle(root);assert target==b.target
    from solana_accounts import controls
    for eid in ('mint','mint-fresh'):
        packet=b.obj(eid);packet['response']['result']['value']=values[target['mint']];b.replace(eid,packet)
    d=b.m['derivations'][0];out=controls(b.obj('mint'),target);b.replace('controls',out);d['output']=out;d['inputs'][0]['sha256']=b.obs('mint')['sha256']
    pool=a['curve'] if kind=='pump_curve' else a['pool']
    add_batch(b,'pool-state',values,100,14)
    params={'adapter':kind,'pool':pool,'observations':dict.fromkeys(values,'pool-state')}
    if 'lead' in a:params['positions']=[a['lead']]
    elif 'holder' in a and kind!='pump_curve':params['lp_accounts']=[a['holder']]
    output=compute('pool',params,b.target,b.obj)
    b.derived('pool-'+kind,'pool',params,['pool-state'],output,{**b.sub,'kind':'pool','address':pool});b.save();return b


def add_batch(b,eid,values,slot,t):
    b.rpc(eid,'getMultipleAccounts',[list(values),settings()],{'context':{'slot':slot},'value':list(values.values())},t)
    b.obs(eid)['sample_id']='sample-'+eid
    b.m['samples'].append({'id':'sample-'+eid,'observation_id':eid,'addresses':list(values),'address_indices':{a:i for i,a in enumerate(values)},'encoding':'base64',
     'commitment':'finalized','context_slot':slot,'captured_at':utc(BASE+t+0.5),'block_evidence_id':'block'+str(slot),'block_recheck_evidence_id':'reblock'+str(slot),'critical':False,'recheck_of':None,'status':'pinned'})
