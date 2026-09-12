#!/usr/bin/env python3
"""Public, finite Solana start → lanes/presets → notes workflow."""
import argparse,copy,json,os,time,sys
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from solana_common import need,sha,pubkey
from solana_session import Session,utc,label
from solana_transport import HttpTransport,provider_availability,transport_settings,is_drpc_host,validate_endpoint
from solana_collect_v2 import collect as collect_sample,execute,queue
from solana_presets import mint_baseline,account_batches,read,settings,validate_plan
from solana_web_capture import register_urls,capture as capture_sources,clean_url
from solana_discovery import MAINNET,source_plan,pools
from solana_import import Importer,refresh,ADAPTERS
from solana_facts import encoded,atomic,build,compact
from solana_profile import regular,strict_json,PROFILE,DIMENSIONS,Evidence,validate_report
from solana_compose import CHECKLISTS,empty_coverage,expand_finding,note_header,validate_imports,ComposeError,preflight

VERSION='1.2.0'
ASSETS=Path(__file__).resolve().parents[1]/'assets'
STAGES=('identity_discovery','related_accounts_controllers','pool_transaction_quote_dependencies','final_consistency_checks')


def public_config(*,allow_network,cost_policy,rpc_url_env='SOLANA_RPC_URL'):
    # No custom dRPC configuration in this release. Existing EVM credentials are irrelevant.
    need(allow_network and cost_policy=='free','Public collection needs explicit --allow-network --cost-policy free.')
    url=os.environ.get(rpc_url_env,'https://api.mainnet-beta.solana.com');parts=validate_endpoint(url)
    need(not is_drpc_host(parts.hostname) and not parts.query and parts.path in ('','/'),'Use a credential-free public Solana RPC root; custom dRPC is deferred.')
    args=SimpleNamespace(provider='public',rpc_url_env=rpc_url_env,auth_env=None,auth_header='Authorization',allow_network=True,cost_policy='free',allow_paid=False)
    # Provider preflight is local configuration validation and makes zero network requests.
    old=os.environ.get(rpc_url_env)
    try:
        os.environ[rpc_url_env]=url;result=provider_availability(args);need(result['status']=='ready','public provider preflight not ready');url,headers=transport_settings(args)
    finally:
        if old is None:os.environ.pop(rpc_url_env,None)
        else:os.environ[rpc_url_env]=old
    return {'url':url,'headers':headers,'preflight':result}


def status(root):
    s=Session(root)
    try:return s.status()
    finally:s.close()


def stage(root,name,fn):
    s=Session(root);before=s.status();s.mark(name,{'state':'started'});s.close();start=time.time();error=None
    try:result=fn()
    except (ValueError,OSError,KeyError,TypeError,IndexError) as exc:
        result=None;error={'category':type(exc).__name__,'reason':str(exc) if isinstance(exc,ValueError) else 'Retained helper failure; inspect diagnostics.'}
    finally:
        s=Session(root)
        try:
            after=s.status();s.mark(name,{'state':'partial' if error else 'finished','started_at':utc(start),'stopped_at':utc(time.time()),
             'attempts':after['started_attempts']-before['started_attempts'],'response_bytes':after['response_bytes']-before['response_bytes'],'error':error})
            try:
                from solana_operations import observe
                attempts=[a for a in s.observations() if a['id']>before['started_attempts'] and a['response']]
                if attempts:
                    last=attempts[-1];failed=any(a['status']!='ok' for a in attempts)
                    observe(root,category='source_failure' if failed else 'collection_summary',
                        source_class='public_rpc' if last['transport_kind']=='rpc' else 'public_http',method=last['method'],
                        recovery='retain_partial' if failed or error else 'none',outcome='unresolved' if failed or error else 'observed',
                        evidence_sha256=sha(last['response'].encode()))
            except Exception:pass  # Optional feedback cannot alter evidence or stage outcome.
        finally:s.close()
    return result,error


def capture(root,urls,owner='ordinary',*,dimension=None,opener_factory=None):
    need(owner in ('ordinary','liquidity','project'),'capture owner not supported')
    need(dimension is None or dimension in DIMENSIONS,'unknown capture dimension')
    s=Session(root)
    try:
        need(opener_factory is None or s.meta['synthetic'],'test web opener requires synthetic session')
        existing={r['url']:dict(r) for r in s.db.execute('SELECT * FROM web_sources')} if s.db.execute("SELECT count(*) FROM sqlite_master WHERE name='web_sources'").fetchone()[0] else {}
        shared=[existing[u] for u in urls if u in existing]
        new=[u for u in urls if u not in existing]
        rows=register_urls(s,new,owners={u:owner for u in new},dimensions={u:dimension for u in new} if dimension else None,cap=12) if new else []
        # Existing ownership never changes and an existing capture is reused by reference.
        ids=[r['source_id'] for r in rows if r['status']=='pending']+[r['id'] for r in shared if r['owner']==owner and r['status']=='pending']
    finally:s.close()
    results=capture_sources(root,ids,owner=owner,opener_factory=opener_factory) if ids else []
    return {'captures':results,'existing_sources':[{'id':r['id'],'owner':r['owner'],'url':r['url']} for r in shared],
       'unattempted':[r for r in rows if r['status']!='pending']}


