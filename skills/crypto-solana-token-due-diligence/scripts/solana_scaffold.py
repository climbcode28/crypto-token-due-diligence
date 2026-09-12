"""Scaffold preserves supported facts while leaving analyst decisions unmistakably TODO."""
import copy
from pathlib import Path
from solana_facts import build,encoded,atomic
from solana_pipeline_note import build_note
from solana_profile import PROFILE,DIMENSIONS,AXES,regular,strict_json,check
from solana_compose import empty_coverage,CHECKLISTS

VERSION='1.1.0'


def scaffold(root,owner='coordinator',allow_synthetic=False):
    check(owner in ('coordinator','liquidity','project'),'owner','Known owner required.')
    root=Path(root).resolve();facts=build(root,allow_synthetic);m=strict_json(regular(root,'manifest.json').read_bytes(),'manifest.json');pipeline=build_note(facts)
    note={'note_version':1,'profile':PROFILE,'owner':owner,'investigation_id':m['investigation_id'],'target':m['target'],
      'question':m['intake']['question'],'focus':m['intake']['focus'],'urls':m['intake']['urls'],'research_status':'partial','findings':[],
      'signal_assignments':{},'overrides':[],'coverage':[],'summary_ids':[],'decision':None,'limitations':[],
      'alias_hints':facts['aliases'],'outstanding_leads':facts['missing_reads']}
    if owner=='coordinator':
        digests={o['id']:o['sha256'] for o in m['observations']}
        # One assignment per fact (field-level restatements inherit it); each carries the digest of the fact it judges.
        from solana_pipeline_note import finding_id
        parents=[f for f in pipeline['findings'] if f['id']==finding_id(f['support'][0]['evidence_id'])]
        note['signal_assignments']={f['id']:{'signal':None,'input_digests':{r['evidence_id']:digests[r['evidence_id']] for r in f['support']}} for f in parents}
        note['coverage']=[empty_coverage(dim,[f['id'] for f in pipeline['findings'] if f['dimension']==dim],
            [a['id'] for a in m['attempts'] if a['dimension']==dim]) for dim in DIMENSIONS]
        note['judgment_todo']='TODO: review facts, assign signals, complete coverage and explicitly answer every original ask.'
        note['decision_template']={'verdict_kind':'TODO','text':'TODO','requirements':[{'quote':m['intake']['question'],'status':'unverified','text':'TODO','finding_ids':[]}],
         'axes':{a:{'text':'TODO','finding_ids':[],'coverage_dimensions':[]} for a in AXES},'finding_ids':[],'counterevidence_ids':[],'mitigations':[],'actions':[]}
    else:
        note['checklist']={k:{'status':'pending','reason':'TODO'} for k in CHECKLISTS[owner]};note['evidence_ids']=[];note['imports']=[]
    return note


def sync_assignments(root):
    """After a refresh: add null assignments for new facts and refresh digests of unjudged ones; judged entries are never touched."""
    root=Path(root);path=root/'notes/coordinator.json'
    if not path.exists():return None
    from solana_pipeline_note import finding_id,generate
    note=strict_json(path.read_bytes(),'coordinator note');m=strict_json(regular(root,'manifest.json').read_bytes(),'manifest.json')
    digests={o['id']:o['sha256'] for o in m['observations']};pipeline=generate(root,m['synthetic'])
    assignments=note.setdefault('signal_assignments',{});changed=0
    for f in pipeline['findings']:
        if f['id']!=finding_id(f['support'][0]['evidence_id']):continue
        current={r['evidence_id']:digests[r['evidence_id']] for r in f['support']}
        entry=assignments.get(f['id'])
        if entry is None:assignments[f['id']]={'signal':None,'input_digests':current};changed+=1
        elif isinstance(entry,dict) and entry.get('signal') is None and entry.get('input_digests')!=current:entry['input_digests']=current;changed+=1
    if changed:atomic(path,encoded(note))
    return changed


def write(root,owner='coordinator',allow_synthetic=False):
    root=Path(root).resolve();check(not (root/'notes').is_symlink(),'notes','Symlink notes directory forbidden.');path=root/'notes'/(owner+'.json')
    check(not path.exists(),str(path),'Existing analyst note retained; choose a new path or edit it explicitly.')
    note=scaffold(root,owner,allow_synthetic);atomic(path,encoded(note));return note
