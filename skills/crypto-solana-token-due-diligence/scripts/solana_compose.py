"""Small analyst notes to validated v2 drafts. Checks are read-only."""
from contextlib import contextmanager
import copy,fcntl,json,os
from pathlib import Path
from solana_common import need,sha
from solana_facts import build as facts_build,encoded,atomic
from solana_pipeline_note import build_note
from solana_profile import (PROFILE,DIMENSIONS,AXES,Evidence,ProfileError,regular,strict_json,check,
    validate_report,findings as validate_findings,coverage as validate_coverage,decision as validate_decision)

VERSION='1.1.0'
OWNERS=('coordinator','liquidity','project')
CHECKLISTS={'liquidity':('discovery','custody','activity','exits','assigned_asks'),
 'project':('identity','delivery','audit_scope','economics','creator_history','contrary_evidence','assigned_asks')}
SIGNALS=(None,'good','potential_risk','bad','unverified')


class ComposeError(ValueError):
    def __init__(self,errors):
        self.errors=errors;super().__init__('; '.join(e['path']+': '+e['message'] for e in errors))


def error(errors,path,message):errors.append({'path':path,'message':message})


def caught(errors,path,fn):
    try:return fn()
    except (ValueError,KeyError,TypeError,IndexError,AttributeError) as exc:
        error(errors,path,str(exc));return None


def placeholders(value,path,errors):
    import re
    if isinstance(value,str) and re.search(r'\bTODO\b|\bTBD\b',value,re.I):error(errors,path,'Replace TODO/TBD with an evidence-backed judgment or a precise unresolved limitation.')
    elif isinstance(value,dict):
        for k,v in value.items():placeholders(v,path+'.'+k,errors)
    elif isinstance(value,list):
        for i,v in enumerate(value):placeholders(v,path+'['+str(i)+']',errors)


def read_note(root,name):return strict_json(regular(root,name).read_bytes(),name)


def alias(value,facts,evidence,path):
    if value in evidence.rows:return value
    choices=facts['aliases'].get(value,[])
    check(len(choices)==1,path,'Alias must resolve uniquely in this run; use an exact evidence ID. Candidates: '+repr(choices))
    return choices[0]


def expand_finding(value,owner,facts,evidence,path):
    f=copy.deepcopy(value);fid=f['id']
    for name in ('dimension','claim','strength','text'):
        check(name in f,path+'.'+name,'Required field; provide an explicit scoped value.')
    check(f['dimension'] in DIMENSIONS,path+'.dimension','Use a defined coverage dimension: '+repr(DIMENSIONS))
    check(isinstance(fid,str) and fid.startswith(owner+'-'),path+'.id','Finding ID must start with '+owner+'-; another owner cannot be replaced.')
    sub=f.get('subject',{'genesis_hash':evidence.target['genesis_hash'],'kind':'mint','address':evidence.target['mint']})
    supports=[]
    for j,raw in enumerate(f.get('support',[])):
        row={'alias':raw} if isinstance(raw,str) else copy.deepcopy(raw)
        eid=alias(row.pop('alias',row.get('evidence_id')),facts,evidence,path+'.support['+str(j)+']')
        obs=evidence.rows[eid];role=row.get('role','derivation' if obs['kind']=='derived' else 'publication' if obs['kind']=='document' else 'state')
        row.update(evidence_id=eid,role=role,subject=row.get('subject',obs['subject']));supports.append(row)
    if 'subject' not in f and supports and all(r['subject']==supports[0]['subject'] for r in supports):sub=copy.deepcopy(supports[0]['subject'])
    counter=[]
    for j,raw in enumerate(f.get('counterevidence',[])):
        row={'alias':raw} if isinstance(raw,str) else copy.deepcopy(raw);eid=alias(row.pop('alias',row.get('evidence_id')),facts,evidence,path+'.counterevidence['+str(j)+']')
        obs=evidence.rows[eid];row.update(evidence_id=eid,subject=row.get('subject',obs['subject']),role=row.get('role','derivation' if obs['kind']=='derived' else 'publication' if obs['kind']=='document' else 'state'));counter.append(row)
    samples=sorted({evidence.rows[x]['sample_id'] for r in supports for x in {r['evidence_id'],*evidence.closure.get(r['evidence_id'],set())} if evidence.rows[x].get('sample_id')})
    default={'owner':owner,'subject':sub,'participants':[],'signal':None,'confidence':'medium','impact':'informational','counterevidence':[],
       'time_basis':{'kind':'mixed','sample_ids':samples,'stability':'not_asserted'},'limitations':[],'concern':None}
    return {**default,**f,'owner':owner,'support':supports,'counterevidence':counter}


