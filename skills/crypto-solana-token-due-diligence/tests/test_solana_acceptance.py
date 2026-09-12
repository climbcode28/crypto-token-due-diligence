"""Independent material outcomes through typed facts, notes and readable delivery."""
from pathlib import Path
import copy,json,sys,tempfile,time,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from facts_fixture import rich
from profile_fixture import Bundle,BASE,utc
from delivery_fixture import complete
from compose_fixture import save,assign
from solana_facts import build,encoded
from solana_pipeline_note import generate
from solana_profile import validate
from solana_render import render,reading
from solana_replay import finalize
from solana_common import base58_bytes,TOKEN_2022,b58encode
EXPECTED=json.loads((Path(__file__).parent/'fixtures/acceptance/expected-material-facts.json').read_text())


def lookup(value,path):
    for part in path.split('.'):value=value[int(part)] if isinstance(value,list) else value[part]
    return value


class AcceptanceTests(unittest.TestCase):
    def test_default_v2_cli_freezes_and_reads_while_legacy_remains_explicit(self):
        import subprocess
        import solana_bundle
        self.assertEqual(solana_bundle.DEFAULT_PROFILE,'solana-evidence-v2')
        root=self.directory();b,n=complete(root/'draft')
        cli=Path(__file__).resolve().parents[1]/'scripts/solana_bundle.py'
        result=subprocess.run([sys.executable,'-B',str(cli),'finalize',str(b.root),'--out',str(root/'final'),'--allow-synthetic'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['deliverable'])
        result=subprocess.run([sys.executable,'-B',str(cli),'read',str(root/'final'),'--allow-synthetic'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['network_requests'],0)
        old=Path(__file__).parent/'fixtures/legacy_v1/independent'
        with self.assertRaises(ValueError):solana_bundle.validate(old,True)
        self.assertEqual(solana_bundle.render(*solana_bundle.validate(old,True,profile='legacy-v1'),profile='legacy-v1').encode(),(old/'report.md').read_bytes())

    def directory(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return Path(t.name)

    def test_eight_products_match_independent_material_constants_in_facts_and_reading(self):
        for kind,expected in EXPECTED['products'].items():
            with self.subTest(product=kind):
                b=rich(self.directory(),kind);facts=build(b.root,True);fact=next(f for f in facts['facts'] if f['operation']=='pool')
                self.assertTrue(fact['usable']);m,r=validate(b.root,True);packet=reading(m,r)
                retained=next(f for f in packet['reading_checklist'] if f['kind']=='typed_fact' and f['operation']=='pool')
                for path,wanted in expected.items():self.assertEqual(lookup(fact['data'],path),wanted,path)
                from solana_render import facts_compact
                self.assertTrue(retained['limits']);self.assertNotIn('details',retained);self.assertEqual(retained['details_ref'],'facts-compact.json#'+retained['evidence_id'])
                self.assertTrue(facts_compact(m,r)['facts'][retained['evidence_id']]['details']);self.assertIn(kind,render(m,r))

    def test_revocation_does_not_hide_permanent_delegate_hook_and_pause(self):
        from test_solana_accounts import mint,tlv
        from solana_accounts import decode_mint
        from pool_fixture import key
        data=tlv(12,base58_bytes(key(8),32))+tlv(14,base58_bytes(key(9),32)+base58_bytes(key(10),32))+tlv(26,base58_bytes(key(11),32)+b'\1')
        result=decode_mint(mint(extensions=data,program=TOKEN_2022));self.assertIsNone(result['mint_authority']);self.assertIsNone(result['freeze_authority'])
        ext={r['type']:r for r in result['extensions']};self.assertEqual(ext[12]['authority'],key(8));self.assertEqual(ext[14]['program'],key(10));self.assertTrue(ext[26]['paused'])
        self.assertNotIn('safe',result)

    def test_exact_holder_aggregation_uses_sample_denominator_and_never_human_ownership(self):
        from test_solana_holders import HolderTests
        from solana_accounts import aggregate_holders
        from solana_fixture import TARGET
        d,s=HolderTests().packets();r=aggregate_holders(d,s,TARGET);expected=EXPECTED['holder_sample']
        self.assertEqual(r['owners'][0]['amount_atomic'],expected['owner_aggregate_atomic']);self.assertEqual(r['observed_base_amount_atomic'],expected['observed_atomic'])
        self.assertEqual(r['supply_atomic'],expected['supply_atomic']);self.assertEqual(r['coverage_share']['percent_display'],expected['percent_display']);self.assertIn('beneficial ownership',r['scope'])

    def test_two_sales_are_sample_counts_quote_failure_does_not_erase_selling(self):
        from transaction_fixture import fixture
        from solana_transactions import decode_transaction,verify_sales
        from solana_quotes import estimate
        from pool_fixture import fixture as pool_fixture,batch
        target,a,p,h=fixture(version=0,wsol=True,closed=True,created=True,tip=100)
        p2=copy.deepcopy(p);signature=b58encode(bytes([7])*64);p2['request']['id']='receipt2';p2['response']['id']='receipt2';p2['request']['params'][0]=signature;p2['response']['result']['transaction']['signatures'][0]=signature
        result=verify_sales(target,[{'pool':a['pool'],'execution':decode_transaction(target,x,h)} for x in (p,p2)])
        self.assertEqual(result['verified_receipts'],2);self.assertIsNone(result['indexed_activity_count'])
        for sale in result['receipts']:
            self.assertEqual(sale['input_atomic'],'1000');self.assertEqual(sale['output_atomic'],'500');self.assertEqual(sale['seller'],a['owner']);self.assertNotEqual(sale['seller'],a['payer'])
            self.assertEqual(sale['native_proceeds']['net_sale_after_seller_network_fee_lamports'],'500');self.assertIsNone(sale['profit'])
        target,a,v=pool_fixture();quote=estimate(target,'raydium_cpmm',a['pool'],batch(v),'1000')
        self.assertIsNone(quote['output_atomic']);self.assertTrue(quote['gaps']);self.assertEqual(result['verified_receipts'],2)

    def test_maturity_publication_survives_explorer_failure_and_does_not_prove_build(self):
        from solana_discovery import pools
        root=self.directory();b,n=complete(root/'draft')
        body=[{'chainId':'solana','pairAddress':b.target['mint'],'baseToken':{'address':b.target['mint']},'quoteToken':{'address':'So11111111111111111111111111111111111111112'},
              'dexId':'raydium','liquidity':{'usd':'1000000'},'volume':{'h24':'500000'},'priceUsd':'2'}]
        b.document('market',status='ok',body=encoded(body));capture=b.obs('market')['source']['capture'];capture['url']=capture['final_url']='https://api.dexscreener.com/token-pairs/v1/solana/'+b.target['mint']
        result=pools(capture,encoded(body),b.target);b.derived('market-facts','discovery_pools',{'capture':'market'},['market'],result);b.obs('market-facts')['captured_at']=utc(BASE+55)
        b.document('release',status='ok',body=b'Synthetic primary publication: v1.4 release dated 2026-08-01; delivered API endpoint and source tag are published. Audit covers v1.2 only; buybacks remain discretionary.')
        b.save();n['signal_assignments']=assign(b,'unverified')
        n['findings'].append({'id':'coordinator-delivery','dimension':'development_disclosure','claim':'source_analysis','strength':'direct','signal':'good',
            'text':'The primary source publishes a dated v1.4 release and API endpoint. Its audit names v1.2; this does not establish deployed byte correspondence.',
            'support':['release'],'limitations':['Publication is directly observed; operation, audit applicability and deployed build remain separate.']})
        n['findings'].append({'id':'coordinator-economics','dimension':'utility_redemption_rights','claim':'source_analysis','strength':'direct','signal':'unverified',
            'text':'The published buyback is discretionary; it is not an enforceable redemption entitlement or evidence of malicious intent.', 'support':['release']})
        n['decision']['axes']['credibility_maturity']['text']='A dated v1.4 release and API publication support public delivery context. The v1.2 audit does not establish current deployed correspondence.'
        n['decision']['axes']['token_economics']['text']='Discretionary buybacks do not create a holder redemption right; the user did not ask for equity-like rights.'
        n['decision']['finding_ids']+=['coordinator-delivery','coordinator-economics'];n['decision']['axes']['credibility_maturity']['finding_ids'].append('coordinator-delivery');n['decision']['axes']['token_economics']['finding_ids'].append('coordinator-economics');save(b,n)
        output=finalize(b.root,root/'final',allow_synthetic=True)
        markdown=Path(output['report_path']).read_text();self.assertNotIn('markdown',output)
        self.assertTrue(output['deliverable']);self.assertIn('dated v1',markdown);self.assertIn('500000',markdown);self.assertIn('1000000',markdown);self.assertIn('discretionary',markdown)
        self.assertEqual(output['research_status'],'completed');self.assertTrue(any(c['kind']=='source' for c in output['citations']))

    def test_adverse_control_remains_in_summary_relevant_axis_and_frozen_reading(self):
        root=self.directory();b,n=complete(root/'draft',adverse=True)
        n['decision']['axes']['technical_exposure']['text']='The retained mint authority can issue additional supply and dilute holders. Public activity does not remove this power.'
        n['decision']['axes']['research_confidence']['text']='The authority is directly sampled; externally unavailable paths retain explicit unknowns.';save(b,n)
        output=finalize(b.root,root/'final',allow_synthetic=True);_,r=validate(root/'final',True)
        self.assertIn('coordinator-controls-finding',r['summary_ids']);self.assertIn('coordinator-controls-finding',r['decision']['axes']['technical_exposure']['finding_ids'])
        markdown=Path(output['report_path']).read_text();self.assertIn('dilute holders',markdown);self.assertTrue(any(x.get('impact')=='high' for x in output['reading_checklist']))
        self.assertIn('| token\\_controls | 🟡 **Potential Risk** |',markdown);self.assertIn('**Conclusions**',markdown);self.assertEqual(markdown.count('- **Technical exposure:**'),1)

    def test_out_of_range_missing_bins_and_multisig_bypass_are_not_blanket_safety(self):
        from concentrated_fixture import fixture,batch
        from adapters import raydium_clmm,meteora_dlmm,squads_v4
        target,a,v=fixture(tick=200);p=raydium_clmm.analyze(target,a['pool'],batch(v),positions=[a['lead']])['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],EXPECTED['out_of_range']['principal_atomic']);self.assertEqual(p['active_liquidity_atomic'],'0');self.assertIsNone(p['whole_pool_principal_share'])
        from meteora_fixture import fixture,batch
        target,a,v=fixture();del v[a['arrays'][1]];r=meteora_dlmm.analyze(target,a['pool'],batch(v),positions=[a['lead']]);self.assertIsNone(r['positions'][0]['principal']);self.assertEqual(len(r['vaults']),2)
        from program_fixture import squads
        from solana_fixture import OTHER
        address,value=squads(config_authority=OTHER);r=squads_v4.decode(address,value)
        self.assertEqual(r['threshold'],2);self.assertEqual(len(r['members']),3);self.assertTrue(r['configuration_bypass']);self.assertEqual(r['time_lock_seconds'],3600)

if __name__=='__main__':unittest.main()