def market_documents(root,target):
    results=[]
    for path in sorted((Path(root)/'web-captures').glob('*.json')):
        record=json.loads(path.read_text())
        if record.get('status')!='ok' or not record.get('raw'):continue
        for source in ('dexscreener','geckoterminal'):
            try:results.append(pools(record,(Path(root)/record['raw']).read_bytes(),target,source=source));break
            except (ValueError,KeyError,TypeError):continue
    return results


def token_info_documents(root,target):
    from solana_discovery import token_info
    results=[]
    for path in sorted((Path(root)/'web-captures').glob('*.json')):
        record=json.loads(path.read_text())
        if record.get('status')!='ok' or not record.get('raw'):continue
        try:results.append(token_info(record,(Path(root)/record['raw']).read_bytes(),target))
        except (ValueError,KeyError,TypeError):continue
    return results


def candidates(root,target):
    from decimal import Decimal
    rows=[r for d in market_documents(root,target) for r in d['candidates']];chosen={}
    for r in sorted(rows,key=lambda r:(-(Decimal(r['liquidity_usd']) if r['liquidity_usd'] is not None else Decimal(-1)),r['pool'])):
        chosen.setdefault(r['pool'],r)
    return list(chosen.values())[:2]


def importer_view(root):
    i=Importer(root)
    try:i.rpc();i.web();return i.latest_accounts(),i.objects,i.checked
    finally:i.session.close()


def dependency_rows(root,pool,kind,*,lp_accounts=None,positions=None):
    from adapters import pool_adapter
    from solana_programs import observed_account
    from solana_presets import pump_sample,position_sample
    from adapters.meteora_common import CLOCK
    accounts,objects,checked=importer_view(root);need(pool in accounts,'Pool lead has not been captured.')
    packet=objects[accounts[pool]];value,meta=observed_account(pool,packet);module=pool_adapter(kind)
    s=Session(root);target=s.meta['target'];s.close()
    if positions:
        pos_packets={a:objects[eid] for a,eid in accounts.items()}
        return position_sample(kind,pool,packet,positions,pos_packets)
    if kind=='pump_curve':return pump_sample(kind,target,{'packets':{a:objects[eid] for a,eid in accounts.items()}})
    state=module.decode_pool(pool,value) if kind in ('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2') else module.decode_pool(value)
    need(target['mint'] in state['mints'],'Pool is not target-bound.')
    addresses=[target['mint'],pool,*state['mints'],*state['vaults'],module.PROGRAM,CLOCK]
    for k in ('config','lp_mint','open_orders','market'):
        if state.get(k):addresses.append(state[k])
    if kind=='raydium_amm_v4' and state.get('legacy_orderbook_enabled') and state['market'] in accounts:
        market,_=observed_account(state['market'],objects[accounts[state['market']]])
        if market:
            try:addresses.append(module.decode_market(state['market'],market,state['mints'])['event_queue'])
            except ValueError:pass
    if kind=='pumpswap':
        from adapters.pump_common import fee_address
        addresses.append(fee_address(module.PROGRAM))
    addresses+=lp_accounts or []
    need(len(set(addresses))<=25,'One atomic pool dependency packet must fit 25 accounts.')
    return account_batches(addresses,prefix='dependencies',floor=meta['context_slot'],critical=True,account_bytes=24000)


def initial_related(root,config,factory,*,include_market=True):
    from adapters import pool_adapter
    from adapters.pump_common import curve_address
    from solana_accounts import decode_mint
    from solana_programs import observed_account,decode_program
    s=Session(root);target=s.meta['target'];s.close();accounts,objects,_=importer_view(root);addresses=[target['mint']]
    leads=candidates(root,target) if include_market else []
    addresses += [r['pool'] for r in leads]
    if target['mint'] in accounts:
        v,_=observed_account(target['mint'],objects[accounts[target['mint']]])
        try:
            m=decode_mint(v);addresses += [v['owner']]+[m[k] for k in ('mint_authority','freeze_authority') if m[k]]
            for ext in m['extensions']:
                for k in ('authority','config_authority','withdraw_authority','program_id','program'):
                    if ext.get(k):addresses.append(ext[k])
        except (ValueError,TypeError):pass
    # Curve PDA is a deterministic candidate, never recognition by suffix.
    if include_market:addresses.append(curve_address(target['mint']))
    rows=account_batches(addresses,prefix='related',critical=True)
    collect_sample(root,root,config,'related',rows,factory=factory)
    return {'pool_candidates':leads,'queried_related_accounts':len(set(addresses))}


