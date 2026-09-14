"""Scaffold preserves supported facts while leaving analyst decisions unmistakably TODO."""
import copy
from pathlib import Path
from solana_facts import build,encoded,atomic
from solana_pipeline_note import build_note
from solana_profile import PROFILE,DIMENSIONS,AXES,regular,strict_json,check
from solana_compose import empty_coverage,CHECKLISTS
from solana_coverage import mechanical,untouched,leads_for,checklists_from_notes,lane_findings_from_notes

VERSION='1.3.0'


def scaffold(root,owner='coordinator',allow_synthetic=False):
    check(owner in ('coordinator','liquidity','project'),'owner','Known owner required.')
    root=Path(root).resolve();facts=build(root,allow_synthetic);m=strict_json(regular(root,'manifest.json').read_bytes(),'manifest.json');leads=leads_for(root);pipeline=build_note(facts,leads)
    note={'note_version':1,'profile':PROFILE,'owner':owner,'investigation_id':m['investigation_id'],'target':m['target'],
      'question':m['intake']['question'],'focus':m['intake']['focus'],'urls':m['intake']['urls'],'research_status':'partial','findings':[],
      'signal_assignments':{},'overrides':[],'coverage':[],'summary_ids':[],'decision':None,'limitations':[],
      'alias_hints':facts['aliases'],'outstanding_leads':facts['missing_reads']}
    if owner=='coordinator':
        digests={o['id']:o['sha256'] for o in m['observations']}
        # One assignment per fact (field-level restatements inherit it); each carries the digest of the fact it judges.
        from solana_pipeline_note import restatement_parent
        by_id={f['id']:f for f in pipeline['findings']};parents=[f for f in pipeline['findings'] if restatement_parent(f,by_id) is None]
        note['signal_assignments']={f['id']:{'signal':None,'input_digests':{r['evidence_id']:digests[r['evidence_id']] for r in f['support']}} for f in parents}
        # Each surface closes itself from the facts when its route ran and answered; the coordinator edits a row only to disagree.
        note['coverage']=[mechanical(dim,[f for f in pipeline['findings'] if f['dimension']==dim],facts['facts'],
            [a['id'] for a in m['attempts'] if a['dimension']==dim],leads=leads,checklists=None) for dim in DIMENSIONS]
        note['judgment_todo']=('TODO: review facts, assign signals, review the prefilled coverage rows (edit one only to disagree) and explicitly answer every original ask. '
            'Copy decision_template into decision; mitigations rows are {finding_id, status: unmitigated|partial|mitigated, text, evidence_ids}, '
            'actions rows are {kind: user_choice|risk_response, text}; a support whose subject is not the finding subject must be listed in participants; '
            'cite a failed read in a coverage_gap with role attempt.')
        note['decision_template']={'verdict_kind':'TODO','text':'TODO','requirements':[{'quote':m['intake']['question'],'status':'unverified','text':'TODO','finding_ids':[]}],
         'axes':{a:{'text':'TODO','finding_ids':[],'coverage_dimensions':[]} for a in AXES},'finding_ids':[],'counterevidence_ids':[],'mitigations':[],'actions':[]}
    else:
        note['checklist']={k:{'status':'pending','reason':'TODO'} for k in CHECKLISTS[owner]};note['evidence_ids']=[];note['imports']=[]
    return note


def sync_assignments(root):
    """After a refresh: add null assignments for new facts and refresh digests of unjudged ones; judged entries are never touched."""
    root=Path(root);path=root/'notes/coordinator.json'
    if not path.exists():return None
    from solana_pipeline_note import restatement_parent,generate
    note=strict_json(path.read_bytes(),'coordinator note');m=strict_json(regular(root,'manifest.json').read_bytes(),'manifest.json')
    digests={o['id']:o['sha256'] for o in m['observations']};facts=build(root,m['synthetic']);pipeline=generate(root,m['synthetic'],facts=facts)
    assignments=note.setdefault('signal_assignments',{});changed=0;by_id={f['id']:f for f in pipeline['findings']}
    for f in pipeline['findings']:
        if restatement_parent(f,by_id) is not None:continue
        current={r['evidence_id']:digests[r['evidence_id']] for r in f['support']}
        entry=assignments.get(f['id'])
        if entry is None:assignments[f['id']]={'signal':None,'input_digests':current};changed+=1
        elif isinstance(entry,dict) and entry.get('signal') is None and entry.get('input_digests')!=current:entry['input_digests']=current;changed+=1
    # Untouched coverage rows follow the facts and the lane notes on disk: a preset or a lane result that closed a surface closes its row.
    leads=leads_for(root);checklists=checklists_from_notes(root) or None;lane=lane_findings_from_notes(root);rows=[]
    for row in note.get('coverage',[]):
        if isinstance(row,dict) and untouched(row) and row.get('dimension'):
            fresh=mechanical(row['dimension'],[f for f in pipeline['findings']+lane if f.get('dimension')==row['dimension']],facts['facts'],
                [a['id'] for a in m['attempts'] if a['dimension']==row['dimension']],leads=leads,checklists=checklists)
            if fresh!=row:changed+=1
            rows.append(fresh)
        else:rows.append(row)
    note['coverage']=rows
    if changed:atomic(path,encoded(note))
    return changed


def write(root,owner='coordinator',allow_synthetic=False):
    root=Path(root).resolve();check(not (root/'notes').is_symlink(),'notes','Symlink notes directory forbidden.');path=root/'notes'/(owner+'.json')
    check(not path.exists(),str(path),'Existing analyst note retained; choose a new path or edit it explicitly.')
    note=scaffold(root,owner,allow_synthetic);atomic(path,encoded(note));return note