def note_header(note,owner,m,errors,path):
    check(isinstance(note,dict),path,'Note must be a JSON object.')
    for k,expected in (('note_version',1),('profile',PROFILE),('owner',owner),('investigation_id',m['investigation_id']),('target',m['target']),('question',m['intake']['question']),('focus',m['intake']['focus'])):
        if note.get(k)!=expected:error(errors,path+'.'+k,'Must match this run exactly: '+str(expected))
    if owner!='coordinator' and (note.get('signal_assignments') or note.get('overrides') or note.get('decision')):error(errors,path,'Lanes may only author their own findings and checklist; coordinator owns assignments, overrides and decision.')
    if m['intake']['scope']=='focused' and owner!='coordinator':error(errors,path,'Focused runs do not use broad lanes.')


def validate_imports(root,note,owner,e,errors,path):
    for i,row in enumerate(note.get('imports',[])):
        at=path+'.imports['+str(i)+']'
        def run():
            name=row['path'];raw=regular(root,name).read_bytes();eid=row['evidence_id'];obs=e.rows[eid]
            check(name==obs['artifact'] and sha(raw)==row['sha256']==obs['sha256'],at,'Import must match registered evidence path and digest.')
            check(name.startswith('lanes/'+owner+'/') or obs.get('source',{}).get('owner') in (owner,'shared'),at,'Import belongs to another lane; cite its existing ID without replacing it.')
        caught(errors,at,run)


def empty_coverage(dim,ids=(),attempts=()):
    return {'dimension':dim,'status':'partial' if ids else 'not_checked','finding_ids':list(ids),'attempt_ids':list(attempts),
      'decision_impact':'Assessment pending.','pending_work':['Complete the standard surface checklist.'],
      'closure':{'reason':'Standard work remains.','attempt_ids':[],'next_route':'standard','boundary':'pending','standard_scope_complete':False}}


def preflight(e,report,digest):
    errors=[];completed=report.get('research_status')=='completed'
    if completed:placeholders(report,'report',errors)
    for i,f in enumerate(report.get('findings',[])):
        caught(errors,'report.findings['+str(i)+']',lambda f=f:validate_findings(e,{'findings':[f]},completed))
    known={f['id']:f for f in report.get('findings',[]) if isinstance(f,dict) and 'id' in f}
    caught(errors,'report.coverage',lambda:validate_coverage(e,report,known,completed))
    covered={r['dimension']:r for r in report.get('coverage',[]) if isinstance(r,dict) and 'dimension' in r}
    caught(errors,'report.decision',lambda:validate_decision(e,report,known,covered,completed))
    caught(errors,'report',lambda:validate_report(e,report,digest))
    return list({(r['path'],r['message']):r for r in errors}.values())


