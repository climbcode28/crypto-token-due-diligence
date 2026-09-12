"""Portable local guidance, command and registration consistency checks."""
from pathlib import Path
import sys,unittest,re,json,subprocess,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from solana_operations import active
S=Path(__file__).resolve().parents[1]
REPO=S.parents[1]


class GuidanceTests(unittest.TestCase):
    def test_utf8_frontmatter_and_local_markdown_links(self):
        skill=(S/'SKILL.md').read_text(encoding='utf-8');self.assertTrue(skill.startswith('---\nname: crypto-solana-token-due-diligence\n'))
        self.assertLessEqual(len(skill.splitlines()),220)
        paths=[S/'SKILL.md',S/'memories.md',*sorted((S/'references').glob('*.md')),*sorted((S/'assets').glob('*.md'))]
        missing=[]
        for path in paths:
            text=path.read_text(encoding='utf-8')
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
                if re.match(r'^[a-z]+:',target) or target.startswith('#'):continue
                dest=target.split('#')[0]
                if dest and not (path.parent/dest).exists():missing.append((str(path.relative_to(S)),dest))
        self.assertEqual(missing,[])

    def test_common_commands_have_matching_help_and_no_install_requirement(self):
        for name in ('solana_broad_collect.py','solana_bundle.py','solana_facts.py','solana_maintain.py'):
            result=subprocess.run([sys.executable,'-B',str(S/'scripts'/name),'--help'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            if name=='solana_bundle.py':
                for action in ('finalize','checkpoint','verify','read','replay','--trust-frozen-code'):self.assertIn(action,result.stdout)
        skill=(S/'SKILL.md').read_text();runbook=(S/'references/runbook.md').read_text()
        for phrase in ('120','64 MiB','receipt +420','deadline −120','at most two','public','checkpoint'):
            self.assertIn(phrase,skill)
        self.assertIn('--cost-policy free',runbook);self.assertIn('solana-evidence-v2',runbook)
        self.assertNotIn('optional transport comes from the EVM sibling',skill)
        self.assertEqual(active(S/'assets/operational-lessons.json'),[])

    def test_provider_policy_and_registrations_unchanged(self):
        # Pinned 2026-09-11 to the generic, credential-free policy section; personal standing
        # authorizations moved to the untracked HANDOFF.local.md, which provider_context prefers.
        policy=(REPO/'HANDOFF.md').read_bytes().split(b'## Project and research operation')[0]
        self.assertEqual(hashlib.sha256(policy).hexdigest(),'f278e8c8a594abb129a1fc340ea0b09a1fd8622146b87c46c35c40a00e4ce346')
        link=REPO/'.agents/skills/crypto-evm-token-due-diligence';self.assertTrue(link.is_symlink());self.assertEqual(link.resolve(),REPO/'skills/crypto-evm-token-due-diligence')
        self.assertNotIn('four folders under', (REPO/'HANDOFF.md').read_text())
        for name in ('crypto-token-due-diligence','crypto-solana-token-due-diligence'):
            personal=Path.home()/'.codex/skills'/name
            if personal.exists():self.assertTrue(personal.is_symlink());self.assertEqual(personal.resolve(),REPO/'skills'/name)

    def test_lane_briefs_preserve_owned_commands_and_absolute_cutoff(self):
        for owner in ('liquidity','project'):
            text=(S/'assets'/('lane-brief-'+owner+'.md')).read_text();self.assertLess(len(text.split()),2000)
            for term in ('cutoff','credentials','spawn agents','lane-check','notes/'+owner+'.json','evidence','original'):
                self.assertIn(term,text)
        release=json.loads((S/'assets/release.json').read_text());self.assertEqual(release['operations_version'],'1.0.0')
        from solana_common import ENGINE_VERSION
        self.assertEqual(release['engine_version'],ENGINE_VERSION);self.assertEqual(release['engine_version'],'1.0.0')
        self.assertIn(release['v2_workflow_version'],(REPO/'README.md').read_text())

if __name__=='__main__':unittest.main()
