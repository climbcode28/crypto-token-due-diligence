import copy
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from backend_fixtures import TOKEN, ALICE, CHAIN, FakeRpc, hh
from backend_common import Cache, load_collection
from investigation import Investigation
from rpc_collect import Collector, HttpTransport
from test_collector_runtime import balance_plan


class InvestigationTests(unittest.TestCase):
    def test_live_python_entrypoint_cannot_omit_shared_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rpc = Path(tmp), FakeRpc()
            cache = Cache(root / "cache.sqlite")
            rpc.synthetic = False
            try:
                with self.assertRaisesRegex(ValueError, "requires an investigation"):
                    Collector(root / "run", cache, rpc, "fixture")
                self.assertFalse(rpc.calls)
            finally:
                cache.close()

    def test_cache_error_preserves_other_started_acquisition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rpc = Path(tmp), FakeRpc()
            cache = Cache(root / "cache.sqlite")
            try:
                Collector(root / "seed", cache, rpc, "fixture").collect(balance_plan(2))
                rows = cache.db.execute("SELECT key,payload FROM responses").fetchall()
                for key, payload in rows:
                    request = json.loads(payload)["request"]
                    with cache.db:
                        if int(request["params"][0], 16) == 1:
                            cache.db.execute("DELETE FROM responses WHERE key=?", (key,))
                        else:
                            cache.db.execute("UPDATE responses SET digest='corrupted' WHERE key=?", (key,))
                rpc.calls.clear()
                result = Collector(root / "run", cache, rpc, "fixture").collect(balance_plan(2))
                self.assertEqual(result["status"], "invalid")
                self.assertEqual(result["statistics"]["network_attempts"], 3)
                self.assertTrue((root / "run/evidence/balance-0.json").is_file())
                self.assertIn("balance-0", [x["id"] for x in result["evidence"]])
            finally:
                cache.close()

    def test_priority_delivers_control_read_with_same_request_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            try:
                spec = balance_plan(0)
                spec["queries"] = [
                    {"id": "a-optional", "pin_id": "current", "method": "eth_getBalance", "params": [ALICE], "priority": 90},
                    {"id": "z-control", "pin_id": "current", "method": "eth_call", "params": [{"to": TOKEN, "data": "0x8da5cb5b"}], "priority": 0}]
                result = Collector(root / "run", cache, FakeRpc(), "fixture", max_requests=4).collect(spec)
                self.assertEqual(result["statistics"]["network_attempts"], 4)
                self.assertEqual(next(e for e in result["evidence"] if e["id"] == "z-control")["observation_status"], "ok")
                self.assertEqual(next(e for e in result["evidence"] if e["id"] == "a-optional")["observation_status"], "budget_exhausted")
            finally:
                cache.close()

    def test_aggregate_budget_survives_another_collector_and_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = Investigation.create(root / "session.sqlite", 8, 120)
            cache = Cache(root / "cache.sqlite")
            try:
                first = Collector(root / "one", cache, FakeRpc(), "fixture", session=session).collect(balance_plan(3))
                self.assertEqual(first["statistics"]["network_attempts"], 6)
                session.close()
                session = Investigation(root / "session.sqlite")
                second = Collector(root / "two", cache, FakeRpc(), "fixture", max_requests=999, session=session).collect(balance_plan(3))
                self.assertEqual(second["status"], "invalid")
                self.assertEqual(second["statistics"]["network_attempts"], 0)
                self.assertEqual(second["execution"]["limit_reached"], "investigation_limit")
                self.assertEqual(session.status()["started_attempts"], 6)
            finally:
                cache.close()
                session.close()

    def test_reserved_checks_survive_shared_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = Investigation.create(root / "session.sqlite", 4, 120)
            cache = Cache(root / "cache.sqlite")
            try:
                result = Collector(root / "run", cache, FakeRpc(), "fixture", session=session).collect(balance_plan(8))
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["statistics"]["network_attempts"], 4)
                self.assertEqual(result["evidence"][-1]["id"], "sys-recheck-current")
                self.assertEqual(session.status()["reserved_requests"], 0)
                load_collection(root / "run", True)
            finally:
                cache.close()
                session.close()

    def test_concurrent_acquisition_cannot_overspend(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.sqlite"
            Investigation.create(path, 7, 120).close()
            def acquire(_):
                session = Investigation(path)
                try:
                    return session.acquire("synthetic_test")
                finally:
                    session.close()
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(acquire, range(20)))
            self.assertEqual(sum(results), 7)

    def test_deadline_does_not_reset_on_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.sqlite"
            with patch("investigation.time.time", return_value=100):
                Investigation.create(path, 20, 1).close()
            with patch("investigation.time.time", return_value=102):
                session = Investigation(path)
                try:
                    self.assertFalse(session.acquire("eth_chainId"))
                    with self.assertRaises(ValueError):
                        session.ensure(1)
                finally:
                    session.close()

    def test_exact_cross_target_read_reuse_but_new_investigation_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            session = Investigation.create(root / "session.sqlite", 20, 120)
            try:
                spec = balance_plan(1, identical=True)
                rpc = FakeRpc()
                one = Collector(root / "one", cache, rpc, "fixture", session=session).collect(spec)
                spec["target"]["address"] = ALICE
                two = Collector(root / "two", cache, rpc, "fixture", session=session).collect(spec)
                self.assertEqual(two["statistics"]["cache_hits"], 1)
                self.assertEqual(next(e for e in two["evidence"] if e["id"] == "balance-0")["address"], TOKEN)
                load_collection(root / "two", True)
                session.close()
                session = Investigation.create(root / "new.sqlite", 20, 120)
                three = Collector(root / "three", cache, rpc, "fixture", session=session).collect(spec)
                self.assertEqual(three["statistics"]["cache_hits"], 0)
                self.assertEqual(sum(x["method"] == "eth_getBalance" for x in rpc.calls), 2)
            finally:
                cache.close()
                session.close()

    def test_cache_key_separates_caller_address_pin_provider_and_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Cache(Path(tmp) / "cache.sqlite")
            try:
                rpc = FakeRpc()
                collector = Collector(Path(tmp) / "out", cache, rpc, "fixture")
                collector.target = {"chain_id": CHAIN, "address": TOKEN}
                params = [{"to": TOKEN, "from": ALICE, "data": "0x12345678"}, "0x65"]
                baseline = collector.request_key("eth_call", params, hh(101))
                for field in ("to", "from"):
                    modified = copy.deepcopy(params)
                    modified[0][field] = "0x" + "34" * 20
                    self.assertNotEqual(baseline, collector.request_key("eth_call", modified, hh(101)))
                self.assertNotEqual(baseline, collector.request_key("eth_call", params, hh(102)))
                rpc.namespace = "different-provider"
                self.assertNotEqual(baseline, collector.request_key("eth_call", params, hh(101)))
                rpc.namespace = FakeRpc.namespace
                rpc.synthetic = False
                self.assertNotEqual(baseline, collector.request_key("eth_call", params, hh(101)))
                self.assertNotEqual(HttpTransport("https://example.invalid/", {"Authorization": "a"}).namespace,
                                    HttpTransport("https://example.invalid/", {"Authorization": "b"}).namespace)
            finally:
                cache.close()

    def test_rolling_scheduler_starts_later_work_before_slow_first_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            fifth_started = threading.Event()
            rpc = FakeRpc()
            def balance(request):
                number = int(request["params"][0], 16)
                if number == 1:
                    if not fifth_started.wait(2):
                        raise TimeoutError("rolling refill did not occur")
                if number == 5:
                    fifth_started.set()
                return hex(number)
            rpc.overrides["eth_getBalance"] = balance
            try:
                result = Collector(root / "run", cache, rpc, "fixture").collect(balance_plan(8))
                self.assertEqual(result["status"], "complete")
                self.assertTrue(fifth_started.is_set())
                self.assertLessEqual(result["telemetry"]["peak_in_flight"], 4)
                rows = [e for e in result["evidence"] if e["id"].startswith("balance")]
                self.assertEqual([e["id"] for e in rows], ["balance-" + str(i) for i in range(8)])
                for index, row in enumerate(rows, 1):
                    payload = json.loads((root / "run" / row["artifact"]).read_text())
                    self.assertEqual(payload["response"]["result"], hex(index))
            finally:
                cache.close()
