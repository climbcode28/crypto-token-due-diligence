from pathlib import Path
import sys,tempfile,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from facts_fixture import rich
from solana_pipeline_note import generate
from solana_profile import validate
from solana_accounts import controls
ENABLED=('raydium_cpmm','raydium_amm_v4','raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2','pump_curve','pumpswap')


class PipelineTests(unittest.TestCase):
    def fixture(self,kind=None):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return rich(t.name,kind) if kind else Bundle(t.name)

    def test_generated_findings_validate_for_all_protocols_and_remain_unjudged(self):
        for kind in ENABLED:
            b=self.fixture(kind);note=generate(b.root,True);b.r['findings']=note['findings'];b.r['summary_ids']=[];b.save();validate(b.root,True)
            self.assertTrue(all(f['signal'] is None for f in note['findings']))
            self.assertTrue(all(f['owner']=='pipeline' for f in note['findings']))

    def test_regeneration_is_byte_identical_and_preserves_coordinator_file(self):
        b=self.fixture();path=b.root/'notes/coordinator.json';path.parent.mkdir(exist_ok=True);path.write_text('existing analyst correction')
        a=generate(b.root,True);raw=(b.root/'notes/pipeline.json').read_bytes();z=generate(b.root,True)
        self.assertEqual(a,z);self.assertEqual(raw,(b.root/'notes/pipeline.json').read_bytes());self.assertEqual(path.read_text(),'existing analyst correction')

    def test_changed_input_replaces_conclusion_without_duplicate_or_stale_digest(self):
        b=self.fixture();first=generate(b.root,True)
        from pool_fixture import mint,key
        for eid in ('mint','mint-fresh'):
            obj=b.obj(eid);obj['response']['result']['value']=mint(2000000,key(60));b.replace(eid,obj)
        out=controls(b.obj('mint'),b.target);b.replace('controls',out);d=b.m['derivations'][0];d['output']=out;d['inputs'][0]['sha256']=b.obs('mint')['sha256'];b.save()
        second=generate(b.root,True);self.assertEqual([f['id'] for f in first['findings']],[f['id'] for f in second['findings']])
        self.assertIn('2000000',second['findings'][0]['text']);self.assertIn(key(60),second['findings'][0]['text'])
        self.assertNotEqual(first['manifest_sha256'],second['manifest_sha256'])

    def test_partial_missing_config_retains_vault_observations_without_reserve_claim(self):
        b=self.fixture('raydium_cpmm');obs=b.obj('pool-state')
        config=b.obj('pool-raydium_cpmm')['state']['config'];i=obs['request']['params'][0].index(config)
        obs['response']['result']['value'][i]=None;b.replace('pool-state',obs)
        from solana_derivations import compute
        d=b.m['derivations'][1];out=compute('pool',d['parameters'],b.target,b.obj);b.replace(d['id'],out);d['output']=out;d['inputs'][0]['sha256']=b.obs('pool-state')['sha256'];b.save()
        note=generate(b.root,True);self.assertTrue(any('vaults:' in f['text'] for f in note['findings']))
        self.assertTrue(any('reserves_atomic: null' in f['text'] for f in note['findings']))

if __name__=='__main__':unittest.main()
