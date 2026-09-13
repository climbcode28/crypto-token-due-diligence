"""Fresh-chat discovery uses paths, never credentials or inferred approval."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class ProviderContextTests(unittest.TestCase):
    def test_linked_install_finds_checkout_context_from_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            checkout = root / "checkout"
            scripts = checkout / "skills/crypto-evm-token-due-diligence/scripts"
            scripts.mkdir(parents=True)
            (checkout / "AGENTS.md").write_text("read docs/provider-setup.md before provider selection")
            (checkout / "docs").mkdir()
            (checkout / "docs/provider-setup.md").write_text("PERSONAL_AUTHORIZATION_NOT_FOR_OUTPUT")
            (scripts / "provider_context.py").write_bytes((SCRIPTS / "provider_context.py").read_bytes())
            installed = root / "installed-skill"
            installed.symlink_to(scripts.parent, target_is_directory=True)
            workspace = root / "workspace"
            nested = workspace / "research/token"
            nested.mkdir(parents=True)
            (workspace / "AGENTS.md").write_text("current task constraints")
            (workspace / "README.md").write_text("local setup instructions")
            result = subprocess.run([sys.executable, str(installed / "scripts/provider_context.py")],
                                    cwd=nested, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            self.assertEqual(data["context_files"], [str(workspace / "AGENTS.md"), str(workspace / "README.md"),
                                                    str(checkout / "AGENTS.md"), str(checkout / "docs/provider-setup.md")])
            self.assertEqual(data["network_requests"], 0)
            self.assertNotIn("PERSONAL_AUTHORIZATION", result.stdout)

    def test_project_claude_skills_layout_finds_checkout_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            checkout = root / "checkout"
            scripts = checkout / ".claude/skills/crypto-evm-token-due-diligence/scripts"
            scripts.mkdir(parents=True)
            (checkout / "AGENTS.md").write_text("read docs/provider-setup.md before provider selection")
            (checkout / "docs").mkdir()
            (checkout / "docs/provider-setup.md").write_text("PERSONAL_AUTHORIZATION_NOT_FOR_OUTPUT")
            (scripts / "provider_context.py").write_bytes((SCRIPTS / "provider_context.py").read_bytes())
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            result = subprocess.run([sys.executable, str(scripts / "provider_context.py")],
                                    cwd=elsewhere, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            self.assertEqual(data["context_files"], [str(checkout / "AGENTS.md"), str(checkout / "docs/provider-setup.md")])
            self.assertEqual(data["network_requests"], 0)
            self.assertNotIn("PERSONAL_AUTHORIZATION", result.stdout)
            # Running from inside the checkout lists each file once.
            result = subprocess.run([sys.executable, str(scripts / "provider_context.py")],
                                    cwd=checkout, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)["context_files"],
                             [str(checkout / "AGENTS.md"), str(checkout / "docs/provider-setup.md")])

    def test_personal_local_handoff_overrides_the_tracked_policy(self):
        with tempfile.TemporaryDirectory() as td:
            checkout = Path(td).resolve() / "checkout"
            scripts = checkout / "skills/crypto-evm-token-due-diligence/scripts"
            scripts.mkdir(parents=True)
            (checkout / "AGENTS.md").write_text("read docs/provider-setup.md before provider selection")
            (checkout / "docs").mkdir()
            (checkout / "docs/provider-setup.md").write_text("# Handoff\n\n## Current provider policy\n\nGENERIC_PUBLIC_POLICY\n\n## Later\n\nother\n")
            (scripts / "provider_context.py").write_bytes((SCRIPTS / "provider_context.py").read_bytes())
            result = subprocess.run([sys.executable, str(scripts / "provider_context.py"), "--policy"], cwd=checkout, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout.splitlines()[0])["policy_source"], str(checkout / "docs/provider-setup.md"))
            self.assertIn("GENERIC_PUBLIC_POLICY", result.stdout)
            self.assertIn("trusted docs/provider-setup.md", result.stdout)
            self.assertNotIn("HANDOFF.local.md", json.loads(result.stdout.splitlines()[0])["context_files"].__str__())
            (checkout / "HANDOFF.local.md").write_text("# Personal\n\n## Standing authorization\n\nPERSONAL_STANDING_AUTHORIZATION\n")
            result = subprocess.run([sys.executable, str(scripts / "provider_context.py"), "--policy"], cwd=checkout, capture_output=True, text=True, check=True)
            first = json.loads(result.stdout.splitlines()[0])
            self.assertEqual(first["policy_source"], str(checkout / "HANDOFF.local.md"))
            self.assertIn(str(checkout / "HANDOFF.local.md"), first["context_files"])
            self.assertIn("PERSONAL_STANDING_AUTHORIZATION", result.stdout)
            self.assertNotIn("GENERIC_PUBLIC_POLICY", result.stdout, "the personal section replaces, not appends")
            self.assertIn("personal HANDOFF.local.md", result.stdout)

    def test_standalone_copy_ignores_unrelated_ancestor_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            ancestor = root / "ancestor"
            ancestor.mkdir()
            (ancestor / "AGENTS.md").write_text("unrelated personal instructions")
            scripts = ancestor / "downloads/shared-copy/scripts"
            scripts.mkdir(parents=True)
            (scripts / "provider_context.py").write_bytes((SCRIPTS / "provider_context.py").read_bytes())
            elsewhere = root / "work"
            elsewhere.mkdir()
            result = subprocess.run([sys.executable, str(scripts / "provider_context.py")],
                                    cwd=elsewhere, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)["context_files"], [])

    def test_shared_standalone_copy_requires_no_personal_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            scripts = root / "shared/scripts"
            scripts.mkdir(parents=True)
            (scripts / "provider_context.py").write_bytes((SCRIPTS / "provider_context.py").read_bytes())
            result = subprocess.run([sys.executable, str(scripts / "provider_context.py")],
                                    cwd=root, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)["context_files"], [])


if __name__ == "__main__":
    unittest.main()
