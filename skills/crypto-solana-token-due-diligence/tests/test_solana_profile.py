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


if __name__=='__main__':unittest.main()
