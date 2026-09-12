from pathlib import Path
import sys,tempfile,unittest,os,copy,shutil
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery_fixture import complete
from solana_replay import finalize,verify,replay,read,ENGINE_ROOT


class ReplayTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);b,n=complete(root/'draft');finalize(b.root,root/'final',allow_synthetic=True);return root,root/'final'

    def test_hash_verification_never_executes_snapshot_and_requires_synthetic_opt_in(self):
        root,frozen=self.fixture()
        with patch('subprocess.run',side_effect=AssertionError('execution forbidden')),patch('solana_replay.render',side_effect=AssertionError('no installed rendering')):
            self.assertTrue(verify(frozen,True)['valid']);self.assertFalse(verify(frozen,True)['executed_frozen_code']);self.assertTrue(read(frozen,True)['deliverable'])
        with self.assertRaisesRegex(ValueError,'Synthetic'):verify(frozen)
        with self.assertRaisesRegex(ValueError,'explicitly trust'):replay(frozen,allow_synthetic=True)

    def test_replay_ignores_installed_engine_pythonpath_cwd_and_bytecode(self):
        root,frozen=self.fixture();poison=root/'poison';poison.mkdir();(poison/'solana_render.py').write_text('raise RuntimeError("poison")')
        before={str(p.relative_to(frozen)):p.read_bytes() for p in frozen.rglob('*') if p.is_file()}
        with patch.dict(os.environ,{'PYTHONPATH':str(poison)}),patch('solana_replay.render',side_effect=RuntimeError('installed version changed')):
            result=replay(frozen,trust_frozen_code=True,allow_synthetic=True)
        self.assertTrue(result['reproduced']);self.assertEqual(before,{str(p.relative_to(frozen)):p.read_bytes() for p in frozen.rglob('*') if p.is_file()})
        self.assertFalse(list(frozen.rglob('*.pyc')))

    def test_missing_tampered_unlisted_dependency_and_escape_are_rejected(self):
        root,frozen=self.fixture();code=frozen/'engine/scripts/solana_render.py';raw=code.read_bytes();code.write_bytes(raw+b'\n# tamper\n')
        with self.assertRaisesRegex(ValueError,'hash/size'):verify(frozen,True)
        code.write_bytes(raw);extra=frozen/'engine/scripts/evil.py';extra.write_text('raise RuntimeError()')
        with self.assertRaisesRegex(ValueError,'unlisted'):verify(frozen,True)
        extra.unlink();code.unlink()
        with self.assertRaisesRegex(ValueError,'missing'):verify(frozen,True)
        code.symlink_to(ENGINE_ROOT/'scripts/solana_render.py')
        with self.assertRaisesRegex(ValueError,'symlink'):verify(frozen,True)

    def test_frozen_code_is_standalone_and_contains_registries_layouts_and_all_adapters(self):
        root,frozen=self.fixture();result=verify(frozen,True);paths={r['path'] for r in result['receipt']['inventory']}
        for name in ('protocol-registry.json','network-registry.json','layout-sources.json','runtime-provenance.json'):
            self.assertIn('engine/assets/'+name,paths)
        for name in ('raydium_cpmm','raydium_amm_v4','raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2','pump_curve','pump_swap'):
            self.assertIn('engine/scripts/adapters/'+name+'.py',paths)
        self.assertTrue(replay(frozen,trust_frozen_code=True,allow_synthetic=True)['reproduced'])

if __name__=='__main__':unittest.main()