def assemble(root,note,*,lane_notes=None,allow_synthetic=False):
    root=Path(root).resolve();raw=regular(root,'manifest.json').read_bytes();m=strict_json(raw,'manifest.json');e=Evidence(root,m,allow_synthetic)
    facts=facts_build(root,allow_synthetic);pipeline=build_note(facts);errors=[];note=copy.deepcopy(note)
    note_header(note,'coordinator',m,errors,'note')
    if note.get('research_status')=='completed':placeholders(note,'note',errors)
    rows=copy.deepcopy(pipeline['findings']);pipeline_rows={f['id']:f for f in rows}
    notes={'coordinator':note,**(lane_notes or {})}
    check(set(notes)<=set(OWNERS),'notes','Unknown note owner.')
    new_lanes=[]
    for owner,n in notes.items():
        path='notes.'+owner;note_header(n,owner,m,errors,path);validate_imports(root,n,owner,e,errors,path)
        for i,value in enumerate(n.get('findings',[])):
            at=path+'.findings['+str(i)+']'
            if isinstance(value,dict):
                for field,accepted in (('claim',('state_observation','historical_execution','source_analysis','inference','coverage_gap')),('strength',('direct','corroborated','bounded','unresolved')),('dimension',DIMENSIONS)):
                    if value.get(field) not in accepted:error(errors,at+'.'+field,'Use one of '+repr(accepted)+'; retain the evidence scope.')
                for field,accepted in (('signal',SIGNALS),('confidence',('high','medium','low')),('impact',('critical','high','medium','low','informational'))):
                    if field in value and value[field] not in accepted:error(errors,at+'.'+field,'Use one of '+repr(accepted)+'.')
            f=caught(errors,path+'.findings['+str(i)+']',lambda value=value:expand_finding(value,owner,facts,e,path))
            if f is not None:rows.append(f)
        if owner!='coordinator':
            checks=n.get('checklist',{});ids=n.get('evidence_ids',[])
            if set(checks)!=set(CHECKLISTS[owner]):error(errors,path+'.checklist','Use all required checklist keys: '+repr(CHECKLISTS[owner]))
            for k,v in checks.items():
                if not isinstance(v,dict) or v.get('status') not in ('done','external_limit','pending') or not v.get('reason'):error(errors,path+'.checklist.'+k,'Use status done/external_limit/pending and a concrete reason.')
            if not isinstance(ids,list) or not ids or not all(i in e.rows for i in ids):error(errors,path+'.evidence_ids','Self-check needs existing evidence IDs.')
            status='returned' if checks and all(isinstance(v,dict) and v.get('status')!='pending' for v in checks.values()) else 'partial'
            if status=='returned':placeholders(n,path,errors)
            new_lanes.append({'owner':owner,'status':status,'self_check':True,'note_artifact':'notes/'+owner+'.json','evidence_ids':ids})
    if len({f['id'] for f in rows})!=len(rows):error(errors,'notes.findings','Duplicate finding IDs; each lane owns its prefix.')
    conflicts=[]
    for a in rows:
        for b in rows:
            if a['id']>=b['id'] or a['owner']==b['owner'] or 'pipeline' in (a['owner'],b['owner']):continue
            shared={r['evidence_id'] for r in a['support']} & {r['evidence_id'] for r in b['support']}
            if a['subject']==b['subject'] and a['dimension']==b['dimension'] and shared and 'good' in (a['signal'],b['signal']) and any(s in ('bad','potential_risk') for s in (a['signal'],b['signal'])):
                conflicts.append({'finding_ids':[a['id'],b['id']],'evidence_ids':sorted(shared),'issue':'Different owners assign opposing signals to the same subject/evidence; coordinator review required.'})
    for conflict in conflicts:
        resolved=any(set(r.get('finding_ids',[]))==set(conflict['finding_ids']) and r.get('reason','').strip() and set(r.get('evidence_ids',[]))>=set(conflict['evidence_ids']) for r in note.get('conflict_resolutions',[]))
        conflict['resolved']=resolved
        if note.get('research_status')=='completed' and not resolved:error(errors,'note.conflict_resolutions',conflict['issue']+' '+repr(conflict['finding_ids']))
    for fid,value in note.get('signal_assignments',{}).items():
        if fid not in pipeline_rows:error(errors,'note.signal_assignments.'+fid,'Stale or non-pipeline finding; regenerate the scaffold and use a current ID.');continue
        assignment=copy.deepcopy({'signal':value} if value in SIGNALS else value)
        if not isinstance(assignment,dict) or set(assignment)-{'signal','impact','confidence','concern','input_digests'}:error(errors,'note.signal_assignments.'+fid,'Use signal plus optional impact/confidence/concern and the fact input_digests.');continue
        digests=assignment.pop('input_digests',None)
        if assignment.get('signal') is not None:
            # A signal binds to the fact bytes it judged; a regenerated fact needs re-review, never a silent carry-over.
            expected={r['evidence_id']:e.rows[r['evidence_id']]['sha256'] for r in pipeline_rows[fid]['support']}
            if digests!=expected:error(errors,'note.signal_assignments.'+fid+'.input_digests','Bind the signal to the current fact digest(s) '+json.dumps(expected,sort_keys=True)+'; a changed fact needs re-review.');continue
        pipeline_rows[fid].update(assignment)
    # Field-level restatements of one fact inherit that fact's judgment unless assigned explicitly,
    # so a coordinator judges each fact once rather than every typed field.
    from solana_pipeline_note import finding_id
    for fid,row in pipeline_rows.items():
        parent=finding_id(row['support'][0]['evidence_id']) if row.get('support') else None
        if row.get('signal') is None and parent and parent!=fid and parent in pipeline_rows and pipeline_rows[parent].get('signal') is not None:
            for k in ('signal','confidence','concern'):  # Severity (impact) stays on the parent fact only.
                if pipeline_rows[parent].get(k) is not None:row[k]=copy.deepcopy(pipeline_rows[parent][k])
    for i,override in enumerate(note.get('overrides',[])):
        at='note.overrides['+str(i)+']'
        def apply_override():
            fid=override['finding_id'];check(fid in pipeline_rows,at,'Override names a stale pipeline finding.')
            f=pipeline_rows[fid];check(bool(override.get('reason','').strip()),at+'.reason','Explain the correction.')
            ids=override.get('evidence_ids');check(isinstance(ids,list) and ids and all(x in e.usable for x in ids),at+'.evidence_ids','Correction requires current usable evidence.')
            check(override.get('input_digests')=={x:e.rows[x]['sha256'] for x in ids},at+'.input_digests','Correction evidence changed or lacks digests; review and bind the current evidence bytes.')
            changes=override['changes'];check(isinstance(changes,dict) and set(changes)<={'text','signal','impact','confidence','concern','limitations','assertion'},at+'.changes','Only explicit judgment/text corrections are permitted.')
            f.update(copy.deepcopy(changes));f['override']={'reason':override['reason'],'evidence_ids':ids}
            for eid in ids:
                if not any(r['evidence_id']==eid for r in f['counterevidence']):f['counterevidence'].append({'evidence_id':eid,'subject':e.rows[eid]['subject'],'role':'derivation' if e.rows[eid]['kind']=='derived' else 'publication' if e.rows[eid]['kind']=='document' else 'state'})
        caught(errors,at,apply_override)
    coverage_rows=[];supplied={r.get('dimension'):r for r in note.get('coverage',[]) if isinstance(r,dict)}
    if len(supplied)!=len(note.get('coverage',[])) or not set(supplied)<=set(DIMENSIONS):error(errors,'note.coverage','Unique known coverage dimensions required.')
    ratings={}
    for dim in DIMENSIONS:
        found=[f for f in rows if f['dimension']==dim];ids=[f['id'] for f in found];attempts=[a['id'] for a in m['attempts'] if a['dimension']==dim]
        row=copy.deepcopy(supplied.get(dim,empty_coverage(dim,ids,attempts)));row['finding_ids']=ids;row.setdefault('attempt_ids',attempts);coverage_rows.append(row)
        ratings[dim]='concern' if any(f['signal'] in ('bad','potential_risk') for f in found) else 'not_applicable' if row['status']=='not_applicable' else 'no_issue_detected' if row['status']=='checked' and found and all(f['signal']=='good' for f in found) else 'unknown'
    summary=list(note.get('summary_ids',[]));decision=copy.deepcopy(note.get('decision'))
    severe=[f['id'] for f in rows if f['signal'] in ('bad','potential_risk') and f['impact'] in ('high','critical')]
    summary=list(dict.fromkeys(summary+severe))
    # Include the actual supplied lane bytes, without granting trust to its self-check label.
    m2=copy.deepcopy(m)
    if new_lanes:
        for lane in new_lanes:
            path=lane['note_artifact'];data=regular(root,path).read_bytes()
            check(strict_json(data,path)==notes[lane['owner']],path,'Lane file changed during composition.')
            m2['artifacts']=[r for r in m2['artifacts'] if r['path']!=path]+[{'path':path,'sha256':sha(data),'bytes':len(data)}]
        m2['lanes']=new_lanes
    digest=sha(encoded(m2)) if new_lanes else sha(raw)
    report={'schema_version':2,'profile':PROFILE,'investigation_id':m['investigation_id'],'target':m['target'],'synthetic':m['synthetic'],
      'question':m['intake']['question'],'focus':m['intake']['focus'],'scope':m['intake']['scope'],'manifest_sha256':digest,
      'research_status':note.get('research_status','partial'),'delivery_status':'draft','findings':rows,'ratings':ratings,'coverage':coverage_rows,
      'summary_ids':summary,'decision':decision,'limitations':note.get('limitations',[]),'coordinator_issues':conflicts}
    e2=Evidence(root,m2,allow_synthetic) if new_lanes else e
    errors+=preflight(e2,report,digest)
    if errors:raise ComposeError(errors)
    check(regular(root,'manifest.json').read_bytes()==raw,'manifest','Evidence changed during composition; retry against current facts.')
    snapshots={}
    for lane in new_lanes:
        old=lane['note_artifact'];data=regular(root,old).read_bytes()
        path='note-snapshots/'+lane['owner']+'-'+sha(data)+'.json';snapshots[path]=data
        m2['artifacts']=[r for r in m2['artifacts'] if r['path'] not in (old,path)]+[{'path':path,'sha256':sha(data),'bytes':len(data)}]
        lane['note_artifact']=path
    manifest_raw=encoded(m2) if new_lanes else raw
    report['manifest_sha256']=sha(manifest_raw)
    return m2,report,manifest_raw,snapshots


