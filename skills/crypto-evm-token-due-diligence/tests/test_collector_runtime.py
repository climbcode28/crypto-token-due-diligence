"""Offline scheduling, concurrency and evidence-preservation regressions."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from backend_fixtures import FakeRpc, TOKEN, TX, plan
from backend_common import Cache, Invalid, load_collection
from rpc_collect import Collector, HttpTransport


def balance_plan(count=4, identical=False):
    spec = plan()
    spec["pins"] = [spec["pins"][1]]
    spec["queries"] = [{"id": f"balance-{i}", "pin_id": "current", "method": "eth_getBalance",
                        "params": [TOKEN if identical else "0x" + format(i + 1, "040x")]}
                       for i in range(count)]
    return spec


class CollectorRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = Cache(self.root / "cache.sqlite")
        self.index = 0

    def tearDown(self):
        self.cache.close()
        self.temp.cleanup()

    def collect(self, rpc=None, spec=None, **kwargs):
        self.index += 1
        root = self.root / str(self.index)
        result = Collector(root, self.cache, rpc or FakeRpc(), "synthetic", **kwargs).collect(spec or balance_plan())
        return root, result

    def test_independent_reads_overlap_with_bounded_workers_and_stable_evidence_order(self):
        barrier = threading.Barrier(4)
        lock = threading.Lock()
        active = peak = 0
        rpc = FakeRpc()

        def balance(request):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            barrier.wait(timeout=3)
            with lock:
                active -= 1
            return "0x0"

        rpc.overrides["eth_getBalance"] = balance
        root, result = self.collect(rpc)
        self.assertEqual(peak, 4)
        self.assertEqual(result["status"], "complete")
        self.assertEqual([row["id"] for row in result["evidence"]],
                         ["sys-chain", "sys-pin-current", "balance-0", "balance-1", "balance-2", "balance-3", "sys-recheck-current"])
        self.assertEqual(result["statistics"]["network_attempts"], 7)
        load_collection(root, True)

    def test_single_worker_remains_supported(self):
        threads = set()
        rpc = FakeRpc()
        rpc.overrides["eth_getBalance"] = lambda request: threads.add(threading.get_ident()) or "0x0"
        _, result = self.collect(rpc, workers=1)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(threads), 1)

    def test_budget_reserves_final_header_and_keeps_partial_packet_usable(self):
        root, result = self.collect(max_requests=4)
        self.assertEqual(result["statistics"]["network_attempts"], 4)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(sum(row["coverage"] == "budget_exhausted" for row in result["evidence"]), 3)
        self.assertEqual(result["evidence"][-1]["id"], "sys-recheck-current")
        load_collection(root, True)

    def test_large_log_pin_plan_fails_before_any_rpc_attempt(self):
        rpc = FakeRpc()
        spec = balance_plan(1)
        spec["log_ranges"] = [{"id": "scan", "from_block": 100, "to_block": 300, "address": TOKEN}]
        _, result = self.collect(rpc, spec, max_requests=24)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["statistics"]["network_attempts"], 0)
        self.assertFalse(rpc.calls)

    def test_identical_successes_are_deduplicated_inside_and_across_waves(self):
        rpc = FakeRpc()
        _, result = self.collect(rpc, balance_plan(9, identical=True))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["statistics"], {"network_attempts": 4, "cache_hits": 8})
        self.assertEqual(sum(call["method"] == "eth_getBalance" for call in rpc.calls), 1)

    def test_identical_failures_are_not_retried_within_run_but_future_runs_retry(self):
        for malformed in (False, True):
            with self.subTest(malformed=malformed):
                rpc = FakeRpc()
                if malformed:
                    base = rpc

                    class BadEnvelope:
                        synthetic = True
                        namespace = "malformed-envelope-test"

                        def __call__(self, request):
                            response = base(request)
                            if request["method"] == "eth_getBalance":
                                response["id"] = True
                            return response

                    transport = BadEnvelope()
                else:
                    rpc.overrides["eth_getBalance"] = lambda request: {"error": {"code": -32000, "message": "unavailable"}}
                    transport = rpc
                for run in (1, 2):
                    root, result = self.collect(transport, balance_plan(9, identical=True))
                    self.assertEqual(result["status"], "partial")
                    self.assertEqual(result["statistics"]["network_attempts"], 4)
                    self.assertEqual(sum(call["method"] == "eth_getBalance" for call in rpc.calls), run)
                    load_collection(root, True)

    def test_query_deadline_leaves_time_for_final_pin_and_no_fabricated_results(self):
        clock = [0.0]
        rpc = FakeRpc()

        def slow_read(request):
            clock[0] = 7.0
            return "0x0"

        rpc.overrides["eth_getBalance"] = slow_read
        with patch("rpc_collect.time.monotonic", side_effect=lambda: clock[0]):
            root, result = self.collect(rpc, workers=1, timeout=9)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["statistics"]["network_attempts"], 4)
        self.assertEqual(sum(row["coverage"] == "deadline_exhausted" for row in result["evidence"]), 3)
        load_collection(root, True)

    def test_expired_final_pin_invalidates_packet_and_cannot_be_replayed(self):
        clock = [0.0]
        rpc = FakeRpc()

        def overrun(request):
            clock[0] = 10.0
            return "0x0"

        rpc.overrides["eth_getBalance"] = overrun
        with patch("rpc_collect.time.monotonic", side_effect=lambda: clock[0]):
            root, result = self.collect(rpc, workers=1, timeout=9)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["statistics"]["network_attempts"], 3)
        with self.assertRaises(Invalid):
            load_collection(root, True)

    def test_unbound_receipt_prevents_trace_even_when_other_reads_are_parallel(self):
        rpc = FakeRpc()
        spec = plan()
        spec["queries"].append({"id": "trace", "pin_id": "launch", "method": "debug_traceTransaction", "params": [TX]})
        rpc.overrides["eth_getTransactionReceipt"] = lambda request: None
        _, result = self.collect(rpc, spec)
        self.assertEqual(result["status"], "partial")
        self.assertFalse(any(call["method"] == "debug_traceTransaction" for call in rpc.calls))

    def test_invalid_early_result_preserves_all_already_started_wave_evidence(self):
        rpc = FakeRpc()
        spec = balance_plan(3)
        spec["queries"].append({"id": "00-bad-receipt", "pin_id": "current",
                                "method": "eth_getTransactionReceipt", "params": [TX]})
        # Fixture receipt belongs to block 100, while this plan is pinned to 101.
        root, result = self.collect(rpc, spec)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(sum(call["method"] == "eth_getBalance" for call in rpc.calls), 3)
        for index in range(3):
            self.assertTrue((root / f"evidence/balance-{index}.json").exists())

    def test_redacted_results_are_gaps_and_are_not_reused_by_later_runs(self):
        class RedactedRpc(FakeRpc):
            def __call__(self, request):
                self.last_redacted = request["method"] == "eth_getBalance"
                return super().__call__(request)

        rpc = RedactedRpc()
        for run in (1, 2):
            root, result = self.collect(rpc, balance_plan(1), workers=1)
            self.assertEqual(result["status"], "partial")
            row = next(row for row in result["evidence"] if row["id"] == "balance-0")
            self.assertEqual(row["coverage"], "redacted")
            self.assertTrue(row["redacted"])
            self.assertEqual(sum(call["method"] == "eth_getBalance" for call in rpc.calls), run)

    def test_transport_redaction_marker_is_thread_local(self):
        transport = HttpTransport("https://example.invalid/", {"Authorization": "SECRET"})
        barrier = threading.Barrier(2)

        def redact(value):
            transport.last_redacted = False
            result = transport.redact(value)
            barrier.wait(timeout=3)
            return result, transport.last_redacted

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(redact, ["SECRET", "clean"]))
        self.assertEqual(results, [("[REDACTED]", True), ("clean", False)])

    def test_legacy_redacted_cache_entry_is_evicted_and_recollected(self):
        rpc = FakeRpc()
        self.collect(rpc, balance_plan(1))
        key, payload = self.cache.db.execute("SELECT key, payload FROM responses").fetchone()
        record = json.loads(payload)
        record["redacted"] = True
        self.cache.record(key, record, reusable=True)
        _, result = self.collect(rpc, balance_plan(1))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["statistics"]["network_attempts"], 4)
        self.assertEqual(sum(call["method"] == "eth_getBalance" for call in rpc.calls), 2)

    def test_slow_drip_response_stops_at_response_deadline(self):
        clock = [0.0]

        class DripResponse:
            reads = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read1(self, count):
                self.reads += 1
                clock[0] += 0.6
                return b"x"

        response = DripResponse()
        transport = HttpTransport("https://example.invalid/", {}, timeout=1)
        with patch("rpc_collect.time.monotonic", side_effect=lambda: clock[0]), \
             patch.object(transport.opener, "open", return_value=response) as opened, \
             self.assertRaises(TimeoutError):
            transport({"jsonrpc": "2.0", "id": "test", "method": "eth_chainId", "params": []})
        self.assertEqual(response.reads, 2)
        self.assertEqual(opened.call_args.kwargs["timeout"], 1)

    def test_late_eof_cannot_accept_complete_json_after_response_deadline(self):
        clock = [0.0]

        class LateEofResponse:
            reads = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read1(self, count):
                self.reads += 1
                if self.reads == 1:
                    clock[0] = 0.5
                    return b'{"jsonrpc":"2.0","id":"test","result":"0x1"}'
                clock[0] = 1.1
                return b""

        response = LateEofResponse()
        transport = HttpTransport("https://example.invalid/", {}, timeout=1)
        with patch("rpc_collect.time.monotonic", side_effect=lambda: clock[0]), \
             patch.object(transport.opener, "open", return_value=response), \
             self.assertRaises(TimeoutError):
            transport({"jsonrpc": "2.0", "id": "test", "method": "eth_chainId", "params": []})
        self.assertEqual(response.reads, 2)

    def test_invalid_runtime_bounds_are_rejected_offline(self):
        for options in ({"timeout": float("nan")}, {"timeout": float("inf")}, {"timeout": 0},
                        {"workers": 5}, {"workers": True}):
            with self.subTest(options=options), self.assertRaises(Invalid):
                self.collect(**options)


if __name__ == "__main__":
    unittest.main()
