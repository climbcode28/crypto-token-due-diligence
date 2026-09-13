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
        # The Solana path is public-only: it reads no policy file, so only the repository's
        # Solana statements are checked, and an installed copy without the repo skips them.
        handoff=REPO/'HANDOFF.md'
        if not handoff.exists():self.skipTest('installed copy without repository handoff')
        text=handoff.read_text()
        for sentence in ('`SOLANA_RPC_URL` only overrides the public root.','needs no\n  private env for the public tier','can use a personal dRPC','A key\n  alone is not authorization to spend.'):
            self.assertIn(sentence,text)
        self.assertNotIn('four folders under',text)
        self.assertNotIn('custom Solana dRPC is deferred',text)  # the policy now permits it
        link=REPO/'.agents/skills/crypto-evm-token-due-diligence'
        if link.is_symlink():self.assertEqual(link.resolve(),REPO/'skills/crypto-evm-token-due-diligence')
        skill=(S/'SKILL.md').read_text()
        for phrase in ('✅ Good','🟡 Potential Risk','🔴 Bad','⚪ Unverified','**Conclusions**','300–600 words','`SOLANA_RPC_URL`'):
            self.assertIn(phrase,skill)
        for stale in ('HANDOFF.md','source its documented private env','README provider setup'):
            self.assertNotIn(stale,skill)
        runbook=(S/'references/runbook.md').read_text()
        for phrase in ('pool_activity','`holders`','"$S/scripts/','"$RUN/draft"','--received-at','diagnostics'):
            self.assertIn(phrase,runbook)
        self.assertNotIn('skills/crypto-solana-token-due-diligence/scripts',runbook)

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
