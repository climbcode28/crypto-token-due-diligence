import tempfile
import unittest
from pathlib import Path
from backend_fixtures import FakeRpc, plan, TOKEN, receipt, header, hh
from backend_common import Cache, load_collection
from rpc_collect import Collector


class WireCacheTests(unittest.TestCase):
    def test_malformed_receipt_log_is_a_preserved_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            try:
                rpc = FakeRpc()
                rpc.overrides["eth_getTransactionReceipt"] = lambda q: {**receipt(), "logs": [{"data": "broken"}]}
                result = Collector(root / "run", cache, rpc, "fixture").collect(plan())
                self.assertEqual(result["status"], "partial")
                row = next(e for e in result["evidence"] if e["id"] == "launch-receipt")
                self.assertEqual(row["observation_status"], "malformed_data")
                self.assertEqual(row["kind"], "document")
                load_collection(root / "run", True)
            finally:
                cache.close()

    def test_recheck_with_same_hash_but_different_root_invalidates_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            try:
                rpc, count = FakeRpc(), {}
                def altered(q):
                    number = int(q["params"][0], 16)
                    count[number] = count.get(number, 0) + 1
                    result = header(number)
                    if count[number] > 1:
                        result["stateRoot"] = hh("contradiction")
                    return result
                rpc.overrides["eth_getBlockByNumber"] = altered
                result = Collector(root / "run", cache, rpc, "fixture").collect(plan())
                self.assertEqual(result["status"], "invalid")
                self.assertEqual(cache.db.execute("SELECT count(*) FROM responses").fetchone()[0], 0)
            finally:
                cache.close()

    def test_malformed_state_is_a_gap_and_never_reused(self):
        for method, bad in (("eth_getBalance", "0x00"), ("eth_getCode", "0x1"), ("eth_getStorageAt", "0x0")):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                cache = Cache(root / "cache.sqlite")
                try:
                    rpc = FakeRpc()
                    rpc.overrides[method] = lambda req: bad
                    spec = plan()
                    spec["queries"] = [{"id": "read", "pin_id": "current", "method": method,
                                        "params": [TOKEN, "0x0"] if method == "eth_getStorageAt" else [TOKEN]}]
                    for n in (1, 2):
                        out = root / str(n)
                        result = Collector(out, cache, rpc, "fixture").collect(spec)
                        self.assertEqual(result["status"], "partial")
                        row = next(e for e in result["evidence"] if e["id"] == "read")
                        self.assertEqual(row["observation_status"], "malformed_data")
                        self.assertIn(bad, (out / row["artifact"]).read_text())
                        load_collection(out, True)
                    self.assertEqual(sum(q["method"] == method for q in rpc.calls), 2)
                    self.assertEqual(cache.db.execute("SELECT count(*) FROM responses").fetchone()[0], 0)
                finally:
                    cache.close()

    def test_empty_code_and_standard_revert_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            try:
                rpc = FakeRpc()
                rpc.overrides["eth_getCode"] = lambda req: "0x"
                rpc.overrides["eth_call"] = lambda req: {"error": {"code": 3, "message": "execution reverted"}}
                result = Collector(root / "run", cache, rpc, "fixture").collect(plan())
                self.assertEqual(result["status"], "partial")
                self.assertEqual(next(e for e in result["evidence"] if e["id"] == "code-current")["observation_status"], "ok")
                fee = next(e for e in result["evidence"] if e["id"] == "fee-current")
                self.assertEqual(fee["observation_status"], "reverted")
                self.assertEqual(fee["acquisition"]["failure_category"], "execution_reverted")
                load_collection(root / "run", True)
            finally:
                cache.close()
