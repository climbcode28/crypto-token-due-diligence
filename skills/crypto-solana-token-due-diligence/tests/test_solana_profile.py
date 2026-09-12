from pathlib import Path
import sys,tempfile,unittest,copy,json,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle,dump,BASE,utc,key
from solana_profile import validate,ProfileError,Evidence
from solana_common import sha


class ProfileTests(unittest.TestCase):
    def fixture(self,**opts):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);return Bundle(tmp.name,**opts)

    def test_partial_and_completed_bounded_unknowns_validate(self):
        for opts in ({},{'completed':True},{'completed':True,'all_gaps':True},{'completed':True,'adverse':True}):
            b=self.fixture(**opts);m,r=validate(b.root,True);self.assertEqual(r['research_status'],b.r['research_status'])
            before=(b.root/'manifest.json').read_bytes();validate(b.root,True);self.assertEqual(before,(b.root/'manifest.json').read_bytes())

    def test_synthetic_opt_in_and_explicit_cli_profile(self):
        b=self.fixture()
        with self.assertRaisesRegex(ProfileError,'synthetic'):validate(b.root)
        command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/solana_bundle.py'),'validate',str(b.root),'--profile','solana-evidence-v2','--allow-synthetic']
        r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
        b.r['question']='Changed question';b.save();r=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(r.returncode,2);self.assertIn('report.question',r.stderr)

    def test_manifest_evidence_and_derived_hashes_cannot_be_changed(self):
        for case in ('manifest','raw','derived','input','missing','unused'):
            b=self.fixture()
            if case=='manifest':b.m['intake']['focus'].append('extra');(b.root/'manifest.json').write_bytes(dump(b.m))
            elif case=='raw':(b.root/'evidence/mint.json').write_text('{}')
            elif case=='missing':(b.root/'evidence/mint.json').unlink()
            else:
                d=b.m['derivations'][0]
                if case=='input':d['inputs'][0]['sha256']='0'*64
                if case=='derived':
                    obj=b.obj('controls');obj['mint']['supply_atomic']='2';b.replace('controls',obj);d['output']=obj
                if case=='unused':d['inputs'].append({'id':'block100','sha256':b.obs('block100')['sha256']});d['transitive_inputs'].append('block100')
                b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_failed_render_does_not_create_empty_report(self):
        b=self.fixture()
        b.r['question']='Changed request';b.save()
        command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/solana_bundle.py'),'render',str(b.root),'--profile','solana-evidence-v2','--allow-synthetic']
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertFalse((b.root/'report.md').exists())

    def test_derived_cycle_and_wrong_subject_rejected(self):
        for case in ('cycle','subject','closure','operation'):
            b=self.fixture();d=b.m['derivations'][0]
            if case=='cycle':d['inputs']=[{'id':'controls','sha256':b.obs('controls')['sha256']}];d['transitive_inputs']=['controls']
            if case=='subject':d['subject']={**d['subject'],'address':key(3)};b.obs('controls')['subject']=d['subject']
            if case=='closure':d['transitive_inputs']=[]
            if case=='operation':d['operation']='eval'
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_strict_json_duplicate_nonfinite_and_symlink_inventory(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":1e999}',b'{"a":NaN}'):
            from solana_profile import strict_json
            with self.assertRaises(ProfileError):strict_json(raw,'bad.json')
        b=self.fixture();p=b.root/'evidence/mint.json';saved=p.read_bytes();p.unlink();(b.root/'outside.json').write_bytes(saved);p.symlink_to(b.root/'outside.json')
        with self.assertRaisesRegex(ProfileError,'symlink'):validate(b.root,True)

    def test_unselected_conflicting_genesis_and_copied_header_recheck(self):
        for case in ('genesis','masked_genesis','recheck','mapping','metadata_status'):
            b=self.fixture()
            if case in ('genesis','masked_genesis'):
                packet=b.rpc('other-genesis','getGenesisHash',[],key(3),45)
                if case=='masked_genesis':packet['status']='transport_failure';b.replace('other-genesis',packet);b.obs('other-genesis')['status']='transport_failure'
            if case=='recheck':b.m['samples'][0]['block_recheck_evidence_id']='block100'
            if case=='mapping':b.m['samples'][0]['address_indices'][key(2)]=1
            if case=='metadata_status':b.obs('mint')['status']='unsupported'
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_critical_change_invalidates_stability_only(self):
        b=self.fixture();obj=b.obj('mint-fresh');obj['response']['result']['value']['lamports']+=1;b.replace('mint-fresh',obj);b.save()
        with self.assertRaisesRegex(ProfileError,'stability'):validate(b.root,True)
        b.r['findings'][0]['time_basis']['stability']='not_asserted';b.save();validate(b.root,True)

    def test_history_outside_verified_bracket_is_retained_but_unusable(self):
        b=self.fixture();b.rpc('history','getSignaturesForAddress',[key(2),{'commitment':'finalized','limit':5}],[],45);b.save()
        m,r=validate(b.root,True);e=Evidence(b.root,m,True)
        self.assertEqual(e.degraded.get('history'),'history outside verified network interval');self.assertNotIn('history',e.usable);self.assertIn('controls',e.usable)
        b.rpc('inside','getSignaturesForAddress',[key(2),{'commitment':'finalized','limit':5}],[],25);b.save();e=Evidence(b.root,validate(b.root,True)[0],True)
        self.assertIn('inside',e.usable);self.assertNotIn('inside',e.degraded)

    def test_sample_outside_bracket_is_unpinned_not_a_crash(self):
        b=self.fixture();packet=b.obj('regenesis');packet['started_at']=BASE+15;packet['completed_at']=BASE+15.5;b.replace('regenesis',packet);b.obs('regenesis')['captured_at']=utc(BASE+15.5);b.save()
        e=Evidence(b.root,json.loads((b.root/'manifest.json').read_bytes()),True)
        self.assertEqual(e.degraded.get('mint-fresh'),'state outside verified provider/network interval');self.assertIn('sample-mint-fresh',e.unpinned)
        self.assertEqual(e.degraded.get('mint'),'critical recheck unavailable');self.assertNotIn('mint',e.pinned);self.assertNotIn('controls',e.usable)
        with self.assertRaisesRegex(ProfileError,'unusable evidence cannot support'):validate(b.root,True)  # a finding-level rule, not an import crash

    def test_operation_versions_report_engine_differences_not_tampering(self):
        import solana_derivations as derivations
        b=self.fixture();b.derived('graph','controllers',{'root_derivations':['controls'],'observations':{}},['controls'],{'nodes':[],'roots':[]});b.m['derivations'][-1]['version']='1.0.0';b.save()
        with self.assertRaisesRegex(ProfileError,'operation version differs from installed engine; use read/replay'):validate(b.root,True)
        b.m['derivations'][-1]['version']='9.9.9';b.save()
        with self.assertRaisesRegex(ProfileError,'newer engine'):validate(b.root,True)
        b.m['derivations'][-1]['version']='x';b.save()
        with self.assertRaisesRegex(ProfileError,'unsupported operation version'):validate(b.root,True)
        b=self.fixture();b.m['derivations'][0]['version']='1.0.0';b.save()
        with self.assertRaisesRegex(ProfileError,'operation version differs'):validate(b.root,True)  # controls output changed in 1.1.0
        self.assertEqual(derivations.recomputable('quote_sizes','1.0.0'),'ok');self.assertEqual(derivations.recomputable('controls',derivations.VERSION),'ok')
        self.assertIn('differs',derivations.recomputable('controllers','1.0.0'))

    def test_supply_tick_between_rechecks_keeps_stability_with_changed_fields(self):
        import base64
        b=self.fixture();packet=b.obj('mint-fresh');raw=bytearray(base64.b64decode(packet['response']['result']['value']['data'][0]))
        raw[36:44]=(1000001).to_bytes(8,'little');packet['response']['result']['value']['data'][0]=base64.b64encode(bytes(raw)).decode();b.replace('mint-fresh',packet);b.save()
        m,r=validate(b.root,True);e=Evidence(b.root,m,True);self.assertIn('mint',e.stable);self.assertEqual(e.stability_changes,{'mint':{key(2):['supply_atomic']}})
        raw[0:4]=(1).to_bytes(4,'little');raw[4:36]=bytes([9])*32;packet['response']['result']['value']['data'][0]=base64.b64encode(bytes(raw)).decode();b.replace('mint-fresh',packet);b.save()
        with self.assertRaisesRegex(ProfileError,'stability'):validate(b.root,True)

    def test_concern_shape_is_validated_for_every_finding(self):
        b=self.fixture();b.r['findings'][0]['concern']='not an object';b.save()
        with self.assertRaisesRegex(ProfileError,'concern must be an object'):validate(b.root,True)
        b.r['findings'][0]['concern']={'basis':'x','mechanism':'y'};b.save()
        with self.assertRaisesRegex(ProfileError,'concern must be an object'):validate(b.root,True)


if __name__=='__main__':unittest.main()
