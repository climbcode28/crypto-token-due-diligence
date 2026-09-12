#!/usr/bin/env python3
"""Offline feedback ingestion and explicit reviewed promotion, outside research."""
import argparse,json,time
from pathlib import Path
from solana_common import sha
from solana_profile import strict_json,regular,check,normalized_status
from solana_operations import VERSION,RULES,validate_record,active
from solana_facts import encoded,atomic


def ingest(roots,now=None):
    now=time.time() if now is None else now;records={};rejected=0
    for directory in roots:
        root=Path(directory)
        try:
            rows=strict_json(regular(root,'operations.json').read_bytes(),'operations.json')
            check(isinstance(rows,list) and len(rows)<=8,'feedback','Bounded feedback file required.')
            for row in rows:
                try:validate_record(row,now);records.setdefault(row['id'],row)
                except Exception:rejected+=1
        except Exception:rejected+=1
    return {'schema_version':1,'records':list(records.values()),'rejected':rejected,'active_lessons_changed':False}


def promote(root,record_id,review,*,now=None):
    now=time.time() if now is None else now;root=Path(root)
    rows=ingest([root],now)['records'];selected=[r for r in rows if r['id']==record_id];check(len(selected)==1,'promotion','One applicable current record required.');row=selected[0]
    check(row['outcome']=='recovered' and row['recovery'] in RULES,'promotion','A demonstrated supported recovery is required.')
    proof=row['proof'];check(len(proof)==2 and proof[0]['status']!='ok' and proof[1]['status']=='ok' and proof[0]['sha256']!=proof[1]['sha256'],'promotion','Independent failure and recovery evidence required.')
    packets=[]
    for item in proof:
        raw=regular(root,item['path']).read_bytes();check(sha(raw)==item['sha256'],'promotion','Recovery evidence changed.');value=strict_json(raw,item['path'])
        check(normalized_status(value)==item['status'],'promotion','Recovery status differs from evidence.')
        if row['source_class']=='public_rpc':
            from solana_wire import validate_request,validate_response
            validate_request(value['request']);check(value['request']['method']==row['method'],'promotion','Recovery method differs.')
            if item['status']=='ok':check(validate_response(value['request'],value['response'])['status']=='ok','promotion','Recovery response is not valid.')
        else:
            check(value.get('method')=='GET','promotion','HTTP method metadata invalid.')
            if item['status']=='ok':check(value.get('http_status')==200,'promotion','HTTP recovery status invalid.')
        packets.append(value)
    check(packets[0]['completed_at']<packets[1]['started_at'],'promotion','Recovery must follow the failure.')
    if row['recovery']=='bounded_retry':
        check(packets[0]['source']==packets[1]['source'] and proof[0]['status'] in ('timeout','transport_failure','rpc_error','node_lag'),'promotion','Retry needs the same source and transient failure.')
        if row['source_class']=='public_rpc':check(packets[0]['request']['params']==packets[1]['request']['params'],'promotion','Retry request scope differs.')
    else:check(packets[0]['source']!=packets[1]['source'],'promotion','Alternate must be a distinct source.')
    if row['source_class']=='public_rpc':check(packets[0]['request']['params']==packets[1]['request']['params'],'promotion','Recovery request scope differs.')
    check(row['evidence_sha256']==sha(encoded(proof)),'promotion','Recovery proof digest differs.')
    lesson={'rule_id':row['recovery'],'text':RULES[row['recovery']],'record_id':row['id'],'component_version':VERSION,
        'expires_at':min(row['expires_at'],now+7*86400),'review':review}
    # Validate without accepting arbitrary reviewer prose as executable guidance.
    import re
    check(set(review)=={'reviewer','reviewed_at','decision'} and review['decision']=='approve' and re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,47}',review['reviewer']) is not None,'review','Named explicit approval required.')
    check(type(review['reviewed_at']) in (int,float) and now-86400<=review['reviewed_at']<=now,'review','Review must be dated within the last day.')
    check(all(type(p[k]) in (int,float) and 0<=p['started_at']<=p['completed_at']<=review['reviewed_at'] for p in packets for k in ('started_at','completed_at')),'review','Evidence must predate its review.')
    lesson['expires_at']=min(row['expires_at'],review['reviewed_at']+7*86400)
    return {'schema_version':1,'lessons':[lesson]}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('ingest','promote','active'));p.add_argument('roots',nargs='+',type=Path)
    p.add_argument('--record-id');p.add_argument('--review',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    try:
        if a.action=='ingest':result=ingest(a.roots)
        elif a.action=='active':check(len(a.roots)==1,'active','One lesson file required.');result={'lessons':active(a.roots[0])}
        else:
            check(len(a.roots)==1 and a.review and a.record_id,'promotion','One run, --record-id and --review required.')
            result=promote(a.roots[0],a.record_id,strict_json(regular(a.review.parent,a.review.name).read_bytes(),'review'))
        if a.out:
            check(not a.out.exists() and not a.out.is_symlink(),'output','Use a new reviewed output file.');atomic(a.out,encoded(result))
        print(json.dumps(result,ensure_ascii=False))
    except (ValueError,OSError,KeyError,TypeError) as exc:p.exit(2,str(exc)+'\n')
if __name__=='__main__':main()
