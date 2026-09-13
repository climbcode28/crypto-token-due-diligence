"""Unjudged pipeline observations, regenerated independently of analyst assignments."""
from pathlib import Path
from solana_facts import build,atomic,encoded
from solana_profile import PROFILE
from solana_common import sha,need

VERSION='1.0.0'
DIMENSIONS={'controls':'token_controls','holders':'current_concentration','programs':'external_dependencies',
 'pools':'canonical_lp_principal_custody','quotes':'sellability_exit_depth','transactions':'sellability_exit_depth',
 'launch':'historical_launch_integrity','creator':'admin_treasury_reward_custody','maturity':'development_disclosure','source_assurance':'development_disclosure',
 'corroboration':'current_concentration'}


def finding_id(eid,field=None):
    value='pipeline-'+eid+('-'+field if field else '')
    return value if len(value)<=80 else value[:55]+'-'+sha(value.encode())[:24]


def findings(facts):
    rows=[]
    for fact in facts['facts']:
        op=fact['operation'];usable=fact['usable'];dim=DIMENSIONS[fact['category']]
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
    need(len(rows)<=500,'pipeline finding bound exceeded; narrow the selected dependency set')
    return rows


def build_note(facts):
    return {'note_version':1,'pipeline_version':VERSION,'profile':PROFILE,'owner':'pipeline',
      'investigation_id':facts['investigation_id'],'target':facts['target'],'question':facts['question'],'focus':facts['focus'],
      'manifest_sha256':facts['manifest_sha256'],'research_status':'partial','findings':findings(facts),
      'signal_assignments':{},'overrides':[],'coverage':[],'summary_ids':[],'decision':None,
      'limitations':['Machine-authored facts require analyst judgment; a sample is not a census and a quote is not execution.']}


def generate(root,allow_synthetic=False,*,facts=None):
    root=Path(root).resolve();facts=build(root,allow_synthetic) if facts is None else facts;note=build_note(facts)
    need(not (root/'notes').is_symlink(),'refuse symlink notes directory')
    atomic(Path(root)/'facts.json',encoded(facts));atomic(Path(root)/'notes/pipeline.json',encoded(note));return note
