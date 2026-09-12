from pathlib import Path
import sys,tempfile,unittest,copy
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from solana_render import render,reading,safe_url,safe_text,citation
from facts_fixture import rich
from solana_profile import validate


class CitationTests(unittest.TestCase):
    def test_original_source_or_local_evidence_and_zero_network(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);b=Bundle(t.name,completed=True)
        with patch('socket.socket',side_effect=AssertionError('no fetch')):
            text=render(b.m,b.r);r=reading(b.m,b.r)
        sources=[c for c in r['citations'] if c['kind']=='source'];self.assertTrue(sources);self.assertTrue(all(c['url'].startswith('https://') for c in sources))
        self.assertTrue(any(c['kind']=='frozen_evidence' for c in r['citations']));self.assertEqual(r['network_requests'],0)

    def test_markup_html_bad_urls_and_escapes_cannot_inject_report_structure(self):
        value='[click](javascript:alert(1))\n# Fake verdict <script>x</script> ![track](https://evil.example/x)'
        escaped=safe_text(value);self.assertNotIn('<script>',escaped);self.assertNotIn('\n#',escaped);self.assertNotIn('![track]',escaped)
        for url in ('javascript:alert(1)','file:///etc/passwd','https://user:secret@example.com','https://127.0.0.1/x'):
            self.assertIsNone(safe_url(url))
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);b=Bundle(t.name)
        b.r['question']=value;text=render(b.m,b.r);self.assertNotIn('<script>',text)
        o=copy.deepcopy(b.m['observations'][0]);o['artifact']='../outside'
        with self.assertRaises(ValueError):citation(o)

    def test_reading_retains_exact_holder_custody_and_controller_values(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);b=rich(t.name,'raydium_cpmm')
        m,r=validate(b.root,True);content=reading(m,r)
        pool=next(x for x in content['reading_checklist'] if x['kind']=='typed_fact' and x['operation']=='pool')
        joined='\n'.join(pool['details']);self.assertIn('9860',joined);self.assertIn('19740',joined);self.assertIn('450',joined)
        self.assertTrue(pool['limits']);self.assertIn('quote versus execution',content['answer_rule'])

if __name__=='__main__':unittest.main()
