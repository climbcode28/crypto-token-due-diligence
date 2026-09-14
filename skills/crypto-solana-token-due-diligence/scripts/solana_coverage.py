"""Mechanical coverage closures: a surface whose standard route ran and answered closes itself from the typed facts; only a
route that never ran, an open coverage-gap finding or a lane item still pending keeps a row open. The coordinator may edit any
row (the edit is detected by digest and kept); an untouched row is recomputed at every refresh and at compose, so presets and
lane results that arrive after the scaffold close their surfaces without a judgment turn."""
from solana_common import sha
from solana_facts import encoded
from solana_pipeline_note import leading_pool

VERSION='1.0.1'
LANE_ITEMS={'development_disclosure':('project',('delivery','audit_scope')),'utility_redemption_rights':('project',('economics',)),
 'reward_accounting_liveness':('project',('economics',))}
PROGRAM_GAPS=('program_upgrade_authority_unresolved','program_control_not_observed')
CONCENTRATED=('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2')
ROW_KEYS=('status','decision_impact','pending_work','closure')


def sampled_ok(pool):
    """A pool fact answered custody when it is observed, or when its only open items are program control (rated under
    external dependencies) while every sampled position resolved and reserves are known or never inferred (concentrated)."""
    if pool.get('status')=='observed':return True,[]
    gaps=[g for g in (pool.get('gaps') or []) if g not in PROGRAM_GAPS]
    if pool.get('position_coverage','sampled')!='sampled':gaps.append('position coverage '+str(pool.get('position_coverage')))
    if pool.get('reserves_atomic') is None and (pool.get('adapter') or {}).get('id') not in CONCENTRATED:gaps.append('reserves not inferred')
    return not gaps,gaps


def digest(row):
    return sha(encoded({k:row.get(k) for k in ROW_KEYS}))


def untouched(row):
    """True when the row is still the mechanical prefill (the coordinator changed nothing)."""
    return isinstance(row,dict) and isinstance(row.get('prefill'),dict) and row['prefill'].get('digest')==digest(row)


def _by_op(facts):
    out={}
    for f in facts:
        if isinstance(f,dict) and f.get('usable'):out.setdefault(f.get('operation'),[]).append(f.get('data') or {})
    return out


def _pools_discovered(by_op):
    return {c.get('pool') for d in by_op.get('discovery_pools',[]) for c in d.get('candidates',[]) if c.get('pool')}


