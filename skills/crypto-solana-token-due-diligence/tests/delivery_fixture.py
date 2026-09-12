"""Maintained compact notes for an independently specified bounded complete case."""
import copy
from profile_fixture import Bundle
from compose_fixture import note,save,lane,assign


def complete(root,adverse=False):
    b=Bundle(root,completed=True,adverse=adverse);original=copy.deepcopy(b.r)
    b.m['lanes']=[];b.m['artifacts']=[a for a in b.m['artifacts'] if not a['path'].startswith('notes/')];b.save()
    n=note(b);mapping={f['id']:'coordinator-'+f['id'] for f in original['findings']}
    def rename(v):
        if isinstance(v,str):return mapping.get(v,v)
        if isinstance(v,list):return [rename(x) for x in v]
        if isinstance(v,dict):return {k:rename(x) for k,x in v.items()}
        return v
    for field in ('findings','coverage','decision','summary_ids','limitations'):n[field]=rename(original[field])
    n['signal_assignments']=assign(b,'unverified')
    n['research_status']='completed';save(b,n);lane(b,'liquidity');lane(b,'project');return b,n