def lp_holder_leads(root,config,sample,lp_mint,kind,*,factory,limit=6):
    """Largest LP accounts, or a bounded SPL census when the provider refuses the largest-accounts method."""
    from solana_presets import holder_scan,discovery_leads
    from solana_wire import validate_response
    packet=execute(root,config,sample,read('largest','getTokenLargestAccounts',[lp_mint,{'commitment':'finalized'}]),factory=factory)
    if packet.get('status')=='ok':return [r['address'] for r in packet['response']['result']['value'][:limit]]
    refused=packet.get('status')=='method_unavailable' or packet.get('reason')=='method_unavailable'
    if not refused or kind not in ('raydium_amm_v4','raydium_cpmm'):return []  # Token-2022 LP mints keep an explicit gap.
    scan=execute(root,config,sample,holder_scan(lp_mint,name='scan'),factory=factory)
    if scan.get('status')!='ok':return []
    try:checked=validate_response(scan['request'],scan['response'])
    except ValueError:return []
    return [r['address'] for r in discovery_leads(lp_mint,scan['request'],checked,limit=limit)] if checked['status']=='ok' else []


def provider_diagnostics(root):
    """What a coordinator must know without reading ledgers: refused methods, unsent reads, unresolved stages."""
    root=Path(root);rows=[];s=status(root)
    methods=sorted({m['method'] for m in s.get('unavailable_methods',[])})
    if methods:rows.append({'stage':'provider','category':'method_unavailable','methods':methods,'reason':'The public RPC tier refuses these methods for this session; dependent facts keep explicit gaps unless a bounded scan or preset substitutes.'})
    path=root/'import-diagnostics.json'
    if path.exists():
        d=strict_json(path.read_bytes(),path.name)
        if d.get('unsent_intents'):rows.append({'stage':'collection','category':'unsent_reads','count':len(d['unsent_intents']),'reads':d['unsent_intents'][:12],'reason':d.get('unsent_meaning')})
    for mark in s['phases']:
        try:details=json.loads(mark['details'])
        except ValueError:continue
        state=details.get('state') or details.get('status')
        if state in ('identity_unresolved','omitted_focused_scope','network_unresolved','consistency_unresolved','partial'):
            error=details.get('error');rows.append({'stage':mark['phase'],'category':state,'sample':details.get('sample'),'reason':error.get('reason') if isinstance(error,dict) else None})
    return rows


def receipt_read(sig):
    """One named receipt read per signature, shared by the start probe and any later sample so a probe is never re-sent."""
    from solana_common import signature
    return read('receipt_'+sha(sig.encode())[:8],'getTransaction',[signature(sig),{'commitment':'finalized','encoding':'json','maxSupportedTransactionVersion':0}])


def classify_probes(root,config,sample,pool,signatures,*,probes,receipts,factory):
    """Probe recent signatures one at a time and classify each before any header is bought: only receipts
    carrying a supported swap at the exact pool are selected (at most `receipts`, from at most `probes`).
    A probe without a supported pool swap is not evidence of no trading."""
    from solana_transactions import classify_receipt
    s=Session(root);target=s.meta['target'];s.close()
    rows=[];selected=[]
    for sig in signatures:
        if len(rows)==probes or len(selected)==receipts:break
        probe=execute(root,config,sample,receipt_read(sig),factory=factory)
        # receipt_status keeps the transport outcome: a probe whose receipt never arrived is not a classification.
        row={'pool':pool,'sample':sample,'receipt_status':probe.get('status'),**classify_receipt(target,probe,pool)};rows.append(row)
        if row['swap']:selected.append(row)
    return rows,selected


def record_probes(root,sample,rows,selected,*,probes,receipts):
    receipts_path=Path(root)/'automatic-receipts.json';known=json.loads(receipts_path.read_text()) if receipts_path.exists() else []
    probes_path=Path(root)/'receipt-classification.json'
    record=json.loads(probes_path.read_text()) if probes_path.exists() else {'probed':0,'selected':0,'maximum_probes':0,'rows':[],
        'scope':'recent-signature classification only; a probe without a supported pool swap is not evidence of no trading'}
    record['rows']+=rows;record['probed']+=len(rows);record['selected']+=len(selected);record['maximum_probes']+=probes
    record.setdefault('samples',[]).append({'sample':sample,'probed':len(rows),'selected':len(selected),'maximum_probes':probes,'maximum_receipts':receipts})
    atomic(probes_path,encoded(record))
    atomic(receipts_path,encoded(known+[{'pool':r['pool'],'signature':r['signature'],'direction':r['direction'],'route':r['route'],'sample':sample} for r in selected]))


