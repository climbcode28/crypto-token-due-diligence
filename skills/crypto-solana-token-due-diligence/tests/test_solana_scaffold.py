from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from solana_scaffold import scaffold,write
from solana_compose import compose,ComposeError
from compose_fixture import save


class ScaffoldTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);return Bundle(t.name)

    def test_scope_aliases_focus_and_todo_without_optimistic_judgment(self):
        b=self.fixture();n=write(b.root,allow_synthetic=True);self.assertEqual(n['question'],b.r['question']);self.assertEqual(n['urls'],b.m['intake']['urls']);self.assertIn('controls',n['alias_hints']);self.assertIsNone(n['decision'])
        self.assertTrue(all(v['signal'] is None for v in n['signal_assignments'].values()));self.assertTrue(all(not r['closure']['standard_scope_complete'] for r in n['coverage']))
        compose(b.root,allow_synthetic=True)
        with self.assertRaisesRegex(ValueError,'Existing analyst'):write(b.root,allow_synthetic=True)

    def test_placeholders_cannot_complete(self):
        b=self.fixture();n=scaffold(b.root,allow_synthetic=True);n['research_status']='completed';save(b,n)
        with self.assertRaisesRegex(ComposeError,'TODO'):compose(b.root,allow_synthetic=True)

    def test_lane_scaffold_has_all_pending_checks_and_no_judgment(self):
        b=self.fixture()
        for owner in ('liquidity','project'):
            n=scaffold(b.root,owner,True);self.assertTrue(all(v['status']=='pending' for v in n['checklist'].values()));self.assertFalse(n['findings']);self.assertFalse(n['evidence_ids'])

if __name__=='__main__':unittest.main()
