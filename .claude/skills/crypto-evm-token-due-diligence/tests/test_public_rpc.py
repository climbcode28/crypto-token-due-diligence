"""No-config public selection and failure recovery; all transports are synthetic."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import broad_collect
import rpc_collect
from backend_fixtures import TOKEN
from investigation import Investigation


class PublicRpcTests(unittest.TestCase):
    def args(self, **changes):
        values = dict(provider="generic", rpc_url_env="ROBINHOOD_DRPC_URL", chain_id=4663,
                      allow_network=True, cost_policy="free", allow_paid=False,
                      auth_env=None, auth_header="Authorization")
        values.update(changes)
        return argparse.Namespace(**values)

    def test_registered_chains_work_without_configuration_or_environment_mutation(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(rpc_collect, "HttpTransport", side_effect=AssertionError("must remain offline")):
            for chain in (1, 10, 56, 137, 4663, 8453, 42161):
                args = self.args(chain_id=chain)
                result = rpc_collect.provider_availability(args)
                self.assertEqual(result["status"], "ready")
                self.assertEqual(result["network_requests"], 0)
                self.assertFalse(result["provider_tested"])
                url, headers = rpc_collect.transport_settings(args)
                self.assertEqual(url, rpc_collect.PUBLIC_RPC_ENDPOINTS[chain])
                self.assertEqual(headers, {})
            self.assertEqual(dict(os.environ), {})

    def test_unknown_chain_and_missing_custom_export_do_not_choose_another_endpoint(self):
        with patch.dict(os.environ, {}, clear=True):
            for args in (self.args(chain_id=46630), self.args(chain_id=None),
                         self.args(rpc_url_env="EXPLICIT_MISSING"),
                         self.args(provider="public", chain_id=99999)):
                self.assertEqual(rpc_collect.provider_availability(args)["status"], "fallback")
                with self.assertRaises(ValueError):
                    rpc_collect.transport_settings(args)

    def test_configured_paid_route_retains_gate_then_explicit_public_has_no_auth(self):
        env = {"ROBINHOOD_DRPC_URL": "https://lb.drpc.org/robinhood", "DRPC_API_KEY": "SYNTHETIC-KEY"}
        with patch.dict(os.environ, env, clear=True):
            denied = rpc_collect.provider_availability(self.args())  # an explicit free policy cannot relabel the configured dRPC endpoint
            self.assertEqual(denied["status"], "invocation_required")
            self.assertIn("free_policy_selects_paid_endpoint", denied["blocking_reasons"])
            for authorized in (self.args(provider="drpc", cost_policy="paid", allow_paid=True), self.args(cost_policy=None), self.args(provider="auto", cost_policy=None)):
                self.assertEqual(rpc_collect.transport_settings(authorized), (env["ROBINHOOD_DRPC_URL"], {"Drpc-Key": "SYNTHETIC-KEY"}))
            public = self.args(provider="public")
            self.assertEqual(rpc_collect.provider_availability(public)["status"], "ready")
            self.assertEqual(rpc_collect.transport_settings(public),
                             (rpc_collect.PUBLIC_RPC_ENDPOINTS[4663], {}))
            self.assertEqual(dict(os.environ), env)

    def test_public_never_forwards_custom_auth_or_accepts_paid_policy(self):
        with patch.dict(os.environ, {"CUSTOM_AUTH": "SYNTHETIC-KEY"}, clear=True):
            for args in (self.args(auth_env="CUSTOM_AUTH"), self.args(provider="public", auth_env="CUSTOM_AUTH"),
                         self.args(provider="public", cost_policy="paid", allow_paid=True)):
                self.assertNotEqual(rpc_collect.provider_availability(args)["status"], "ready")
                with self.assertRaises(ValueError):
                    rpc_collect.transport_settings(args)

    def test_explicit_configuration_errors_and_omitted_network_flags_are_not_hidden(self):
        with patch.dict(os.environ, {"ROBINHOOD_DRPC_URL": "invalid"}, clear=True):
            self.assertEqual(rpc_collect.provider_availability(self.args())["reason"], "rpc_configuration_invalid")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(rpc_collect.provider_availability(self.args(provider="drpc"))["reason"], "drpc_key_missing")
            args = self.args(allow_network=False)
            self.assertEqual(rpc_collect.provider_availability(args)["status"], "invocation_required")
            with self.assertRaises(ValueError):
                rpc_collect.transport_settings(args)
            self.assertEqual(rpc_collect.provider_availability(self.args(cost_policy=None))["status"], "ready", "a cost policy is optional on the public default")

    def test_cli_start_reaches_public_transport_and_failed_retry_preserves_ledger(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {}, clear=True):
            run = Path(td) / "run"
            argv = ["broad_collect.py", "start", "--run", str(run), "--chain-id", "4663",
                    "--address", TOKEN, "--question", "synthetic unavailable endpoint",
                    "--allow-network", "--cost-policy", "free", "--no-web", "--no-lanes",
                    "--max-requests", "10", "--request-ceiling", "10", "--timeout", "60", "--timeout-ceiling", "60"]
            states = []

            def unavailable(pipeline):
                pipeline.session.acquire("eth_chainId")
                states.append(pipeline.session.status())
                raise broad_collect.StartFailure({"stage": "chain_check", "category": "timeout", "message": "synthetic timeout"})

            with patch.object(sys, "argv", argv), patch.object(rpc_collect, "HttpTransport") as transport, \
                 patch.object(broad_collect.Pipeline, "run_all", unavailable), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(broad_collect.main(), 2)
                self.assertEqual(broad_collect.main(), 2)
            for call in transport.call_args_list:
                self.assertEqual(call.args, (rpc_collect.PUBLIC_RPC_ENDPOINTS[4663], {}))
            self.assertEqual(len(transport.call_args_list), 2)
            self.assertEqual([s["started_attempts"] for s in states], [1, 2])
            for field in ("investigation_id", "request_ceiling", "deadline_ceiling_unix", "deadline_unix"):
                self.assertEqual(states[0][field], states[1][field])
            self.assertEqual(json.loads((run / "start-failed.json").read_text())["status"], "start_failed")
            self.assertFalse((run / "report").exists())
            self.assertFalse((run / "lanes/project/brief.md").exists())

    def test_preset_uses_saved_target_for_public_selection(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {}, clear=True):
            run = Path(td)
            (run / "facts.json").write_text(json.dumps({"target": {"chain_id": 8453, "address": TOKEN}}))
            Investigation.create(run / "session.sqlite", 10, 60).close()
            args = self.args()
            del args.chain_id
            args.run = run
            observed = []

            def selected(config):
                observed.append(rpc_collect.transport_settings(config))
                raise RuntimeError("stop before synthetic preset work")

            with patch.object(broad_collect, "configured_transport", side_effect=selected):
                with self.assertRaisesRegex(RuntimeError, "stop before"):
                    broad_collect.preset_collect(args)
            self.assertEqual(observed, [(rpc_collect.PUBLIC_RPC_ENDPOINTS[8453], {})])


if __name__ == "__main__":
    unittest.main()
