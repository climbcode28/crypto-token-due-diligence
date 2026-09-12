from pathlib import Path
import sys,tempfile,unittest,unittest.mock,time,json,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from broad_fixture import RichRpc,Web
from solana_broad_collect import start,collect,status,STAGES
from solana_profile import validate


class BroadTests(unittest.TestCase):
    def setup_run(self,scope='broad',urls=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)/'run';target=RichRpc.reset();Web.calls=[];Web.blocked=False
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
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];quote=next(f for f in facts if f['operation']=='public_quote')
        self.assertTrue(quote['usable']);self.assertEqual((quote['data']['source'],quote['data']['output_atomic'],quote['data']['provider_usd_value']),('jupiter_v1_lite','500','1.5'))
        self.assertFalse(quote['data']['execution_observed'])

    def test_focused_scope_omits_lanes_markets_and_broad_dependencies(self):
        root,target,opts=self.setup_run('focused');r=start(root,target,**opts);self.assertFalse(r['lane_pointers']);self.assertFalse(Web.calls);self.assertFalse((root/'lanes').exists())
        m,report=validate(root/'draft',True);self.assertEqual(report['scope'],'focused');self.assertTrue(all(q['method']!='getTokenLargestAccounts' for q in RichRpc.calls))

    def test_source_failure_keeps_control_facts_and_pending_work(self):
        root,target,opts=self.setup_run();Web.blocked=True;r=start(root,target,**opts);m,report=validate(root/'draft',True)
        self.assertTrue(any(f['id']=='pipeline-auto-controls' for f in report['findings']));self.assertEqual(report['research_status'],'partial');self.assertTrue(any(o['status']=='permission_denied' for o in m['observations']))
        self.assertTrue(all(not c['closure']['standard_scope_complete'] for c in report['coverage']))

    def test_two_followup_presets_share_grants_and_third_is_refused(self):
        root,target,opts=self.setup_run('focused');start(root,target,**opts);before=status(root)
        for ident in ('followup1','followup2'):
            spec={'id':ident,'kind':'programs','parameters':{'addresses':[target['mint']]}}
            result=collect(root,spec,opts['config'],factory=RichRpc);self.assertEqual(result['research_status'],'partial')
        after=status(root);self.assertEqual(before['deadline_at'],after['deadline_at']);self.assertGreater(after['started_attempts'],before['started_attempts'])
        with self.assertRaisesRegex(ValueError,'Two coordinator'):collect(root,{'id':'followup3','kind':'programs','parameters':{'addresses':[]}},opts['config'],factory=RichRpc)

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
        f=json.loads((root/'draft/facts.json').read_text())['facts'];latest=next(r for r in f if r['evidence_id']=='auto-controls');prior=next(r for r in f if r['evidence_id']=='prior-controls')
        self.assertFalse(latest['usable']);self.assertEqual(latest['data']['mint']['mint_authority'],key(90))
        self.assertTrue(prior['usable']);self.assertEqual(prior['data']['selection_scope'],'earlier_pinned_snapshot_newer_unpinned')
        self.assertNotEqual(prior['data']['mint']['supply_atomic'],latest['data']['mint']['supply_atomic'])
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
        # The newest snapshot sits outside the verified interval and stays unusable; the earlier usable one is retained.
        self.assertFalse(next(x for x in after['facts'] if x['evidence_id']=='auto-controls')['usable'])
        self.assertTrue(next(x for x in after['facts'] if x['evidence_id']=='prior-controls')['usable'])
        self.assertTrue(next(x for x in after['facts'] if x['evidence_id']=='auto-sizes')['usable'])
        again=refresh(root);self.assertEqual(again['research_status'],'partial')  # A second import never raises.
        validate(root/'draft',True)

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