@contextmanager
def draft_lock(root):
    path=root/'.compose.lock';check(not path.is_symlink(),str(path),'Symlink lock forbidden.')
    with path.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def save_pair(root,manifest_raw,report):
    """Recoverable two-file mutation; never expose a crash as a valid completed draft."""
    journal=root/'.draft-transaction.json';old={n:regular(root,n).read_text() if (root/n).exists() or (root/n).is_symlink() else None for n in ('manifest.json','report.json')}
    atomic(journal,encoded(old))
    try:
        atomic(root/'manifest.json',manifest_raw);atomic(root/'report.json',encoded(report));journal.unlink()
    except BaseException:
        recover(root);raise


def recover(root):
    journal=root/'.draft-transaction.json'
    if not journal.exists():return
    old=strict_json(regular(root,journal.name).read_bytes(),journal.name)
    check(set(old)=={'manifest.json','report.json'},journal.name,'Invalid recovery journal.')
    for name,value in old.items():
        if value is None:
            if (root/name).exists():(root/name).unlink()
        else:atomic(root/name,value.encode())
    journal.unlink()


def compose(root,note_name='notes/coordinator.json',*,lane_names=None,allow_synthetic=False,check_only=False):
    root=Path(root).resolve()
    check(not (root/'delivery.json').exists(),'draft','Frozen bundles are immutable; compose only an active draft.')
    def run():
        note=read_note(root,note_name)
        selected={o:'notes/'+o+'.json' for o in CHECKLISTS if (root/'notes'/(o+'.json')).exists()}
        selected.update(lane_names or {})
        check(all(n=='notes/'+o+'.json' for o,n in selected.items()),'lane notes','Each lane must use its fixed owned notes path.')
        lanes={o:read_note(root,n) for o,n in selected.items()}
        m,r,raw,snapshots=assemble(root,note,lane_notes=lanes,allow_synthetic=allow_synthetic)
        if not check_only:
            check(not (root/'note-snapshots').is_symlink(),'note-snapshots','Symlink snapshot directory forbidden.')
            for name,data in snapshots.items():
                path=root/name
                if path.exists():check(regular(root,name).read_bytes()==data,name,'Immutable note snapshot changed.')
                else:atomic(path,data)
            validate_report(Evidence(root,m,allow_synthetic),r,sha(raw))
            save_pair(root,raw,r)
        return {'valid':True,'written':not check_only,'research_status':r['research_status'],'findings':len(r['findings']),'report':r}
    if check_only:
        check(not (root/'.draft-transaction.json').exists(),'draft','Interrupted composition requires recovery before checking.');return run()
    with draft_lock(root):recover(root);return run()