def rule(dim,by_op,leads,checklists,facts_all=()):
    """(resolved, reason, next_route) for one surface from the usable facts alone; findings and gaps are applied by mechanical()."""
    pools=by_op.get('pool',[]);by_pool={d.get('pool'):d for d in pools}
    # The leading pool is the pipeline note's (automatic lead, else discovery order, else fact order) so the custody row judges the
    # pool whose findings sit on that surface; every other sampled pool is a side pool, lane-led ones first.
    lead_id=leading_pool({'facts':[f for f in facts_all if isinstance(f,dict)]},leads) if facts_all else (pools[0].get('pool') if pools else None)
    side=[by_pool[l['pool']] for l in (leads or []) if l.get('pool') in by_pool and l['pool']!=lead_id]+[d for d in pools if d.get('pool')!=lead_id and not any(l.get('pool')==d.get('pool') for l in (leads or []))]
    if dim=='token_controls':
        if by_op.get('controls'):return True,'The mint account was sampled and decoded: mint and freeze authorities, extensions and the owning program are typed facts.',None
        return False,'No usable mint controls fact: the identity read did not resolve.','standard'
    if dim=='current_concentration':
        h=[d for d in by_op.get('holders',[]) if d.get('status') in ('observed','sampled')]
        if h:return True,('Holders fact '+str(h[0].get('status'))+': '+('the exact largest-20 read' if (h[0].get('discovery') or {}).get('method')=='getTokenLargestAccounts' else 'a bounded holder scan')+' with custody exclusions applied.'),None
        partial=[d for d in by_op.get('holders',[]) if d.get('status') not in ('observed','sampled')]
        if partial:return False,'Holders fact is '+str(partial[0].get('status'))+': '+'; '.join(str(x) for x in (partial[0].get('gaps') or ['balances or extensions unresolved']))[:200],'holders'
        return False,'No usable holders fact: the largest-accounts read or the bounded scan did not answer.','holders'
    if dim=='canonical_lp_principal_custody':
        if lead_id is None:return False,('No pool sampled: discovery listed no pool for the exact mint.' if not _pools_discovered(by_op) else 'The leading pool was not sampled.'),'pool'
        lead=by_pool.get(lead_id)
        if lead is None:return False,'The leading pool fact is unusable: its state read did not decode.','pool'
        status=lead.get('status');positions=len(lead.get('positions') or []);ok,gaps=sampled_ok(lead)
        # Program control is the external-dependencies surface; a pool whose only open item is its program still answered custody.
        if ok:return True,'Leading pool '+str((lead.get('adapter') or {}).get('id'))+' sampled with '+str(positions)+' position(s) or LP custody named; principal, custodians and locks are typed facts'+(' (program control is rated under external dependencies)' if status!='observed' else '')+'.',None
        return False,'Leading pool fact is '+str(status)+': '+('; '.join(gaps)[:200]),'positions'
    if dim=='side_pool_removal_risk':
        discovered=_pools_discovered(by_op)
        if not by_op.get('discovery_pools'):return False,'No usable exact-mint discovery fact: the pool listing did not answer.','pool'
        if len(discovered)<=1 and not side:return True,('Exact-mint discovery lists one pool; no side pool exists to sample.' if discovered else 'Exact-mint discovery lists no pool; there is no side pool.'),None
        if side:
            second=side[0];extra=max(0,len(discovered)-2);ok,gaps=sampled_ok(second)
            if ok:return True,'Second pool '+str((second.get('adapter') or {}).get('id'))+' sampled'+(' with '+str(len(second.get('positions') or []))+' position(s)' if second.get('positions') else '')+'; '+str(extra)+' further indexed pool(s) are outside the two-pool standard scope.',None
            return False,'Second pool fact is '+str(second.get('status'))+': '+('; '.join(gaps)[:200]),'positions'
        return False,'Discovery lists '+str(len(discovered))+' pools but only the leading one was sampled.','pool'
    if dim=='sellability_exit_depth':
        sales=[d for d in by_op.get('sales',[]) if (d.get('verified_receipts') or 0)>=1];ladder=[d for d in by_op.get('quote_ladder',[]) if (d.get('sizes_quoted') or 0)>=1]
        if sales or ladder:
            parts=[]
            if sales:parts.append(str(sales[0]['verified_receipts'])+' sale receipt(s) verified at the exact pool')
            if ladder:parts.append('a read-only quote ladder at '+str(ladder[0]['sizes_quoted'])+' of '+str(ladder[0].get('sizes_requested'))+' illustrative sizes')
            return True,'Exit route ran: '+' and '.join(parts)+'.',None
        return False,'No sale verified and no quote captured.','pool_activity'
    if dim=='historical_launch_integrity':
        unusable=[f for f in facts_all if f.get('operation')=='creator_activity' and not f.get('usable')]
        if unusable and not by_op.get('creator_activity'):return False,'The creator activity fact is unusable; attribution and history cannot be read from it.','creator_history'
        keys=[k.get('address') for d in by_op.get('creator_activity',[]) for k in d.get('keys',[]) if k.get('address')]
        histories={d.get('address') for d in by_op.get('history',[])};missing=[k for k in keys if k not in histories]
        launch=by_op.get('launch');stage=(launch[0].get('stage') if launch else None);inits=len((launch[0].get('initializations') or [])) if launch else 0
        if not keys:return False,'No key is attributed by receipt, curve or metadata, so no launch history can be read; the coordinator closes this surface by judgment on the sampled receipts or as an evidenced limit.','standard'
        if missing:return False,'Attributed key(s) without a signature history: '+', '.join(k[:8]+'…' for k in missing)+'.','creator_history'
        if not launch:return False,'No receipt was sampled, so the launch stage is unread.','transactions'
        return True,'Signature history read for every attributed key ('+', '.join(k[:8]+'…' for k in keys)+'). Launch stage '+str(stage)+' with '+str(inits)+' verified initialization(s).',None
    if dim=='admin_treasury_reward_custody':
        if by_op.get('creator_activity'):return True,'Creator attribution and activity are typed facts (receipts, curve or metadata keys, sales and rebuys reconciled).',None
        return False,'No creator activity fact: no key is attributed by receipt, curve or metadata, so no history preset can run; the coordinator closes this surface by judgment on the sampled receipts or as an evidenced limit.','standard'
    if dim=='external_dependencies':
        if not pools:return False,'No pool program to read.','programs'
        open_=[d for d in pools if any(g in PROGRAM_GAPS for g in (d.get('gaps') or []))]
        if open_:return False,'Pool program control unresolved for '+', '.join(str((d.get('adapter') or {}).get('id')) for d in open_)+'.','programs'
        return True,'Every sampled pool program and its ProgramData were read; upgrade authorities are typed facts.',None
    if dim in LANE_ITEMS:
        owner,items=LANE_ITEMS[dim];checks=(checklists or {}).get(owner)
        if not checks:return False,'Closes when the '+owner+' lane returns its '+', '.join(items)+' item(s).','standard'
        statuses={k:(checks.get(k) or {}).get('status') for k in items}
        if all(v=='done' for v in statuses.values()):return True,'The '+owner+' lane reported '+', '.join(items)+' done.',None
        limits=[k for k,v in statuses.items() if v=='external_limit']
        if limits and all(v in ('done','external_limit') for v in statuses.values()):return False,'The '+owner+' lane reported an external limit on '+', '.join(limits)+': close it as an evidenced external limit with the failed attempts, or leave it pending.','standard'
        return False,'The '+owner+' lane item(s) '+', '.join(k for k,v in statuses.items() if v!='done')+' are pending.','standard'
    return False,'Standard work remains.','standard'


