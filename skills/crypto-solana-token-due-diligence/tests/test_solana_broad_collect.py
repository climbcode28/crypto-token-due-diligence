from pathlib import Path
import sys,os,tempfile,unittest,unittest.mock,time,json,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pool_fixture import key
from broad_fixture import RichRpc,Web
from test_solana_web_capture import Response
import solana_session
from solana_broad_collect import start,collect,status,STAGES
from solana_profile import validate


class BroadTests(unittest.TestCase):
    def setup_run(self,scope='broad',urls=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)/'run';target=RichRpc.reset();Web.calls=[];Web.blocked=False
        # The public connection-rate window (40 sends per 10 s) is provider pacing, not behaviour under test here; unpatched it adds ~10 s waits.
        patcher=unittest.mock.patch.object(solana_session,'CONNECTION_WINDOW',10000);patcher.start();self.addCleanup(patcher.stop)
        opts={'question':'Assess exact token, project claims and exit depth.','received_at':time.time()-10,'deadline_at':time.time()+590,'scope':scope,'focus':['exit depth'],
          'urls':urls or [],'synthetic':True,'config':{'url':'https://synthetic.invalid','headers':{}},'factory':RichRpc,'opener_factory':Web}
        return root,target,opts

    def test_one_start_has_facts_two_briefs_and_valid_rich_partial_draft(self):
        root,target,opts=self.setup_run();r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics']);m,report=validate(root/'draft',True)
        self.assertEqual(len(r['lane_pointers']),2);self.assertEqual(report['research_status'],'partial');self.assertIsNone(report['decision'])
        f=json.loads((root/'draft/facts.json').read_text());p=next(x for x in f['facts'] if x['operation']=='pool');self.assertEqual(p['data']['reserves_atomic'],['9860','19740']);self.assertEqual(p['data']['lp_custody']['observed_atomic'],'450')
        self.assertTrue(any(x['operation']=='holders' for x in f['facts']));self.assertTrue(any(x['operation']=='discovery_pools' for x in f['facts']));self.assertLessEqual(status(root)['started_attempts'],120)
        graph=next(x['data'] for x in f['facts'] if x['operation']=='controllers')
        self.assertTrue(graph['nodes']);self.assertTrue(graph['root_links']);self.assertIsNone(graph['safe_or_locked_conclusion'])
        self.assertTrue(any(r['role']=='owning_token_program' for r in graph['root_links']))
        self.assertTrue(all((root/'draft/notes'/(o+'.json')).exists() for o in ('coordinator','liquidity','project')))
        marks=status(root)['phases'];self.assertTrue(set(STAGES)<={x['phase'] for x in marks})

    def test_resume_preserves_attempts_absolute_timing_and_question_urls(self):
        root,target,opts=self.setup_run(urls=['https://project.example/token']);first=start(root,target,**opts);before=status(root);calls=len(RichRpc.calls)
        again=start(root,target,**opts);after=status(root);self.assertEqual(calls,len(RichRpc.calls));self.assertEqual(before['grants'],after['grants']);self.assertEqual(before['deadline_at'],after['deadline_at'])
        self.assertEqual(again['investigation_id'],first['investigation_id']);self.assertEqual(after['question'],opts['question']);self.assertEqual(after['urls'],opts['urls'])
        with self.assertRaisesRegex(ValueError,'Resume'):start(root,target,**{**opts,'received_at':time.time()})

    def test_automatic_candidate_receipt_is_independently_verified(self):
        from transaction_fixture import fixture
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx
        result=start(root,target,**opts);self.assertFalse(result['diagnostics'],result['diagnostics']);validate(root/'draft',True)
        facts=json.loads((root/'draft/facts.json').read_text())
        sales=next(f['data'] for f in facts['facts'] if f['operation']=='sales')
        self.assertEqual(sales['verified_receipts'],1);sale=sales['receipts'][0]
        self.assertEqual(sale['input_atomic'],'1000');self.assertEqual(sale['output_atomic'],'500');self.assertEqual(sale['seller'],a['owner'])
        self.assertIsNone(sale['profit']);self.assertEqual(len([r for r in RichRpc.calls if r['method']=='getTransaction']),1)

    def test_receipts_are_classified_before_sampling_and_the_swap_probe_is_reused(self):
        from transaction_fixture import fixture
        from solana_common import b58encode
        from solana_transactions import SYSTEM
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx
        # A more recent receipt with no supported swap (the swap instruction points at the System program) is probed first and skipped.
        other=copy.deepcopy(tx);sig=b58encode(bytes([77])*64);other['transaction']['signatures'][0]=sig
        keys=other['transaction']['message']['accountKeys'];other['transaction']['message']['instructions'][a['swap_index']]['programIdIndex']=keys.index(SYSTEM)
        RichRpc.receipts={sig:other}
        result=start(root,target,**opts);self.assertFalse(result['diagnostics'],result['diagnostics']);validate(root/'draft',True)  # an unheadered probe is a plain observation
        receipts=json.loads((root/'automatic-receipts.json').read_text());classification=json.loads((root/'receipt-classification.json').read_text())
        self.assertEqual([(r['signature']==sig,r['direction'],r['route']) for r in receipts],[(False,'sell','direct')])
        self.assertEqual((classification['probed'],classification['selected']),(2,1));self.assertEqual([r['swap'] for r in classification['rows']],[False,True])
        self.assertEqual(len([r for r in RichRpc.calls if r['method']=='getTransaction']),2)  # one send per probe; the sample resumed the swap probe
        facts=json.loads((root/'draft/facts.json').read_text())['facts']
        self.assertEqual(next(f['data']['verified_receipts'] for f in facts if f['operation']=='sales'),1)
        self.assertEqual(next(f['data']['verified_receipts'] for f in facts if f['operation']=='rebuys'),0)
        self.assertEqual(next(f['data']['receipts'][0]['route'] for f in facts if f['operation']=='sales'),'direct')

    def test_indexer_project_links_need_a_second_source_before_automatic_capture(self):
        root,target,opts=self.setup_run();start(root,target,**opts)
        decided=json.loads((root/'project-links.json').read_text())
        self.assertEqual([(d['url'],d['status']) for d in decided],[('https://project.example/token','corroborated')])
        self.assertIn('https://project.example/token',Web.calls);self.assertTrue(any(u.endswith('/info') for u in Web.calls))
        root,target,opts=self.setup_run();Web.token_info=False;start(root,target,**opts)
        decided=json.loads((root/'project-links.json').read_text())
        self.assertEqual(decided[0]['status'],'unverified_indexer_profile');self.assertNotIn('https://project.example/token',Web.calls)

    def test_lane_captured_public_quote_becomes_a_typed_quote_fact(self):
        from solana_broad_collect import capture
        from solana_quotes import quote_url
        from solana_import import refresh
        from pool_fixture import key
        root,target,opts=self.setup_run();start(root,target,**opts)
        url=quote_url('jupiter_v1_lite',target,key(3),'1000');capture(root,[url],'liquidity',opener_factory=Web);refresh(root)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];quote=next(f for f in facts if f['operation']=='public_quote' and f['data']['input_atomic']=='1000')  # start's own ladder sizes sit beside it
        self.assertTrue(quote['usable']);self.assertEqual((quote['data']['source'],quote['data']['output_atomic'],quote['data']['provider_usd_value']),('jupiter_v1_lite','500','1.5'))
        self.assertFalse(quote['data']['execution_observed'])

    def test_focused_scope_omits_lanes_markets_and_broad_dependencies(self):
        root,target,opts=self.setup_run('focused');r=start(root,target,**opts);self.assertFalse(r['lane_pointers']);self.assertFalse(Web.calls);self.assertFalse((root/'lanes').exists())
        m,report=validate(root/'draft',True);self.assertEqual(report['scope'],'focused');self.assertTrue(all(q['method']!='getTokenLargestAccounts' for q in RichRpc.calls))

    def test_source_failure_keeps_control_facts_and_pending_work(self):
        root,target,opts=self.setup_run();Web.blocked=True;r=start(root,target,**opts);m,report=validate(root/'draft',True)
        self.assertTrue(any(f['id']=='pipeline-auto-controls' for f in report['findings']));self.assertEqual(report['research_status'],'partial');self.assertTrue(any(o['status']=='permission_denied' for o in m['observations']))
        self.assertTrue(all(not c['closure']['standard_scope_complete'] for c in report['coverage']))

    def test_four_followup_presets_share_grants_and_fifth_is_refused(self):
        root,target,opts=self.setup_run('focused');start(root,target,**opts);before=status(root)
        for ident in ('followup1','followup2','followup3','followup4'):
            spec={'id':ident,'kind':'programs','parameters':{'addresses':[target['mint']]}}
            result=collect(root,spec,opts['config'],factory=RichRpc);self.assertEqual(result['research_status'],'partial')
        after=status(root);self.assertEqual(before['deadline_at'],after['deadline_at']);self.assertGreater(after['started_attempts'],before['started_attempts'])
        with self.assertRaisesRegex(ValueError,'Four coordinator'):collect(root,{'id':'followup5','kind':'programs','parameters':{'addresses':[]}},opts['config'],factory=RichRpc)

    def test_wrong_network_keeps_diagnostics_and_never_completes(self):
        root,target,opts=self.setup_run();RichRpc.mode='wrong_network';r=start(root,target,**opts);self.assertEqual(r['research_status'],'partial');self.assertTrue(r['diagnostics'])
        self.assertTrue((root/'session.sqlite').exists());self.assertTrue((root/'start-result.json').exists())

    def test_indexed_pool_followup_captures_lead_before_dependencies(self):
        from solana_broad_collect import capture
        from solana_discovery import source_plan
        root,target,opts=self.setup_run('focused');start(root,target,**opts)
        capture(root,[source_plan(target)['primary']],'ordinary',opener_factory=Web)
        result=collect(root,{'id':'custody','kind':'pool','parameters':{'adapter':'raydium_cpmm','pool':RichRpc.pool['pool']}},opts['config'],factory=RichRpc)
        self.assertIsNone(result['preset_error']);facts=json.loads((root/'draft/facts.json').read_text())
        self.assertTrue(any(f['operation']=='pool' and f['data']['reserves_atomic']==['9860','19740'] for f in facts['facts']))
        self.assertTrue((root/'preset-requests/custody.json').exists())
        from pool_fixture import key
        before=status(root)['started_attempts']
        with self.assertRaisesRegex(ValueError,'exact-mint discovery'):
            collect(root,{'id':'foreign','kind':'pool','parameters':{'adapter':'raydium_cpmm','pool':key(99)}},opts['config'],factory=RichRpc)
        self.assertEqual(before,status(root)['started_attempts']);self.assertFalse((root/'preset-requests/foreign.json').exists())

    def test_repeated_start_preserves_edited_note_and_draft(self):
        root,target,opts=self.setup_run();start(root,target,**opts)
        path=root/'draft/notes/coordinator.json';n=json.loads(path.read_text());n['limitations']=['Analyst correction retained.'];path.write_text(json.dumps(n))
        before={p:p.read_bytes() for p in (path,root/'draft/report.json',root/'work-plan.json')}
        r=start(root,target,**opts);self.assertTrue(r['resumed']);self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_later_unpinned_mint_does_not_erase_earlier_usable_controls(self):
        from unittest.mock import patch
        from pool_fixture import mint,key
        import urllib.error,io
        root,target,opts=self.setup_run('focused');start(root,target,**opts)
        original=RichRpc.__call__;RichRpc.values[target['mint']]=mint(2000000,key(90))
        def changed(rpc,request):
            if request['method']=='getBlock' and request['params'][0]==101:
                raise urllib.error.HTTPError('https://synthetic.invalid',429,'fixture',{},io.BytesIO(b''))
            result=original(rpc,request)
            if request['method'] in ('getAccountInfo','getMultipleAccounts'):result['result']['context']['slot']=101
            return result
        with patch.object(RichRpc,'__call__',changed):
            collect(root,{'id':'changed','kind':'programs','parameters':{'addresses':[target['mint']]}},opts['config'],factory=RichRpc)
        f=json.loads((root/'draft/facts.json').read_text())['facts'];controls=next(r for r in f if r['evidence_id']=='auto-controls')
        # The controls fact comes from the latest pinned snapshot; the newer unpinned read is a limit that says its authorities differ.
        self.assertTrue(controls['usable']);self.assertEqual(controls['data']['selection_scope'],'earlier_pinned_snapshot_newer_unpinned')
        self.assertNotEqual(controls['data']['mint']['mint_authority'],key(90));self.assertNotEqual(controls['data']['mint']['supply_atomic'],'2000000')
        self.assertEqual((controls['data']['newer_unpinned']['authorities_match'],controls['data']['newer_unpinned']['reason']),(False,None));self.assertFalse(any(r['evidence_id']=='prior-controls' for r in f))
        self.assertIn('newer_unpinned',{l['path'] for l in controls['limits']});self.assertIn('its controllers differ',controls['summary'])
        m=json.loads((root/'draft/manifest.json').read_text());d=next(x for x in m['derivations'] if x['id']=='auto-controls')
        self.assertNotIn(controls['data']['newer_unpinned']['observation'],[i['id'] for i in d['inputs']])  # a note, never an input
        # Aggregates take the latest usable snapshot and the authority graph is built from usable roots only.
        sizes=next(r for r in f if r['evidence_id']=='auto-sizes');self.assertTrue(sizes['usable'])
        graph=next(r for r in f if r['evidence_id']=='auto-controllers');self.assertTrue(graph['usable'])

    def test_unpinned_optional_epoch_does_not_invalidate_mint_authority_snapshot(self):
        from solana_import import Importer
        from solana_profile import Evidence
        root,target,opts=self.setup_run('focused');start(root,target,**opts)
        importer=Importer(root)
        try:
            importer.rpc();importer.web()
            for sample in importer.m['samples']:
                if importer.objects[sample['observation_id']]['request']['method']=='getEpochInfo':sample['status']='partial'
            importer.facts();e=Evidence(importer.root,importer.m,True)
            self.assertIn('auto-controls',e.usable)
            controls=next(d for d in importer.m['derivations'] if d['id']=='auto-controls')
            self.assertNotIn('epoch',controls['parameters'])
            self.assertTrue(any(o['id'].startswith('baseline_epoch') for o in importer.m['observations']))
        finally:importer.session.close()

    def test_concurrent_followups_are_serialized_and_invalid_invocation_does_not_use_slot(self):
        root,target,opts=self.setup_run('focused');start(root,target,**opts)
        with self.assertRaises(ValueError):collect(root,{'id':'invalid','kind':'write_transaction'},opts['config'],factory=RichRpc)
        self.assertFalse((root/'preset-requests/invalid.json').exists())
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda ident:collect(root,{'id':ident,'kind':'programs','parameters':{'addresses':[target['mint']]}},opts['config'],factory=RichRpc),('p1','p2')))
        self.assertEqual(len(results),2);marks=[m for m in status(root)['phases'] if m['phase'] in ('preset_p1','preset_p2')]
        self.assertEqual(marks[0]['phase'],marks[1]['phase']);self.assertNotEqual(marks[1]['phase'],marks[2]['phase'])

    def test_start_without_any_network_is_blocked_and_names_the_cause(self):
        # A sandbox that denies outbound network makes every send fail before any response; start must stop rather than
        # hand out lane pointers for a token it never observed (live Codex run, 2026-09-13).
        root,target,opts=self.setup_run()
        def denied(rpc,request):raise PermissionError(1,'Operation not permitted')
        class Denied(Web):
            def open(self,request,timeout):type(self).calls.append(request.full_url);raise PermissionError(1,'Operation not permitted')
        with unittest.mock.patch.object(RichRpc,'__call__',denied):r=start(root,target,**{**opts,'opener_factory':Denied})
        self.assertEqual((r['research_status'],r['blocked'],r['lane_pointers'],r['facts_summary']),('blocked','network_unavailable',[],None))
        self.assertEqual(list(r)[:2],['next','research_status'])  # the action leads the output
        block=next(d for d in r['diagnostics'] if d.get('category')=='network_unavailable')
        self.assertEqual(set(block['failures']),{'not_permitted'});self.assertGreaterEqual(block['failures']['not_permitted'],2)
        self.assertIn('Retain this blocked run',block['next_action']);self.assertIn('escalated permissions',block['next_action'])
        self.assertNotIn('NEW run directory',block['next_action'])
        self.assertFalse((root/'lanes').exists());self.assertFalse(any((root/'draft/notes'/(o+'.json')).exists() for o in ('liquidity','project')))
        self.assertEqual(json.loads((root/'start-result.json').read_text())['research_status'],'blocked')
        again=start(root,target,**{**opts,'opener_factory':Denied});self.assertTrue(again['resumed']);self.assertEqual(again['research_status'],'blocked')

    def test_start_with_a_dead_rpc_endpoint_but_a_live_web_is_blocked_as_identity_unavailable(self):
        root,target,opts=self.setup_run()
        def refused(rpc,request):raise ConnectionRefusedError(61,'Connection refused')
        with unittest.mock.patch.object(RichRpc,'__call__',refused):r=start(root,target,**opts)
        self.assertEqual((r['research_status'],r['blocked'],r['lane_pointers']),('blocked','identity_unavailable',[]))
        block=next(d for d in r['diagnostics'] if d.get('category')=='identity_unavailable')
        self.assertEqual(block['failures'],{'connection_refused':2});self.assertIn('same session',block['next_action'])
        self.assertNotIn('--provider public',block['next_action'])
        self.assertTrue(Web.calls)  # the web answered, so the host network was fine and only the endpoint was dead
        packets=[json.loads(a['response']) for a in __import__('solana_session').Session(root).observations() if a['request_id'].startswith('baseline_network')]
        self.assertEqual([(p['status'],p['failure']) for p in packets],[('transport_failure','connection_refused')]*2)

    def test_blocked_paid_start_preserves_accounting_and_lock_during_permitted_document_work(self):
        from solana_broad_collect import capture
        root,target,opts=self.setup_run()
        opts['config']={**opts['config'],'provider':'drpc','headers':{'Drpc-Key':'synthetic-only'}}
        def refused(rpc,request):raise ConnectionRefusedError(61,'Connection refused')
        with unittest.mock.patch.object(RichRpc,'__call__',refused):r=start(root,target,**opts)
        self.assertEqual(r['research_status'],'blocked');before=status(root)
        self.assertGreater(before['started_attempts'],0)
        again=start(root,target,**opts)
        self.assertEqual(again['session']['started_attempts'],before['started_attempts'])
        public={**opts['config'],'provider':'public','headers':{}}
        with self.assertRaisesRegex(ValueError,'same provider flags'):
            start(root,target,**{**opts,'config':public})
        capture(root,['https://project.example/permitted-document'],opener_factory=Web)
        after=status(root);self.assertGreater(after['started_attempts'],before['started_attempts'])
        for key in ('investigation_id','received_at','deadline_at','target_at'):
            self.assertEqual(after[key],before[key])
        self.assertEqual(json.loads((root/'provider.json').read_text())['provider'],'drpc')
        self.assertFalse((root/'lanes').exists())

    def test_start_whose_identity_read_answered_is_not_blocked(self):
        root,target,opts=self.setup_run();RichRpc.mode='wrong_network';r=start(root,target,**opts)
        self.assertEqual(r['research_status'],'partial');self.assertNotIn('blocked',r)  # an answered read that mismatches is a finding, not a block

    def test_pool_vault_among_largest_holders_is_excluded_as_custody(self):
        root,target,opts=self.setup_run();vault=RichRpc.pool['vaults'][0];RichRpc.largest[target['mint']].append(vault)
        start(root,target,**opts);facts=json.loads((root/'draft/facts.json').read_text())['facts']
        holders=next(f['data'] for f in facts if f['operation']=='holders')
        row=next(a for a in holders['accounts'] if a['address']==vault)
        self.assertTrue(row['custody_exclusion'] and row['custody_exclusion']['reason'].startswith('pool_vault:'),row)
        self.assertTrue(all(e in {o['id'] for o in json.loads((root/'draft/manifest.json').read_text())['observations']} for e in row['custody_exclusion']['evidence']))
        self.assertGreater(int(holders['custody_excluded_amount_atomic']),0)
        plain=next(a for a in holders['accounts'] if a['address']!=vault);self.assertIsNone(plain['custody_exclusion'])

    def test_capture_names_a_host_network_denial(self):
        from solana_broad_collect import capture
        root,target,opts=self.setup_run();start(root,target,**opts)
        class Denied(Web):
            def open(self,request,timeout):type(self).calls.append(request.full_url);raise PermissionError(1,'Operation not permitted')
        r=capture(root,['https://project.example/denied-page'],'project',opener_factory=Denied)
        self.assertTrue(r['network_unavailable']);self.assertIn('escalated permissions',r['next']);self.assertEqual([c['failure'] for c in r['captures']],['not_permitted'])
        ok=capture(root,['https://project.example/another-page'],'project',opener_factory=Web)
        self.assertNotIn('network_unavailable',ok)

    def test_start_reads_metaplex_metadata_and_attributes_its_keys(self):
        root,target,opts=self.setup_run();r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics'])
        facts=json.loads((root/'draft/facts.json').read_text())['facts']
        meta=next(f['data'] for f in facts if f['operation']=='metadata');self.assertEqual((meta['name'],meta['update_authority'],meta['update_authority_platform']),('Fixture Token',__import__('solana_common').b58encode(bytes([90])*32),None))
        creator=next((f['data'] for f in facts if f['operation']=='creator_activity'),None);self.assertIsNotNone(creator,'metadata keys should be attributed when no launch receipt names a creator')
        self.assertEqual([(row['attribution']['role'],row['attribution']['basis']) for row in creator['keys']][:2],[('creator','metaplex_update_authority'),('creator','metaplex_verified_creator')])
        self.assertTrue(all(e in {o['id'] for o in json.loads((root/'draft/manifest.json').read_text())['observations']} for row in creator['keys'] for e in row['attribution']['evidence']))
        self.assertIn('Metaplex metadata',json.dumps(r['facts_summary']))

    def test_absent_metadata_account_is_not_a_diagnostic(self):
        root,target,opts=self.setup_run();del RichRpc.values[RichRpc.metadata['address']]
        r=start(root,target,**opts);self.assertFalse([d for d in r['diagnostics'] if d.get('category')=='unresolved_reads'],r['diagnostics'])
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertFalse([f for f in facts if f['operation'] in ('metadata','creator_activity')])  # neither receipt nor metadata: nothing is attributed

    def test_pump_curve_recorded_creator_outranks_metadata_and_an_unset_creator_is_never_attributed(self):
        import base64
        from pump_fixture import fixture as pump_fixture,put
        from adapters.pump_common import ZERO
        from solana_common import b58encode
        key=lambda n:b58encode(bytes([n])*32)
        root,target,opts=self.setup_run();_,pa,pv=pump_fixture();RichRpc.values.update(pv)
        r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics']);validate(root/'draft',True)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];creator=next(f['data'] for f in facts if f['operation']=='creator_activity')
        self.assertEqual([(k['attribution']['address'],k['attribution']['basis']) for k in creator['keys']],[(pa['creator'],'pump_curve_recorded_creator'),(key(90),'metaplex_update_authority')])
        known={o['id'] for o in json.loads((root/'draft/manifest.json').read_text())['observations']}
        self.assertTrue(all(e in known for k in creator['keys'] for e in k['attribution']['evidence']))
        # An unset curve creator decodes as the system program key and must not become an attribution.
        root2,target,opts=self.setup_run();_,pa,pv=pump_fixture();raw=bytearray(base64.b64decode(pv[pa['curve']]['data'][0]));put(raw,49,ZERO)
        pv[pa['curve']]={**pv[pa['curve']],'data':[base64.b64encode(bytes(raw)).decode(),'base64']};RichRpc.values.update(pv)
        start(root2,target,**opts);facts=json.loads((root2/'draft/facts.json').read_text())['facts'];creator=next(f['data'] for f in facts if f['operation']=='creator_activity')
        self.assertEqual([k['attribution']['basis'] for k in creator['keys']],['metaplex_update_authority','metaplex_verified_creator'])
        self.assertNotIn(ZERO,[k['address'] for k in creator['keys']])

    def test_keyed_runs_get_the_240_send_ceiling_and_public_runs_keep_120(self):
        from solana_session import KEYED_MAX_REQUESTS,PUBLIC_MAX_REQUESTS
        root,target,opts=self.setup_run();start(root,target,**opts);self.assertEqual(status(root)['max_requests'],PUBLIC_MAX_REQUESTS)
        root2,target,opts=self.setup_run();keyed={'url':'https://lb.drpc.org/solana','headers':{'Drpc-Key':'synthetic'},'provider':'drpc'}
        start(root2,target,**{**opts,'config':keyed});s=status(root2);self.assertEqual(s['max_requests'],KEYED_MAX_REQUESTS);self.assertEqual((PUBLIC_MAX_REQUESTS,KEYED_MAX_REQUESTS),(120,240),'the documented ceilings')
        self.assertEqual(json.loads((root2/'provider.json').read_text())['provider'],'drpc')

