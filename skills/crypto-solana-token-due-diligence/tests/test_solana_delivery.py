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
        markdown=Path(result['report_path']).read_text();self.assertNotIn('markdown',result)
        self.assertIn('issue additional units',markdown);self.assertIn('dilute holders',markdown);self.assertIn('whether I can sell',markdown)
        self.assertIn('## Summary',markdown);self.assertIn('🟡 **Potential Risk**',markdown);self.assertIn('**Conclusions**',markdown)
        for axis in ('Technical exposure','Credibility and maturity','Token economics','Research confidence'):self.assertEqual(markdown.count('- **'+axis+':**'),1)
        verdict=next(x for x in result['reading_checklist'] if x['kind']=='verdict');self.assertEqual(set(verdict['axes']),{'technical_exposure','credibility_maturity','token_economics','research_confidence'})
        finding=next(x for x in result['reading_checklist'] if x['kind']=='finding' and x['signal']=='potential_risk');self.assertEqual(finding['label'],'🟡 Potential Risk');self.assertTrue(finding['citations'])
        self.assertEqual(result,read(root/'final',True));self.assertEqual(result['network_requests'],0)

    def test_reading_payload_collapses_field_restatements_and_unreferenced_citations(self):
        root,b,n=self.fixture(True);result=finalize(b.root,root/'final',allow_synthetic=True)
        findings=[x for x in result['reading_checklist'] if x['kind']=='finding']
        import json
        report=json.loads((root/'final/report.json').read_text());pipeline=[f for f in report['findings'] if f['owner']=='pipeline']
        parents={f['id'] for f in pipeline if f['id']=='pipeline-'+f['support'][0]['evidence_id']}
        self.assertTrue(parents);self.assertTrue(all(x['id'] in parents or not x['id'].startswith('pipeline-') for x in findings))
        self.assertEqual(result['field_restatements_omitted'],len(pipeline)-len(parents))
        self.assertTrue(any(x.get('field_restatements') for x in findings if x['id'] in parents))
        self.assertEqual(result['citations_omitted']+len(result['citations']),len(json.loads((root/'final/manifest.json').read_text())['observations']))
        cited={c['evidence_id'] for x in findings for c in x['citations']}
        self.assertTrue(cited<={c['evidence_id'] for c in result['citations']})

    def test_checkpoint_records_unjudged_work_but_cannot_deliver(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);b=Bundle(root/'draft');save(b,note(b))
        result=finalize(b.root,root/'checkpoint',allow_synthetic=True,checkpoint=True)
        self.assertFalse(result['deliverable']);self.assertIsNone(validate(root/'checkpoint',True)[1]['decision'])
        markdown=Path(result['report_path']).read_text();self.assertIn('Unjudged checkpoint',markdown);self.assertEqual(markdown.count('Unjudged; standard research'),4)
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
