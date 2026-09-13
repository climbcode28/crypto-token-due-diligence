"""Clean link/copy installs, routing and synthetic report delivery; no network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from install_support import export_package, install, test_environment


class FirstInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.package = export_package(cls.root / "package")

    def check_installed(self, mode):
        test_home = self.root / mode
        env = test_environment(test_home)
        install(self.package, test_home, mode)
        install(self.package, test_home, mode)  # Repeat must preserve existing installs.
        self.assertFalse((self.package / "HANDOFF.local.md").exists())
        self.assertFalse((test_home / ".config/crypto-research/env").exists())
        for host, directory in (("Codex", ".agents"), ("Cursor", ".agents"), ("Claude", ".claude")):
            with self.subTest(host=host, mode=mode):
                skills = test_home / directory / "skills"
                for name in ("crypto-token-due-diligence", "crypto-evm-token-due-diligence",
                             "crypto-solana-token-due-diligence", "deep-plan", "implement-review-improve"):
                    self.assertTrue((skills / name / "SKILL.md").is_file())
                    self.assertEqual((skills / name).is_symlink(), mode == "link")
                route = skills / "crypto-token-due-diligence/scripts/route.py"
                request = {"request": "0x39dBED3a2bd333467115dE45665cC57F813C4571 - PONS",
                           "address": "0x39dBED3a2bd333467115dE45665cC57F813C4571", "received_at": time.time()}
                result = subprocess.run([sys.executable, str(route)], input=json.dumps(request),
                                        cwd=test_home, env=env, capture_output=True, text=True, check=True)
                self.assertIn("crypto-evm-token-due-diligence", result.stdout)
                request.update(request="6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx - STONK",
                               address="6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx")
                result = subprocess.run([sys.executable, str(route)], input=json.dumps(request),
                                        cwd=test_home, env=env, capture_output=True, text=True, check=True)
                self.assertIn("crypto-solana-token-due-diligence", result.stdout)
                evm = skills / "crypto-evm-token-due-diligence"
                result = subprocess.run([sys.executable, str(evm / "scripts/provider_context.py"), "--policy"],
                                        cwd=test_home, env=env, capture_output=True, text=True, check=True)
                policy = json.loads(result.stdout.splitlines()[0])
                self.assertFalse(any(Path(p).name == "HANDOFF.local.md" for p in policy["context_files"]))
                self.assertTrue(policy["policy_source"] is None or
                                policy["policy_source"].endswith("docs/provider-setup.md"))
                result = subprocess.run([sys.executable, str(evm / "scripts/rpc_collect.py"),
                                         "--check-availability", "--chain-id", "4663",
                                         "--allow-network", "--cost-policy", "free"],
                                        cwd=test_home, env=env, capture_output=True, text=True, check=True)
                data = json.loads(result.stdout)
                self.assertEqual((data["status"], data["network_requests"], data["provider_tested"]),
                                 ("ready", 0, False))
        return test_home

    def test_clean_link_install_and_uninstall_preserve_unrelated_files(self):
        test_home = self.check_installed("link")
        unrelated = test_home / ".agents/skills/unrelated"
        unrelated.mkdir()
        marker = unrelated / "SKILL.md"
        marker.write_text("user-owned content")
        install(self.package, test_home, "uninstall")
        self.assertEqual(marker.read_text(), "user-owned content")
        self.assertFalse((test_home / ".agents/skills/crypto-evm-token-due-diligence").exists())

    def test_clean_copy_install_can_deliver_synthetic_reports_without_the_checkout(self):
        test_home = self.check_installed("copy")
        hidden = self.root / "package-hidden"
        self.package.rename(hidden)
        try:
            suites = [
                (".agents/skills/crypto-evm-token-due-diligence/tests", "test_broad_collect.BroadCollectTests.test_compose_note_reaches_delivery"),
                (".claude/skills/crypto-evm-token-due-diligence/tests", "test_broad_collect.BroadCollectTests.test_compose_note_reaches_delivery"),
                (".agents/skills/crypto-solana-token-due-diligence/tests", "test_solana_acceptance.AcceptanceTests.test_default_v2_cli_freezes_and_reads_while_legacy_remains_explicit"),
                (".agents/skills/crypto-solana-token-due-diligence/tests", "test_solana_handoff.HandoffTests.test_public_recovery_ignores_unused_paid_configuration_without_sends"),
            ]
            for directory, case in suites:
                with self.subTest(case=case, directory=directory):
                    result = subprocess.run([sys.executable, "-m", "unittest", case, "-q"],
                                            cwd=test_home / directory, env=test_environment(test_home),
                                            capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            hidden.rename(self.package)


if __name__ == "__main__":
    unittest.main()
