from pathlib import Path
import sys,tempfile,unittest,json,copy
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery_fixture import complete
from profile_fixture import Bundle
from compose_fixture import note,save
from solana_replay import finalize,read,verify
from solana_profile import validate
from solana_facts import encoded


class DeliveryTests(unittest.TestCase):
    def fixture(self,adverse=False):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);b,n=complete(root/'draft',adverse)
        return root,b,n

    def test_completed_note_freezes_and_returns_reading_and_citations_same_call(self):
        root,b,n=self.fixture(True);before=(b.root/'report.json').read_bytes()
        result=finalize(b.root,root/'final',allow_synthetic=True)
        self.assertTrue(result['deliverable']);self.assertEqual(result['delivery_status'],'delivered');self.assertTrue(result['citations']);self.assertTrue(result['reading_checklist'])
        self.assertEqual(before,(b.root/'report.json').read_bytes());validate(root/'final',True)
        self.assertIn('issue additional units',result['markdown']);self.assertIn('dilute holders',result['markdown']);self.assertIn('whether I can sell',result['markdown'])
        self.assertEqual(result,read(root/'final',True));self.assertEqual(result['network_requests'],0)

    def test_checkpoint_records_unjudged_work_but_cannot_deliver(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);b=Bundle(root/'draft');save(b,note(b))
        result=finalize(b.root,root/'checkpoint',allow_synthetic=True,checkpoint=True)
        self.assertFalse(result['deliverable']);self.assertIsNone(validate(root/'checkpoint',True)[1]['decision'])
        self.assertIn('Unjudged checkpoint',result['markdown'])
        with self.assertRaisesRegex(ValueError,'Completed broad'):finalize(b.root,root/'final',allow_synthetic=True)
        self.assertFalse((root/'final').exists())

    def test_pending_focused_malformed_and_existing_outputs_are_not_delivered(self):
        root,b,n=self.fixture();out=root/'final';out.mkdir();(out/'keep').write_text('old report')
        with self.assertRaisesRegex(ValueError,'new output'):finalize(b.root,out,allow_synthetic=True)
        self.assertEqual((out/'keep').read_text(),'old report')
        n['decision']=None;save(b,n)
        with self.assertRaises(ValueError):finalize(b.root,root/'malformed',allow_synthetic=True)
        self.assertFalse((root/'malformed').exists())
        n['scope']='focused';b.m['intake']['scope']='focused';b.r['scope']='focused';b.save();save(b,n)
        with self.assertRaises(ValueError):finalize(b.root,root/'focused',allow_synthetic=True)

    def test_failed_freeze_keeps_prior_draft_and_no_delivery_directory(self):
        root,b,n=self.fixture();before={str(p.relative_to(b.root)):p.read_bytes() for p in b.root.rglob('*') if p.is_file()}
        with patch('solana_replay.snapshot_engine',side_effect=ValueError('snapshot failure')):
            with self.assertRaisesRegex(ValueError,'snapshot failure'):finalize(b.root,root/'failed',allow_synthetic=True)
        self.assertFalse((root/'failed').exists())
        after={str(p.relative_to(b.root)):p.read_bytes() for p in b.root.rglob('*') if p.is_file() and p.name!='.compose.lock'}
        self.assertEqual(before,after)

    def test_delivered_label_without_physical_freeze_fails(self):
        root,b,n=self.fixture();from solana_compose import compose
        compose(b.root,allow_synthetic=True);r=json.loads((b.root/'report.json').read_text());r['delivery_status']='delivered';(b.root/'report.json').write_bytes(encoded(r))
        with self.assertRaises(ValueError):validate(b.root,True)

if __name__=='__main__':unittest.main()
