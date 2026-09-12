from pathlib import Path
import sys,tempfile,unittest,time,json,copy
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from broad_fixture import RichRpc,Web
from solana_broad_collect import start,capture,lane_check,write_briefs
from solana_facts import encoded
from solana_profile import validate
from solana_session import Session
from solana_compose import compose


class LaneTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name)/'run';target=RichRpc.reset();Web.blocked=False;Web.calls=[]
        start(root,target,question='Check project and exit depth at https://project.example/token',focus=['audit truth'],urls=['https://project.example/token'],
            received_at=time.time()-20,deadline_at=time.time()+580,config={'url':'https://synthetic.invalid','headers':{}},synthetic=True,factory=RichRpc,opener_factory=Web)
        return root

    def test_briefs_preserve_intake_captured_sources_commands_and_owner_limits(self):
        root=self.fixture();before={p:p.read_bytes() for p in (root/'lanes').rglob('brief.md')};pointers=write_briefs(root)
        self.assertEqual(len(pointers),2);self.assertEqual(before,{p:p.read_bytes() for p in before})
        for path,raw in before.items():
            text=raw.decode();self.assertIn('audit truth',text);self.assertIn('https://project.example/token',text);self.assertIn('lane_cutoff',text);self.assertIn('credentials',text);self.assertIn('spawn agents',text);self.assertIn('lane-check',text)

    def test_existing_source_is_reused_without_cross_owner_resend(self):
        root=self.fixture();before=len(Web.calls);result=capture(root,['https://project.example/token'],'liquidity',opener_factory=Web)
        self.assertFalse(result['captures']);self.assertTrue(result['existing_sources']);self.assertEqual(before,len(Web.calls))

    def test_check_is_read_only_and_pending_lane_cannot_complete(self):
        root=self.fixture();before={str(p):p.read_bytes() for p in (root/'draft').rglob('*') if p.is_file()}
        result=lane_check(root,'liquidity',allow_synthetic=True);self.assertTrue(result['valid']);self.assertFalse(result['complete']);self.assertFalse(result['written'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in (root/'draft').rglob('*') if p.is_file()})
        n=json.loads((root/'draft/notes/coordinator.json').read_text());n['research_status']='completed';(root/'draft/notes/coordinator.json').write_bytes(encoded(n))
        with self.assertRaises(ValueError):compose(root/'draft',allow_synthetic=True)

    def test_late_lane_does_not_receive_new_grant_or_cutoff(self):
        root=self.fixture();s=Session(root)
        try:
            before=s.status();cutoff=s.meta['lane_cutoff']
            with patch('solana_session.time.time',return_value=cutoff+1):
                with self.assertRaisesRegex(ValueError,'deadline'):s.acquire('late','late','web','public',owner='project',transport_kind='web')
            self.assertEqual(before['grants'],s.status()['grants'])
        finally:s.close()

    def test_documented_two_lane_note_handoff_composes_honest_partial(self):
        root=self.fixture()
        for owner in ('liquidity','project'):
            path=root/'draft/notes'/(owner+'.json');note=json.loads(path.read_text())
            note['evidence_ids']=['auto-controls'];note['findings']=[{'id':owner+'-scope','dimension':'token_controls',
              'claim':'state_observation','strength':'direct','signal':'unverified','text':'Mint controls were sampled; this lane has unfinished standard work.',
              'support':['auto-controls']}]
            path.write_bytes(encoded(note));result=lane_check(root,owner,allow_synthetic=True)
            self.assertTrue(result['valid']);self.assertFalse(result['complete'])
        result=compose(root/'draft',allow_synthetic=True);validate(root/'draft',True)
        self.assertEqual(result['research_status'],'partial')
        self.assertTrue({'liquidity-scope','project-scope'}<={f['id'] for f in result['report']['findings']})

if __name__=='__main__':unittest.main()
