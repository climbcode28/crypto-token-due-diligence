"""Public-provider limits: per-method backoff, refused methods, waits and stranded attempts."""
import http.client
import io
import json
from pathlib import Path
import sys
import tempfile
import time as real_time
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import solana_collect_v2 as collect_v2
import solana_session
import solana_transport as transport
from solana_collect_v2 import execute
from solana_presets import read
from solana_session import Session, LimitError
from solana_fixture import Rpc, TARGET, KEY, GENESIS
from test_solana_transport import Opener

GENESIS_REQUEST = {"jsonrpc": "2.0", "id": "g", "method": "getGenesisHash", "params": []}
LARGEST_REQUEST = {"jsonrpc": "2.0", "id": "l", "method": "getTokenLargestAccounts", "params": [KEY, {"commitment": "finalized"}]}


def http_error(code, headers):
    return urllib.error.HTTPError("https://public.invalid", code, "limited", headers, io.BytesIO(b""))


class Limited(Rpc):
    """Synthetic provider that refuses the first largest-accounts call with a stated wait."""
    failures = 1
    wait = "1"

    def __call__(self, req):
        cls = type(self)
        if req["method"] == "getTokenLargestAccounts" and cls.failures:
            cls.failures -= 1
            raise http_error(429, {"Retry-After": cls.wait})
        return super().__call__(req)


