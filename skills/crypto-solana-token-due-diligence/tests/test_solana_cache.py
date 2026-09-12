import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_cache import ObservationCache
from solana_presets import settings
from solana_fixture import KEY, OTHER, SIG, TARGET, account, request, response


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = ObservationCache(self.root, investigation_id="investigation", namespace="provider", target=TARGET, synthetic=True)
        self.req = request("getAccountInfo", [KEY, settings(10)])
        self.packet = {"request": self.req, "status": "ok", "response": response(self.req, {"context": {"slot": 20}, "value": account()})}
        self.now = time.time()

    def reuse(self, digest, **kwargs):
        options = dict(digest=digest, method=self.req["method"], params=self.req["params"], max_age=60, now=self.now+10)
        options.update(kwargs)
        return self.cache.reuse("one", **options)

    def test_named_sample_freshness_and_new_reads_are_not_cache_hits(self):
        digest = self.cache.capture("one", self.packet, captured_at=self.now)
        self.assertEqual(self.reuse(digest)["context_slot"], 20)
        self.assertIsNone(self.reuse(digest, max_age=1))
        for purpose in ("current", "recheck"):
            self.assertIsNone(self.reuse(digest, purpose=purpose))
        with self.assertRaises(ValueError):
            self.reuse(digest, params=[KEY, settings(11)])
        with self.assertRaises(FileExistsError):
            self.cache.capture("one", self.packet, captured_at=self.now)

    def test_failures_wrong_network_modes_and_changed_bytes_rejected(self):
        with self.assertRaises(ValueError):
            self.cache.capture("failed", {**self.packet, "status": "timeout"}, captured_at=self.now)
        self.assertFalse((self.root/"failed.json").exists())
        digest = self.cache.capture("one", self.packet, captured_at=self.now)
        for identity in ({"namespace": "different"}, {"investigation_id": "other"}, {"synthetic": False}, {"target": {**TARGET, "mint": OTHER}}):
            args = {**self.cache.identity, **identity}
            cache = ObservationCache(self.root, **args)
            with self.assertRaises(ValueError):
                cache.reuse("one", digest=digest, method=self.req["method"], params=self.req["params"], max_age=60)
        path = self.root/"one.json"
        value = json.loads(path.read_text())
        value["observation"]["context_slot"] = 21
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "digest"):
            self.reuse(digest)

    def test_historical_reuse_keeps_signature_slot_and_header(self):
        req = request("getTransaction", [SIG, {"commitment": "finalized", "encoding": "json", "maxSupportedTransactionVersion": 0}])
        value = {"slot": 10, "blockTime": 1000, "version": "legacy", "meta": None,
                 "transaction": {"signatures": [SIG], "message": {"accountKeys": [KEY]}}}
        packet = {"request": req, "status": "ok", "response": response(req, value)}
        with self.assertRaises(ValueError):
            self.cache.capture("tx", packet, captured_at=self.now)
        header = {"blockhash": KEY, "previousBlockhash": OTHER, "parentSlot": 9, "blockTime": 1000}
        digest = self.cache.capture("tx", packet, captured_at=self.now, block=header)
        reused = self.cache.reuse("tx", digest=digest, method=req["method"], params=req["params"], max_age=60)
        self.assertEqual(reused["historical_slot"], 10)
        self.assertEqual(reused["block"], header)


if __name__ == "__main__":
    unittest.main()