def automatic_dependencies(root,config,factory):
    from adapters import pool_adapter
    from solana_programs import observed_account,decode_program
    accounts,objects,checked=importer_view(root);by_program={pool_adapter(k).PROGRAM:k for k in ADAPTERS};selected=[]
    for address,eid in accounts.items():
        value,_=observed_account(address,objects[eid])
        if value and value['owner'] in by_program:
            kind=by_program[value['owner']];module=pool_adapter(kind)
            try:
                if kind in ('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2'):module.decode_pool(address,value)
                else:module.decode_pool(value)
                selected.append((address,kind))
            except ValueError:continue
    results=[];automatic=[]
    for n,(pool,kind) in enumerate(selected[:2]):
        try:
            module=pool_adapter(kind);value,_=observed_account(pool,objects[accounts[pool]])
            state=module.decode_pool(pool,value) if kind in ('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2') else module.decode_pool(value)
            holders=lp_holder_leads(root,config,'lpleads'+str(n),state['lp_mint'],kind,factory=factory) if state.get('lp_mint') else []
            rows=dependency_rows(root,pool,kind,lp_accounts=holders);collect_sample(root,root,config,'pool'+str(n),rows,factory=factory)
            automatic.append({'pool':pool,'adapter':kind,'lp_accounts':holders})
            results.append({'pool':pool,'adapter':kind,'status':'sampled'})
        except (ValueError,KeyError,TypeError) as exc:results.append({'pool':pool,'adapter':kind,'status':'partial','reason':str(exc) if isinstance(exc,ValueError) else type(exc).__name__})
    atomic(Path(root)/'automatic-leads.json',encoded(automatic))
    # A small recent candidate sample is not archive coverage or proof of selling.
    # Recent pool signatures are probed one at a time and classified before the receipt budget
    # is spent on headers: only receipts carrying a supported swap at the exact pool are sampled
    # (at most two, from at most four probes). Historical effects still verify the actual flow.
    s=Session(root);target=s.meta['target'];s.close()
    receipts=[];classified=[];probed=set()
    for n,lead in enumerate(automatic):
        if len(receipts)==2 or len(probed)==4:break
        packet=execute(root,config,'activity'+str(n),read('history','getSignaturesForAddress',
            [lead['pool'],{'commitment':'finalized','limit':10}]),factory=factory)
        if packet.get('status')!='ok':continue
        signatures=[r['signature'] for r in packet['response']['result'] if r['err'] is None and r['signature'] not in probed]
        # The probe shares the receipts sample's read name, so the later sample resumes it without a second send.
        rows,selected=classify_probes(root,config,'receipts',lead['pool'],signatures,probes=4-len(probed),receipts=2-len(receipts),factory=factory)
        probed.update(r['signature'] for r in rows);classified+=rows;receipts+=selected
    record_probes(root,'receipts',classified,receipts,probes=4,receipts=2)
    if automatic:
        collect_sample(root,root,config,'receipts',mint_baseline(target['mint'],largest=False)+[receipt_read(r['signature']) for r in receipts],factory=factory)
    # Capture known ProgramData authority metadata without pretending the slice is a
    # complete executable or silently exceeding the public response-byte allowance.
    accounts,objects,_=importer_view(root);programdata=[]
    for address,eid in accounts.items():
        value,_=observed_account(address,objects[eid])
        if not value or not value.get('executable'):continue
        try:
            d=decode_program(address,objects[eid])
            if d.get('programdata_address'):programdata.append(d['programdata_address'])
        except ValueError:pass
    if programdata:
        s=Session(root);mint=s.meta['target']['mint'];s.close()
        # One sliced batch shares a context slot: program metadata costs one header pair, not one per program.
        rows=mint_baseline(mint,largest=False)+[read('programdata','getMultipleAccounts',[list(dict.fromkeys(programdata))[:4],{**settings(),'dataSlice':{'offset':0,'length':45}}])]
        collect_sample(root,root,config,'programs',rows,factory=factory)
    return results


def write_briefs(root):
    root=Path(root).resolve();s=Session(root)
    try:meta=s.meta;resources=s.status()
    finally:s.close()
    if meta['scope']=='focused':return []
    pointers=[];facts_path=root/'draft/facts.json'
    facts=strict_json(facts_path.read_bytes(),'facts.json') if facts_path.exists() else None
    for owner in CHECKLISTS:
        directory=root/'lanes'/owner;directory.mkdir(parents=True,exist_ok=True);path=directory/'brief.md'
        note_path=root/'draft/notes'/(owner+'.json')
        contents=(ASSETS/('lane-brief-'+owner+'.md')).read_text()
        intake={k:meta[k] for k in ('investigation_id','target','question','focus','urls','scope','received_at','target_at','deadline_at','lane_cutoff','collection_cutoff')}
        skill_dir=Path(__file__).resolve().parents[1]
        contract={'note_exists':'Start already wrote the scaffold at note_path with the header filled in; edit it in place and keep the header.',
            'header_fields':['note_version','profile','owner','investigation_id','target','question','focus'],
            'finding_fields':{'required':['id (prefix '+owner+'-)','dimension','claim','strength','text','support'],'optional':['signal','confidence','limitations','subject','counterevidence']},
            'dimensions':list(DIMENSIONS),'claims':['state_observation','historical_execution','source_analysis','inference','coverage_gap'],
            'strengths':['direct','corroborated','bounded','unresolved'],'signals':['good','potential_risk','bad','unverified'],
            'checklist_status':['done','external_limit','pending'],'checklist_keys':list(CHECKLISTS[owner]),
            'adverse_signals':'potential_risk and bad require impact (low/medium/high/critical) and a concern object {basis, mechanism, consequence}; a finding whose support has a pool or program subject must declare that subject or list it in participants.',
            'capture_dimension':'Add --dimension <surface> to a capture whose purpose is one coverage surface (for example utility_redemption_rights for terms pages) so that surface records an attempt.',
            'citeable_ids':'Use the keys of alias_hints in your note or the evidence IDs shown in facts (for example baseline_mint_0, auto-controls, or category:address); the fact- display prefix is not an ID. Your own captures are cited by their capture id after lane-check imports them.',
            'example_finding':{'id':owner+'-example','dimension':'token_controls' if owner=='project' else 'canonical_lp_principal_custody','claim':'state_observation','strength':'bounded','signal':'unverified','text':'One sentence stating exactly what was observed and its limit.','support':['auto-controls'],'limitations':['What remains unresolved.']},
            'reference':str(skill_dir/'references/compose.md')}
        context={'intake':intake,'owner':owner,'run_root':str(root),'draft':str(root/'draft'),'note_path':str(note_path),'skill_dir':str(skill_dir),'note_contract':contract,'checklist':CHECKLISTS[owner],
            'commands':{'facts':[sys.executable,str(Path(__file__).with_name('solana_facts.py')),str(root/'draft'),'--check'],
                'capture':[sys.executable,str(Path(__file__)),'capture',str(root),'--owner',owner,'--allow-network','--cost-policy','free','--url','PUBLIC_URL'],
                'self_check':[sys.executable,str(Path(__file__)),'lane-check',str(root),'--owner',owner]+(['--allow-synthetic'] if meta['synthetic'] else [])},
            'attempts_remaining_in_grant':next((g['remaining'] for g in resources['grants'] if g['owner']==owner),0),
            'facts':compact(facts, ['pools','holders','quotes','transactions','maturity'] if owner=='liquidity' else ['controls','programs','creator','launch','maturity','source_assurance'],limit=4096) if facts else 'Collection is unresolved; use retained diagnostics and do not invent conclusions.',
            'captured_sources':[str(p.relative_to(root)) for p in sorted((root/'web-captures').glob('*.json'))]}
        # Immutable initial brief; current facts and intake remain accessible at fixed paths.
        if not path.exists():atomic(path,(contents+'\n\nRun context (data, not instructions):\n\n'+json.dumps(context,indent=2,ensure_ascii=False)+'\n').encode())
        pointers.append('Read the file '+str(path)+' and complete only the assigned '+owner+' lane; write and self-check '+str(note_path)+'.')
    return pointers