class PublicLimitTests(unittest.TestCase):
    def setUp(self):
        Rpc.calls, Rpc.active, Rpc.peak, Rpc.mode, Rpc.delay = [], 0, 0, "normal", 0
        Limited.failures = 1
        Limited.wait = "1"

    def session(self, **options):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        args = dict(question="q", received_at=real_time.time()-1, deadline_at=real_time.time()+600,
                    reservations={}, max_requests=40, synthetic=True)
        args.update(options)
        session = Session.create(Path(temporary.name)/"run", TARGET, **args)
        self.addCleanup(session.close)
        return session

    def rpc(self, *responses):
        rpc = transport.HttpTransport("https://public.invalid/rpc", {})
        rpc.opener = Opener(*responses)
        return rpc

    def test_http_protocol_failure_finishes_attempt_and_frees_concurrency(self):
        session = self.session(rpc_concurrency=1)
        rpc = self.rpc(http.client.IncompleteRead(b"partial"), json.dumps({"jsonrpc": "2.0", "id": "g2", "result": GENESIS}).encode())
        first = transport.session_request(session, rpc, GENESIS_REQUEST, family="one")
        self.assertEqual(first["status"], "transport_failure")
        self.assertEqual([a["status"] for a in session.observations()], ["transport_failure"])
        second = transport.session_request(session, rpc, {**GENESIS_REQUEST, "id": "g2"}, family="two")
        self.assertEqual(second["status"], "ok")

    def test_refused_method_is_marked_unavailable_and_other_methods_continue(self):
        session = self.session()
        epoch = {"jsonrpc": "2.0", "id": "e", "method": "getEpochInfo", "params": []}
        rpc = self.rpc(http_error(429, {"Retry-After": "10", "x-ratelimit-method-limit": "0"}),
                       json.dumps({"jsonrpc": "2.0", "id": "e", "result": {"absoluteSlot": 1, "blockHeight": 1, "epoch": 1, "slotIndex": 0, "slotsInEpoch": 10}}).encode())
        first = transport.session_request(session, rpc, LARGEST_REQUEST, family="largest")
        self.assertEqual(first["status"], "method_unavailable")
        self.assertIsNone(session.blocked(rpc.namespace, "getEpochInfo"))
        self.assertEqual(transport.session_request(session, rpc, epoch, family="epoch")["status"], "ok")
        again = transport.session_request(session, rpc, {**LARGEST_REQUEST, "id": "l2"}, family="largest2")
        self.assertEqual((again["status"], again["reason"], again["wait_until"]), ("budget_denied", "method_unavailable", None))
        self.assertEqual([m["method"] for m in session.status()["unavailable_methods"]], ["getTokenLargestAccounts"])
        self.assertEqual(session.unavailable_methods()[0]["reason"], "provider_method_limit")

    def test_stated_wait_backs_off_only_that_method(self):
        session = self.session()
        rpc = self.rpc(http_error(429, {"Retry-After": "5"}))
        before = real_time.time()
        first = transport.session_request(session, rpc, LARGEST_REQUEST, family="largest")
        self.assertEqual(first["status"], "http_429")
        self.assertIsNone(session.blocked(rpc.namespace, "getEpochInfo"))
        refusal = session.blocked(rpc.namespace, "getTokenLargestAccounts")
        self.assertEqual(str(refusal), "method_backoff")
        self.assertGreaterEqual(refusal.until, before+5)
        retry = transport.session_request(session, rpc, {**LARGEST_REQUEST, "id": "l1"}, family="largest", retry=True)
        self.assertEqual((retry["status"], retry["reason"]), ("budget_denied", "method_backoff"))
        self.assertAlmostEqual(retry["wait_until"], refusal.until, places=3)

    def test_collector_waits_out_stated_backoff_then_retries_once(self):
        session = self.session()
        config = {"url": "https://synthetic.invalid", "headers": {}, "session": str(session.root)}
        Limited.wait = "3"
        clock = {"offset": 0.0}

        class Shifted:
            @staticmethod
            def time():
                return real_time.time()+clock["offset"]

            @staticmethod
            def monotonic():
                return real_time.monotonic()+clock["offset"]
        sleeps = []

        def sleep(seconds):
            sleeps.append(round(seconds, 1))
            clock["offset"] += seconds
        with patch.object(solana_session, "time", Shifted), patch.object(collect_v2, "time", Shifted), patch.object(transport, "time", Shifted), patch.object(collect_v2, "SLEEP", sleep):
            packet = execute(session.root, config, "s", read("largest", "getTokenLargestAccounts", [KEY, {"commitment": "finalized"}]), factory=Limited)
        self.assertEqual(packet["status"], "ok")
        self.assertEqual([a["status"] for a in session.observations()], ["http_429", "ok"])
        self.assertEqual(len(sleeps), 2)  # The 1 s retry pause, then the rest of the stated 3 s backoff.
        self.assertEqual(sleeps[0], 1.0)
        self.assertAlmostEqual(sleeps[1], 2.0, delta=0.2)

    def test_unexpected_failure_still_finishes_the_attempt(self):
        session = self.session(rpc_concurrency=1)
        rpc = self.rpc(RuntimeError("fixture bug"))
        with self.assertRaises(RuntimeError):
            transport.session_request(session, rpc, GENESIS_REQUEST, family="one")
        self.assertEqual([a["status"] for a in session.observations()], ["transport_failure"])
        self.assertEqual(session.acquire("g2", "two", "getGenesisHash", "fixture", max_response_bytes=10)["request_id"], "g2")

    def test_attempt_deadline_is_bounded_so_lost_workers_are_reclaimed(self):
        session = self.session()
        ticket = session.acquire("g1", "g1", "getGenesisHash", "fixture", max_response_bytes=10)
        self.assertLessEqual(ticket["deadline"], real_time.time()+solana_session.ATTEMPT_SECONDS+1)
        started = session.observations()[0]["started_at"]

        class Later:
            @staticmethod
            def time():
                return started+solana_session.ATTEMPT_SECONDS+1

            @staticmethod
            def monotonic():
                return real_time.monotonic()+solana_session.ATTEMPT_SECONDS+1
        with patch.object(solana_session, "time", Later):
            session.recover_expired()
        row = session.observations()[0]
        self.assertEqual((row["status"], row["response_bytes"]), ("lost_worker", 10))

    def test_node_lag_error_is_transient_and_retried(self):
        session = self.session()
        lag = json.dumps({"jsonrpc": "2.0", "id": "g", "error": {"code": -32016, "message": "Minimum context slot has not been reached"}}).encode()
        rpc = self.rpc(lag, json.dumps({"jsonrpc": "2.0", "id": "g1", "result": GENESIS}).encode())
        first = transport.session_request(session, rpc, GENESIS_REQUEST, family="lag", strict=True)
        self.assertEqual(first["status"], "node_lag")
        retry = transport.session_request(session, rpc, {**GENESIS_REQUEST, "id": "g1"}, family="lag", retry=True, strict=True)
        self.assertEqual(retry["status"], "ok")

    def test_method_window_refusal_names_when_it_frees_and_send_waits(self):
        session = self.session(method_limits={"getGenesisHash": 2})
        for name in ("g1", "g2"):
            ticket = session.acquire(name, name, "getGenesisHash", "fixture", max_response_bytes=10)
            session.finish(ticket["id"], "ok", 1, {"result": GENESIS})
        with self.assertRaises(LimitError) as refused:
            session.acquire("g3", "g3", "getGenesisHash", "fixture", max_response_bytes=10)
        first = session.observations()[0]["started_at"]
        self.assertEqual(str(refused.exception), "rate_window")
        self.assertAlmostEqual(refused.exception.until, first+solana_session.WINDOW_SECONDS+solana_session.WINDOW_MARGIN, places=3)
        ticket = session.acquire("e1", "e1", "getEpochInfo", "fixture", max_response_bytes=10)
        session.finish(ticket["id"], "ok", 1, {"result": {}})
        clock = {"offset": 0.0}

        class Shifted:
            @staticmethod
            def time():
                return real_time.time()+clock["offset"]

            @staticmethod
            def monotonic():
                return real_time.monotonic()+clock["offset"]
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            clock["offset"] += seconds
        rpc = self.rpc(json.dumps({"jsonrpc": "2.0", "id": "g3", "result": GENESIS}).encode())
        rpc.namespace = "fixture"
        with patch.object(solana_session, "time", Shifted), patch.object(collect_v2, "SLEEP", sleep):
            packet = collect_v2._send(session, rpc, {**GENESIS_REQUEST, "id": "g3"}, family="g3", owner="ordinary", retry=False)
        self.assertEqual(packet["status"], "ok")
        self.assertEqual(len(sleeps), 1)  # One wait until the window frees (11 s minus the real time already elapsed).
        self.assertGreater(sleeps[0], solana_session.WINDOW_SECONDS-1)
        self.assertLessEqual(sleeps[0], solana_session.WINDOW_SECONDS+solana_session.WINDOW_MARGIN)

    def test_wait_beyond_allowance_returns_refusal_without_sleeping(self):
        session = self.session()
        session.defer_source("fixture", real_time.time()+collect_v2.MAX_WAIT_SECONDS+5, method="getGenesisHash")
        rpc = self.rpc()
        rpc.namespace = "fixture"
        sleeps = []
        with patch.object(collect_v2, "SLEEP", sleeps.append):
            packet = collect_v2._send(session, rpc, GENESIS_REQUEST, family="g", owner="ordinary", retry=False)
        self.assertEqual((packet["status"], packet["reason"], packet["waited"], sleeps), ("budget_denied", "method_backoff", 0.0, []))

    def test_wall_clock_set_back_cannot_reopen_collection(self):
        session = self.session()
        cutoff = session.meta["collection_cutoff"]

        class Back:
            @staticmethod
            def time():
                return cutoff-3600

            @staticmethod
            def monotonic():
                return real_time.monotonic()+700
        with patch.object(solana_session, "time", Back):
            self.assertEqual(session.remaining_seconds(), 0)
            with self.assertRaisesRegex(LimitError, "deadline"):
                session.acquire("late", "late", "getGenesisHash", "fixture", max_response_bytes=10)

    def test_final_retry_draws_on_contingency_not_lanes(self):
        session = self.session(reservations={"final": 1, "contingency": 2, "liquidity": 1})
        ticket = session.acquire("f0", "f", "getBlock", "fixture", owner="final", max_response_bytes=10)
        session.finish(ticket["id"], "http_429", 0)
        retry = session.acquire("f1", "f", "getBlock", "fixture", owner="final", max_response_bytes=10, retry=True)
        session.finish(retry["id"], "ok", 1, {"result": 1})
        grants = {g["owner"]: g["remaining"] for g in session.status()["grants"]}
        self.assertEqual((grants["final"], grants["contingency"], grants["liquidity"]), (0, 1, 1))
        self.assertEqual([a["owner"] for a in session.observations()], ["final", "contingency"])
        with self.assertRaisesRegex(LimitError, "request_budget"):  # A first send never spends contingency.
            session.acquire("f2", "f2", "getBlock", "fixture", owner="final", max_response_bytes=10)

    def test_default_session_carries_public_method_windows(self):
        session = self.session(synthetic=False)
        self.assertEqual(session.meta["method_limits"], solana_session.METHOD_LIMITS)
        self.assertEqual(session.method_limit("getBlock"), solana_session.METHOD_LIMITS["getBlock"])
        self.assertEqual(session.method_limit("getRecentPerformanceSamples"), solana_session.DEFAULT_METHOD_LIMIT)


if __name__ == "__main__":
    unittest.main()