if __name__=='__main__':unittest.main()


class PublicProviderTests(unittest.TestCase):
    """The live failure on the free public endpoint: one refused method must not cancel identity or expansion."""
    setup_run=BroadTests.setup_run
    def test_refused_largest_method_does_not_block_identity_rechecks_or_expansion(self):
        import urllib.error,io
        root,target,opts=self.setup_run();original=RichRpc.__call__
        def refusing(rpc,request):
            if request['method']=='getTokenLargestAccounts':
                raise urllib.error.HTTPError('https://synthetic.invalid',429,'limited',{'Retry-After':'10','x-ratelimit-method-limit':'0'},io.BytesIO(b''))
            return original(rpc,request)
        with unittest.mock.patch.object(RichRpc,'__call__',refusing):r=start(root,target,**opts)
        s=status(root);self.assertEqual([m['method'] for m in s['unavailable_methods']],['getTokenLargestAccounts'])
        marks={m['phase']:json.loads(m['details']) for m in s['phases']}
        self.assertEqual(marks['related_accounts_controllers']['state'],'finished');self.assertEqual(marks['pool_transaction_quote_dependencies']['state'],'finished')
        f=json.loads((root/'draft/facts.json').read_text())
        controls=next(x for x in f['facts'] if x['operation']=='controls');self.assertTrue(controls['usable'])
        self.assertTrue(any(x['operation']=='pool' and x['usable'] for x in f['facts']))
        holders=next(x for x in f['facts'] if x['operation']=='holders');self.assertTrue(holders['usable'])
        self.assertEqual((holders['data']['discovery']['method'],holders['data']['discovery']['accounts_scanned']),('getProgramAccounts',1))
        pool=next(x for x in f['facts'] if x['operation']=='pool' and x['data']['adapter']['id']=='raydium_cpmm');self.assertEqual(pool['data']['lp_custody']['observed_atomic'],'450')
        self.assertTrue(any(c['method']=='getProgramAccounts' for c in RichRpc.calls));self.assertTrue(r['diagnostics'] and r['diagnostics'][0]['category']=='method_unavailable')
        self.assertIn('facts_summary',r);self.assertIn('auto-controls [',r['facts_summary'])
        self.assertEqual(s['failures'].get('method_unavailable'),1)  # One refused send; later same-method reads are never sent.
        diagnostics=json.loads((root/'import-diagnostics.json').read_text());self.assertNotIn('baseline_critical_0_0',diagnostics['unsent_intents'])