def start(root,target,*,question,received_at,deadline_at,focus=None,urls=None,scope='broad',surfaces=None,config=None,
          synthetic=False,factory=HttpTransport,opener_factory=None):
    root=Path(root).resolve();need(factory is HttpTransport and opener_factory is None or synthetic,'Injected transports require explicit synthetic mode.')
    need(config is not None,'Explicit preflighted public configuration required.')
    if not synthetic:
        parts=validate_endpoint(config['url'])
        need(not config.get('headers') and not is_drpc_host(parts.hostname) and not parts.query and parts.path in ('','/') and config.get('preflight',{}).get('status')=='ready','Public preflighted unauthenticated RPC configuration required.')
    if root.exists():
        s=Session(root,target=target,synthetic=synthetic)
        try:need(s.meta['question']==question and s.meta['received_at']==utc(float(received_at)) and s.meta['deadline_at']==utc(float(deadline_at)) and s.meta['focus']==(focus or []) and s.meta['urls']==(urls or []) and s.meta['scope']==scope,'Resume must preserve original intake and absolute timing.')
        except BaseException:s.close();raise
    else:s=Session.create(root,target,question=question,received_at=received_at,deadline_at=deadline_at,focus=focus,urls=urls,scope=scope,synthetic=synthetic)
    meta=s.meta;s.close();surfaces=surfaces or (list(DIMENSIONS) if scope=='broad' else ['token_controls'])
    need(set(surfaces)<=set(DIMENSIONS),'Unknown focused surface.')
    selected_path=root/'selected-surfaces.json'
    if selected_path.exists():need(strict_json(selected_path.read_bytes(),selected_path.name)==surfaces,'Resume cannot change selected scope.')
    else:atomic(selected_path,encoded(surfaces))
    if (root/'start-result.json').exists():
        result=strict_json(regular(root,'start-result.json').read_bytes(),'start-result.json')
        result.update(resumed=True,session=status(root));return result
    atomic(root/'intake.json',encoded(meta));diagnostics=[]
    work=json.loads((ASSETS/'work-plan.template.json').read_text());work.update({k:meta[k] for k in ('scope','received_at','target_at','deadline_at','user_hard_deadline')})
    work['investigation_id']=meta['investigation_id'];work['target']=target;work['question']=question;work['focus']=focus or [];work['urls']=urls or []
    work['surfaces']=[{**row,'required':row['dimension'] in surfaces} for row in work['surfaces']]
    if not (root/'work-plan.json').exists():atomic(root/'work-plan.json',encoded(work))
    def identity_discovery():
        requested=list(urls or [])
        if scope=='broad' or any(d in surfaces for d in ('canonical_lp_principal_custody','sellability_exit_depth','development_disclosure')):
            if target['genesis_hash']==MAINNET:requested+=list(source_plan(target).values())+([source_plan(target,surface='token_info')['primary']] if scope=='broad' else [])
        with ThreadPoolExecutor(max_workers=2) as pool:
            web=pool.submit(capture,root,requested,opener_factory=opener_factory) if requested else None
            collect_sample(root,root,config,'baseline',mint_baseline(target['mint'],largest=scope=='broad' or 'current_concentration' in surfaces),factory=factory,expand_largest=scope=='broad' or 'current_concentration' in surfaces)
            result=web.result() if web else None
        # Indexer project links are fetched only when a second indexer names the same identity;
        # single-indexer profiles stay recorded as unverified and are never crawled automatically.
        from solana_discovery import corroborate_links
        links=[r for d in market_documents(root,target) for r in d['project_links']]
        decided=corroborate_links(links,token_info_documents(root,target))
        atomic(root/'project-links.json',encoded(decided))
        proposed=[d['url'] for d in decided if d['status']=='corroborated'][:4]
        if scope=='broad' and proposed:capture(root,proposed,opener_factory=opener_factory)
        return result
    _,error=stage(root,STAGES[0],identity_discovery)
    if error:diagnostics.append(error)
    first=None
    try:first=refresh(root)
    except (ValueError,OSError,KeyError,TypeError) as exc:diagnostics.append({'stage':'initial_import','category':type(exc).__name__,'reason':str(exc) if isinstance(exc,ValueError) else 'Import incomplete.'})
    pointers=write_briefs(root)
    have_identity=False
    if (root/'draft/facts.json').exists():
        f=strict_json((root/'draft/facts.json').read_bytes(),'facts.json');have_identity=any(x['operation']=='controls' and x['usable'] for x in f['facts'])
    market_needed=scope=='broad' or bool(set(surfaces)&{'canonical_lp_principal_custody','side_pool_removal_risk','sellability_exit_depth','historical_launch_integrity'})
    related_needed=market_needed or bool(set(surfaces)&{'token_controls','external_dependencies','admin_treasury_reward_custody'})
    if have_identity and related_needed:
        for name,fn in ((STAGES[1],lambda:initial_related(root,config,factory,include_market=market_needed)),(STAGES[2],lambda:automatic_dependencies(root,config,factory))):
            _,error=stage(root,name,fn)
            if error:diagnostics.append(error)
    else:
        for name in STAGES[1:3]:
            s=Session(root);s.mark(name,{'state':'identity_unresolved' if not have_identity else 'omitted_focused_scope','surfaces':surfaces});s.close()
    result,error=stage(root,STAGES[3],lambda:refresh(root))
    if error:diagnostics.append(error)
    diagnostics+=provider_diagnostics(root)
    if (root/'draft/manifest.json').exists():
        from solana_scaffold import write
        for owner in (('coordinator','liquidity','project') if scope=='broad' else ('coordinator',)):
            if not (root/'draft/notes'/(owner+'.json')).exists():
                try:write(root/'draft',owner,synthetic)
                except ValueError as exc:diagnostics.append({'stage':'scaffold','reason':str(exc)})
    summary=None
    if (root/'draft/facts.json').exists():
        try:summary=compact(strict_json((root/'draft/facts.json').read_bytes(),'facts.json'),['controls','pools','holders','quotes','transactions','programs','launch','maturity','source_assurance'],limit=6000)
        except (ValueError,KeyError,TypeError):summary=None
    output={'run':str(root),'draft':str(root/'draft'),'profile':PROFILE,'investigation_id':meta['investigation_id'],'research_status':'partial','facts_summary':summary,
      'collection':result or first,'diagnostics':diagnostics,'lane_pointers':pointers,'next':'Dispatch both pointers before a separate facts-reading step; then complete notes and compose.' if scope=='broad' else 'Answer the focused request with its dependencies and limits; no final broad delivery.',
      'session':status(root)}
    atomic(root/'start-result.json',encoded(output));return output


