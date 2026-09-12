"""Offline regressions: every RPC retry spends the same bounded request budget."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from backend_fixtures import CHAIN, FakeRpc, header, plan
from backend_common import Cache, load_collection
from investigation import Investigation
from rpc_collect import Collector
from test_collector_runtime import balance_plan


class RetryBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = Cache(self.root / "cache.sqlite")
        self.addCleanup(self.cache.close)
        self.index = 0

    def collect(self, rpc, spec=None, session_limit=100, **kwargs):
        self.index += 1
        root = self.root / str(self.index)
        session = Investigation.create(self.root / f"session-{self.index}.sqlite", session_limit, 120)
        self.addCleanup(session.close)
        coordinator = threading.get_ident()
        acquire = session.acquire

        def acquire_on_coordinator(*args, **options):
            self.assertEqual(threading.get_ident(), coordinator, "SQLite budget writes belong to the coordinator")
            return acquire(*args, **options)

        with patch.object(session, "acquire", side_effect=acquire_on_coordinator):
            result = Collector(root, self.cache, rpc, "fixture", session=session, **kwargs).collect(
                balance_plan(1) if spec is None else spec)
        self.assertEqual(result["statistics"]["network_attempts"], len(rpc.calls))
        self.assertEqual(session.status()["started_attempts"], len(rpc.calls))
        self.assertEqual(session.status()["reserved_requests"], 0)
        if result["status"] != "invalid":
            load_collection(root, True)
        return result

    @staticmethod
    def balance_rows(result):
        return [row for row in result["evidence"] if row["query"]["method"] == "eth_getBalance"]

    def test_synchronous_chain_retry_is_charged_and_keeps_final_header_capacity(self):
        rpc = FakeRpc()
        attempts = 0

        def chain(request):
            nonlocal attempts
            attempts += 1
            return TimeoutError("synthetic timeout") if attempts == 1 else hex(CHAIN)

        rpc.overrides["eth_chainId"] = chain
        with patch("rpc_collect.time.sleep"):
            result = self.collect(rpc, balance_plan(0), max_requests=4, session_limit=4)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(attempts, 2)
        self.assertEqual(len(rpc.calls), 4)
        self.assertEqual(result["evidence"][-1]["id"], "sys-recheck-current")

    def test_success_path_keeps_original_request_count_and_never_backs_off(self):
        rpc = FakeRpc()
        with patch("rpc_collect.time.sleep") as sleep:
            result = self.collect(rpc, balance_plan(4), max_requests=7, session_limit=7)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(rpc.calls), 7)
        sleep.assert_not_called()

    def test_same_run_failed_read_is_reused_after_unrelated_lease_releases(self):
        session = Investigation.create(self.root / "reuse-session.sqlite", 2, 120)
        self.addCleanup(session.close)
        session.reserve("other", 1)
        rpc = FakeRpc()
        rpc.overrides["eth_getBalance"] = lambda request: TimeoutError("synthetic timeout")
        root = self.root / "reuse"
        root.mkdir()
        collector = Collector(root, self.cache, rpc, "fixture", session=session)
        spec = balance_plan(1)
        collector.target = spec["target"]
        params = [collector.target["address"], "0x65"]
        with patch("rpc_collect.time.sleep"):
            collector.request("first", "eth_getBalance", params)
            session.release("other")
            collector.request("same", "eth_getBalance", params)
        self.assertEqual(len(rpc.calls), 1, "a reused failed acquisition is not a new retry opportunity")
        self.assertEqual(session.status()["started_attempts"], 1)

    def test_concurrent_retries_overlap_and_every_attempt_is_charged(self):
        barrier = threading.Barrier(4)
        lock = threading.Lock()
        attempts = {}
        rpc = FakeRpc()

        def balance(request):
            with lock:
                count = attempts[request["id"]] = attempts.get(request["id"], 0) + 1
            if count == 1:
                barrier.wait(timeout=3)
                return TimeoutError("synthetic timeout")
            return "0x0"

        rpc.overrides["eth_getBalance"] = balance
        with patch("rpc_collect.time.sleep"):
            result = self.collect(rpc, balance_plan(4), max_requests=11, session_limit=11)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(list(attempts.values()), [2] * 4)
        self.assertEqual(len(rpc.calls), 11)
        self.assertEqual([row["id"] for row in self.balance_rows(result)], [f"balance-{i}" for i in range(4)])

    def test_local_and_shared_exhaustion_preserve_failure_and_final_header(self):
        for collection_limit, session_limit, limit in ((4, 100, "request_budget"), (100, 4, "investigation_limit")):
            with self.subTest(limit=limit):
                rpc = FakeRpc()
                rpc.overrides["eth_getBalance"] = lambda request: TimeoutError("synthetic timeout")
                with patch("rpc_collect.time.sleep"):
                    result = self.collect(rpc, max_requests=collection_limit, session_limit=session_limit)
                self.assertEqual(result["status"], "partial")
                self.assertEqual(len(rpc.calls), 4)
                self.assertEqual(result["execution"]["limit_reached"], limit)
                row = self.balance_rows(result)[0]
                self.assertEqual(row["observation_status"], "transport_failure")
                self.assertEqual(row["acquisition"]["failure_category"], "timeout")
                self.assertEqual(result["evidence"][-1]["observation_status"], "ok")

    def test_concurrent_retries_cannot_overspend_either_limit(self):
        for collection_limit, session_limit in ((8, 100), (100, 8)):
            with self.subTest(collection_limit=collection_limit, session_limit=session_limit):
                rpc = FakeRpc()
                rpc.overrides["eth_getBalance"] = lambda request: TimeoutError("synthetic timeout")
                with patch("rpc_collect.time.sleep"):
                    result = self.collect(rpc, balance_plan(4), max_requests=collection_limit, session_limit=session_limit)
                self.assertEqual(result["status"], "partial")
                self.assertEqual(len(rpc.calls), 8)
                self.assertEqual(sum(call["method"] == "eth_getBalance" for call in rpc.calls), 5)
                self.assertEqual(result["evidence"][-1]["observation_status"], "ok")

    def test_repeated_transient_errors_stop_after_one_retry(self):
        for workers in (1, 4):
            with self.subTest(workers=workers):
                rpc = FakeRpc()
                rpc.overrides["eth_getBalance"] = lambda request: {"error": {
                    "code": -32000, "message": "unsupported block number"}}
                with patch("rpc_collect.time.sleep"):
                    result = self.collect(rpc, balance_plan(4), workers=workers)
                self.assertEqual(result["status"], "partial")
                self.assertEqual(len(rpc.calls), 11)
                self.assertTrue(all(row["acquisition"]["failure_category"] == "node_lag"
                                    for row in self.balance_rows(result)))

    def test_query_retry_cannot_spend_time_reserved_for_final_header(self):
        clock = [0.0]
        rpc = FakeRpc()

        def timed_out(request):
            clock[0] = 4.5  # Query cutoff is 6; collection cutoff is 9.
            return TimeoutError("synthetic timeout")

        rpc.overrides["eth_getBalance"] = timed_out
        with patch("rpc_collect.time.monotonic", side_effect=lambda: clock[0]), \
             patch("rpc_collect.time.sleep", side_effect=lambda pause: clock.__setitem__(0, clock[0] + pause)):
            result = self.collect(rpc, workers=1, timeout=9)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(rpc.calls), 4)
        self.assertLessEqual(clock[0], 6)
        self.assertEqual(result["evidence"][-1]["observation_status"], "ok")

    def test_deadline_is_rechecked_after_backoff_before_charging_retry(self):
        clock = [0.0]
        rpc = FakeRpc()
        rpc.overrides["eth_getBalance"] = lambda request: TimeoutError("synthetic timeout")
        with patch("rpc_collect.time.monotonic", side_effect=lambda: clock[0]), \
             patch("rpc_collect.time.sleep", side_effect=lambda pause: clock.__setitem__(0, 6.5)):
            result = self.collect(rpc, workers=1, timeout=9)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(rpc.calls), 4)
        self.assertEqual(result["evidence"][-1]["observation_status"], "ok")

    def test_recheck_retry_uses_spare_capacity_and_keeps_other_pin_lease(self):
        rpc = FakeRpc()
        attempts = {}

        def block(request):
            number = int(request["params"][0], 16)
            attempts[number] = attempts.get(number, 0) + 1
            if number == 100 and attempts[number] == 2:
                return TimeoutError("synthetic recheck timeout")
            return header(number)

        rpc.overrides["eth_getBlockByNumber"] = block
        spec = plan()
        spec["queries"] = []
        with patch("rpc_collect.time.sleep"):
            result = self.collect(rpc, spec, max_requests=6, session_limit=6)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(attempts, {100: 3, 101: 2})
        self.assertEqual(len(rpc.calls), 6)

    def test_recheck_retry_cannot_consume_the_next_pins_reserved_attempt(self):
        for collection_limit, session_limit in ((5, 100), (100, 5)):
            with self.subTest(collection_limit=collection_limit, session_limit=session_limit):
                rpc = FakeRpc()
                attempts = {}

                def block(request):
                    number = int(request["params"][0], 16)
                    attempts[number] = attempts.get(number, 0) + 1
                    return TimeoutError("synthetic recheck timeout") if number == 100 and attempts[number] > 1 else header(number)

                rpc.overrides["eth_getBlockByNumber"] = block
                spec = plan()
                spec["queries"] = []
                with patch("rpc_collect.time.sleep"):
                    result = self.collect(rpc, spec, max_requests=collection_limit, session_limit=session_limit)
                self.assertEqual(result["status"], "invalid")
                self.assertEqual(attempts[100], 2, "failed recheck must not borrow the next pin's lease")
                self.assertEqual(len(rpc.calls), 4)


if __name__ == "__main__":
    unittest.main()
