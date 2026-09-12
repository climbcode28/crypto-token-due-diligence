"""Provider selection is offline; lack of optional credentials is a workflow handoff."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend_fixtures import CHAIN, FakeRpc, plan
from backend_common import write_new
import rpc_collect
from investigation import Investigation

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class OptionalRpcTests(unittest.TestCase):
    def args(self, **changes):
        values = dict(allow_network=True, cost_policy="paid", allow_paid=True,
                      rpc_url_env="CRYPTO_RPC_URL", provider="drpc", auth_env=None,
                      auth_header="Authorization")
        values.update(changes)
        return argparse.Namespace(**values)

    def check(self, args=None, env=None):
        with patch.dict(os.environ, env or {}, clear=True), \
             patch.object(rpc_collect.HttpTransport, "__init__", side_effect=AssertionError("no client during selection")):
            return rpc_collect.provider_availability(args or self.args())

    def test_missing_drpc_key_hands_back_to_standard_flow(self):
        result = self.check(env={"CRYPTO_RPC_URL": "https://lb.drpc.org/?network=robinhood-mainnet"})
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["reason"], "drpc_key_missing")
        self.assertEqual(result["next_action"], "continue_standard_flow")
        self.assertEqual(result["network_requests"], 0)

    def test_blank_drpc_key_is_absent_even_with_generic_provider_alias(self):
        result = self.check(self.args(provider="generic"),
                            {"CRYPTO_RPC_URL": "https://lb.drpc.live./robinhood-mainnet", "DRPC_API_KEY": "  \n"})
        self.assertEqual(result["reason"], "drpc_key_missing")

    def test_key_alone_does_not_authorize_paid_use(self):
        result = self.check(self.args(allow_paid=False),
                            {"CRYPTO_RPC_URL": "https://lb.drpc.org/robinhood-mainnet", "DRPC_API_KEY": "TEST-SECRET"})
        self.assertEqual(result["status"], "invocation_required")
        self.assertEqual(result["reason"], "paid_usage_not_authorized")
        self.assertEqual(result["next_action"], "review_invocation_context")

    def test_drpc_labeled_free_does_not_bypass_paid_gate(self):
        result = self.check(self.args(cost_policy="free"),
                            {"CRYPTO_RPC_URL": "https://lb.drpc.org/robinhood-mainnet", "DRPC_API_KEY": "TEST-SECRET"})
        self.assertEqual(result["status"], "invocation_required")

    def test_configured_no_flags_requires_context_review_not_provider_fallback(self):
        result = self.check(self.args(allow_network=False, cost_policy=None, allow_paid=False),
                            {"CRYPTO_RPC_URL": "https://lb.drpc.live/robinhood-mainnet", "DRPC_API_KEY": "TEST-SECRET"})
        self.assertEqual(result["status"], "invocation_required")
        self.assertEqual(result["reason_category"], "invocation")
        self.assertEqual(result["next_action"], "review_invocation_context")
        self.assertEqual(result["blocking_reasons"],
                         ["network_disabled", "cost_policy_undeclared", "paid_usage_not_authorized"])
        self.assertFalse(result["provider_tested"])
        self.assertEqual(result["network_requests"], 0)

    def test_malformed_endpoint_is_configuration_gap_even_without_flags(self):
        result = self.check(self.args(allow_network=False, cost_policy=None, allow_paid=False),
                            {"CRYPTO_RPC_URL": "https://lb.drpc.live/?network=x&dkey=TEST-SECRET", "DRPC_API_KEY": "TEST-SECRET"})
        self.assertEqual(result["reason"], "rpc_configuration_invalid")
        self.assertEqual(result["reason_category"], "configuration")
        self.assertEqual(result["next_action"], "continue_standard_flow")
        self.assertFalse(result["provider_tested"])
        self.assertNotIn("TEST-SECRET", json.dumps(result))

    def test_omitted_flags_do_not_construct_transport_or_create_collection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pp = root/"plan.json"; write_new(pp, plan())
            argv = ["rpc_collect.py", str(pp), "--out", str(root/"collection"),
                    "--cache", str(root/"cache.sqlite"), "--provider", "drpc"]
            stdout = io.StringIO()
            with patch.dict(os.environ, {"CRYPTO_RPC_URL": "https://lb.drpc.live/robinhood-mainnet",
                                         "DRPC_API_KEY": "TEST-SECRET"}, clear=True), \
                 patch.object(sys, "argv", argv), \
                 patch.object(rpc_collect, "configured_transport", side_effect=AssertionError("no transport")), \
                 redirect_stdout(stdout):
                self.assertEqual(rpc_collect.main(), 3)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "invocation_required")
            self.assertEqual(list(root.iterdir()), [pp])

    def test_sourced_flags_reach_bounded_collection_and_verify_pin(self):
        # Synthetic chain 31337 and invented runtime; never real BOW evidence.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pp = root/"plan.json"
            sample = plan()
            sample["pins"] = sample["pins"][:1]
            pid = sample["pins"][0]["id"]
            sample["queries"] = [{"id": "runtime", "pin_id": pid, "method": "eth_getCode",
                                  "params": [sample["target"]["address"]]}]
            write_new(pp, sample)
            argv = ["rpc_collect.py", str(pp), "--out", str(root/"collection"),
                    "--cache", str(root/"cache.sqlite"), "--provider", "drpc",
                    "--allow-network", "--cost-policy", "paid", "--allow-paid", "--max-requests", "4"]
            Investigation.create(root / "session.sqlite", 100, 120).close()
            argv.extend(["--session", str(root / "session.sqlite")])
            stdout = io.StringIO()
            with patch.dict(os.environ, {"CRYPTO_RPC_URL": "https://lb.drpc.live/robinhood-mainnet",
                                         "DRPC_API_KEY": "TEST-SECRET"}, clear=True), \
                 patch.object(sys, "argv", argv), \
                 patch.object(rpc_collect, "configured_transport", return_value=FakeRpc()) as transport, \
                 redirect_stdout(stdout):
                self.assertEqual(rpc_collect.main(), 0)
            transport.assert_called_once()
            self.assertEqual(json.loads(stdout.getvalue())["network_attempts"], 4)
            saved = json.loads((root/"collection/collection.json").read_text())
            self.assertEqual(saved["status"], "complete")
            self.assertTrue(saved["pins"])

    def test_fresh_shell_must_source_exports_with_each_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private = root/"env"
            private.write_text("export CRYPTO_RPC_URL='https://lb.drpc.live/robinhood-mainnet'\n"
                               "export DRPC_API_KEY='SYNTHETIC-SECRET'\n")
            prefix = 'set +x\nsource "$1" >/dev/null 2>&1 || exit 2\nshift\nexec "$@"\n'
            command = [sys.executable, str(SCRIPTS/"rpc_collect.py"), "--check-availability", "--provider", "drpc"]
            flags = ["--allow-network", "--cost-policy", "paid", "--allow-paid"]
            for extra, expected in [([], "invocation_required"), (flags, "ready")]:
                result = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-c", prefix,
                                         "check", str(private), *command, *extra], cwd=root,
                                        env={"PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], expected)
                self.assertNotIn("SYNTHETIC-SECRET", result.stdout + result.stderr)
                self.assertNotIn("https://", result.stdout + result.stderr)
            # A subsequent tool shell does not inherit the preceding source command.
            result = subprocess.run(command + flags, env={"PYTHONDONTWRITEBYTECODE": "1"},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)["reason"], "drpc_key_missing")
            self.assertEqual(list(root.iterdir()), [private])

    def test_no_endpoint_needs_no_account_setup(self):
        result = self.check(self.args(provider="generic", cost_policy="free"))
        self.assertEqual(result["reason"], "rpc_endpoint_unconfigured")
        self.assertEqual(result["next_action"], "continue_standard_flow")

    def test_free_generic_provider_works_without_drpc_key(self):
        result = self.check(self.args(provider="generic", cost_policy="free", allow_paid=False),
                            {"CRYPTO_RPC_URL": "https://public-rpc.example.invalid/"})
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["next_action"], "run_collector")

    def test_missing_generic_auth_hands_back_to_standard_flow(self):
        result = self.check(self.args(provider="generic", cost_policy="free", auth_env="CUSTOM_AUTH"),
                            {"CRYPTO_RPC_URL": "https://example.invalid/"})
        self.assertEqual(result["reason"], "rpc_authentication_missing")

    def test_network_disabled_or_cost_undeclared_stays_offline(self):
        for args, reason in [(self.args(provider="generic", cost_policy="free", allow_network=False), "network_disabled"),
                             (self.args(provider="generic", cost_policy=None), "cost_policy_undeclared")]:
            with self.subTest(reason=reason):
                self.assertEqual(self.check(args, {"CRYPTO_RPC_URL": "https://example.invalid/"})["reason"], reason)

    def test_ready_drpc_check_neither_contacts_provider_nor_prints_secrets(self):
        result = self.check(env={"CRYPTO_RPC_URL": "https://lb.drpc.org/robinhood-mainnet", "DRPC_API_KEY": "TEST-SECRET"})
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["network_requests"], 0)
        self.assertNotIn("TEST-SECRET", json.dumps(result))
        self.assertNotIn("https://", json.dumps(result))

    def test_invalid_configuration_reports_category_without_credentials(self):
        result = self.check(env={"CRYPTO_RPC_URL": "https://lb.drpc.org/?network=ethereum&dkey=TEST-SECRET", "DRPC_API_KEY": "TEST-SECRET"})
        self.assertEqual(result["reason"], "rpc_configuration_invalid")
        self.assertNotIn("TEST-SECRET", json.dumps(result))

    def test_default_generic_alias_detects_drpc_and_sends_key_only_as_header(self):
        args = self.args(provider="generic")
        env = {"CRYPTO_RPC_URL": "https://lb.drpc.live/robinhood-mainnet", "DRPC_API_KEY": "TEST-SECRET"}
        self.assertEqual(self.check(args, env)["status"], "ready")
        with patch.dict(os.environ, env, clear=True):
            url, headers = rpc_collect.transport_settings(args)
        self.assertEqual(url, env["CRYPTO_RPC_URL"])
        self.assertEqual(headers, {"Drpc-Key": "TEST-SECRET"})

    def test_malformed_port_and_header_credentials_fail_offline(self):
        for url, key in [("https://lb.drpc.live:bad/robinhood-mainnet", "TEST-SECRET"),
                         ("https://lb.drpc.live:70000/robinhood-mainnet", "TEST-SECRET"),
                         ("https://lb.drpc.live/robinhood-mainnet", "TEST-SECRET\nInjected: value")]:
            with self.subTest(url=url):
                result = self.check(env={"CRYPTO_RPC_URL": url, "DRPC_API_KEY": key})
                self.assertEqual(result["reason"], "rpc_configuration_invalid")
                self.assertEqual(result["network_requests"], 0)
                self.assertNotIn("TEST-SECRET", json.dumps(result))

    def test_budget_stop_does_not_request_an_alternate_provider(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pp = root / "plan.json"
            write_new(pp, plan())
            argv = ["rpc_collect.py", str(pp), "--out", str(root / "collection"),
                    "--cache", str(root / "cache.sqlite"), "--allow-network", "--cost-policy", "free",
                    "--max-requests", "6"]
            Investigation.create(root / "session.sqlite", 100, 120).close()
            argv.extend(["--session", str(root / "session.sqlite")])
            stdout = io.StringIO()
            with patch.dict(os.environ, {"CRYPTO_RPC_URL": "https://example.invalid/"}, clear=True), \
                 patch.object(sys, "argv", argv), patch.object(rpc_collect, "configured_transport", return_value=FakeRpc()), \
                 redirect_stdout(stdout):
                self.assertEqual(rpc_collect.main(), 2)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["limit_reached"], "request_budget")
            self.assertEqual(result["next_action"], "review_evidence")

    def test_cli_preflight_requires_no_plan_output_cache_or_network(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run([sys.executable, str(SCRIPTS/"rpc_collect.py"), "--check-availability", "--provider", "drpc"],
                                    cwd=td, env={"PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["next_action"], "continue_standard_flow")
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_cli_missing_key_returns_distinct_handoff_without_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pp = root/"plan.json"; write_new(pp, plan())
            result = subprocess.run([sys.executable, str(SCRIPTS/"rpc_collect.py"), str(pp), "--out", str(root/"collection"),
                                     "--cache", str(root/"cache.sqlite"), "--provider", "drpc", "--allow-network",
                                     "--cost-policy", "paid", "--allow-paid"],
                                    env={"CRYPTO_RPC_URL": "https://lb.drpc.org/robinhood-mainnet", "PYTHONDONTWRITEBYTECODE": "1"},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "fallback")
            self.assertEqual(result.stderr, "")
            self.assertFalse((root/"collection").exists())
            self.assertFalse((root/"cache.sqlite").exists())

    def test_invalid_plan_is_still_an_error_not_a_provider_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pp = root/"plan.json"; write_new(pp, {"schema_version": 999})
            result = subprocess.run([sys.executable, str(SCRIPTS/"rpc_collect.py"), str(pp), "--out", str(root/"collection"),
                                     "--cache", str(root/"cache.sqlite")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def test_provider_failure_handoff_preserves_partial_or_invalid_packet(self):
        for expected in ("partial", "invalid"):
            with self.subTest(status=expected), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                pp = root/"plan.json"; write_new(pp, plan())
                fake = FakeRpc()
                if expected == "partial":
                    fake.overrides["eth_call"] = lambda r: {"error": {"code": -32000, "message": "unavailable"}}
                else:
                    fake.overrides["eth_chainId"] = lambda r: hex(CHAIN+1)
                argv = ["rpc_collect.py", str(pp), "--out", str(root/"collection"),
                        "--cache", str(root/"cache.sqlite"), "--allow-network", "--cost-policy", "free"]
                Investigation.create(root / "session.sqlite", 100, 120).close()
                argv.extend(["--session", str(root / "session.sqlite")])
                stdout = io.StringIO()
                with patch.dict(os.environ, {"CRYPTO_RPC_URL": "https://example.invalid/"}, clear=True), \
                     patch.object(sys, "argv", argv), patch.object(rpc_collect, "configured_transport", return_value=fake), \
                     redirect_stdout(stdout):
                    self.assertEqual(rpc_collect.main(), 2)
                report = json.loads(stdout.getvalue())
                self.assertEqual(report["status"], expected)
                self.assertEqual(report["next_action"], "continue_standard_flow")
                saved = json.loads((root/"collection/collection.json").read_text())
                self.assertEqual(saved["status"], expected)
                self.assertTrue(saved["coverage_gaps"])


if __name__ == "__main__":
    unittest.main()