def collect(root,spec,config,*,factory=HttpTransport):
    from solana_compose import draft_lock
    with draft_lock(Path(root).resolve()):
        return _collect(root,spec,config,factory=factory)


def _collect(root,spec,config,*,factory=HttpTransport):
    """At most two distinct coordinator follow-up presets, serialized by the session."""
    from solana_presets import position_sample,historical_sample,creator_history,quote_sample
    root=Path(root).resolve();ident=label(spec['id']);need(len(ident)<=12,'Preset ID at most 12 characters.');s=Session(root)
    try:
        need(factory is HttpTransport or s.meta['synthetic'],'Injected RPC requires synthetic session.');need(s.remaining_seconds()>0,'Original collection cutoff reached.')
        target=s.meta['target']
    finally:s.close()
    kind=spec['kind'];args=spec.get('parameters',{});accounts,objects,_=importer_view(root)
    lead_rows=None
    if kind in ('pool','positions'):
        from adapters import pool_adapter
        pool=pubkey(args['pool']);pool_adapter(args['adapter'])
        for field in ('lp_accounts','positions'):
            values=args.get(field,[]);need(isinstance(values,list) and len(values)<=6,'At most six known account leads required.')
            for address in values:pubkey(address)
        if pool not in accounts:
            need(any(r['pool']==pool for d in market_documents(root,target) for r in d['candidates']),'Pool lead has not been captured in exact-mint discovery.')
            lead_rows=account_batches([target['mint'],pool],prefix='poollead',critical=True)
            rows=lead_rows
        else:rows=dependency_rows(root,pool,args['adapter'],lp_accounts=args.get('lp_accounts'),positions=args.get('positions'))
    elif kind=='transactions':rows=historical_sample(args['signatures'])
    elif kind=='creator_history':rows=creator_history(args['keys'],before=args.get('before'))
    elif kind=='programs':rows=account_batches([target['mint']]+[pubkey(a) for a in args['addresses']],prefix='programs',critical=True)
    elif kind=='quote':rows=quote_sample(args['adapter'],args['pool'],objects[accounts[args['pool']]])
    elif kind=='holders':rows=mint_baseline(target['mint'],largest=True)
    elif kind=='pool_activity':
        pool=pubkey(args['pool']);need(pool in accounts,'Pool lead has not been captured.')
        limit=args.get('limit',10);receipts=args.get('receipts',2);probes=args.get('probes',4)
        need(type(limit) is int and 1<=limit<=25 and type(receipts) is int and 0<=receipts<=4,'Activity limit 1-25 signatures and at most four receipts.')
        need(type(probes) is int and receipts<=probes<=8,'Activity probes must be at least the receipts and at most eight.')
        rows=[]
    else:raise ValueError('Supported presets: pool, positions, transactions, creator_history, programs, quote, holders, pool_activity.')
    if not any(r['critical'] and target['mint'] in (r['params'][0] if r['method']=='getMultipleAccounts' else [r['params'][0]]) for r in rows):rows=mint_baseline(target['mint'],largest=False)+rows
    validate_plan(rows)
    s=Session(root)
    try:
        folder=root/'preset-requests';folder.mkdir(exist_ok=True);path=folder/(ident+'.json')
        with s.transaction():
            if path.exists():need(strict_json(path.read_bytes(),path.name)==spec,'Named preset changed.')
            else:
                need(len(list(folder.glob('*.json')))<2,'Two coordinator preset calls already used.')
                # A new preset must not reuse a start sample id: pool_activity would resume that sample's classification as its
                # own. Classification rows can exist without a sample plan (a refused reserve), so both records are checked.
                probes_path=root/'receipt-classification.json';record=json.loads(probes_path.read_text()) if probes_path.exists() else {}
                classified={r.get('sample') for r in record.get('rows',[])}|{r.get('sample') for r in record.get('samples',[])}
                need(not (root/'sample-plans'/(ident+'.json')).exists() and ident not in classified,'Preset ID collides with an existing sample; choose another id.');atomic(path,encoded(spec))
    finally:s.close()
    def run_preset():
        planned=rows
        if lead_rows is not None:
            collect_sample(root,root,config,ident+'lead',lead_rows,factory=factory)
            planned=dependency_rows(root,pool,args['adapter'],lp_accounts=args.get('lp_accounts'),positions=args.get('positions'))
        if kind=='pool_activity':
            # Recent signatures are candidates only. Like start, each unseen signature is probed and classified
            # before any header is bought; only supported swaps at the exact pool are sampled, and receipts must
            # still independently establish the exact flow.
            packet=execute(root,config,ident,read('activity','getSignaturesForAddress',[pool,{'commitment':'finalized','limit':limit}]),factory=factory)
            need(packet.get('status')=='ok','Pool activity read unresolved: '+str(packet.get('reason') or packet.get('status')))
            probes_path=root/'receipt-classification.json';record=json.loads(probes_path.read_text()) if probes_path.exists() else {'rows':[]}
            mine=[r for r in record['rows'] if r.get('sample')==ident]
            if mine:selected=[r for r in mine if r['swap']]  # An identical named preset resumes its own classification.
            else:
                path=root/'automatic-receipts.json';seen={k['signature'] for k in (json.loads(path.read_text()) if path.exists() else [])}
                seen|={r['signature'] for r in record['rows'] if r.get('receipt_status','ok')=='ok'}
                # A signature already sampled or classified is never fetched twice: it would duplicate the receipt and waste
                # the window. A probe with any status other than ok (budget, timeout, provider error, empty result) keeps that
                # status and may be probed again here under this preset's own read family.
                signatures=[r['signature'] for r in packet['response']['result'] if r['err'] is None and r['signature'] not in seen]
                classified,selected=classify_probes(root,config,ident,pool,signatures,probes=probes,receipts=receipts,factory=factory)
                record_probes(root,ident,classified,selected,probes=probes,receipts=receipts)
            if not selected:return None
            planned=mint_baseline(target['mint'],largest=False)+[receipt_read(r['signature']) for r in selected]
        return collect_sample(root,root,config,ident,planned,factory=factory,expand_largest=kind=='holders')
    _,error=stage(root,'preset_'+ident,run_preset)
    result=refresh(root);result['preset_error']=error
    from solana_scaffold import sync_assignments
    result['assignments_synced']=sync_assignments(root/'draft');return result


