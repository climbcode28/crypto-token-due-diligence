"""Offline transport boundaries; no real endpoints are contacted."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import solana_transport as transport
from solana_collect import parser
from solana_session import Session

TARGET = {"family": "solana", "genesis_hash": "1"*32, "mint": "1"*32}
REQUEST = {"jsonrpc": "2.0", "id": "genesis", "method": "getGenesisHash", "params": []}


class Body(io.BytesIO):
    status = 200

    def read1(self, size):
        return self.read(size)


class Opener:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def open(self, request, timeout=None):
        self.calls += 1
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result if hasattr(result, "read1") else Body(result)


class TransportTests(unittest.TestCase):
    def rpc(self, *responses, **options):
        rpc = transport.HttpTransport("https://public.invalid/rpc", options.pop("headers", {}), **options)
        rpc.opener = Opener(*responses)
        return rpc

    def session(self, **options):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        args = dict(question="q", received_at=time.time(), deadline_at=time.time()+600,
                    reservations={}, max_requests=4, synthetic=True)
        args.update(options)
        session = Session.create(Path(temporary.name)/"run", TARGET, **args)
        self.addCleanup(session.close)
        return session

    def test_preflight_is_zero_request_without_files_or_credentials(self):
        args = parser().parse_args(["--allow-network", "--cost-policy", "free"])
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com"}, clear=True), patch("solana_transport.urllib.request.build_opener") as opener:
            before = list(Path(temporary).iterdir())
            result = transport.provider_availability(args)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["network_requests"], 0)
            self.assertFalse(result["provider_tested"])
            self.assertEqual(before, list(Path(temporary).iterdir()))
            opener.assert_not_called()
        args.allow_network = False
        with patch.dict(os.environ, {"SOLANA_RPC_URL": "https://public.invalid"}, clear=True):
            self.assertEqual(transport.provider_availability(args)["status"], "invocation_required")
            with self.assertRaises(ValueError):
                transport.transport_settings(args)

    def test_invalid_settings_and_paid_drpc_never_infer_authorization(self):
        args = parser().parse_args(["--allow-network", "--cost-policy", "free"])
        for url in ("http://public.invalid", "https://user:secret@public.invalid", "https://public.invalid/#secret", "https://public.invalid:99999", "https://public.invalid/\nsecret"):
            with self.subTest(url=url), patch.dict(os.environ, {"SOLANA_RPC_URL": url}, clear=True):
                result = transport.provider_availability(args)
                self.assertEqual(result["status"], "fallback")
                self.assertNotIn("secret", json.dumps(result))
        with patch.dict(os.environ, {"SOLANA_RPC_URL": "https://lb.drpc.live/solana", "DRPC_API_KEY": "secret-key"}, clear=True):
            result = transport.provider_availability(args)
            self.assertEqual(result["reason"], "free_policy_selects_paid_endpoint")  # the explicit free policy, not a missing consent, blocks
            self.assertNotIn("secret-key", json.dumps(result))
            args.cost_policy = None
            result = transport.provider_availability(args)
            self.assertEqual(result["status"], "ready")  # the configured key is the standing authorization
            self.assertNotIn("secret-key", json.dumps(result))

    def test_secret_echoes_are_redacted_before_durable_storage(self):
        rpc = self.rpc(b'{"result":"secret-value", "secret-value":"Bearer secret-value"}', headers={"Authorization": "Bearer secret-value"})
        session = self.session()
        packet = transport.session_request(session, rpc, REQUEST)
        self.assertEqual(packet["status"], "redacted")
        self.assertNotIn("secret-value", json.dumps(packet))
        self.assertNotIn(b"secret-value", (session.root/"session.sqlite").read_bytes())

    def test_zero_grants_and_exhausted_batches_send_nothing(self):
        rpc = self.rpc(b'{}')
        session = self.session(reservations={"liquidity": 0}, max_requests=0)
        for i in range(2):
            packet = transport.session_request(session, rpc, {**REQUEST, "id": str(i)}, owner="liquidity")
            self.assertEqual(packet["status"], "budget_denied")
        self.assertEqual(rpc.opener.calls, 0)

    def test_retry_is_one_more_attempt_and_keeps_final_reservation(self):
        error = urllib.error.HTTPError("https://secret.invalid", 429, "secret-error", {}, io.BytesIO())
        rpc = self.rpc(error, b'{"ok":true}', b'{}')
        session = self.session(max_requests=3, reservations={"final": 1})
        first = transport.session_request(session, rpc, REQUEST)
        self.assertEqual(first["status"], "http_429")
        retry = transport.session_request(session, rpc, {**REQUEST, "id": "retry"}, retry=True)
        self.assertEqual(retry["status"], "ok")
        denied = transport.session_request(session, rpc, {**REQUEST, "id": "third"}, retry=True)
        self.assertEqual(denied["status"], "budget_denied")
        final = transport.session_request(session, rpc, {**REQUEST, "id": "final"}, family="fresh-recheck", owner="final")
        self.assertEqual(final["status"], "ok")
        self.assertEqual(session.status()["started_attempts"], rpc.opener.calls)
        self.assertEqual(rpc.opener.calls, 3)

    def test_redirect_is_refused_without_forwarding_auth_or_second_send(self):
        self.assertIsNone(transport.NoRedirect().redirect_request(None, None, 302, "m", {}, "https://other.invalid"))
        redirect = urllib.error.HTTPError("https://public.invalid", 302, "redirect", {"Location": "https://secret.invalid"}, io.BytesIO())
        rpc = self.rpc(redirect, headers={"Authorization": "secret-value"})
        session = self.session()
        self.assertEqual(transport.session_request(session, rpc, REQUEST)["status"], "http_302")
        self.assertEqual(rpc.opener.calls, 1)
        self.assertNotIn("secret.invalid", json.dumps(session.observations()))

    def test_late_body_is_rejected_but_bytes_are_accounted(self):
        clock = [0.0]

        class LateBody(Body):
            def read1(self, size):
                result = super().read1(size)
                clock[0] = 0.5 if result else 1.1
                return result

        rpc = self.rpc(LateBody(b'{}'), timeout=1)
        with patch("solana_transport.time.monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                rpc(REQUEST)
        self.assertEqual(rpc.local.response_bytes, 2)

    def test_response_ceiling_never_reads_unreserved_overflow_byte(self):
        rpc = self.rpc(b'x'*100, max_bytes=10)
        session = self.session(max_bytes=10)
        result = transport.session_request(session, rpc, REQUEST)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(session.status()["response_bytes"], 10)

    def test_duplicate_keys_and_nonfinite_json_are_invalid(self):
        for raw in (b'{"result":1,"result":2}', b'{"result":NaN}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.rpc(raw)(REQUEST)

    def test_unsafe_method_is_refused_before_acquisition(self):
        rpc = self.rpc(b'{}')
        session = self.session()
        for method in ("sendTransaction", "requestAirdrop", "simulateTransaction"):
            with self.assertRaises(ValueError):
                transport.session_request(session, rpc, {**REQUEST, "method": method})
        self.assertEqual(session.status()["started_attempts"], 0)
        self.assertEqual(rpc.opener.calls, 0)

    def test_collector_uses_same_session_and_keeps_recheck_grants(self):
        import solana_collect as collect
        from test_solana import FakeTransport, TARGET as fixture_target
        session = self.session(max_requests=9, reservations={"final": 4})
        # Create a separate session with the nonzero synthetic mint fixture identity.
        root = session.root.parent / "fixture-session"
        shared = Session.create(root, fixture_target, question="q", received_at=time.time(),
            deadline_at=time.time()+600, max_requests=9, reservations={"final": 4}, synthetic=True)
        self.addCleanup(shared.close)
        calls = []

        class SyntheticHttp(transport.HttpTransport):
            synthetic = True

            def __call__(self, request):
                calls.append(request)
                result = FakeTransport("normal", {})(request)
                self.local.response_bytes = len(json.dumps(result).encode())
                return result

        packet = session.root.parent / "packet"
        for name in ("attempts", "evidence"):
            (packet/name).mkdir(parents=True)
        config = {"url": "https://public.invalid", "headers": {}, "session": str(root)}
        collect.worker(packet, config, fixture_target, True, 9, SyntheticHttp)
        self.assertEqual(len(calls), 9)
        self.assertEqual(shared.status()["started_attempts"], 9)
        self.assertEqual(shared.status()["reserved_requests"], 0)
        self.assertTrue(collect.summarize(packet, fixture_target, True)["sample_consistent"])
        self.assertTrue(all(row["response"] for row in shared.observations()))




class FailureCategoryTests(unittest.TestCase):
    def test_failure_category_is_coarse_and_url_free(self):
        import errno, http.client, socket, ssl, urllib.error
        from solana_transport import failure_category
        self.assertEqual(failure_category(PermissionError(errno.EPERM, "Operation not permitted")), "not_permitted")
        self.assertEqual(failure_category(urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided"))), "dns")
        self.assertEqual(failure_category(urllib.error.URLError("no host given")), "url_error")
        self.assertEqual(failure_category(ConnectionRefusedError(61, "Connection refused")), "connection_refused")
        self.assertEqual(failure_category(ConnectionResetError(54, "reset")), "connection_reset")
        self.assertEqual(failure_category(TimeoutError()), "timeout")
        self.assertEqual(failure_category(ssl.SSLError(1, "handshake")), "tls")
        self.assertEqual(failure_category(OSError(errno.ENETUNREACH, "unreachable")), "unreachable")
        self.assertEqual(failure_category(http.client.BadStatusLine("x")), "http_protocol")
        self.assertEqual(failure_category(OSError(99, "something else")), "other")
        for category in ("not_permitted", "dns", "url_error", "connection_refused", "tls", "other"):
            self.assertNotIn("http", category.split("_")[0])  # categories name causes, never hosts or URLs


if __name__ == "__main__":
    unittest.main()
