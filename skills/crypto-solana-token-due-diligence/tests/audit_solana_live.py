#!/usr/bin/env python3
"""Offline acceptance bookkeeping for existing frozen live cases; never collects."""
import argparse,json,platform,sqlite3,statistics,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from solana_replay import verify
from solana_facts import encoded,atomic


def epoch(value):return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
def utc(value):return datetime.fromtimestamp(value,timezone.utc).isoformat()


def audit(root,events):
    root=Path(root).resolve();frozen=root/'checkpoint';checked=verify(frozen)
    db=sqlite3.connect((root/'session.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        meta=json.loads(db.execute('SELECT metadata FROM session WHERE singleton=1').fetchone()[0])
        attempts=[dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY id')]
        phases=[dict(r) for r in db.execute('SELECT * FROM marks ORDER BY id')]
    finally:db.close()
    start=epoch(meta['received_at']);end=(frozen/'delivery.json').stat().st_mtime
    calls=[e for e in events if e.get('type')=='response_item' and e.get('payload',{}).get('type') in ('function_call','custom_tool_call')]
    before=[e for e in calls if epoch(e['timestamp'])<=start and 'solana_broad_collect.py start' in str(e['payload']) and str(root.name) in str(e['payload'])]
    initial=max(before,key=lambda e:e['timestamp']) if before else None
    active=[e for e in calls if start<=epoch(e['timestamp'])<=end]
    if initial and initial not in active:active.insert(0,initial)
    models=[e['payload'].get('model') for e in events if e.get('type')=='turn_context' and epoch(e['timestamp'])<=start]
    m=json.loads((frozen/'manifest.json').read_text());r=json.loads((frozen/'report.json').read_text());lanes={}
    for owner in ('liquidity','project'):
        n=json.loads((root/'draft/notes'/(owner+'.json')).read_text());lanes[owner]=n.get('lane_timing')
    sale_count=0;ownership_count=0
    by_id={o['id']:o for o in m['observations']}
    for d in m['derivations']:
        if d['operation'] not in ('sales','pool'):continue
        value=json.loads((frozen/by_id[d['id']]['artifact']).read_text())
        if d['operation']=='sales':sale_count+=value.get('verified_receipts',0)
        else:ownership_count+=len(value.get('positions',[]))+len((value.get('lp_custody') or {}).get('accounts',[]))
    stage_rows=[]
    for p in phases:
        d=json.loads(p['details'])
        if d.get('started_at') and d.get('stopped_at'):
            stage_rows.append({'phase':p['phase'],'seconds':epoch(d['stopped_at'])-epoch(d['started_at']),'details':d})
    return {'case':root.name,'mint':meta['target']['mint'],'received_at':meta['received_at'],'frozen_at':utc(end),
        'freeze_time_basis':'Original delivery.json filesystem mtime on the acceptance host, before later code repairs.',
        'elapsed_seconds':round(end-start,6),'start_helper_seconds':round(next(epoch(p['details']['stopped_at'])-start for p in stage_rows if p['phase']=='final_consistency_checks'),6),
        'deadline_at':meta['deadline_at'],'lane_cutoff':utc(meta['lane_cutoff']),'collection_cutoff':utc(meta['collection_cutoff']),
        'model':models[-1] if models else None,'coordinator_tool_actions':len(active),
        'action_count_basis':'Root task function/custom tool calls from initiating start call through freeze; includes orchestration and case-time bookkeeping, excludes lane internals. Proxy for model-facing steps, not user turns.',
        'tool_names':[e['payload'].get('name') for e in active],
        'started_attempts':len(attempts),'completed_attempts':sum(a['completed_at'] is not None for a in attempts),
        'rpc_attempts':sum(a['transport_kind']=='rpc' for a in attempts),'http_attempts':sum(a['transport_kind']=='web' for a in attempts),
        'response_bytes':sum(a['response_bytes'] or 0 for a in attempts),'account_reads':sum(a['accounts'] for a in attempts),
        'wire_attempt_interval_seconds_sum':round(sum(a['completed_at']-a['started_at'] for a in attempts if a['completed_at'] is not None),6),
        'wire_time_basis':'Sum of durable per-attempt start/completion intervals; includes processing and overlaps concurrent calls, not elapsed wall time.',
        'statuses':{s:sum(a['status']==s for a in attempts) for s in sorted({a['status'] for a in attempts})},
        'helper_stages':stage_rows,'lane_timing':lanes,'observations':len(m['observations']),
        'critical_initial_samples':sum(s['critical'] for s in m['samples']),
        'critical_recheck_samples':sum(bool(s.get('recheck_of')) for s in m['samples']),
        'pinned_samples':sum(s['status']=='pinned' for s in m['samples']),
        'coverage':[{'dimension':c['dimension'],'status':c['status'],'standard_scope_complete':c['closure']['standard_scope_complete'],'pending_work':c['pending_work']} for c in r['coverage']],
        'verified_sale_receipts':sale_count,'position_or_lp_ownership_samples':ownership_count,
        'research_status':r['research_status'],'delivery_status':r['delivery_status'],'frozen_integrity_valid':checked['valid'],
        'rich_case_parity_pass':False,'network_requests_by_audit':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--round-root',type=Path,required=True);p.add_argument('--task-log',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    events=[]
    with a.task_log.open() as stream:
        for line in stream:
            try:e=json.loads(line)
            except ValueError:continue
            if e.get('type') in ('response_item','turn_context'):events.append(e)
    rows=[audit(a.round_root/name,events) for name in ('usdc','pyusd','pump')]
    result={'schema_version':1,'host':platform.platform(),'python':sys.version,'cases':rows,'round_attempts':sum(r['started_attempts'] for r in rows),
        'median_partial_handling_seconds':statistics.median(r['elapsed_seconds'] for r in rows),
        'all_handled_within_600_seconds':all(r['elapsed_seconds']<=600 for r in rows),
        'rich_case_live_parity':'unmet','reason':'All cases are substantive partial checkpoints; no completed broad live case, verified sale sample or principal-ownership sample.'}
    assert result['round_attempts']<=360 and all(r['started_attempts']==r['completed_attempts'] and r['started_attempts']<=120 and r['response_bytes']<=67108864 for r in rows)
    atomic(a.out,encoded(result));print(json.dumps({k:v for k,v in result.items() if k!='cases'}))


if __name__=='__main__':main()