def lane_check(root,owner,*,allow_synthetic=False):
    root=Path(root).resolve();draft=root/'draft';s=Session(root)
    try:meta=s.meta
    finally:s.close()
    need(owner in CHECKLISTS and meta['scope']=='broad','Known broad lane required.')
    m=strict_json(regular(draft,'manifest.json').read_bytes(),'manifest.json');known={o['id'] for o in m['observations']}
    captures=[json.loads(p.read_text()) for p in sorted((root/'web-captures').glob('*.json'))]
    if any(c.get('owner')==owner and c.get('captured_at') and c.get('id') not in known for c in captures):
        # A lane's own registered captures are imported mechanically so a one-shot lane can cite them.
        # refresh() takes the draft lock itself; taking it here as well would deadlock on flock.
        refresh(root)
        m=strict_json(regular(draft,'manifest.json').read_bytes(),'manifest.json')
    e=Evidence(draft,m,allow_synthetic);facts=build(draft,allow_synthetic)
    n=strict_json(regular(draft,'notes/'+owner+'.json').read_bytes(),'lane note');errors=[];note_header(n,owner,m,errors,'note');validate_imports(draft,n,owner,e,errors,'note')
    rows=[]
    for i,value in enumerate(n.get('findings',[])):
        try:rows.append(expand_finding(value,owner,facts,e,'note.findings['+str(i)+']'))
        except (ValueError,KeyError,TypeError) as exc:errors.append({'path':'note.findings['+str(i)+']','message':str(exc)})
    from solana_profile import findings
    try:findings(e,{'findings':rows},False)
    except ValueError as exc:errors+=getattr(exc,'errors',[{'path':'findings','message':str(exc)}])
    checks=n.get('checklist',{});need(set(checks)==set(CHECKLISTS[owner]),'Lane checklist keys differ.')
    for k,v in checks.items():
        if not isinstance(v,dict) or v.get('status') not in ('done','external_limit','pending') or not v.get('reason'):errors.append({'path':'checklist.'+k,'message':'Use done/external_limit/pending with a concrete reason.'})
    complete=all(isinstance(v,dict) and v.get('status') in ('done','external_limit') for v in checks.values())
    if complete:
        from solana_compose import placeholders
        placeholders(n,'note',errors)
        if not n.get('evidence_ids') or not all(i in e.rows for i in n['evidence_ids']):errors.append({'path':'evidence_ids','message':'Completed lane needs retained current-run evidence IDs.'})
    if errors:raise ComposeError(errors)
    return {'valid':True,'owner':owner,'complete':complete,'lane_cutoff':meta['lane_cutoff'],'late':time.time()>meta['lane_cutoff'],'written':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('start','collect','brief','capture','lane-check','refresh','status'));p.add_argument('root',type=Path)
    p.add_argument('--mint');p.add_argument('--genesis-hash',default=MAINNET);p.add_argument('--question');p.add_argument('--received-at');p.add_argument('--deadline-at');p.add_argument('--focus',action='append',default=[]);p.add_argument('--url',action='append',default=[])
    p.add_argument('--scope',choices=('broad','focused'),default='broad');p.add_argument('--surface',action='append');p.add_argument('--owner',choices=('ordinary','liquidity','project'),default='ordinary');p.add_argument('--dimension',choices=DIMENSIONS);p.add_argument('--request',type=Path)
    p.add_argument('--allow-network',action='store_true');p.add_argument('--cost-policy',choices=('free',));p.add_argument('--rpc-url-env',default='SOLANA_RPC_URL');p.add_argument('--allow-synthetic',action='store_true');a=p.parse_args()
    try:
        if a.action in ('start','collect'):config=public_config(allow_network=a.allow_network,cost_policy=a.cost_policy,rpc_url_env=a.rpc_url_env)
        if a.action=='start':
            from solana_session import epoch
            need(a.mint and a.question and a.received_at and a.deadline_at,'Start needs exact mint, original question, received-at and deadline-at.')
            result=start(a.root,{'family':'solana','genesis_hash':a.genesis_hash,'mint':a.mint},question=a.question,received_at=epoch(a.received_at),deadline_at=epoch(a.deadline_at),focus=a.focus,urls=a.url,scope=a.scope,surfaces=a.surface,config=config)
        elif a.action=='collect':need(a.request is not None,'A bounded preset JSON request is required.');result=collect(a.root,strict_json(a.request.read_bytes(),'preset request'),config)
        elif a.action=='brief':result={'lane_pointers':write_briefs(a.root)}
        elif a.action=='capture':
            need(a.allow_network and a.cost_policy=='free','Public capture requires --allow-network --cost-policy free.')
            result=capture(a.root,a.url,a.owner,dimension=a.dimension)
        elif a.action=='lane-check':result=lane_check(a.root,a.owner,allow_synthetic=a.allow_synthetic)
        elif a.action=='refresh':
            from solana_scaffold import sync_assignments
            result=refresh(a.root);result['assignments_synced']=sync_assignments(Path(a.root).resolve()/'draft')
        else:result=status(a.root)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError,TypeError,IndexError) as exc:
        print(json.dumps({'valid':False,'errors':getattr(exc,'errors',[{'path':'workflow','message':str(exc) if isinstance(exc,ValueError) else type(exc).__name__}])}));return 2
if __name__=='__main__':raise SystemExit(main())