class LaneAndPresetTests(unittest.TestCase):
    setup_run=BroadTests.setup_run

    def test_lane_check_imports_the_lanes_own_capture_without_deadlocking(self):
        import threading
        from solana_broad_collect import capture,lane_check
        root,target,opts=self.setup_run();start(root,target,**opts)
        capture(root,['https://project.example/liquidity-page'],'liquidity',opener_factory=Web)
        before={o['id'] for o in json.loads((root/'draft/manifest.json').read_text())['observations']}
        outcome={}
        def run():
            try:outcome['result']=lane_check(root,'liquidity',allow_synthetic=True)
            except Exception as exc:outcome['error']=exc
        worker=threading.Thread(target=run,daemon=True);worker.start();worker.join(30)
        self.assertFalse(worker.is_alive(),'lane-check must not block on its own draft lock')
        self.assertTrue(outcome.get('result',{}).get('valid'),outcome)
        after={o['id'] for o in json.loads((root/'draft/manifest.json').read_text())['observations']};self.assertGreater(len(after),len(before))

    def test_pool_activity_preset_never_refetches_a_sampled_receipt(self):
        from transaction_fixture import fixture
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx;start(root,target,**opts)
        facts=json.loads((root/'draft/facts.json').read_text());self.assertEqual(next(f['data']['verified_receipts'] for f in facts['facts'] if f['operation']=='sales'),1)
        sent=len([c for c in RichRpc.calls if c['method']=='getTransaction'])
        result=collect(root,{'id':'act','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool'],'limit':10,'receipts':2}},opts['config'],factory=RichRpc)
        self.assertIsNone(result['preset_error']);self.assertEqual(len([c for c in RichRpc.calls if c['method']=='getTransaction']),sent)
        facts=json.loads((root/'draft/facts.json').read_text());self.assertEqual(next(f['data']['verified_receipts'] for f in facts['facts'] if f['operation']=='sales'),1)
        self.assertEqual(json.loads((root/'import-diagnostics.json').read_text())['errors'],[])
        self.assertIn('pipeline-auto-sales',json.loads((root/'draft/notes/coordinator.json').read_text())['signal_assignments'])

    def test_pool_activity_preset_classifies_probes_like_start_and_resumes(self):
        from transaction_fixture import fixture
        from solana_common import b58encode
        from solana_transactions import SYSTEM
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx;start(root,target,**opts)
        # Two newer signatures appear after start: one without a supported swap (probed, skipped) and one exact-pool swap (probed, selected, sampled).
        other=copy.deepcopy(tx);plain=b58encode(bytes([78])*64);other['transaction']['signatures'][0]=plain
        keys=other['transaction']['message']['accountKeys'];other['transaction']['message']['instructions'][a['swap_index']]['programIdIndex']=keys.index(SYSTEM)
        swap=copy.deepcopy(tx);again=b58encode(bytes([79])*64);swap['transaction']['signatures'][0]=again
        RichRpc.receipts={plain:other,again:swap};sent=len([c for c in RichRpc.calls if c['method']=='getTransaction'])
        spec={'id':'act','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool'],'limit':10,'receipts':1,'probes':4}}
        result=collect(root,spec,opts['config'],factory=RichRpc);self.assertIsNone(result['preset_error'])
        self.assertEqual(len([c for c in RichRpc.calls if c['method']=='getTransaction']),sent+2)  # one send per probe; the sample resumed the swap probe
        classification=json.loads((root/'receipt-classification.json').read_text());mine=[r for r in classification['rows'] if r['sample']=='act']
        self.assertEqual([(r['signature'],r['swap']) for r in mine],[(plain,False),(again,True)]);self.assertEqual((classification['probed'],classification['selected']),(3,2))
        receipts=json.loads((root/'automatic-receipts.json').read_text());self.assertEqual([(r['signature'],r.get('direction'),r.get('sample')) for r in receipts][-1],(again,'sell','act'))
        facts=json.loads((root/'draft/facts.json').read_text());self.assertEqual(next(f['data']['verified_receipts'] for f in facts['facts'] if f['operation']=='sales'),2)
        self.assertEqual(json.loads((root/'import-diagnostics.json').read_text())['errors'],[])
        again_result=collect(root,spec,opts['config'],factory=RichRpc);self.assertIsNone(again_result['preset_error'])
        self.assertEqual(len([c for c in RichRpc.calls if c['method']=='getTransaction']),sent+2)  # an identical preset resumes without a new send
        with self.assertRaisesRegex(ValueError,'probes'):collect(root,{'id':'bad','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool'],'receipts':3,'probes':2}},opts['config'],factory=RichRpc)

    def test_preset_id_matching_a_start_sample_is_refused_before_any_send(self):
        from transaction_fixture import fixture
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx;start(root,target,**opts);calls=len(RichRpc.calls)
        # Named like the start receipts sample, a pool_activity preset would resume start's classification as its own and report success without probing.
        with self.assertRaisesRegex(ValueError,'collides'):collect(root,{'id':'receipts','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool']}},opts['config'],factory=RichRpc)
        self.assertEqual(len(RichRpc.calls),calls);self.assertFalse((root/'preset-requests'/'receipts.json').exists())

    def test_unavailable_probe_keeps_its_status_and_a_later_preset_may_probe_it_again(self):
        from transaction_fixture import fixture
        from solana_common import b58encode
        from solana_transactions import SYSTEM
        import solana_collect_v2 as collect_v2
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx;start(root,target,**opts)
        # Three newer signatures: one whose receipt times out (probed, recorded with its status), one served without a
        # supported swap (probed, classified, skipped) and one exact-pool swap (probed, selected, sampled).
        swap=copy.deepcopy(tx);again=b58encode(bytes([79])*64);swap['transaction']['signatures'][0]=again
        other=copy.deepcopy(tx);plain=b58encode(bytes([78])*64);other['transaction']['signatures'][0]=plain
        keys=other['transaction']['message']['accountKeys'];other['transaction']['message']['instructions'][a['swap_index']]['programIdIndex']=keys.index(SYSTEM)
        lost=b58encode(bytes([80])*64);RichRpc.receipts={lost:TimeoutError('fixture timeout'),plain:other,again:swap};first=len(RichRpc.calls)
        with unittest.mock.patch.object(collect_v2,'SLEEP',lambda seconds:None):
            result=collect(root,{'id':'act','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool'],'receipts':1,'probes':4}},opts['config'],factory=RichRpc)
        self.assertIsNone(result['preset_error']);rows=[r for r in json.loads((root/'receipt-classification.json').read_text())['rows'] if r['sample']=='act']
        self.assertEqual([(r['signature'],r['receipt_status'],r['swap']) for r in rows],[(lost,'timeout',False),(plain,'ok',False),(again,'ok',True)])
        # The lost receipt got its single transient retry, each served probe was sent once and the sample resumed the swap.
        self.assertEqual([c['params'][0] for c in RichRpc.calls[first:] if c['method']=='getTransaction'],[lost,lost,plain,again])
        facts=json.loads((root/'draft/facts.json').read_text());self.assertEqual(next(f['data']['verified_receipts'] for f in facts['facts'] if f['operation']=='sales'),2)
        self.assertEqual(json.loads((root/'import-diagnostics.json').read_text())['errors'],[])
        # Once the lost receipt is served, a later preset probes only that signature. The classified non-swap row is given
        # the pre-status shape (no receipt_status key): only the compatibility default keeps it skipped, since it is not a
        # sampled receipt.
        probes_path=root/'receipt-classification.json';record=json.loads(probes_path.read_text())
        for r in record['rows']:
            if r.get('receipt_status')=='ok':r.pop('receipt_status')
        probes_path.write_text(json.dumps(record))
        served=copy.deepcopy(other);served['transaction']['signatures'][0]=lost
        RichRpc.receipts={lost:served,plain:other,again:swap};sent=len(RichRpc.calls)
        later=collect(root,{'id':'act2','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool'],'receipts':1,'probes':4}},opts['config'],factory=RichRpc)
        self.assertIsNone(later['preset_error']);self.assertEqual([c['params'][0] for c in RichRpc.calls[sent:] if c['method']=='getTransaction'],[lost])
        rows=[r for r in json.loads((root/'receipt-classification.json').read_text())['rows'] if r['sample']=='act2']
        self.assertEqual([(r['signature'],r['receipt_status'],r['swap']) for r in rows],[(lost,'ok',False)])


