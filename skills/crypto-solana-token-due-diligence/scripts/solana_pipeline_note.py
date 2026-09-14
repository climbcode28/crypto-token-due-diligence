"""Unjudged pipeline observations, regenerated independently of analyst assignments."""
from pathlib import Path
from solana_facts import build,atomic,encoded
from solana_profile import PROFILE
from solana_common import sha,need

VERSION='1.2.0'
DIMENSIONS={'controls':'token_controls','holders':'current_concentration','programs':'external_dependencies',
 'pools':'canonical_lp_principal_custody','quotes':'sellability_exit_depth','transactions':'sellability_exit_depth',
 'launch':'historical_launch_integrity','creator':'admin_treasury_reward_custody','maturity':'development_disclosure','source_assurance':'development_disclosure',
 'corroboration':'current_concentration'}


def finding_id(eid,field=None):
    value='pipeline-'+eid+('-'+field if field else '')
    return value if len(value)<=80 else value[:55]+'-'+sha(value.encode())[:24]


def restatement_parent(finding,by_id):
    """The pipeline finding this row restates (the typed fact it is a field of), or None: a restatement cites that fact as its
    first support and sits on the same surface. A pipeline observation on another surface (the no-side-pool row) is its own
    judged finding, never an inheritor."""
    if not isinstance(finding,dict) or finding.get('owner')!='pipeline' or not finding.get('support'):return None
    parent=finding_id(finding['support'][0]['evidence_id'])
    row=by_id.get(parent)
    return parent if parent!=finding.get('id') and row is not None and row.get('dimension')==finding.get('dimension') else None


def leading_pool(facts,leads=None):
    """The pool whose custody is the canonical surface: the run's first automatic lead, else the first discovery candidate
    that has a usable pool fact, else the first pool fact. Every other sampled pool is a side pool."""
    pools=[f['data'].get('pool') for f in facts['facts'] if f['operation']=='pool' and isinstance(f.get('data'),dict)]
    for lead in leads or []:
        if lead.get('pool') in pools:return lead['pool']
    for f in facts['facts']:
        if f['operation']=='discovery_pools' and f['usable']:
            for c in f['data'].get('candidates') or []:
                if c.get('pool') in pools:return c['pool']
    return pools[0] if pools else None


