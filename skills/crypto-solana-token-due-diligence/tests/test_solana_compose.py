from pathlib import Path
import sys,tempfile,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from compose_fixture import note,save,lane,assign
from solana_compose import compose,ComposeError
from solana_profile import validate


class ComposeTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return Bundle(t.name)

    def test_small_note_expands_aliases_and_composes_idempotently(self):
        b=self.fixture();n=note(b)
        n['findings']=[{'id':'coordinator-supply','dimension':'token_controls','claim':'state_observation','strength':'direct','signal':'good','text':'The mint base configuration was captured.','support':['controls']}]
        save(b,n);a=compose(b.root,allow_synthetic=True);validate(b.root,True);raw=(b.root/'report.json').read_bytes();compose(b.root,allow_synthetic=True)
        self.assertEqual(raw,(b.root/'report.json').read_bytes());f=a['report']['findings'][-1];self.assertEqual(f['support'][0]['evidence_id'],'controls');self.assertEqual(f['time_basis']['sample_ids'],['sample-mint'])

    def test_assignment_and_explicit_correction_survive_pipeline_regeneration(self):
        b=self.fixture();n=note(b);n['signal_assignments']=assign(b,'unverified',{'pipeline-controls'})
        n['overrides']=[{'finding_id':'pipeline-controls','reason':'Keep the remaining control scope explicit.','evidence_ids':['controls'],'input_digests':{'controls':b.obs('controls')['sha256']},'changes':{'text':'Mint base facts were sampled; program/controller paths remain unresolved.'}}]
        save(b,n);compose(b.root,allow_synthetic=True)
        from solana_pipeline_note import generate
        generate(b.root,True);r=compose(b.root,allow_synthetic=True)['report'];self.assertEqual(r['findings'][0]['text'],n['overrides'][0]['changes']['text'])
        self.assertEqual(r['findings'][0]['signal'],'unverified')
        n['overrides'][0]['input_digests']['controls']='0'*64;save(b,n)
        with self.assertRaisesRegex(ComposeError,'input_digests'):compose(b.root,allow_synthetic=True)

    def test_both_lanes_round_trip_and_cannot_replace_pipeline(self):
        b=self.fixture();n=note(b);save(b,n);lane(b,'liquidity');lane(b,'project');compose(b.root,allow_synthetic=True);m,r=validate(b.root,True)
        self.assertEqual({x['owner'] for x in m['lanes']},{'liquidity','project'});before=(b.root/'report.json').read_bytes()
        n=lane(b,'liquidity');n['findings']=[{'id':'pipeline-controls','dimension':'token_controls','claim':'state_observation','strength':'direct','text':'Overwrite','support':['controls']}];save(b,n,'liquidity')
        with self.assertRaisesRegex(ComposeError,'must start with liquidity'):compose(b.root,allow_synthetic=True)
        self.assertEqual(before,(b.root/'report.json').read_bytes())

    def test_wrong_alias_and_cross_lane_import_fail_without_draft_writes(self):
        b=self.fixture();n=note(b);save(b,n);before=(b.root/'report.json').read_bytes();l=lane(b,'liquidity')
        l['imports']=[{'path':b.obs('controls')['artifact'],'evidence_id':'controls','sha256':b.obs('controls')['sha256']}];save(b,l,'liquidity')
        with self.assertRaisesRegex(ComposeError,'another lane'):compose(b.root,allow_synthetic=True)
        self.assertEqual(before,(b.root/'report.json').read_bytes())

    def test_check_only_does_not_create_lock_or_modify_any_file(self):
        b=self.fixture();n=note(b);save(b,n)
        def inventory():return {str(p.relative_to(b.root)):p.read_bytes() for p in b.root.rglob('*') if p.is_file()}
        before=inventory();r=compose(b.root,allow_synthetic=True,check_only=True);self.assertFalse(r['written']);self.assertEqual(before,inventory())

    def test_complete_bounded_note_with_lanes_expands_to_valid_complete_draft(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);b=Bundle(t.name,completed=True)
        original=copy.deepcopy(b.r);b.m['lanes']=[];b.m['artifacts']=[a for a in b.m['artifacts'] if not a['path'].startswith('notes/')];b.save()
        n=note(b);mapping={f['id']:'coordinator-'+f['id'] for f in original['findings']}
        def rename(v):
            if isinstance(v,str):return mapping.get(v,v)
            if isinstance(v,list):return [rename(x) for x in v]
            if isinstance(v,dict):return {k:rename(x) for k,x in v.items()}
            return v
        for field in ('findings','coverage','decision','summary_ids','limitations'):n[field]=rename(original[field])
        n['signal_assignments']=assign(b,'unverified')
        n['research_status']='completed';save(b,n);lane(b,'liquidity');lane(b,'project')
        compose(b.root,allow_synthetic=True);m,r=validate(b.root,True);self.assertEqual(r['research_status'],'completed')
        self.assertTrue(all(l['note_artifact'].startswith('note-snapshots/') for l in m['lanes']))
        before=(b.root/'report.json').read_bytes();compose(b.root,allow_synthetic=True);self.assertEqual(before,(b.root/'report.json').read_bytes())

    def test_editing_lane_note_does_not_invalidate_previous_report(self):
        b=self.fixture();save(b,note(b));lane(b,'liquidity');lane(b,'project');compose(b.root,allow_synthetic=True)
        (b.root/'notes/liquidity.json').write_text('{invalid ongoing edit')
        validate(b.root,True)

    def test_ambiguous_operation_alias_requires_exact_id(self):
        b=self.fixture();out=b.obj('controls');b.derived('other-controls','controls',{'mint':'mint'},['mint'],out);b.save()
        n=note(b);n['findings']=[{'id':'coordinator-controls','dimension':'token_controls','claim':'state_observation','strength':'direct','text':'Base facts.','support':['controls:'+b.target['mint']]}];save(b,n)
        with self.assertRaisesRegex(ComposeError,'uniquely'):compose(b.root,allow_synthetic=True)
    def test_signal_assignment_binds_to_current_fact_digest(self):
        b=self.fixture();n=note(b);n['signal_assignments']={'pipeline-controls':'good'};save(b,n)
        with self.assertRaisesRegex(ComposeError,'signal_assignments.pipeline-controls.input_digests'):compose(b.root,allow_synthetic=True)
        n['signal_assignments']=assign(b,'good',{'pipeline-controls'});save(b,n);compose(b.root,allow_synthetic=True)
        n['signal_assignments']['pipeline-controls']['input_digests']['controls']='0'*64;save(b,n)
        with self.assertRaisesRegex(ComposeError,'changed fact needs re-review'):compose(b.root,allow_synthetic=True)
        from solana_scaffold import scaffold
        fresh=scaffold(b.root,allow_synthetic=True)['signal_assignments']['pipeline-controls'];self.assertIsNone(fresh['signal']);self.assertEqual(fresh['input_digests'],{'controls':b.obs('controls')['sha256']})

    def test_field_level_pipeline_findings_inherit_the_fact_signal(self):
        import json
        from solana_scaffold import scaffold
        b=self.fixture();fresh=scaffold(b.root,allow_synthetic=True)['signal_assignments']
        self.assertIn('pipeline-controls',fresh);self.assertFalse([k for k in fresh if k.startswith('pipeline-controls-')])  # one judgment per fact
        n=note(b);n['signal_assignments']=assign(b,'good',{'pipeline-controls'});save(b,n);compose(b.root,allow_synthetic=True)
        rows=[f for f in json.loads((b.root/'report.json').read_text())['findings'] if f['id'].startswith('pipeline-controls-')]
        self.assertTrue(rows);self.assertTrue(all(f['signal']=='good' for f in rows))
        n['signal_assignments']=assign(b,'good',{'pipeline-controls'});n['signal_assignments'].update(assign(b,'unverified',{rows[0]['id']}));save(b,n);compose(b.root,allow_synthetic=True)
        explicit=next(f for f in json.loads((b.root/'report.json').read_text())['findings'] if f['id']==rows[0]['id']);self.assertEqual(explicit['signal'],'unverified')
        # Severity and the concern never inherit: a high-impact parent does not make every field restatement severe.
        n['signal_assignments']=assign(b,'potential_risk',{'pipeline-controls'});n['signal_assignments']['pipeline-controls'].update({'impact':'high','concern':{'basis':'Observed mint authority.','mechanism':'It can mint.','consequence':'Dilution.'}})
        n['summary_ids']=['pipeline-controls'];save(b,n);compose(b.root,allow_synthetic=True)
        report=json.loads((b.root/'report.json').read_text());children=[f for f in report['findings'] if f['id'].startswith('pipeline-controls-')]
        self.assertTrue(all(f['signal']=='potential_risk' and f['impact']=='informational' and f['concern']['basis']=='Observed mint authority.' for f in children))
        self.assertEqual(report['summary_ids'],['pipeline-controls'])

    def test_malformed_concern_is_a_field_error_not_a_render_crash(self):
        b=self.fixture();n=note(b)
        n['findings']=[{'id':'coordinator-odd','dimension':'token_controls','claim':'state_observation','strength':'direct','signal':'good','text':'Observed.','support':['controls'],'concern':'free text'}]
        save(b,n)
        with self.assertRaisesRegex(ComposeError,'concern must be an object'):compose(b.root,allow_synthetic=True)


if __name__=='__main__':unittest.main()