class ImporterBoundaryTests(unittest.TestCase):
    """A later sample outside the verified network interval stays partial; the run keeps importing."""
    setup_run=BroadTests.setup_run

    def test_failed_final_network_recheck_keeps_run_importable(self):
        from solana_import import refresh
        root,target,opts=self.setup_run('focused');start(root,target,**opts)
        before=json.loads((root/'draft/facts.json').read_text());self.assertTrue(next(x for x in before['facts'] if x['evidence_id']=='auto-controls')['usable'])
        original=RichRpc.__call__;seen={'genesis':0}
        def flaky(rpc,request):
            if request['method']=='getGenesisHash':
                seen['genesis']+=1
                if seen['genesis']>=2:raise TimeoutError('fixture: provider stalled on the final network recheck')
            return original(rpc,request)
        with unittest.mock.patch.object(RichRpc,'__call__',flaky):
            result=collect(root,{'id':'late','kind':'programs','parameters':{'addresses':[target['mint']]}},opts['config'],factory=RichRpc)
        self.assertEqual(result['research_status'],'partial')
        m=json.loads((root/'draft/manifest.json').read_text())
        late=[s for s in m['samples'] if s['observation_id'].startswith('late_')];self.assertTrue(late)
        self.assertTrue(all(s['status']=='partial' for s in late))
        after=json.loads((root/'draft/facts.json').read_text())
        # The newest snapshot sits outside the verified interval and stays unusable; the controls fact keeps the earlier pinned one.
        controls=next(x for x in after['facts'] if x['evidence_id']=='auto-controls');self.assertTrue(controls['usable'])
        self.assertEqual(controls['data']['selection_scope'],'earlier_pinned_snapshot_newer_unpinned');self.assertEqual(controls['data']['newer_unpinned']['authorities_match'],True)
        self.assertFalse(any(x['evidence_id']=='prior-controls' for x in after['facts']));self.assertIn('its controllers are unchanged',controls['summary'])
        self.assertTrue(next(x for x in after['facts'] if x['evidence_id']=='auto-sizes')['usable'])
        again=refresh(root);self.assertEqual(again['research_status'],'partial')  # A second import never raises.
        validate(root/'draft',True)

    def test_later_unpinned_pool_read_keeps_the_earlier_usable_pool_fact(self):
        from solana_common import sha
        root,target,opts=self.setup_run();start(root,target,**opts);pid='pool-'+sha(RichRpc.pool['pool'].encode())[:16]
        before=json.loads((root/'draft/facts.json').read_text());self.assertTrue(next(x for x in before['facts'] if x['evidence_id']==pid)['usable'])
        original=RichRpc.__call__;seen={'genesis':0}
        def flaky(rpc,request):
            if request['method']=='getGenesisHash':
                seen['genesis']+=1
                if seen['genesis']>=2:raise TimeoutError('fixture: provider stalled on the final network recheck')
            return original(rpc,request)
        with unittest.mock.patch.object(RichRpc,'__call__',flaky):
            result=collect(root,{'id':'late','kind':'pool','parameters':{'adapter':'raydium_cpmm','pool':RichRpc.pool['pool']}},opts['config'],factory=RichRpc)
        self.assertEqual(result['research_status'],'partial')
        # The newest pool read is unpinned; the pool fact keeps the earlier pinned read instead of becoming a coverage gap.
        after=json.loads((root/'draft/facts.json').read_text());self.assertTrue(next(x for x in after['facts'] if x['evidence_id']==pid)['usable'])
        m=json.loads((root/'draft/manifest.json').read_text());self.assertTrue([s for s in m['samples'] if s['observation_id'].startswith('late_') and s['status']=='partial'])

    def test_node_lag_is_retried_a_few_times_before_a_read_fails(self):
        from solana_transport import NODE_LAG_CODES
        root,target,opts=self.setup_run();original=RichRpc.__call__;lagged={'n':0}
        def lagging(rpc,request):
            if request['method']=='getEpochInfo' and lagged['n']<2:
                lagged['n']+=1;return {'jsonrpc':'2.0','id':request['id'],'error':{'code':sorted(NODE_LAG_CODES)[0],'message':'Minimum context slot has not been reached'}}
            return original(rpc,request)
        import solana_collect_v2;sleeps=[]
        with unittest.mock.patch.object(RichRpc,'__call__',lagging),unittest.mock.patch.object(solana_collect_v2,'SLEEP',sleeps.append):result=start(root,target,**opts)
        self.assertFalse(result['diagnostics'],result['diagnostics'])
        import sqlite3;rows=[r for r in sqlite3.connect(root/'session.sqlite').execute("select request_id,status from attempts where family='baseline_epoch' order by id")]
        self.assertEqual([r[1] for r in rows],['node_lag','node_lag','ok']);self.assertEqual([r[0][-1] for r in rows],['0','1','2'])
        self.assertEqual([s for s in sleeps if s==2.0],[2.0,2.0])  # an error naming no backend slot waits the default before each retry

    def test_node_lag_stops_at_the_retry_budget(self):
        from solana_transport import NODE_LAG_CODES
        root,target,opts=self.setup_run();original=RichRpc.__call__
        def always_lag(rpc,request):
            if request['method']=='getEpochInfo':return {'jsonrpc':'2.0','id':request['id'],'error':{'code':sorted(NODE_LAG_CODES)[0],'message':'Minimum context slot has not been reached'}}
            return original(rpc,request)
        import solana_collect_v2
        with unittest.mock.patch.object(RichRpc,'__call__',always_lag),unittest.mock.patch.object(solana_collect_v2,'SLEEP',lambda s:None):start(root,target,**opts)
        import sqlite3;rows=[r[0] for r in sqlite3.connect(root/'session.sqlite').execute("select status from attempts where family='baseline_epoch' order by id")]
        self.assertEqual(rows,['node_lag']*(solana_collect_v2.NODE_LAG_RETRIES+1))  # capped at the retry budget, never an unbounded loop
        self.assertFalse((root/'read-intents'/'baseline_epoch_4.json').exists())

    def test_a_transient_failure_before_node_lag_does_not_extend_the_retry_budget(self):
        import urllib.error,io
        from solana_transport import NODE_LAG_CODES
        root,target,opts=self.setup_run();original=RichRpc.__call__;seen={'n':0}
        def transient_then_lag(rpc,request):
            if request['method']=='getEpochInfo':
                seen['n']+=1
                if seen['n']==1:raise urllib.error.HTTPError('u',503,'busy',{},io.BytesIO(b''))
                return {'jsonrpc':'2.0','id':request['id'],'error':{'code':sorted(NODE_LAG_CODES)[0],'message':'Minimum context slot has not been reached'}}
            return original(rpc,request)
        import solana_collect_v2
        with unittest.mock.patch.object(RichRpc,'__call__',transient_then_lag),unittest.mock.patch.object(solana_collect_v2,'SLEEP',lambda s:None):result=start(root,target,**opts)
        import sqlite3;rows=[r[0] for r in sqlite3.connect(root/'session.sqlite').execute("select status from attempts where family='baseline_epoch' order by id")]
        self.assertEqual(rows,['http_503','node_lag'])  # one transient retry only; node lag after it does not buy more attempts
        self.assertFalse((root/'read-intents'/'baseline_epoch_2.json').exists())  # no ineligible third attempt/intent
        self.assertFalse([d for d in result['diagnostics'] if d.get('category')=='unsent_reads'],result['diagnostics'])

    def test_node_lag_wait_is_the_slot_gap_the_error_names(self):
        from solana_collect_v2 import lag_delay
        request={'method':'getMultipleAccounts','params':[['m'],{'commitment':'finalized','minContextSlot':1000}]}
        lag=lambda slot:{'status':'node_lag','response':{'error':{'code':-32016,'message':'Minimum context slot has not been reached','data':{'contextSlot':slot}}}}
        self.assertEqual(lag_delay(request,lag(970)),13.0)  # 30 slots behind at 0.4 s each, plus a second
        self.assertEqual(lag_delay(request,lag(10)),20.0)  # bounded
        self.assertEqual(lag_delay(request,lag(1000)),2.0)  # not behind the floor (another lag code): the default
        self.assertEqual(lag_delay(request,{'status':'node_lag','response':{'error':{'code':-32004,'message':'Block not available'}}}),2.0)
        self.assertEqual(lag_delay({'method':'getEpochInfo','params':[{'commitment':'finalized'}]},lag(1)),2.0)  # no floor pinned

    def test_account_census_methods_get_a_longer_request_timeout(self):
        from solana_collect_v2 import request_timeout
        self.assertEqual((request_timeout('getTokenLargestAccounts'),request_timeout('getProgramAccounts'),request_timeout('getAccountInfo'),request_timeout('getTransaction')),(20,20,5,5))

    def test_candidates_rank_within_one_indexer_scale_at_a_time(self):
        import solana_broad_collect as module
        docs=[{'source':'geckoterminal','candidates':[{'pool':'GT','liquidity_usd':'9000000'},{'pool':'D2','liquidity_usd':'5'}]},
              {'source':'dexscreener','candidates':[{'pool':'D1','liquidity_usd':'100'},{'pool':'D2','liquidity_usd':'200'}]}]
        with unittest.mock.patch.object(module,'market_documents',lambda root,target:docs):rows=module.candidates('.',{'mint':'x'})
        # Primary-listed pools first by the primary's figure (D2 200 over D1 100); the alternate-only pool's larger figure is a different scale and ranks after.
        self.assertEqual([(r['pool'],r['liquidity_usd']) for r in rows],[('D2','200'),('D1','100')])
        docs[1]['candidates']=[{'pool':'D1','liquidity_usd':'100'}]
        with unittest.mock.patch.object(module,'market_documents',lambda root,target:docs):self.assertEqual([r['pool'] for r in module.candidates('.',{'mint':'x'})],['D1','GT'])
        # When every shared pool agrees within a factor of two the indexers report one scale, and an alternate-only pool
        # larger than the primary's second pool ranks by its figure instead of being lost (the DLMM diversity run).
        docs=[{'source':'geckoterminal','candidates':[{'pool':'Z','liquidity_usd':'4599051'},{'pool':'GT','liquidity_usd':'3698062'},{'pool':'A','liquidity_usd':'1314361'}]},
              {'source':'dexscreener','candidates':[{'pool':'A','liquidity_usd':'1314878'},{'pool':'Z','liquidity_usd':'4614790'},{'pool':'D','liquidity_usd':'1405944'}]}]
        with unittest.mock.patch.object(module,'market_documents',lambda root,target:docs):self.assertEqual([(r['pool'],r['liquidity_usd']) for r in module.candidates('.',{'mint':'x'})],[('Z','4614790'),('GT','3698062')])
        docs[0]['candidates'][0]['liquidity_usd']='45990510'  # one shared pool ten times apart: different scales again
        with unittest.mock.patch.object(module,'market_documents',lambda root,target:docs):self.assertEqual([r['pool'] for r in module.candidates('.',{'mint':'x'})],['Z','D'])

    def test_indexer_listed_trades_are_probed_before_a_bot_dominated_chain_listing(self):
        from transaction_fixture import fixture
        from solana_common import b58encode
        from solana_transactions import SYSTEM
        def seed():
            root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
            tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
            tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx
            # Seven newer receipts touch the pool without a supported swap: the chain listing alone exhausts the probe window.
            bots={}
            for n in range(7):
                other=copy.deepcopy(tx);sig=b58encode(bytes([60+n])*64);other['transaction']['signatures'][0]=sig
                keys=other['transaction']['message']['accountKeys'];other['transaction']['message']['instructions'][a['swap_index']]['programIdIndex']=keys.index(SYSTEM);bots[sig]=other
            RichRpc.receipts=bots;return root,target,opts,tx['transaction']['signatures'][0]
        root,target,opts,swap=seed();result=start(root,target,**opts);self.assertFalse(result['diagnostics'],result['diagnostics'])
        classification=json.loads((root/'receipt-classification.json').read_text())
        standard=[r for r in classification['rows'] if r['sample']=='receipts']
        self.assertEqual((len(standard),sum(r['swap'] for r in standard),classification['listings'][0]['listed'],classification['listings'][0]['indexed_candidates']),(6,0,8,0))
        # No sale verified, so start ran the recommended pool_activity preset itself: it probed the two listed signatures the
        # standard window left and found the swap, so the sale is verified inside start without a coordinator turn.
        activity=next(r for r in result['presets_run'] if r['kind']=='pool_activity');self.assertEqual((activity['status'],activity['error']),('ran',None))
        self.assertEqual((classification['probed'],classification['selected']),(8,1));self.assertEqual([r['sample'] for r in classification['rows'] if r['swap']],['rec-activity'])
        self.assertEqual([(r['sample'],r['signature']) for r in json.loads((root/'automatic-receipts.json').read_text())],[('rec-activity',swap)])
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertEqual(next(f['data']['verified_receipts'] for f in facts if f['operation']=='sales'),1)
        # The indexer lists the swap as a sell: it is probed first and the receipt verifies it, one probe instead of a missed window.
        root,target,opts,swap=seed()
        Web.trades=[{'id':'t1','type':'trade','attributes':{'tx_hash':swap,'kind':'sell','block_number':100,'tx_from_address':key(8)}},
                    {'id':'t2','type':'trade','attributes':{'tx_hash':swap,'kind':'sell','block_number':100,'tx_from_address':key(8)}}]  # a duplicate row is one candidate
        result=start(root,target,**opts);self.assertFalse(result['diagnostics'],result['diagnostics']);validate(root/'draft',True)
        classification=json.loads((root/'receipt-classification.json').read_text())
        # The first probe is the indexed sell; the remaining probes keep looking for a second receipt among the bots.
        self.assertEqual((classification['probed'],classification['selected'],classification['listings'][0]['indexed_candidates']),(6,1,1))
        self.assertEqual([r['swap'] for r in classification['rows']],[True]+[False]*5);self.assertIn(swap,[r['signature'] for r in json.loads((root/'automatic-receipts.json').read_text())])
        self.assertTrue(any(u.endswith('/pools/'+RichRpc.pool['pool']+'/trades') for u in Web.calls))

    def test_pipeline_captures_never_consume_the_lane_capture_allowance(self):
        from solana_broad_collect import capture
        root,target,opts=self.setup_run();start(root,target,**opts)
        import solana_session
        s=solana_session.Session(root)
        try:
            pipeline=s.db.execute("SELECT count(*) FROM web_sources WHERE owner='ordinary' AND status='pending'").fetchone()[0]
        finally:s.close()
        self.assertGreaterEqual(pipeline,9)  # discovery pages, the project link, the leading pool's trade feed and the three-size quote ladder
        urls=['https://lane.example/page'+str(n) for n in range(12)]
        result=capture(root,urls,'project',opener_factory=Web)
        self.assertEqual(len(result['captures']),12);self.assertEqual(result['unattempted'],[])
        self.assertEqual(capture(root,['https://lane.example/extra'],'liquidity',opener_factory=Web)['unattempted'][0]['status'],'unattempted_cap')
        # The pipeline's own class is capped at sixteen, independently of the lanes' twelve.
        more=capture(root,['https://pipeline.example/page'+str(n) for n in range(16-pipeline+1)],'ordinary',opener_factory=Web)
        self.assertEqual((len(more['captures']),[r['status'] for r in more['unattempted']]),(16-pipeline,['unattempted_cap']))

    def test_start_runs_the_recommended_queue_itself_and_defers_it_only_near_the_lane_cutoff(self):
        from solana_broad_collect import collect,recommended_presets
        root,target,opts=self.setup_run();result=start(root,target,**opts)
        # No receipt verified a sale, the metadata authority has no history page and the pool program was never read: start
        # derived the three rows and ran them itself, in order, under the run's own grant, so nothing is left to recommend.
        ran=result['presets_run'];self.assertEqual([(r['id'],r['kind'],r['status'],r['error']) for r in ran],[('rec-activity','pool_activity','ran',None),('rec-history','creator_history','ran',None),('rec-programs','programs','ran',None)])
        self.assertEqual(result['recommended_presets'],[]);self.assertIn('rec-activity, rec-history, rec-programs already ran inside start',result['next']);self.assertIn('no preset remains recommended',result['next'])
        self.assertEqual(sorted(p.stem for p in (root/'preset-requests').glob('*.json')),['rec-activity','rec-history','rec-programs'])
        for r in ran:
            spec=json.loads((root/'recommended-presets'/(r['id']+'.json')).read_text());self.assertEqual(set(spec),{'id','kind','parameters'});self.assertEqual(spec,json.loads((root/'preset-requests'/(r['id']+'.json')).read_text()))
        self.assertEqual([r['sends'] for r in ran],[13,6,6]);self.assertTrue({'preset_rec-activity','preset_rec-history','preset_rec-programs'}<={x['phase'] for x in status(root)['phases']})
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertEqual({d['parameters']['address'] for d in json.loads((root/'draft/manifest.json').read_text())['derivations'] if d['operation']=='history'},{key(90),key(91)})
        self.assertLessEqual(status(root)['started_attempts'],120)
        # The recommended rows never count against the coordinator's four: four named presets still run and a fifth is refused.
        for n in range(4):
            named=collect(root,{'id':'named'+str(n),'kind':'programs','parameters':{'addresses':[target['mint']]}},opts['config'],factory=RichRpc);self.assertIsNone(named['preset_error'],named['preset_error'])
        with self.assertRaisesRegex(ValueError,'Four coordinator'):collect(root,{'id':'named5','kind':'programs','parameters':{'addresses':[target['mint']]}},opts['config'],factory=RichRpc)
        # Near the lane cutoff start defers the queue: the rows stay printed with their request files and the coordinator runs them.
        root,target,opts=self.setup_run();opts={**opts,'received_at':time.time()-200,'deadline_at':time.time()+400}  # lane cutoff in 100 s, collection cutoff in 280 s
        result=start(root,target,**opts);queue=result['recommended_presets'];kinds=[q['kind'] for q in queue]
        self.assertEqual(kinds,['pool_activity','creator_history','programs']);self.assertEqual([(r['status'],r['error']) for r in result['presets_run']],[('deferred',None)]*3)
        self.assertIn('lane cutoff',result['presets_run'][0]['reason']);self.assertIn('remaining recommended presets in order',result['next']);self.assertIn('lane cutoff',result['next'])
        self.assertEqual(queue[0]['parameters'],{'pool':RichRpc.pool['pool'],'limit':25,'receipts':2,'probes':6})
        self.assertEqual(queue[1]['parameters'],{'keys':[key(90),key(91)]});self.assertEqual(queue[2]['dimension'],'external_dependencies')  # update authority and verified creator
        for q in queue:
            spec=json.loads(Path(q['request']).read_text());self.assertEqual(set(spec),{'id','kind','parameters'});self.assertIn('recommended-presets',q['request'])
        self.assertFalse(list((root/'preset-requests').glob('*.json')) if (root/'preset-requests').exists() else [],'deferred requests are not leads until they run')
        # Running the history recommendation from its request file removes it from the queue.
        spec=json.loads(Path(queue[1]['request']).read_text());after=collect(root,spec,opts['config'],factory=RichRpc)
        self.assertIsNone(after['preset_error']);self.assertEqual([q['kind'] for q in after['recommended_presets']],['pool_activity','programs'])
        # A row whose preset ran without closing its gap leaves the queue: the open gap is the named limit, not a loop.
        spec=json.loads(Path(after['recommended_presets'][0]['request']).read_text());self.assertEqual(spec['kind'],'pool_activity')
        again=collect(root,spec,opts['config'],factory=RichRpc);self.assertIsNone(again['preset_error'])
        self.assertEqual([q['kind'] for q in again['recommended_presets']],['programs'])
        # Four coordinator-named request files leave the recommended row in place: the cap bounds the coordinator, not the pipeline's own queue.
        for n in range(4):(root/'preset-requests'/('pad'+str(n)+'.json')).write_text('{}')
        self.assertEqual([q['kind'] for q in recommended_presets(root)],['programs'])
        # A verified sale removes the sellability recommendation.
        from transaction_fixture import fixture
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx
        self.assertNotIn('pool_activity',[q['kind'] for q in start(root,target,**opts)['recommended_presets']])
        # A focused run gets no queue and no request folder.
        root,target,opts=self.setup_run();focused=start(root,target,**{**opts,'scope':'focused','surfaces':['token_controls']})
        self.assertEqual(focused['recommended_presets'],[]);self.assertFalse((root/'recommended-presets').exists())

    def test_start_rechecks_the_grant_per_row_names_refusals_and_credits_an_earlier_attempt(self):
        import solana_broad_collect
        from transaction_fixture import fixture
        from solana_common import b58encode
        from solana_transactions import SYSTEM
        # A bot-dominated listing makes the activity row spend most of a small grant: the later rows are re-checked against the
        # live session and deferred for budget instead of being started and refused mid-preset.
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']];tx['blockTime']=RichRpc.stamp
        bots={}
        for n in range(7):
            other=copy.deepcopy(tx);sig=b58encode(bytes([60+n])*64);other['transaction']['signatures'][0]=sig
            keys=other['transaction']['message']['accountKeys'];other['transaction']['message']['instructions'][a['swap_index']]['programIdIndex']=keys.index(SYSTEM);bots[sig]=other
        RichRpc.receipts=bots;RichRpc.receipt=tx
        # Measure what the standard stages spend (a deferred-queue start with the same seed), then leave exactly 17 sends: the
        # 13-send activity row fits the initial filter and what it spends starves a later row.
        probe=start(root,target,**{**opts,'received_at':time.time()-200,'deadline_at':time.time()+400});measured=status(root)
        self.assertTrue(all(r['status']=='deferred' for r in probe['presets_run']));ceiling=measured['max_requests']-measured['remaining_requests']+17
        root,target,opts=self.setup_run();RichRpc.receipts=bots;RichRpc.receipt=tx
        with unittest.mock.patch.object(solana_broad_collect,'PUBLIC_MAX_REQUESTS',ceiling):result=start(root,target,**opts)
        rows={r['id']:r for r in result['presets_run']};self.assertEqual(rows['rec-activity']['status'],'ran',rows)
        deferred=[r for r in result['presets_run'] if r['status']=='deferred'];self.assertTrue(deferred,result['presets_run'])
        self.assertTrue(all('leftover grant' in r['reason'] for r in deferred),deferred);self.assertLessEqual(status(root)['started_attempts'],ceiling)
        self.assertEqual(result['recommended_presets'],[],'an unaffordable row is dropped, not re-offered');self.assertIn('deferred: rec-history: the leftover grant',result['next'])
        # A row refused before its request is recorded is a named limit: it leaves the queue and next says so instead of asking for a rerun.
        root,target,opts=self.setup_run();original=solana_broad_collect.collect
        def refusing(root,spec,config,**kw):
            if spec['id']=='rec-history':raise ValueError('Pool lead has not been captured.')
            return original(root,spec,config,**kw)
        with unittest.mock.patch.object(solana_broad_collect,'collect',refusing):result=start(root,target,**opts)
        self.assertEqual([(r['id'],r['status']) for r in result['presets_run']],[('rec-activity','ran'),('rec-history','refused'),('rec-programs','ran')])
        self.assertEqual(result['presets_run'][1]['error']['reason'],'Pool lead has not been captured.');self.assertFalse((root/'preset-requests/rec-history.json').exists())
        self.assertEqual(result['recommended_presets'],[]);self.assertIn('rec-history was refused before any send (Pool lead has not been captured.)',result['next']);self.assertNotIn('rec-history already',result['next'])
        # A start that died after its queue and before its result file credits the rows the earlier attempt ran.
        root,target,opts=self.setup_run();start(root,target,**opts);(root/'start-result.json').unlink();again=start(root,target,**opts)
        self.assertEqual([(r['id'],r['status'],r.get('reason')) for r in again['presets_run']],[(i,'ran','ran in an earlier attempt of this start') for i in ('rec-activity','rec-history','rec-programs')])
        self.assertEqual(again['recommended_presets'],[]);self.assertIn('rec-activity, rec-history, rec-programs already ran inside start',again['next'])

    def test_lane_leads_become_presets_that_follow_up_runs_mechanically(self):
        from solana_broad_collect import lane_leads,recommended_presets,follow_up,lane_check
        from solana_scaffold import scaffold
        from solana_common import b58encode
        from solana_compose import ComposeError
        root,target,opts=self.setup_run();opts={**opts,'received_at':time.time()-400,'deadline_at':time.time()+300};start(root,target,**opts)  # the lane cutoff has passed: follow-up time
        sig=b58encode(bytes([7])*64);note=scaffold(root/'draft','project',True)
        note['leads']=[{'kind':'creator_key','value':key(95),'reason':'the platform token page names this creator'},{'kind':'signature','value':sig,'reason':'a burn the docs cite'}]
        (root/'draft/notes/project.json').write_text(json.dumps(note))
        self.assertEqual([(l['kind'],l['value'],l['owner']) for l in lane_leads(root)],[('creator_key',key(95),'project'),('signature',sig,'project')])
        queue={q['id']:q for q in recommended_presets(root)}
        self.assertEqual((queue['rec-lanekeys']['kind'],queue['rec-lanekeys']['parameters'],queue['rec-lanekeys']['dimension']),('creator_history',{'keys':[key(95)]},'historical_launch_integrity'))
        self.assertEqual((queue['rec-lanetx']['kind'],queue['rec-lanetx']['parameters']),('transactions',{'signatures':[sig]}));self.assertIn('platform token page',queue['rec-lanekeys']['reason'])
        # One coordinator command after the lanes returned runs both rows with no lane window owed, refreshes and resyncs the note.
        before=status(root)['remaining_requests'];result=follow_up(root,opts['config'],factory=RichRpc)
        # start deferred its own three rows (too close to the lane cutoff); the follow-up owes no lane window, so they run with the lane rows.
        self.assertEqual({(r['id'],r['status']) for r in result['presets_run']},{('rec-lanekeys','ran'),('rec-lanetx','ran'),('rec-activity','ran'),('rec-history','ran'),('rec-programs','ran')});self.assertEqual(result['recommended_presets'],[]);self.assertIsNone(result['queue_note'])
        self.assertEqual(result['lane_grants_released'],30,'past the lane cutoff both lanes\' unspent reservations return to the ordinary pool');self.assertGreater(result['session']['started_attempts'],0)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertIn(key(95),{f['data'].get('address') for f in facts if f['operation']=='history'})
        self.assertEqual(len(result['leads']),2);self.assertTrue((root/'preset-requests/rec-lanekeys.json').exists())
        # The chain attributed its own keys, so the launch row closes on them and never mentions the lane key; the lane key's history
        # is still read and filed on the admin surface as a lane-named observation (extra evidence that holds nothing open).
        rows={r['dimension']:r for r in json.loads((root/'draft/notes/coordinator.json').read_text())['coverage']}
        self.assertNotIn(key(95)[:8],rows['historical_launch_integrity']['closure']['reason']);self.assertIn('Creator attribution and activity are typed facts',rows['admin_treasury_reward_custody']['closure']['reason'])
        lanekey=[f for f in json.loads((root/'draft/notes/pipeline.json').read_text())['findings'] if f['id'].startswith('pipeline-lanekey-')]
        self.assertEqual([f['dimension'] for f in lanekey],['admin_treasury_reward_custody']);self.assertIn(key(95),lanekey[0]['text'])
        self.assertEqual(sum(1 for l in lanekey[0]['limitations'] if l.startswith('gaps:')),1,'the history fact\'s limits are carried once')
        # A malformed lead is refused by the lane's own self-check, never silently dropped from the queue.
        note['leads']=[{'kind':'wallet','value':key(95),'reason':'x'}];(root/'draft/notes/project.json').write_text(json.dumps(note))
        with self.assertRaises(ComposeError) as ctx:lane_check(root,'project',allow_synthetic=True)
        self.assertTrue(any(e['path']=='leads' for e in ctx.exception.errors));self.assertEqual(lane_leads(root),[])

    def test_refresh_recomputes_untouched_coverage_rows_and_keeps_edited_ones(self):
        from solana_broad_collect import collect
        from solana_coverage import untouched
        from solana_scaffold import sync_assignments
        root,target,opts=self.setup_run();opts={**opts,'received_at':time.time()-200,'deadline_at':time.time()+400};result=start(root,target,**opts)  # queue deferred: history not yet read
        path=root/'draft/notes/coordinator.json';note=json.loads(path.read_text());rows={r['dimension']:r for r in note['coverage']}
        self.assertEqual((rows['historical_launch_integrity']['closure']['boundary'],rows['historical_launch_integrity']['closure']['next_route']),('pending','creator_history'))
        edited=rows['token_controls'];edited['status']='partial';edited['decision_impact']='Held open by the coordinator pending a controller review.';edited['closure'].update(boundary='pending',standard_scope_complete=False,next_route='standard')
        path.write_text(json.dumps(note));kept=json.loads(json.dumps(edited))
        spec=json.loads(Path(next(q for q in result['recommended_presets'] if q['kind']=='creator_history')['request']).read_text());after=collect(root,spec,opts['config'],factory=RichRpc);self.assertIsNone(after['preset_error'])
        rows={r['dimension']:r for r in json.loads(path.read_text())['coverage']}
        self.assertEqual((rows['historical_launch_integrity']['closure']['boundary'],rows['historical_launch_integrity']['closure']['next_route']),('pending','transactions'),'the untouched row followed the new history facts: the receipt route is now the one open')
        self.assertTrue(untouched(rows['historical_launch_integrity']));self.assertEqual(rows['token_controls'],kept,'the edited row is byte-identical');self.assertFalse(untouched(rows['token_controls']))
        # A lane finding on a lane-owned surface counts at the sync exactly as it does at compose.
        project=json.loads((root/'draft/notes/project.json').read_text());project['checklist']={k:{'status':'done','reason':'answered'} for k in project['checklist']}
        project['findings']=[{'id':'project-econ','dimension':'reward_accounting_liveness','claim':'source_analysis','strength':'bounded','text':'No reward is claimed.','support':[]}]
        (root/'draft/notes/project.json').write_text(json.dumps(project));sync_assignments(root/'draft');rows={r['dimension']:r for r in json.loads(path.read_text())['coverage']}
        self.assertEqual((rows['reward_accounting_liveness']['closure']['boundary'],rows['reward_accounting_liveness']['finding_ids']),('resolved',['project-econ']))
        self.assertIn('no affirmative finding',rows['utility_redemption_rights']['closure']['reason'])

    def test_start_prefills_coverage_closures_from_the_facts(self):
        root,target,opts=self.setup_run();result=start(root,target,**opts)
        note=json.loads((root/'draft/notes/coordinator.json').read_text());rows={r['dimension']:r for r in note['coverage']}
        closed={d for d,r in rows.items() if r['closure']['boundary']=='resolved'};open_={d:r['closure']['next_route'] for d,r in rows.items() if r['closure']['boundary']=='pending'}
        # Controls, the exact largest-20 holders, the observed leading pool, the single discovered pool, the quote ladder and creator attribution all answered
        # in start; the pool program stayed unread, and with histories read for both keys the launch row still waits for a sampled receipt.
        self.assertEqual(closed,{'token_controls','current_concentration','canonical_lp_principal_custody','side_pool_removal_risk','sellability_exit_depth','admin_treasury_reward_custody'},rows)
        self.assertEqual(open_,{'external_dependencies':'programs','historical_launch_integrity':'transactions','development_disclosure':'standard','utility_redemption_rights':'standard','reward_accounting_liveness':'standard'})
        self.assertIn('No receipt was sampled',rows['historical_launch_integrity']['closure']['reason'])
        self.assertTrue(all(rows[d]['closure']['next_route']=='standard' and 'project lane' in rows[d]['closure']['reason'] for d in ('development_disclosure','utility_redemption_rights','reward_accounting_liveness')))
        self.assertTrue(all(rows[d]['status']=='checked' and rows[d]['pending_work']==[] and rows[d]['closure']['standard_scope_complete'] for d in closed))
        self.assertTrue(all(r['prefill']['basis']=='mechanical' for r in note['coverage']))
        pipeline=json.loads((root/'draft/notes/pipeline.json').read_text());side=[f for f in pipeline['findings'] if f['dimension']=='side_pool_removal_risk']
        self.assertEqual(len(side),1);self.assertIn('no side pool exists to sample',side[0]['text']);self.assertEqual(side[0]['claim'],'source_analysis')

    def test_a_later_mint_re_read_keeps_the_quote_ladder_at_the_sizes_that_were_quoted(self):
        from solana_broad_collect import collect,recommended_presets
        from solana_scaffold import scaffold
        root,target,opts=self.setup_run();opts={**opts,'deadline_at':time.time()+3000};start(root,target,**opts)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertEqual(next(f for f in facts if f['operation']=='quote_ladder')['data']['sizes_quoted'],3)
        # A lane-named creator key read six minutes later re-reads the mint for its pin; the captured $2 price is then older than the policy's five-minute window.
        note=scaffold(root/'draft','project',True);note['leads']=[{'kind':'creator_key','value':key(95),'reason':'named by the project page'}];(root/'draft/notes/project.json').write_text(json.dumps(note))
        spec=json.loads(Path(next(q for q in recommended_presets(root) if q['id']=='rec-lanekeys')['request']).read_text())
        real=time.time;stamp=RichRpc.stamp;original=RichRpc.__call__
        def later(rpc,request):  # the chain has moved on to slot 101 with a fresh header, so the re-read is a pinned, usable snapshot
            result=original(rpc,request);m=request['method']
            if m=='getBlock' and request['params'][0]==101:result['result'].update(blockhash=key(22),previousBlockhash=key(20),parentSlot=100,blockTime=stamp+330)
            elif m=='getBlockTime' and request['params'][0]==101:result['result']=stamp+330
            elif m in ('getAccountInfo','getMultipleAccounts'):result['result']['context']['slot']=101
            return result
        with unittest.mock.patch.object(RichRpc,'__call__',later),unittest.mock.patch.object(time,'time',lambda:real()+330):after=collect(root,spec,opts['config'],factory=RichRpc)
        self.assertIsNone(after['preset_error']);facts=json.loads((root/'draft/facts.json').read_text())['facts']
        self.assertEqual(next(f for f in facts if f['operation']=='controls')['data']['selection_scope'],'latest_retained_account_snapshot','the later read is the usable snapshot')
        self.assertIn(key(95),{f['data'].get('address') for f in facts if f['operation']=='history'})
        sizes=next(f for f in facts if f['operation']=='quote_sizes')
        self.assertEqual((sizes['data']['basis'],sizes['data']['gaps']),('illustrative_USD_equivalents_floor_to_atomic_units',[]),'the size policy is judged as of the first captured quote, not the newest mint read')
        ladder=next(f for f in facts if f['operation']=='quote_ladder');self.assertEqual((ladder['usable'],ladder['data']['sizes_quoted'],ladder['data']['largest_impact_vs_smallest_percent']),(True,3,'9.9099'))

    def test_a_lane_named_creator_closes_launch_and_admin_when_the_chain_attributes_none(self):
        from transaction_fixture import fixture
        from solana_broad_collect import follow_up
        from solana_scaffold import scaffold
        from solana_metadata import metadata_address
        root,target,opts=self.setup_run();opts={**opts,'received_at':time.time()-400,'deadline_at':time.time()+300}
        _,a,packet,_=fixture();tx=packet['response']['result'];tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx  # a sampled receipt gives the launch fact; nothing in it names a creator
        original=RichRpc.__call__;pda=metadata_address(target['mint'])
        def no_metadata(rpc,request):  # a Token-2022 style mint without a Metaplex metadata account: the chain attributes no creator
            result=original(rpc,request)
            if request['method']=='getAccountInfo' and request['params'][0]==pda:result['result']['value']=None
            return result
        with unittest.mock.patch.object(RichRpc,'__call__',no_metadata):start(root,target,**opts)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertFalse([f['operation'] for f in facts if f['operation'] in ('metadata','creator_activity')],'no chain attribution')
        self.assertTrue([f for f in facts if f['operation']=='launch'])
        rows={r['dimension']:r for r in json.loads((root/'draft/notes/coordinator.json').read_text())['coverage']}
        self.assertEqual((rows['historical_launch_integrity']['closure']['next_route'],rows['admin_treasury_reward_custody']['closure']['next_route']),('standard','standard'))
        self.assertFalse([f for f in json.loads((root/'draft/notes/pipeline.json').read_text())['findings'] if f['id'].startswith('pipeline-lanekey-')],'no lane, no lane-key finding')
        # The project lane names the creator from the launch platform; the follow-up reads that key's history and both surfaces close on it.
        note=scaffold(root/'draft','project',True);note['leads']=[{'kind':'creator_key','value':key(95),'reason':'the platform launch record names this creator'}]
        note['checklist']={k:{'status':'done','reason':'answered'} for k in note['checklist']};(root/'draft/notes/project.json').write_text(json.dumps(note))
        liq=scaffold(root/'draft','liquidity',True);liq['checklist']={k:{'status':'done','reason':'answered'} for k in liq['checklist']};(root/'draft/notes/liquidity.json').write_text(json.dumps(liq))
        with unittest.mock.patch.object(RichRpc,'__call__',no_metadata):result=follow_up(root,opts['config'],factory=RichRpc)
        self.assertIn(('rec-lanekeys','ran'),{(p['id'],p['status']) for p in result['presets_run']},result['presets_run'])
        rows={r['dimension']:r for r in json.loads((root/'draft/notes/coordinator.json').read_text())['coverage']};launch=rows['historical_launch_integrity'];admin=rows['admin_treasury_reward_custody']
        self.assertEqual((launch['closure']['boundary'],admin['closure']['boundary']),('resolved','resolved'),(launch['closure'],admin['closure']))
        self.assertIn('(project lane: the platform launch record names this creator)',launch['closure']['reason']);self.assertIn('lane-named key',admin['closure']['reason'])
        pipeline=json.loads((root/'draft/notes/pipeline.json').read_text());lanekey=[f for f in pipeline['findings'] if f['id'].startswith('pipeline-lanekey-')]
        self.assertEqual(len(lanekey),1);self.assertEqual(lanekey[0]['dimension'],'admin_treasury_reward_custody');self.assertIn(key(95),lanekey[0]['text']);self.assertIn(lanekey[0]['id'],admin['finding_ids'])
        self.assertIn('named by the project lane (the platform launch record names this creator)',lanekey[0]['text']);self.assertIn('slots (',lanekey[0]['text']);self.assertTrue(any('Lane attribution only (project lane)' in l for l in lanekey[0]['limitations']))
        self.assertIn(lanekey[0]['id'],json.loads((root/'draft/notes/coordinator.json').read_text())['signal_assignments'],'its own judgment slot, not a restatement')

    def test_a_refused_quote_still_anchors_the_size_policy_time(self):
        from solana_broad_collect import capture,refresh
        from solana_quotes import quote_url
        root,target,opts=self.setup_run();opts={**opts,'deadline_at':time.time()+3000};original=Web.open
        def refusing(self_,request,timeout):
            if 'lite-api.jup.ag' in request.full_url:return Response(b'rate limited',429,{'Content-Type':'text/plain'})
            return original(self_,request,timeout)
        with unittest.mock.patch.object(Web,'open',refusing):start(root,target,**opts)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertFalse([f for f in facts if f['operation']=='quote_ladder'])
        self.assertEqual([x['input_atomic'] for x in next(f for f in facts if f['operation']=='quote_sizes')['data']['sizes']],['50000000','500000000','5000000000'])
        # The coordinator quotes the smallest policy size itself 330 s later: the refused captures at start still mark when the sizes were quoted.
        real=time.time
        with unittest.mock.patch.object(time,'time',lambda:real()+330):capture(root,[quote_url('jupiter_v1_lite',target,key(3),'50000000',slippage_bps=100)],'ordinary',opener_factory=Web);refresh(root)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];after=next(f for f in facts if f['operation']=='quote_sizes')['data']
        self.assertEqual((after['basis'],after['gaps']),('illustrative_USD_equivalents_floor_to_atomic_units',[]))
        ladder=next(f for f in facts if f['operation']=='quote_ladder');self.assertEqual((ladder['data']['sizes_quoted'],ladder['data']['sizes_requested']),(1,3))

    def test_the_policy_price_is_the_earliest_captured_not_the_first_by_hash(self):
        root,target,opts=self.setup_run();original=Web.open
        def priced_alternate(self_,request,timeout):  # the planned GeckoTerminal alternate also carries a price and completes after Dexscreener's capture
            url=request.full_url
            if 'geckoterminal' in url and url.endswith('/pools?page=1'):
                row={'id':'solana_'+RichRpc.pool['pool'],'type':'pool','attributes':{'address':RichRpc.pool['pool'],'reserve_in_usd':'1000','base_token_price_usd':'3','volume_usd':{'h24':'10'}},
                     'relationships':{'base_token':{'data':{'type':'token','id':'solana_'+target['mint']}},'quote_token':{'data':{'type':'token','id':'solana_'+key(3)}},'dex':{'data':{'id':'raydium'}}}}
                time.sleep(0.2);return Response(json.dumps({'data':[row]}).encode(),200,{'Content-Type':'application/json'})
            return original(self_,request,timeout)
        with unittest.mock.patch.object(Web,'open',priced_alternate):start(root,target,**opts)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];by_source={f['data'].get('source'):f for f in facts if f['operation']=='discovery_pools'}
        self.assertEqual([c['price_usd'] for c in by_source['geckoterminal']['data']['candidates'] if c.get('price_usd')],['3'])
        self.assertLess(by_source['dexscreener']['data']['candidates'][0]['captured_at'],by_source['geckoterminal']['data']['candidates'][0]['captured_at'])
        m=json.loads((root/'draft/manifest.json').read_text());d=next(x for x in m['derivations'] if x['id']=='auto-sizes')
        self.assertEqual(d['parameters']['price_discovery'],by_source['dexscreener']['evidence_id'],'Dexscreener was captured first; its $2 price sizes the policy whatever the capture ids hash to')
        self.assertEqual([x['input_atomic'] for x in next(f for f in facts if f['operation']=='quote_sizes')['data']['sizes']],['50000000','500000000','5000000000'])
        self.assertEqual(next(f for f in facts if f['operation']=='quote_ladder')['data']['sizes_quoted'],3)

    def test_start_captures_a_three_size_jupiter_quote_ladder_under_sellability(self):
        root,target,opts=self.setup_run();result=start(root,target,**opts);self.assertFalse(result['diagnostics'],result['diagnostics'])
        quotes=[u for u in Web.calls if 'lite-api.jup.ag' in u];self.assertEqual(len(quotes),3)
        facts=json.loads((root/'draft/facts.json').read_text())['facts']
        public=sorted((f for f in facts if f['operation']=='public_quote'),key=lambda f:int(f['data']['input_atomic']))
        # The quote_sizes derivation fixed $100/$1,000/$10,000 equivalents at the captured $2 price; each was quoted read-only into the lead pool's counter asset.
        self.assertEqual([(f['usable'],f['data']['input_atomic'],f['data']['output_mint']) for f in public],[(True,'50000000',key(3)),(True,'500000000',key(3)),(True,'5000000000',key(3))])
        ladder=next(f for f in facts if f['operation']=='quote_ladder');d=ladder['data']
        self.assertTrue(ladder['usable']);self.assertEqual((ladder['category'],d['sizes_quoted'],d['sizes_requested'],d['largest_size_quoted'],d['source']),('quotes',3,3,True,'jupiter_v1_lite'))
        self.assertEqual([r['impact_vs_smallest_percent'] for r in d['rows']],['0.0000','0.9009','9.9099']);self.assertEqual(d['largest_impact_vs_smallest_percent'],'9.9099')
        self.assertEqual(d['rows'][2]['impact_vs_smallest'],{'numerator':'11','denominator':'111'});self.assertFalse(d['execution_observed']);self.assertEqual(d['gaps'],[])
        self.assertIn('Read-only jupiter_v1_lite quotes at 3 of 3 illustrative sizes',ladder['summary']);self.assertIn('(baseline); 500000000 -> 247500000 (0.9009% vs smallest)',ladder['summary'])
        m=json.loads((root/'draft/manifest.json').read_text());attempts=[a for a in m['attempts'] if a.get('source')=='lite-api.jup.ag']
        self.assertEqual({(a['dimension'],a['owner']) for a in attempts},{('sellability_exit_depth','pipeline')});self.assertEqual(len(attempts),3)
        note=json.loads((root/'draft/notes/pipeline.json').read_text());row=next(f for f in note['findings'] if f['id']=='pipeline-'+ladder['evidence_id'])
        self.assertEqual((row['dimension'],row['claim']),('sellability_exit_depth','inference'))
        # A lane quote at another size stays its own fact and never displaces a policy size: the ladder is bound to the quote_sizes policy.
        from solana_broad_collect import capture
        from solana_quotes import quote_url
        from solana_import import refresh
        capture(root,[quote_url('jupiter_v1_lite',target,key(3),'1000')],'liquidity',opener_factory=Web);refresh(root)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];after=next(f for f in facts if f['operation']=='quote_ladder')['data']
        self.assertEqual(([r['input_atomic'] for r in after['rows']],after['largest_impact_vs_smallest_percent']),(['50000000','500000000','5000000000'],'9.9099'))
        self.assertEqual(sum(1 for f in facts if f['operation']=='public_quote'),4)
        # A refused quote route is a stated capture limit: the other sizes still form the ladder and the missing size is a named row.
        root,target,opts=self.setup_run();original=Web.open
        def refusing(self_,request,timeout):
            if 'lite-api.jup.ag' in request.full_url and 'amount=500000000&' in request.full_url:return Response(b'rate limited',429,{'Content-Type':'text/plain'})
            return original(self_,request,timeout)
        with unittest.mock.patch.object(Web,'open',refusing):result=start(root,target,**opts)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];ladder=next(f for f in facts if f['operation']=='quote_ladder')
        self.assertTrue(ladder['usable']);d=ladder['data'];self.assertEqual((d['sizes_quoted'],d['sizes_requested'],d['largest_size_quoted'],d['largest_impact_vs_smallest_percent']),(2,3,True,'9.9099'))
        self.assertEqual([(r['input_atomic'],r['status']) for r in d['rows']],[('50000000','quoted'),('500000000','not_captured'),('5000000000','quoted')])
        self.assertIn('429',d['rows'][1]['reason']);self.assertEqual(len(d['gaps']),1);self.assertIn('size 500000000 not captured',d['gaps'][0]);self.assertIn('2 of 3 illustrative sizes',ladder['summary']);self.assertIn('not captured (',ladder['summary'])
        self.assertFalse(any(x.get('category')=='quote_capture_skipped' for x in result['diagnostics']));self.assertEqual(json.loads((root/'quote-ladder.json').read_text())['status'],'captured')
        # A ladder start could not capture is a named diagnostic, not a silent absence.
        import solana_quotes
        root,target,opts=self.setup_run()
        with unittest.mock.patch.object(solana_quotes,'quote_url',side_effect=ValueError('invalid quote inputs')):result=start(root,target,**opts)
        skipped=[x for x in result['diagnostics'] if x.get('category')=='quote_capture_skipped'];self.assertEqual(len(skipped),1);self.assertIn('invalid quote inputs',skipped[0]['reason'])
        self.assertFalse(any(f['operation']=='quote_ladder' for f in json.loads((root/'draft/facts.json').read_text())['facts']))
        # Without a decodable pool lead there is nothing to sell into: the skip is recorded, and the missing pool facts already say why.
        root,target,opts=self.setup_run();Web.pairs=[];result=start(root,target,**opts)
        self.assertEqual(json.loads((root/'quote-ladder.json').read_text())['reason'],'no decodable pool lead; nothing to sell into');self.assertFalse([x for x in result['diagnostics'] if x.get('category')=='quote_capture_skipped'])

    def test_rugcheck_report_becomes_a_corroboration_fact_cross_checked_against_the_sample(self):
        from pool_fixture import key
        root,target,opts=self.setup_run();result=start(root,target,**opts);self.assertFalse(result['diagnostics'],result['diagnostics'])
        self.assertTrue(any('api.rugcheck.xyz' in u for u in Web.calls))
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];row=next(f for f in facts if f['operation']=='rugcheck')
        self.assertEqual((row['category'],row['usable']),('corroboration',True));d=row['data']
        self.assertEqual((d['insider_networks'][0]['size'],d['insider_networks'][0]['supply_share']['percent_display']),(5,'20.0000'))
        verified=[t for t in d['top_holders'] if t['verified_in_sample']];self.assertEqual([(t['address'],t['sample_amount_atomic']) for t in verified],[(key(7),'10000')])
        self.assertEqual((d['top_holders_verified_in_sample'],d['lockers'][0]['type'],d['creator']),(1,'streamflow',key(90)))
        self.assertIn('RugCheck report',row['summary']);self.assertIn('20.0000% of supply',row['summary'])
        validate(root/'draft',True)
        m=json.loads((root/'draft/manifest.json').read_text());att=next(a for a in m['attempts'] if a.get('source')=='api.rugcheck.xyz')
        self.assertEqual((att['dimension'],att['route']),('current_concentration','follow_up'))
        self.assertIn('corroboration',result['facts_summary'])
        # A refused report is a stated capture limit, never a fact or an error.
        root,target,opts=self.setup_run();Web.rugcheck=False;result=start(root,target,**opts)  # reset() restores the default report, so refuse after setup
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertFalse([f for f in facts if f['operation']=='rugcheck'])
        self.assertFalse([d for d in result['diagnostics'] if d.get('category')=='derivation_errors'],result['diagnostics'])
        # A report about another mint is a derivation error diagnostic, never a fact about this one.
        root,target,opts=self.setup_run();Web.rugcheck={'mint':key(40),'token':{'supply':5},'insiderNetworks':[],'topHolders':[]};result=start(root,target,**opts)
        self.assertTrue(any(d.get('category')=='derivation_errors' and any(e['operation']=='rugcheck' for e in d['errors']) for d in result['diagnostics']),result['diagnostics'])
        self.assertFalse([f for f in json.loads((root/'draft/facts.json').read_text())['facts'] if f['operation']=='rugcheck'])
        # A focused concentration run requests the report; a focused controls run does not.
        root,target,opts=self.setup_run();start(root,target,**{**opts,'scope':'focused','surfaces':['current_concentration']})
        self.assertTrue(any('api.rugcheck.xyz' in u for u in Web.calls))
        root,target,opts=self.setup_run();start(root,target,**{**opts,'scope':'focused','surfaces':['token_controls']})
        self.assertFalse(any('api.rugcheck.xyz' in u for u in Web.calls))

    def test_creator_history_for_an_attributed_wallet_is_bound_to_the_wallet_subject(self):
        from solana_broad_collect import collect
        root,target,opts=self.setup_run();start(root,target,**opts)
        from pool_fixture import key
        wallet=key(90)  # the fixture metadata update authority: an attributed key that is not the mint
        result=collect(root,{'id':'history','kind':'creator_history','parameters':{'keys':[wallet]}},opts['config'],factory=RichRpc)
        self.assertIsNone(result.get('preset_error'),result.get('preset_error'))
        manifest=json.loads((root/'draft/manifest.json').read_text())
        rows=[d for d in manifest['derivations'] if d['operation']=='history']
        # start's own history preset covered both attributed keys; the coordinator's named preset repeats the wallet, one row per address.
        self.assertEqual({d['parameters']['address'] for d in rows},{key(90),key(91)})
        self.assertTrue(all((d['subject']['kind'],d['subject']['address'])==('wallet',d['parameters']['address']) for d in rows),rows)

    def test_run_keeps_its_provider_and_degraded_reads_are_diagnosed(self):
        from solana_broad_collect import run_provider,check_config,provider_diagnostics,collect
        root,target,opts=self.setup_run();start(root,target,**opts)
        recorded=json.loads((root/'provider.json').read_text());self.assertEqual((recorded['provider'],bool(recorded['namespace'])),('public',True));self.assertNotIn('synthetic.invalid',json.dumps(recorded))
        with self.assertRaisesRegex(ValueError,'started on the public provider'):
            collect(root,{'id':'followup','kind':'creator_history','parameters':{'keys':[target['mint']]}},{'url':'https://synthetic.invalid','headers':{'Drpc-Key':'x'},'provider':'drpc'},factory=RichRpc)
        with self.assertRaisesRegex(ValueError,'started on the public provider'):run_provider(root,{'url':'https://synthetic.invalid','headers':{},'provider':'drpc'},RichRpc)
        from solana_transport import HttpTransport
        with self.assertRaisesRegex(ValueError,'started on the public provider'):run_provider(root,{'url':'https://api.mainnet-beta.solana.com','headers':{}},HttpTransport)  # same provider, a real endpoint namespace != the recorded one
        self.assertEqual(run_provider(root,opts['config'],RichRpc),'public')
        # A live start accepts only the preflighted shapes: the bare public root, or a dRPC network URL with its key header.
        ready={'status':'ready'}
        self.assertEqual(check_config({'url':'https://api.mainnet-beta.solana.com','headers':{},'preflight':ready,'provider':'public'}),'public')
        self.assertEqual(check_config({'url':'https://lb.drpc.org/solana','headers':{'Drpc-Key':'k'},'preflight':ready,'provider':'drpc'}),'drpc')
        for bad in ({'url':'https://api.mainnet-beta.solana.com','headers':{},'provider':'public'},{'url':'https://lb.drpc.org/solana','headers':{},'preflight':ready,'provider':'drpc'},
                    {'url':'https://api.mainnet-beta.solana.com/?x=1','headers':{},'preflight':ready,'provider':'public'},{'url':'https://lb.drpc.org/solana','headers':{'Drpc-Key':'k'},'preflight':ready,'provider':'public'}):
            with self.assertRaises(ValueError):check_config(bad)
        self.assertEqual(check_config({'url':'https://synthetic.invalid','headers':{}},True),'public')
        facts_path=root/'draft/facts.json';f=json.loads(facts_path.read_text());f['missing_reads']=[{'id':'baseline_mint_0','reason':'context below requested floor'},{'id':'other_read'}]
        facts_path.write_text(json.dumps(f));rows=[r for r in provider_diagnostics(root) if r['category']=='degraded_reads']
        self.assertEqual((len(rows),rows[0]['count'],rows[0]['reads']),(1,1,[{'read':'baseline_mint_0','reason':'context below requested floor'}]))

    def test_release_lane_seconds_match_the_session_constant(self):
        release=json.loads((Path(__file__).resolve().parents[1]/'assets/release.json').read_text())
        budget=next(v for v in release.values() if isinstance(v,dict) and 'lane_seconds' in v)
        self.assertEqual((budget['lane_seconds'],budget['collection_seconds']),(solana_session.LANE_SECONDS,solana_session.COLLECTION_SECONDS))

    def test_capture_accepts_the_runs_paid_flags(self):
        import subprocess,sys
        script=Path(__file__).resolve().parents[1]/'scripts/solana_broad_collect.py'
        with tempfile.TemporaryDirectory() as d:
            for policy in ('free','paid'):
                out=subprocess.run([sys.executable,str(script),'capture',d+'/missing','--owner','liquidity','--allow-network','--cost-policy',policy,'--url','https://example.invalid/x'],capture_output=True,text=True,env={'PYTHONDONTWRITEBYTECODE':'1','PATH':os.environ.get('PATH','')})
                message=json.loads(out.stdout)['errors'][0]['message'];self.assertNotIn('cost-policy',message,policy)  # refused for the missing run, never for the flag
            out=subprocess.run([sys.executable,str(script),'capture',d+'/missing','--owner','liquidity','--allow-network','--url','https://example.invalid/x'],capture_output=True,text=True,env={'PYTHONDONTWRITEBYTECODE':'1','PATH':os.environ.get('PATH','')})
            self.assertNotIn('cost-policy',json.loads(out.stdout)['errors'][0]['message'])  # the cost policy is optional for a web capture
            out=subprocess.run([sys.executable,str(script),'capture',d+'/missing','--owner','liquidity','--url','https://example.invalid/x'],capture_output=True,text=True,env={'PYTHONDONTWRITEBYTECODE':'1','PATH':os.environ.get('PATH','')})
            self.assertIn('allow-network',json.loads(out.stdout)['errors'][0]['message'])

    def test_unusable_fact_finding_names_the_degraded_reads(self):
        from solana_pipeline_note import findings
        fact={'id':'fact-auto-controls','evidence_id':'auto-controls','operation':'controls','category':'controls','subject':{'genesis_hash':'g','kind':'mint','address':'m'},
              'usable':False,'status':'observed','captured_at':'2026-09-12T00:00:00+00:00','sample_ids':['s'],'dependencies':['auto-controls','baseline_mint_0','baseline_header_1_0'],
              'input_digests':{},'data':{},'summary':'x','limits':[],'attention':[]}
        rows=findings({'facts':[fact],'missing_reads':[{'id':'baseline_header_1_0','status':'ok','reason':'critical recheck unavailable'},{'id':'other_0','status':'timeout','reason':None}]})
        gap=next(r for r in rows if r['id']=='pipeline-auto-controls');self.assertEqual(gap['claim'],'coverage_gap');self.assertIn('baseline_header_1_0: critical recheck unavailable',gap['limitations'])
        self.assertFalse(any('other_0' in l for l in gap['limitations']))

    def test_leads_follow_discovery_liquidity_order(self):
        from solana_broad_collect import ordered_leads
        self.assertEqual(ordered_leads([('B','pumpswap'),('A','meteora_damm_v2'),('C','raydium_cpmm')],['A','B']),[('A','meteora_damm_v2'),('B','pumpswap'),('C','raydium_cpmm')])
        root,target,opts=self.setup_run();start(root,target,**opts);leads=json.loads((root/'automatic-leads.json').read_text())
        self.assertEqual([l['pool'] for l in leads],[RichRpc.pool['pool']])

    def second_pool(self,target,a,n=45):
        """Another decodable CPMM pool for the same mints at key(n), with its own PDA vaults and LP mint."""
        import struct
        from pool_fixture import key,mint,holding
        from solana_fixture import account
        from solana_addresses import find_program_address
        from adapters import raydium_cpmm as cp
        from adapters.binary import discriminator
        from solana_common import base58_bytes,TOKEN_PROGRAM
        pool=key(n);program=cp.PROGRAM;mints=a['mints'];authority,bump=find_program_address([b'vault_and_lp_mint_auth_seed'],program)
        vaults=[find_program_address([b'pool_vault',base58_bytes(pool,32),base58_bytes(m,32)],program)[0] for m in mints];lp=find_program_address([b'pool_lp_mint',base58_bytes(pool,32)],program)[0]
        keys=[a['config'],key(31),*vaults,lp,*mints,TOKEN_PROGRAM,TOKEN_PROGRAM,key(37)]
        raw=discriminator('PoolState')+b''.join(base58_bytes(k,32) for k in keys)+bytes([bump,0,9,6,6])+struct.pack('<7Q',1000,100,200,30,40,1,5)+bytes([0,1])+bytes(6)+struct.pack('<2Q',10,20)+bytes(224)
        RichRpc.values.update({pool:{**account(raw),'owner':program},vaults[0]:holding(mints[0],authority,40000),vaults[1]:holding(mints[1],authority,80000),lp:mint(900,authority,9)})
        return pool

    def test_two_pools_are_sampled_in_discovery_liquidity_order_not_observation_order(self):
        import solana_broad_collect as module
        root,target,opts=self.setup_run();a=RichRpc.pool;pool2=self.second_pool(target,a,45);pool3=self.second_pool(target,a,46)
        pair=lambda pool,liq:{'chainId':'solana','pairAddress':pool,'baseToken':{'address':target['mint']},'quoteToken':{'address':a['mints'][1]},'dexId':'raydium','liquidity':{'usd':liq},'priceUsd':'2','volume':{'h24':'500000'},'info':{'websites':[{'url':'https://project.example/token'}]}}
        Web.pairs=[pair(a['pool'],'1000000'),pair(pool2,'5000000'),pair(pool3,'3000000')]  # liquidity order: pool2, pool3, pool1
        real=module.candidates;calls=[]
        def skewed(root_,target_):
            rows=real(root_,target_);calls.append(len(rows))  # discovery keeps the top two by liquidity: pool2, pool3
            # The related stage reads all three pools in an order that is neither the liquidity order nor its reverse.
            return [{**rows[0],'pool':pool3},{**rows[0],'pool':a['pool']},{**rows[0],'pool':pool2}] if len(calls)==1 else rows
        with unittest.mock.patch.object(module,'candidates',skewed):result=start(root,target,**opts)
        self.assertGreaterEqual(len(calls),2);self.assertEqual([r['pool'] for r in real(root,target)],[pool2,pool3])
        leads=json.loads((root/'automatic-leads.json').read_text())
        self.assertEqual([l['pool'] for l in leads],[pool2,pool3])  # liquidity order, whatever the observation order (pool3, pool1, pool2)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];self.assertTrue({pool2,pool3}<={f['subject']['address'] for f in facts if f['operation']=='pool'})
        rows=json.loads((root/'receipt-classification.json').read_text());self.assertEqual(rows['listings'][0]['pool'],pool2)

    def test_pool_whose_listed_signatures_all_failed_is_a_stated_diagnostic(self):
        from transaction_fixture import fixture
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx;original=RichRpc.__call__
        def failing(rpc,request):
            res=original(rpc,request)
            if request['method']=='getSignaturesForAddress':
                for row in res['result']:row['err']={'InstructionError':[0,'Custom']}
            return res
        with unittest.mock.patch.object(RichRpc,'__call__',failing):result=start(root,target,**opts)
        rows=[r for r in result['diagnostics'] if r.get('category')=='activity_signatures_all_failed'];self.assertEqual(rows and rows[0]['pools'],[RichRpc.pool['pool']])
        record=json.loads((root/'receipt-classification.json').read_text());self.assertEqual((record['probed'],record['listings'][0]['failed'],record['listings'][0]['listed']),(0,1,1))
        self.assertFalse(any(f['operation'] in ('sales','rebuys') for f in json.loads((root/'draft/facts.json').read_text())['facts']))

    def test_unresolved_reads_reach_the_coordinator_diagnostics(self):
        root,target,opts=self.setup_run();RichRpc.mode='largest_refused';original=RichRpc.__call__
        def broken(rpc,request):
            if request['method']=='getProgramAccounts':raise ValueError('fixture: provider answered with an unusable body')
            return original(rpc,request)
        with unittest.mock.patch.object(RichRpc,'__call__',broken):result=start(root,target,**opts)
        rows=[r for r in result['diagnostics'] if r.get('category')=='unresolved_reads'];self.assertEqual(len(rows),1)
        self.assertEqual([(r['read'],r['status']) for r in rows[0]['reads']],[('baseline_holderscan','invalid'),('lpleads0_scan','invalid')])  # the holder census and the LP-holder scan
        self.assertFalse(any(f['operation']=='holders' for f in json.loads((root/'draft/facts.json').read_text())['facts']))

    def test_derivation_errors_reach_the_coordinator_diagnostics(self):
        from solana_broad_collect import provider_diagnostics
        root,target,opts=self.setup_run();start(root,target,**opts);path=root/'import-diagnostics.json';d=json.loads(path.read_text());self.assertEqual(d['errors'],[])
        d['errors']=[{'operation':'controls','id':'auto-controls','reason':'fixture: derivation failed'}];path.write_text(json.dumps(d))
        rows=[r for r in provider_diagnostics(root) if r.get('category')=='derivation_errors'];self.assertEqual((rows[0]['count'],rows[0]['errors'][0]['id']),(1,'auto-controls'))

    def test_sales_and_rebuys_include_preset_receipts_beyond_the_start_sample(self):
        from transaction_fixture import fixture
        from solana_common import b58encode
        root,target,opts=self.setup_run();_,a,packet,_=fixture();tx=packet['response']['result']
        tx['transaction']['message']['accountKeys']=[RichRpc.pool['pool'] if k==a['pool'] else k for k in tx['transaction']['message']['accountKeys']]
        tx['blockTime']=RichRpc.stamp;RichRpc.receipt=tx
        # Start samples two swap receipts; a pool_activity preset adds a third, which the sale and rebuy facts must include.
        second=copy.deepcopy(tx);two=b58encode(bytes([81])*64);second['transaction']['signatures'][0]=two;RichRpc.receipts={two:second}
        start(root,target,**opts);facts=json.loads((root/'draft/facts.json').read_text())
        sales=next(f['data'] for f in facts['facts'] if f['operation']=='sales');self.assertEqual((sales['requested_receipts'],sales['verified_receipts'],sales['maximum_receipts']),(2,2,10))
        third=copy.deepcopy(tx);three=b58encode(bytes([82])*64);third['transaction']['signatures'][0]=three;RichRpc.receipts={three:third,two:second}
        result=collect(root,{'id':'act','kind':'pool_activity','parameters':{'pool':RichRpc.pool['pool'],'receipts':1}},opts['config'],factory=RichRpc)
        self.assertIsNone(result['preset_error']);facts=json.loads((root/'draft/facts.json').read_text())
        sales=next(f['data'] for f in facts['facts'] if f['operation']=='sales');rebuys=next(f['data'] for f in facts['facts'] if f['operation']=='rebuys')
        self.assertEqual((sales['requested_receipts'],sales['verified_receipts']),(3,3));self.assertEqual((rebuys['requested_receipts'],rebuys['verified_receipts']),(3,0))
        self.assertEqual([r['signature'] for r in sales['receipts']][-1],three);self.assertEqual(json.loads((root/'import-diagnostics.json').read_text())['errors'],[])

    def test_capture_routes_mark_the_first_host_per_dimension_primary_and_later_hosts_alternate(self):
        from solana_broad_collect import capture
        from solana_import import refresh
        root,target,opts=self.setup_run();start(root,target,**opts);Web.blocked=True
        # The lane registers a docs host first, then the project host twice: per surface and owner, its first host is primary and
        # the later, different host alternate, whatever the pipeline registered. Both hosts fail, so the surface can close as an external limit.
        capture(root,['https://docs.project.example/terms'],'project',dimension='development_disclosure',opener_factory=Web)
        capture(root,['https://project.example/docs','https://project.example/team'],'project',dimension='development_disclosure',opener_factory=Web)
        refresh(root);m=json.loads((root/'draft/manifest.json').read_text());url={o['id']:o['source']['capture']['url'] for o in m['observations'] if o['kind']=='document'}
        rows={url[a['evidence_id']]:(a['route'],a['source'],a['status']) for a in m['attempts'] if a['dimension']=='development_disclosure' and a['owner']=='project'}
        self.assertEqual(rows,{'https://docs.project.example/terms':('primary','docs.project.example','permission_denied'),'https://project.example/docs':('alternate','project.example','permission_denied'),
            'https://project.example/team':('alternate','project.example','permission_denied')})
        pipeline={url[a['evidence_id']].split('/')[2]+('/info' if url[a['evidence_id']].endswith('/info') else ''):(a['dimension'],a['route']) for a in m['attempts'] if a['owner']=='pipeline' and a['evidence_id'] in url}
        self.assertEqual(pipeline.get('project.example'),('development_disclosure','primary'))  # the pipeline's own project link keeps its primary
        self.assertEqual(pipeline.get('api.geckoterminal.com/info'),('development_disclosure','primary'))  # the token-info plan primary, filed with project disclosure
        market={a['source']:a['route'] for a in m['attempts'] if a['dimension']=='canonical_lp_principal_custody' and a['evidence_id'] in url}
        self.assertEqual(market,{'api.dexscreener.com':'primary','api.geckoterminal.com':'alternate'})  # the discovery plan's routes stay fixed

    def test_capture_dimension_and_sample_dimensions_reach_the_attempt_ledger(self):
        from solana_broad_collect import capture
        root,target,opts=self.setup_run();start(root,target,**opts)
        capture(root,['https://project.example/terms'],'project',dimension='utility_redemption_rights',opener_factory=Web)
        from solana_import import refresh
        refresh(root);m=json.loads((root/'draft/manifest.json').read_text())
        dims={a['dimension'] for a in m['attempts']}
        self.assertIn('utility_redemption_rights',dims);self.assertIn('canonical_lp_principal_custody',dims);self.assertIn('sellability_exit_depth',dims)
        terms=[a for a in m['attempts'] if a['dimension']=='utility_redemption_rights'];self.assertEqual(terms[0]['owner'],'project')
        with self.assertRaisesRegex(ValueError,'unknown capture dimension'):capture(root,['https://project.example/x'],'project',dimension='adoption',opener_factory=Web)
