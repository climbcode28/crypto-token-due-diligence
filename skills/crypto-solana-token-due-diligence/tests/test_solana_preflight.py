from pathlib import Path
import sys,tempfile,unittest,copy
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from compose_fixture import note,save
from solana_compose import compose,ComposeError,save_pair,recover
from solana_profile import validate
from solana_facts import encoded


class PreflightTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return Bundle(t.name)

    def test_multiple_independent_errors_report_specific_paths(self):
        b=self.fixture();n=note(b)
        for ident,claim,signal in [('bad-claim','imaginary','good'),('no-concern','state_observation','bad')]:
            n['findings'].append({'id':'coordinator-'+ident,'dimension':'token_controls','claim':claim,'strength':'direct','signal':signal,'text':'Observed base facts.','support':['controls']})
        n['signal_assignments']={'stale-id':'good'};n['coverage'][0]['status']='not_applicable';n['coverage'][0]['pending_work']=['unfinished'];save(b,n)
        before=(b.root/'report.json').read_bytes()
        with self.assertRaises(ComposeError) as caught:compose(b.root,allow_synthetic=True)
        text=str(caught.exception);self.assertIn('signal_assignments.stale-id',text);self.assertIn('claim',text);self.assertIn('concern',text);self.assertIn('report.coverage',text);self.assertGreaterEqual(len(caught.exception.errors),4)
        self.assertEqual(before,(b.root/'report.json').read_bytes())

    def test_failed_two_file_write_restores_original_pair(self):
        b=self.fixture();old={n:(b.root/n).read_bytes() for n in ('manifest.json','report.json')};import solana_compose as c
        real=c.atomic;failed=False
        def fail_once(path,data):
            nonlocal failed
            if path.name=='report.json' and not failed:failed=True;raise OSError('simulated disk failure')
            real(path,data)
        with patch.object(c,'atomic',fail_once),self.assertRaises(OSError):save_pair(b.root,encoded({**b.m,'extra':'change'}),b.r)
        self.assertEqual(old,{n:(b.root/n).read_bytes() for n in old});validate(b.root,True)

    def test_interrupted_pair_is_rejected_then_recovers(self):
        b=self.fixture();old={n:(b.root/n).read_text() for n in ('manifest.json','report.json')};(b.root/'.draft-transaction.json').write_bytes(encoded(old));(b.root/'report.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Interrupted'):validate(b.root,True)
        recover(b.root);validate(b.root,True)

if __name__=='__main__':unittest.main()
