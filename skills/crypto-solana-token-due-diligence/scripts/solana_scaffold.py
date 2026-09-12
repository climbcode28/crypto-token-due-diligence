"""Scaffold preserves supported facts while leaving analyst decisions unmistakably TODO."""
import copy
from pathlib import Path
from solana_facts import build,encoded,atomic
from solana_pipeline_note import build_note
from solana_profile import PROFILE,DIMENSIONS,AXES,regular,strict_json,check
from solana_compose import empty_coverage,CHECKLISTS

VERSION='1.0.0'


def scaffold(root,owner='coordinator',allow_synthetic=False):
    check(owner in ('coordinator','liquidity','project'),'owner','Known owner required.')
    root=Path(root).resolve();facts=build(root,allow_synthetic);m=strict_json(regular(root,'manifest.json').read_bytes(),'manifest.json');pipeline=build_note(facts)
    note={'note_version':1,'profile':PROFILE,'owner':owner,'investigation_id':m['investigation_id'],'target':m['target'],
      'question':m['intake']['question'],'focus':m['intake']['focus'],'urls':m['intake']['urls'],'research_status':'partial','findings':[],
      'signal_assignments':{},'overrides':[],'coverage':[],'summary_ids':[],'decision':None,'limitations':[],
      'alias_hints':facts['aliases'],'outstanding_leads':facts['missing_reads']}
    if owner=='coordinator':
        note['signal_assignments']={f['id']:{'signal':None} for f in pipeline['findings']}
        note['coverage']=[empty_coverage(dim,[f['id'] for f in pipeline['findings'] if f['dimension']==dim],
            [a['id'] for a in m['attempts'] if a['dimension']==dim]) for dim in DIMENSIONS]
        note['judgment_todo']='TODO: review facts, assign signals, complete coverage and explicitly answer every original ask.'
        note['decision_template']={'verdict_kind':'TODO','text':'TODO','requirements':[{'quote':m['intake']['question'],'status':'unverified','text':'TODO','finding_ids':[]}],
         'axes':{a:{'text':'TODO','finding_ids':[],'coverage_dimensions':[]} for a in AXES},'finding_ids':[],'counterevidence_ids':[],'mitigations':[],'actions':[]}
    else:
        note['checklist']={k:{'status':'pending','reason':'TODO'} for k in CHECKLISTS[owner]};note['evidence_ids']=[];note['imports']=[]
    return note


def write(root,owner='coordinator',allow_synthetic=False):
    root=Path(root).resolve();check(not (root/'notes').is_symlink(),'notes','Symlink notes directory forbidden.');path=root/'notes'/(owner+'.json')
    check(not path.exists(),str(path),'Existing analyst note retained; choose a new path or edit it explicitly.')
    note=scaffold(root,owner,allow_synthetic);atomic(path,encoded(note));return note
