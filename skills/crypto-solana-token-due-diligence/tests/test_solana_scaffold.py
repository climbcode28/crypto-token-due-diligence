from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from solana_scaffold import scaffold,write
from solana_compose import compose,ComposeError
from compose_fixture import save


class ScaffoldTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return Bundle(t.name)

    def test_scope_aliases_focus_and_todo_without_optimistic_judgment(self):
        b=self.fixture();n=write(b.root,allow_synthetic=True);self.assertEqual(n['question'],b.r['question']);self.assertEqual(n['urls'],b.m['intake']['urls']);self.assertIn('controls',n['alias_hints']);self.assertIsNone(n['decision'])
        self.assertTrue(all(v['signal'] is None for v in n['signal_assignments'].values()))
        # The mint controls fact is usable, so its surface closes itself; every other surface has no route answered yet and stays pending with its route named.
        rows={r['dimension']:r for r in n['coverage']};tc=rows['token_controls']
        self.assertEqual((tc['status'],tc['closure']['boundary'],tc['closure']['standard_scope_complete'],tc['closure']['next_route'],tc['pending_work']),('checked','resolved',True,None,[]))
        self.assertTrue(all(not r['closure']['standard_scope_complete'] and r['closure']['boundary']=='pending' for d,r in rows.items() if d!='token_controls'))
        self.assertEqual({rows[d]['closure']['next_route'] for d in ('current_concentration','sellability_exit_depth','external_dependencies')},{'holders','pool_activity','programs'})
        from solana_coverage import untouched
        self.assertTrue(all(untouched(r) for r in n['coverage']));tc['status']='partial';self.assertFalse(untouched(tc),'an edited row is the coordinator\'s')
        self.assertTrue(all(v['input_digests']=={'controls':b.obs('controls')['sha256']} for v in n['signal_assignments'].values()))
        compose(b.root,allow_synthetic=True)
        with self.assertRaisesRegex(ValueError,'Existing analyst'):write(b.root,allow_synthetic=True)

    def test_mechanical_closure_never_closes_a_surface_the_evidence_does_not_support(self):
        from solana_coverage import mechanical
        lane=[{'id':'liquidity-side','claim':'inference','strength':'bounded','dimension':'side_pool_removal_risk'}]
        def fact(op,data,usable=True):return {'operation':op,'usable':usable,'data':data}
        # No usable discovery fact: a lane's affirmative finding alone cannot close the side-pool surface.
        row=mechanical('side_pool_removal_risk',lane,[fact('pool',{'pool':'P1','status':'observed','adapter':{'id':'raydium_cpmm'}})],[])
        self.assertEqual((row['status'],row['closure']['boundary'],row['closure']['next_route']),('partial','pending','pool'));self.assertIn('No usable exact-mint discovery fact',row['closure']['reason'])
        # A partial leading pool whose only listed gap is program control still answered custody; one with unresolved position coverage did not.
        pipeline=[{'id':'pipeline-pool-x','claim':'state_observation','strength':'bounded','dimension':'canonical_lp_principal_custody'}]
        ok=mechanical('canonical_lp_principal_custody',pipeline,[fact('pool',{'pool':'P1','status':'partial','gaps':['program_control_not_observed'],'adapter':{'id':'raydium_clmm'},'positions':[{}]})],[])
        self.assertEqual((ok['status'],ok['closure']['boundary']),('checked','resolved'));self.assertIn('program control is rated under external dependencies',ok['closure']['reason'])
        bad=mechanical('canonical_lp_principal_custody',pipeline,[fact('pool',{'pool':'P1','status':'partial','gaps':[],'position_coverage':'partial','adapter':{'id':'raydium_clmm'},'positions':[{}]})],[])
        self.assertEqual((bad['status'],bad['closure']['boundary']),('partial','pending'));self.assertIn('position coverage partial',bad['closure']['reason'])
        amm=mechanical('canonical_lp_principal_custody',pipeline,[fact('pool',{'pool':'P1','status':'partial','gaps':[],'adapter':{'id':'raydium_amm_v4'},'reserves_atomic':None})],[])
        self.assertIn('reserves not inferred',amm['closure']['reason'])
        # Custody judges the pipeline note's leading pool (discovery order when no automatic lead exists), never a better-looking side pool.
        discovery=fact('discovery_pools',{'candidates':[{'pool':'P1'},{'pool':'P2'}]});good=fact('pool',{'pool':'P2','status':'observed','adapter':{'id':'raydium_cpmm'}})
        weak=fact('pool',{'pool':'P1','status':'partial','gaps':['some_requested_lp_holdings_unresolved'],'adapter':{'id':'raydium_cpmm'},'reserves_atomic':{}})
        row=mechanical('canonical_lp_principal_custody',pipeline,[discovery,good,weak],[])
        self.assertEqual((row['closure']['boundary'],row['closure']['next_route']),('pending','positions'));self.assertIn('some_requested_lp_holdings_unresolved',row['closure']['reason'])
        self.assertEqual(mechanical('canonical_lp_principal_custody',pipeline,[discovery,good,weak],[],leads=[{'pool':'P2'}])['closure']['boundary'],'resolved','the automatic lead names the leading pool')
        unusable_lead=mechanical('canonical_lp_principal_custody',pipeline,[discovery,fact('pool',{'pool':'P1'},usable=False),good],[])
        self.assertEqual((unusable_lead['closure']['boundary'],unusable_lead['closure']['next_route']),('pending','pool'));self.assertIn('unusable',unusable_lead['closure']['reason'])
        side=mechanical('side_pool_removal_risk',lane,[discovery,good,weak],[])
        self.assertEqual(side['closure']['boundary'],'resolved');self.assertIn('Second pool raydium_cpmm sampled',side['closure']['reason'])
        # Launch integrity needs a sampled receipt and a history for every attributed key; with no key at all the coordinator closes it by judgment.
        launch=[{'id':'pipeline-launch-x','claim':'inference','strength':'bounded','dimension':'historical_launch_integrity'}]
        none=mechanical('historical_launch_integrity',launch,[fact('launch',{'stage':'launch_unverified','initializations':[]})],[])
        self.assertEqual((none['closure']['boundary'],none['closure']['next_route']),('pending','standard'));self.assertIn('by judgment',none['closure']['reason'])
        keyed=mechanical('historical_launch_integrity',launch,[fact('launch',{'stage':'launch_unverified','initializations':[]}),fact('creator_activity',{'keys':[{'address':'K1'}]}),fact('history',{'address':'K1'})],[])
        self.assertEqual(keyed['closure']['boundary'],'resolved');self.assertIn('Launch stage launch_unverified with 0 verified initialization(s)',keyed['closure']['reason'])
        no_receipt=mechanical('historical_launch_integrity',launch,[fact('creator_activity',{'keys':[{'address':'K1'}]}),fact('history',{'address':'K1'})],[])
        self.assertEqual((no_receipt['closure']['boundary'],no_receipt['closure']['next_route']),('pending','transactions'));self.assertIn('No receipt was sampled',no_receipt['closure']['reason'])
        unusable=mechanical('historical_launch_integrity',launch,[fact('creator_activity',{'keys':[{'address':'K1'}]},usable=False),fact('history',{'address':'K1'})],[])
        self.assertEqual(unusable['closure']['boundary'],'pending');self.assertIn('unusable',unusable['closure']['reason'])
        # A partial holders fact does not close concentration.
        holders=[{'id':'pipeline-holders-x','claim':'state_observation','strength':'bounded','dimension':'current_concentration'}]
        self.assertEqual(mechanical('current_concentration',holders,[fact('holders',{'status':'partial','gaps':['missing balances']})],[])['closure']['boundary'],'pending')
        self.assertEqual(mechanical('current_concentration',holders,[fact('holders',{'status':'sampled'})],[])['closure']['boundary'],'resolved')

    def test_placeholders_cannot_complete(self):
        b=self.fixture();n=scaffold(b.root,allow_synthetic=True);n['research_status']='completed';save(b,n)
        with self.assertRaisesRegex(ComposeError,'TODO'):compose(b.root,allow_synthetic=True)

    def test_lane_scaffold_has_all_pending_checks_and_no_judgment(self):
        b=self.fixture()
        for owner in ('liquidity','project'):
            n=scaffold(b.root,owner,True);self.assertTrue(all(v['status']=='pending' for v in n['checklist'].values()));self.assertFalse(n['findings']);self.assertFalse(n['evidence_ids'])

if __name__=='__main__':unittest.main()
