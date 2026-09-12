"""Range logs, timeline marks and bounded web capture behave without network or turns."""
import io
import json
import tempfile
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from unittest.mock import patch

from backend_common import Cache, load_collection
from backend_fixtures import CHAIN, FakeRpc, TOKEN, hh, plan
from investigation import Investigation
from rpc_collect import Collector
from validate_bundle import Invalid
from web_capture import capture


class RangeLogTests(unittest.TestCase):
    def test_range_logs_are_bounded_pinned_and_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            rpc = FakeRpc()
            seen = []

            def logs(request):
                seen.append(request["params"][0])
                return [{"address": TOKEN, "topics": ["0x" + "ab" * 32], "data": "0x", "blockNumber": "0x60", "blockHash": hh(96),
                         "transactionHash": hh("t"), "transactionIndex": "0x0", "logIndex": "0x0", "removed": False}]
            rpc.overrides["eth_getLogs"] = logs
            spec = plan()
            spec["pins"] = [spec["pins"][1]]
            spec["queries"] = [{"id": "range", "pin_id": "current", "method": "eth_getLogs",
                                "params": [{"address": TOKEN, "topics": ["0x" + "ab" * 32], "from_block": 90, "to_block": 101}]}]
            try:
                result = Collector(root / "run", cache, rpc, "synthetic").collect(spec)
                self.assertEqual(result["status"], "complete", result["coverage_gaps"])
                self.assertEqual(seen[0]["fromBlock"], hex(90))
                self.assertEqual(seen[0]["toBlock"], hex(101))
                self.assertNotIn("blockHash", seen[0])
                load_collection(root / "run", True)
                bad = dict(spec)
                bad["queries"] = [{"id": "range", "pin_id": "current", "method": "eth_getLogs",
                                   "params": [{"address": TOKEN, "from_block": 90, "to_block": 200}]}]
                result = Collector(root / "run2", cache, rpc, "synthetic").collect(bad)
                self.assertEqual(result["status"], "invalid", "range past the pin is rejected")
                with self.assertRaises(Invalid):
                    Collector(root / "run3", cache, rpc, "synthetic").collect({**spec, "queries": [{"id": "r", "pin_id": "current", "method": "eth_getLogs",
                                                                                                   "params": [{"address": TOKEN, "from_block": 0, "to_block": 20000}]}]})
            finally:
                cache.close()


class TimelineTests(unittest.TestCase):
    def test_marks_record_phases_and_legacy_sessions_still_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Investigation.create(Path(tmp) / "s.sqlite", 20, 600, request_ceiling=40, timeout_ceiling=900, limit_basis="analyst_safety")
            try:
                self.assertEqual(s.schema, 3)
                s.mark("intake")
                s.acquire("eth_call")
                timeline = s.mark("phase1")
                self.assertEqual([t["phase"] for t in timeline], ["intake", "phase1"])
                self.assertEqual(timeline[1]["used"], 1)
                self.assertEqual(len(s.status()["phases"]), 2)
                with self.assertRaises(ValueError):
                    s.mark("bad phase!")
                with s.db:
                    s.db.execute("PRAGMA user_version=2")
            finally:
                s.close()
            legacy = Investigation(Path(tmp) / "s.sqlite")
            try:
                self.assertEqual(legacy.timeline(), [])
                self.assertEqual(legacy.status()["phases"], [])
                with self.assertRaisesRegex(ValueError, "schema 3"):
                    legacy.mark("x")
            finally:
                legacy.close()


class FakeResponse(io.BytesIO):
    def __init__(self, body, status=200, content_type="application/json"):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, routes):
        self.routes, self.requests = routes, []

    def open(self, request, timeout=None):
        self.requests.append(request)
        route = self.routes[request.full_url]
        if isinstance(route, Exception):
            raise route
        return FakeResponse(*route)


class WebCaptureTests(unittest.TestCase):
    def test_capture_records_provenance_redirects_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "captures"
            forbidden = urllib.error.HTTPError("https://explorer.invalid/api", 403, "Forbidden", {}, io.BytesIO(b"denied"))
            moved = urllib.error.HTTPError("https://old.invalid/x", 301, "Moved", {"Location": "https://new.invalid/x"}, io.BytesIO(b""))
            opener = FakeOpener({"https://api.invalid/pairs": (b'{"ok": true}',), "https://explorer.invalid/api": forbidden,
                                 "https://old.invalid/x": moved, "https://new.invalid/x": (b"<html>ok</html>", 200, "text/html")})
            items = [{"id": "pairs", "url": "https://api.invalid/pairs"}, {"id": "explorer", "url": "https://explorer.invalid/api"},
                     {"id": "moved", "url": "https://old.invalid/x"}]
            with patch("web_capture.urllib.request.build_opener", return_value=opener):
                records = capture(items, out, workers=2)
            by_id = {r["id"]: r for r in records}
            self.assertEqual(by_id["pairs"]["http_status"], 200)
            self.assertEqual((out / "pairs.raw").read_bytes(), b'{"ok": true}')
            self.assertEqual(by_id["explorer"]["failure_category"], "access_denied")
            self.assertEqual(by_id["moved"]["redirects"], ["https://old.invalid/x"])
            self.assertEqual(by_id["moved"]["final_url"], "https://new.invalid/x")
            self.assertTrue(all(r["sha256"] or r["failure_category"] for r in records))
            saved = json.loads((out / "explorer.json").read_text())
            self.assertEqual(saved["http_status"], 403)
            self.assertNotIn("Authorization", str(opener.requests[0].headers))
            with self.assertRaises(ValueError):
                capture([{"id": "pairs", "url": "https://api.invalid/pairs"}], out)


if __name__ == "__main__":
    unittest.main()
