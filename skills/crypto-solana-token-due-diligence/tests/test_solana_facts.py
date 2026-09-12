from pathlib import Path
import sys,tempfile,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from facts_fixture import rich
from solana_facts import build,compact,describe
ENABLED=('raydium_cpmm','raydium_amm_v4','raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2','pump_curve','pumpswap')


class FactsTests(unittest.TestCase):
    def fixture(self,kind=None):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return rich(t.name,kind) if kind else Bundle(t.name)

    def test_all_eight_protocol_facts_preserve_typed_principal_and_custody(self):
        for kind in ENABLED:
            with self.subTest(kind=kind):
                b=self.fixture(kind);f=build(b.root,True);row=next(r for r in f['facts'] if r['operation']=='pool')
                self.assertTrue(row['usable']);self.assertEqual(row['data'],b.obj('pool-'+kind))
                self.assertIsNone(row['data']['all_principal_locked']);self.assertTrue(row['limits']);self.assertIn(kind,compact(f))

    def test_controls_zero_missing_and_named_authorities_are_visible(self):
        b=self.fixture();f=build(b.root,True);view=compact(f)
        self.assertIn('1000000 atomic',view);self.assertIn('absent in sample',view);self.assertIn('controller and upgrade paths',view)
        self.assertEqual(f['facts'][0]['data']['mint']['supply_atomic'],'1000000')
        self.assertIsNone(f['facts'][0]['data']['mint']['freeze_authority'])

    def test_unusable_source_keeps_independent_facts_and_counts(self):
        b=self.fixture();before=build(b.root,True)['facts'];b.document('failed');b.save();after=build(b.root,True)
        self.assertEqual(before,after['facts']);self.assertIn('failed',[r['id'] for r in after['missing_reads']]);self.assertIn('not passing checks',compact(after))

    def test_compact_soft_cap_has_omitted_index_and_keeps_material_limits(self):
        b=self.fixture('raydium_clmm');f=build(b.root,True);view=compact(f,limit=1024)
        self.assertIn('Omitted-detail index:',view);self.assertIn('program_control_not_observed',view);self.assertIn('facts.json#fact-',view)
        selected=compact(f,['controls']);self.assertIn('category not selected',selected)
        with self.assertRaises(ValueError):compact(f,['imaginary'])

    def test_exact_holder_totals_and_spending_owner_scope_need_no_addition(self):
        from test_solana_holders import HolderTests
        from solana_accounts import aggregate_holders
        from solana_fixture import TARGET
        d,s=HolderTests().packets();r=aggregate_holders(d,s,TARGET);view=describe('holders',r)
        self.assertIn(str(2**59+108)+'/'+str(2**60+17),view);self.assertIn('50.0000%',view)
        self.assertIn(str(2**59+101),view);self.assertIn('2 accounts',view);self.assertIn('beneficial ownership',view)

    def test_source_metrics_have_no_organic_or_fraud_inference(self):
        view=describe('repository_metadata',{'stars':0,'pushed_at':None});self.assertIn('do not establish organic use',view)
    def test_degraded_reads_carry_their_reason(self):
        from profile_fixture import key
        b=self.fixture();b.rpc('history','getSignaturesForAddress',[key(2),{'commitment':'finalized','limit':5}],[],45);b.save()
        row=next(r for r in build(b.root,True)['missing_reads'] if r['id']=='history');self.assertEqual(row['reason'],'history outside verified network interval');self.assertEqual(row['status'],'ok')

    def test_describe_names_program_controller_and_assurance_subjects(self):
        from pool_fixture import key
        self.assertIn(key(5),describe('program',{'address':key(5),'loader':'BPFLoaderUpgradeab1e11111111111111111111111','upgradeability':'authority_present','upgrade_authority':key(6),'code_capture':'unavailable'}))
        self.assertIn(key(7),describe('controllers',{'roots':[key(7)],'nodes':[{'status':'observed'},{'status':'unresolved'}],'status':'partial','safe_or_locked_conclusion':None}))
        self.assertIn('1 of 2',describe('controllers',{'roots':[key(7)],'nodes':[{'status':'observed'},{'status':'unresolved'}],'status':'partial','safe_or_locked_conclusion':None}))
        self.assertIn(key(8),describe('source_assurance',{'program':key(8),'publication':'not_observed','third_party_verification':'not_observed','byte_correspondence':'incomplete_executable_bytes','independent_reproduction':'not_performed'}))

    def test_facts_check_is_read_only_and_plain_facts_writes(self):
        import subprocess,sys
        b=self.fixture();cli=Path(__file__).resolve().parents[1]/'scripts/solana_bundle.py';before=sorted(p.name for p in b.root.iterdir())
        r=subprocess.run([sys.executable,'-B',str(cli),'facts',str(b.root),'--allow-synthetic','--check'],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('controls [',r.stdout);self.assertIn('digest=',r.stdout)
        self.assertEqual(before,sorted(p.name for p in b.root.iterdir()));self.assertFalse((b.root/'facts.json').exists())
        r=subprocess.run([sys.executable,'-B',str(cli),'facts',str(b.root),'--allow-synthetic'],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((b.root/'facts.json').exists());self.assertTrue((b.root/'notes/pipeline.json').exists())


if __name__=='__main__':unittest.main()
