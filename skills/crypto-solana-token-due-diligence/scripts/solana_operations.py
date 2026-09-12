"""Bounded, nonblocking operational observations; never token facts or advice."""
import copy,fcntl,re,time
from pathlib import Path
from solana_common import sha
from solana_profile import check,strict_json,regular
from solana_facts import atomic,encoded

VERSION='1.0.0'
METHODS={'getGenesisHash','getAccountInfo','getMultipleAccounts','getEpochInfo','getTokenLargestAccounts','getSignaturesForAddress','getTransaction','getBlock','getBlockTime','getProgramAccounts','GET'}
CATEGORIES={'source_failure','transient_recovery','source_recovery','source_reuse','collection_summary'}
RECOVERIES={'none','bounded_retry','alternate_public_source','retain_partial','reuse_capture'}
OUTCOMES={'observed','unresolved','recovered'}
SOURCE_CLASSES={'public_rpc','public_http'}
RULES={'bounded_retry':'A single recorded transient retry recovered this method. Keep retries inside the existing attempt and deadline grants.',
       'alternate_public_source':'A recorded public alternate recovered this source class. Use it only within the existing source ownership and run budget.'}


def validate_record(row,now=None):
    now=time.time() if now is None else now
    keys={'schema_version','id','category','source_class','method','recovery','outcome','evidence_sha256','component_version','observed_at','expires_at','proof'}
    check(isinstance(row,dict) and set(row)==keys,'feedback','Unexpected feedback fields; no free-form instructions or token facts.')
    check(type(row['schema_version']) is int and row['schema_version']==1 and row['category'] in CATEGORIES and row['source_class'] in SOURCE_CLASSES and row['method'] in METHODS,'feedback','Unknown typed observation.')
    check(row['recovery'] in RECOVERIES and row['outcome'] in OUTCOMES,'feedback','Unknown recovery/outcome.')
    check(row['component_version']==VERSION,'feedback','Inapplicable component version.')
    for k in ('id','evidence_sha256'):check(isinstance(row[k],str) and re.fullmatch('[0-9a-f]{64}',row[k]),'feedback.'+k,'SHA-256 required.')
    for k in ('observed_at','expires_at'):check(type(row[k]) in (int,float) and 0<=row[k]<=now+8*86400,'feedback.'+k,'Bounded timestamp required.')
    check(row['observed_at']<=now+60 and now<row['expires_at']<=row['observed_at']+7*86400,'feedback.expiry','Expired/future/unbounded feedback.')
    proof=row['proof'];check(isinstance(proof,list) and len(proof)<=2,'feedback.proof','At most two proof records.')
    for item in proof:
        check(set(item)=={'path','sha256','status','source_class','method'},'feedback.proof','Unexpected proof fields.')
        check(re.fullmatch(r'evidence/[a-zA-Z0-9_.-]{1,180}',item['path']) is not None,'feedback.proof','Confined evidence path required.')
        check(re.fullmatch('[0-9a-f]{64}',item['sha256']) is not None and item['status'] in ('ok','timeout','transport_failure','rpc_error','node_lag','permission_denied','null'),'feedback.proof','Invalid evidence hash/status.')
        check(item['method']==row['method'] and item['source_class']==row['source_class'],'feedback.proof','Proof method/source applicability differs.')
    unsigned={k:v for k,v in row.items() if k!='id'};check(sha(encoded(unsigned))==row['id'],'feedback.id','Feedback content changed.')
    return row


def observe(run_root,*,category,source_class,method,recovery,outcome,evidence_sha256,proof=None,now=None):
    """Feedback storage failure cannot corrupt collection, notes or final delivery."""
    try:
        now=time.time() if now is None else now;root=Path(run_root);lock=root/'.operations.lock'
        check(root.is_dir() and not lock.is_symlink(),'feedback','Existing run and regular lock required.')
        row={'schema_version':1,'category':category,'source_class':source_class,'method':method,'recovery':recovery,'outcome':outcome,
            'evidence_sha256':evidence_sha256,'component_version':VERSION,'observed_at':now,'expires_at':now+7*86400,'proof':proof or []}
        row['id']=sha(encoded(row));validate_record(row,now)
        with lock.open('a+b') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX)
            path=root/'operations.json';rows=strict_json(regular(root,path.name).read_bytes(),path.name) if path.exists() else []
            check(isinstance(rows,list) and len(rows)<=8,'feedback','Corrupt feedback file.')
            for old in rows:validate_record(old,now)
            if len(rows)>=8:return {'recorded':False,'reason':'bounded_capacity'}
            if any(x['id']==row['id'] for x in rows):return {'recorded':False,'reason':'duplicate'}
            atomic(path,encoded(rows+[row]));return {'recorded':True,'id':row['id']}
    except Exception:return {'recorded':False,'reason':'feedback_unavailable'}


def active(path,*,now=None):
    """Optional advisory loading; nothing here changes runtime controls or verdicts."""
    try:
        now=time.time() if now is None else now;p=Path(path);value=strict_json(regular(p.parent,p.name).read_bytes(),p.name)
        check(set(value)=={'schema_version','lessons'} and value['schema_version']==1 and len(value['lessons'])<=8,'lessons','Invalid lesson file.')
        result=[]
        for row in value['lessons']:
            check(set(row)=={'rule_id','text','record_id','component_version','expires_at','review'},'lesson','Unexpected lesson fields.')
            check(row['rule_id'] in RULES and row['text']==RULES[row['rule_id']] and row['component_version']==VERSION,'lesson','Unrecognized rule/version.')
            check(re.fullmatch('[0-9a-f]{64}',row['record_id']) is not None,'lesson','Review record required.')
            review=row['review'];check(set(review)=={'reviewer','reviewed_at','decision'} and review['decision']=='approve' and re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,47}',review['reviewer']) is not None,'lesson','Explicit review provenance required.')
            check(type(review['reviewed_at']) in (int,float) and 0<=review['reviewed_at']<=now and now<row['expires_at']<=review['reviewed_at']+7*86400,'lesson','Review/expiry inapplicable.')
            result.append(copy.deepcopy(row))
        return result
    except Exception:return []