def findings(facts,leads=None,lane_keys=None):
    rows=[];lead=leading_pool(facts,leads)
    for fact in facts['facts']:
        op=fact['operation'];usable=fact['usable'];dim=DIMENSIONS[fact['category']]
        if op=='pool' and isinstance(fact.get('data'),dict) and fact['data'].get('pool')!=lead:dim='side_pool_removal_risk'  # a sampled side pool is the side-pool surface's own evidence
        claim=('source_analysis' if fact['category'] in ('maturity','source_assurance','corroboration') else 'inference' if fact['category'] in ('quotes','transactions','launch','creator') else 'state_observation') if usable else 'coverage_gap'
        base={'id':finding_id(fact['evidence_id']),'owner':'pipeline','dimension':dim,'claim':claim,'strength':'bounded' if usable else 'unresolved',
              'confidence':'medium' if usable else 'low','impact':'informational','signal':None,'subject':fact['subject'],'participants':[],
              'text':fact['summary'] if usable else 'The '+op+' dependencies are unresolved; computed values are not a supported conclusion.',
              'support':[{'evidence_id':fact['evidence_id'],'subject':fact['subject'],'role':'derivation' if usable else 'context'}],
              'counterevidence':[],'time_basis':{'kind':'mixed','sample_ids':fact['sample_ids'],'stability':'not_asserted'},
              'limitations':[str(r['path'])+': '+str(r['value']) for r in fact['limits']],'concern':None,'assertion':'observation'}
        if not usable:
            # The unusable inputs and why: a refused method, an unpinned recheck, a header outside the verified interval.
            base['limitations']+=[r['id']+': '+str(r.get('reason') or r['status']) for r in facts.get('missing_reads',[]) if r['id'] in fact['dependencies']]
        rows.append(base)
        # Split top-level typed fields into bounded precise restatements. No downstream
        # source text is promoted into executable instructions or assessment signals.
        if usable and isinstance(fact['data'],dict):
            for field,value in sorted(fact['data'].items()):
                if field in ('target','evidence','contexts','adapter','mint_accounts') or value in ({},[]):continue
                text=op+' '+field+': '+encoded(value).decode().strip()
                if len(text)>19000:
                    # Full facts remain inventoried; an explicit limit replaces an oversized claim.
                    base['limitations'].append('Oversized '+field+' details retained in facts.json#'+fact['id']+'; inspect before assigning judgment.')
                    continue
                row={**base,'id':finding_id(fact['evidence_id'],field),'text':text};rows.append(row)
    # A token with one discovered pool has no side pool: that is an observation from the discovery facts, stated so the
    # side-pool surface can close on it instead of waiting for a judgment nothing supports.
    discovery=[f for f in facts['facts'] if f['operation']=='discovery_pools' and f['usable']]
    pools={c.get('pool') for f in discovery for c in (f['data'].get('candidates') or []) if c.get('pool')}
    if discovery and len(pools)<=1:
        first=discovery[0]
        rows.append({'id':'pipeline-no-side-pool-'+sha(first['evidence_id'].encode())[:16],'owner':'pipeline','dimension':'side_pool_removal_risk','claim':'source_analysis','strength':'bounded',
            'confidence':'medium','impact':'informational','signal':None,'subject':first['subject'],'participants':[],
            'text':'Exact-mint discovery lists '+str(len(pools))+' pool; no side pool exists to sample. Indexed listings are publications, not proof that no other market exists.',
            'support':[{'evidence_id':f['evidence_id'],'subject':f['subject'],'role':'derivation'} for f in discovery],'counterevidence':[],
            'time_basis':{'kind':'mixed','sample_ids':first['sample_ids'],'stability':'not_asserted'},'limitations':['Discovery covers the indexers captured at start.'],'concern':None,'assertion':'observation'})
    # A creator key a lane named in its leads, once its signature history was read, is evidence on the admin/treasury surface
    # too (the pipeline attributed no key there): stated as its own observation that names the lane and its reason, so that
    # surface can close on it instead of waiting for a judgment nothing supports.
    from solana_coverage import lane_key_rows
    attributed={k.get('address') for f in facts['facts'] if f['operation']=='creator_activity' and f['usable'] for k in ((f.get('data') or {}).get('keys') or [])}
    by_key={r['value']:r for r in lane_key_rows(lane_keys)}
    for f in facts['facts']:
        d=f.get('data') if isinstance(f.get('data'),dict) else {}
        if f['operation']=='history' and f['usable'] and d.get('address') in by_key and d.get('address') not in attributed:
            row=by_key[d['address']];owner=str(row.get('owner') or 'project');reason=row.get('reason')
            rows.append({'id':'pipeline-lanekey-'+sha(f['evidence_id'].encode())[:16],'owner':'pipeline','dimension':'admin_treasury_reward_custody','claim':'state_observation','strength':'bounded',
                'confidence':'medium','impact':'informational','signal':None,'subject':f['subject'],'participants':[],
                'text':'Creator key '+d['address']+' was named by the '+owner+' lane'+(' ('+reason[:200]+')' if reason else '')+', not attributed by receipt, curve or metadata; its signature history was read: '+str(len(d.get('signatures') or []))+' signature(s) over '+str(d.get('pages_attempted'))+' page(s), slots ('+str(d.get('start_slot'))+', '+str(d.get('end_slot'))+'], window '+('covered' if d.get('window_covered') else 'not fully covered')+'. Creator sales and rebuys are not reconciled against a lane-named key.',
                'support':[{'evidence_id':f['evidence_id'],'subject':f['subject'],'role':'derivation'}],'counterevidence':[],
                'time_basis':{'kind':'mixed','sample_ids':f['sample_ids'],'stability':'not_asserted'},
                'limitations':['Lane attribution only ('+owner+' lane); no sampled receipt names this key.']+[str(r['path'])+': '+str(r['value']) for r in f.get('limits') or []],'concern':None,'assertion':'observation'})
    need(len(rows)<=500,'pipeline finding bound exceeded; narrow the selected dependency set')
    return rows


def build_note(facts,leads=None,lane_keys=None):
    return {'note_version':1,'pipeline_version':VERSION,'profile':PROFILE,'owner':'pipeline',
      'investigation_id':facts['investigation_id'],'target':facts['target'],'question':facts['question'],'focus':facts['focus'],
      'manifest_sha256':facts['manifest_sha256'],'research_status':'partial','findings':findings(facts,leads,lane_keys),
      'signal_assignments':{},'overrides':[],'coverage':[],'summary_ids':[],'decision':None,
      'limitations':['Machine-authored facts require analyst judgment; a sample is not a census and a quote is not execution.']}


def generate(root,allow_synthetic=False,*,facts=None):
    from solana_coverage import leads_for,lane_creator_leads_from_notes
    root=Path(root).resolve();facts=build(root,allow_synthetic) if facts is None else facts;note=build_note(facts,leads_for(root),lane_creator_leads_from_notes(root,facts['target']['mint']))
    need(not (root/'notes').is_symlink(),'refuse symlink notes directory')
    atomic(Path(root)/'facts.json',encoded(facts));atomic(Path(root)/'notes/pipeline.json',encoded(note));return note
