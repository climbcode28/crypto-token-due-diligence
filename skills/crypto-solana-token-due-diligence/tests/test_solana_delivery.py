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
        finding=next(x for x in result['reading_checklist'] if x['kind']=='finding' and x['signal']=='potential_risk');self.assertNotIn('label',finding);self.assertTrue(finding['citations'])
        self.assertTrue(all(c in {r['evidence_id'] for r in result['citations']} for c in finding['citations']));self.assertIn('potential_risk 🟡 Potential Risk',result['compaction'])
        self.assertEqual(result,read(root/'final',True));self.assertEqual(result['network_requests'],0)

    def test_reading_payload_collapses_field_restatements_and_unreferenced_citations(self):
        root,b,n=self.fixture(True);result=finalize(b.root,root/'final',allow_synthetic=True)
        findings=[x for x in result['reading_checklist'] if x['kind']=='finding'];typed=[x for x in result['reading_checklist'] if x['kind']=='typed_fact']
        import json
        report=json.loads((root/'final/report.json').read_text());pipeline=[f for f in report['findings'] if f['owner']=='pipeline']
        parents={f['id'] for f in pipeline if f['id']=='pipeline-'+f['support'][0]['evidence_id']}
        # A typed fact's own pipeline finding travels inside the fact entry; only analyst findings stay separate entries.
        self.assertTrue(parents);self.assertFalse(any(x['id'].startswith('pipeline-') for x in findings))
        self.assertEqual({'pipeline-'+x['evidence_id'] for x in typed if 'finding' in x},parents)
        self.assertEqual(result['field_restatements_omitted'],len(pipeline)-len(parents))
        self.assertTrue(any(x['finding'].get('field_restatements') for x in typed if 'finding' in x))
        self.assertEqual(result['citations_omitted']+len(result['citations']),len(json.loads((root/'final/manifest.json').read_text())['observations']))
        cited={c for x in findings for c in x['citations']}
        self.assertTrue(cited<={c['evidence_id'] for c in result['citations']})

    def test_reading_keeps_every_typed_quantity_and_limit_and_aliases_round_trip(self):
        from solana_render import PROVENANCE_KEYS,ADDRESS
        root,b,n=self.fixture(True);result=finalize(b.root,root/'final',allow_synthetic=True)
        manifest=json.loads((root/'final/manifest.json').read_text());typed={x['evidence_id']:x for x in result['reading_checklist'] if x['kind']=='typed_fact'}
        table=result['addresses'];self.assertTrue(table)
        def expand(text):return ADDRESS.sub(lambda m:m.group(0),text) if not table else __import__('re').sub(r'@[A-Za-z0-9_]+',lambda m:table.get(m.group(0),m.group(0)),text)
        def leaves(value,path=()):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k in PROVENANCE_KEYS:continue
                    yield from leaves(v,path+(k,))
            elif isinstance(value,list):
                for v in value:yield from leaves(v,path)
            elif value is not None and value not in ([],{},''):yield path,value
        for d in manifest['derivations']:
            entry=typed[d['id']];text=expand(json.dumps([entry['details'],entry['limits'],entry['attention'],entry['summary']],ensure_ascii=False))
            for path,value in leaves(d['output']):
                if path and path[-1] in ('places','rounding'):continue  # share objects collapse to numerator/denominator = percent
                self.assertIn(json.dumps(value,ensure_ascii=False).strip('"'),text,(d['id'],path,value))
            for row in [str(r['path']) for r in __import__('solana_facts').scan(d['output'],__import__('solana_facts').LIMIT_KEYS)]:
                self.assertTrue(any(expand(l).startswith(row.split('[')[0]) for l in entry['limits']),(d['id'],row))
        for alias in __import__('re').findall(r'@[A-Za-z0-9_]+',json.dumps(list(typed.values()),ensure_ascii=False)):
            if alias.startswith('@a') or alias in ('@target_mint','@wsol','@spl_token','@token_2022','@system','@genesis_hash'):self.assertIn(alias,table,alias)
        for alias,address in table.items():self.assertRegex(address,ADDRESS)
        self.assertLess(len(json.dumps(result,ensure_ascii=False).encode()),60_000)

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