def mechanical(dim,findings,facts,attempt_ids,*,leads=None,checklists=None):
    """The coverage row for one surface: checked/resolved when its route ran and answered and every finding on it is
    affirmative; otherwise partial/pending with the reason and the route that would close it."""
    findings=[f for f in findings if isinstance(f,dict)]
    gaps=[f['id'] for f in findings if f.get('claim')=='coverage_gap' or f.get('strength')=='unresolved']
    affirmative=[f for f in findings if f.get('claim')!='coverage_gap' and f.get('strength')!='unresolved']
    resolved,reason,route=rule(dim,_by_op(facts),leads,checklists,facts)
    if resolved and gaps:resolved=False;reason='Open coverage-gap finding(s) '+', '.join(gaps[:4])+' keep this surface open although its route answered: '+reason;route='standard'
    elif resolved and not affirmative:resolved=False;reason='The route answered but no affirmative finding sits on this surface yet: '+reason;route='standard'
    if resolved:
        row={'dimension':dim,'status':'checked','finding_ids':[f['id'] for f in findings],'attempt_ids':list(attempt_ids),
             'decision_impact':'Standard route ran and answered; the rating follows the findings\' signals.','pending_work':[],
             'closure':{'reason':reason,'attempt_ids':[],'next_route':None,'boundary':'resolved','standard_scope_complete':True}}
    else:
        row={'dimension':dim,'status':'partial' if (findings or attempt_ids) else 'not_checked','finding_ids':[f['id'] for f in findings],'attempt_ids':list(attempt_ids),
             'decision_impact':'Assessment pending until the named route runs or the coordinator closes the row with a reason.','pending_work':['Run the '+route+' route.' if route not in (None,'standard') else 'Complete the standard surface checklist.'],
             'closure':{'reason':reason,'attempt_ids':[],'next_route':route or 'standard','boundary':'pending','standard_scope_complete':False}}
    row['prefill']={'basis':'mechanical','digest':digest(row)}
    return row


def leads_for(root):
    """The run's automatic pool leads (leading pool first); the draft root's parent is the run root."""
    from pathlib import Path
    from solana_profile import strict_json
    path=Path(root).resolve().parent/'automatic-leads.json'
    try:return strict_json(path.read_bytes(),path.name) if path.exists() else None
    except (ValueError,OSError):return None


def lane_findings_from_notes(root):
    """Lane findings read from the lane notes on disk (for the note sync) so the note's rows agree with the composed report on
    the lane-owned surfaces; a malformed note contributes nothing here and fails in compose."""
    from pathlib import Path
    from solana_profile import strict_json
    out=[]
    for owner in ('liquidity','project'):
        path=Path(root)/'notes'/(owner+'.json')
        try:note=strict_json(path.read_bytes(),path.name) if path.exists() else None
        except (ValueError,OSError):note=None
        if isinstance(note,dict) and isinstance(note.get('findings'),list):
            out+=[f for f in note['findings'] if isinstance(f,dict) and isinstance(f.get('id'),str) and isinstance(f.get('dimension'),str)]
    return out


def checklists_from_notes(root):
    """Lane checklists read from the lane notes on disk (for the note sync); compose reads them from the composed notes."""
    from pathlib import Path
    from solana_profile import strict_json
    out={}
    for owner in ('liquidity','project'):
        path=Path(root)/'notes'/(owner+'.json')
        try:
            note=strict_json(path.read_bytes(),path.name) if path.exists() else None
        except (ValueError,OSError):note=None
        if isinstance(note,dict) and isinstance(note.get('checklist'),dict):out[owner]=note['checklist']
    return out
