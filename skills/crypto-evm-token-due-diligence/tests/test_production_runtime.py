"""Offline production boundaries: every HTTP attempt is bounded and restart keeps its ledger."""
import io
import json
import sqlite3
import sys
import tempfile
import time
import unittest
import urllib.error
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import broad_collect
from backend_fixtures import CHAIN, TOKEN
from investigation import Investigation
from test_pipeline_helpers import FakeOpener, FakeResponse
from test_broad_collect import PipelineRpc, REGISTRY, fake_fetch, ALICE, BOB, CAROL, POOL, QUOTE
from web_capture import capture, capture_one, prepare_budget


class WebBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = Investigation.create(self.root / "session.sqlite", 3, 60)
        self.addCleanup(self.session.close)

    def capture(self, items, opener, **kwargs):
        with patch("web_capture.urllib.request.build_opener", return_value=opener), patch("web_capture.time.sleep"):
            return capture(items, self.root / "web", **kwargs)

    def test_retry_and_redirect_charge_each_attempt(self):
        class RetryOpener:
            def __init__(self):
                self.requests = []

            def open(self, request, timeout=None):
                self.requests.append(request.full_url)
                if len(self.requests) == 1:
                    raise urllib.error.HTTPError(request.full_url, 429, "retry", {}, io.BytesIO())
                if len(self.requests) == 2:
                    raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": "https://example.invalid/new"}, io.BytesIO())
                return FakeResponse(b'{"ok":true}')

        opener = RetryOpener()
        rows = self.capture([{"id": "a", "url": "https://example.invalid/start"}], opener, session=self.session)
        self.assertEqual(rows[0]["http_status"], 200)
        self.assertEqual(rows[0]["requests_used"], 3)
        self.assertEqual(self.session.status()["started_attempts"], len(opener.requests))

    def test_concurrent_retries_do_not_exceed_session_limit(self):
        class Unavailable:
            def __init__(self):
                self.requests = []

            def open(self, request, timeout=None):
                self.requests.append(request.full_url)
                raise urllib.error.HTTPError(request.full_url, 503, "retry", {}, io.BytesIO())

        opener = Unavailable()
        items = [{"id": str(i), "url": "https://example.invalid/" + str(i)} for i in range(4)]
        rows = self.capture(items, opener, session=self.session)
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(sum(r["requests_used"] for r in rows), 3)
        self.assertEqual(self.session.status()["started_attempts"], 3)
        self.assertTrue(all(r["failure_category"] for r in rows))

    def test_prepaid_lane_budget_survives_multiple_batches(self):
        out = self.root / "web"
        prepare_budget(out, 2, time.time() + 30)
        opener = FakeOpener({"https://example.invalid/": (b"{}",)})
        for i in range(3):
            rows = self.capture([{"id": str(i), "url": "https://example.invalid/"}], opener)
        self.assertEqual(len(opener.requests), 2)
        self.assertEqual(rows[0]["failure_category"], "budget_exhausted")
        self.assertEqual(self.session.status()["started_attempts"], 0, "prepaid requests are never double-charged")
        with closing(sqlite3.connect(out / "web-budget.sqlite")) as db:
            self.assertEqual(db.execute("SELECT remaining FROM budget").fetchone()[0], 0)

    def test_zero_grant_and_expired_deadline_make_no_requests(self):
        opener = FakeOpener({})
        prepare_budget(self.root / "web", 0, time.time() + 30)
        self.capture([{"id": "a", "url": "https://example.invalid/"}], opener)
        with self.session.db:
            self.session.db.execute("UPDATE session SET deadline=?", (time.time() - 1,))
        rows = self.capture([{"id": "b", "url": "https://example.invalid/"}], opener, session=self.session)
        self.assertEqual(opener.requests, [])
        self.assertEqual(rows[0]["failure_category"], "timeout")

    def test_refused_credentials_are_neither_sent_nor_saved(self):
        opener = FakeOpener({})
        urls = ["https://user:secret-password@example.invalid/", "https://example.invalid/?api_key=secret-query#secret-fragment"]
        for i, url in enumerate(urls):
            rows = self.capture([{"id": str(i), "url": url}], opener, session=self.session)
            self.assertEqual(rows[0]["failure_category"], "refused_credential_url")
            self.assertNotIn("secret-", json.dumps(rows))
            self.assertNotIn("secret-", (self.root / "web" / (str(i) + ".json")).read_text())
        self.assertEqual(opener.requests, [])
        self.assertEqual(self.session.status()["started_attempts"], 0)

    def test_redirect_to_credentials_is_refused_and_redacted(self):
        moved = urllib.error.HTTPError("https://example.invalid/", 302, "redirect",
                                      {"Location": "https://user:secret-password@next.invalid/?api_key=secret-query"}, io.BytesIO())
        opener = FakeOpener({"https://example.invalid/": moved})
        rows = self.capture([{"id": "a", "url": "https://example.invalid/"}], opener, session=self.session)
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(rows[0]["failure_category"], "refused_credential_url")
        self.assertNotIn("secret-", json.dumps(rows))

    def test_body_finishing_after_deadline_is_not_accepted(self):
        now = [0.0]

        class LateBody(FakeResponse):
            def read1(self, size):
                value = super().read1(size)
                now[0] = 0.5 if value else 1.1
                return value

        class Opener:
            def open(self, request, timeout=None):
                return LateBody(b'{}')

        out = self.root / "late"
        out.mkdir()
        with patch("web_capture.time.monotonic", side_effect=lambda: now[0]):
            row = capture_one({"id": "a", "url": "https://example.invalid/"}, out, timeout=1, opener=Opener())
        self.assertEqual(row["failure_category"], "timeout")
        self.assertIsNone(row["raw"])

    def test_budget_acquisition_cannot_start_a_request_after_deadline(self):
        now = [0.0]
        opener = FakeOpener({})

        def acquired_late():
            now[0] = 1.1
            return True

        out = self.root / "late-budget"
        out.mkdir()
        with patch("web_capture.time.monotonic", side_effect=lambda: now[0]):
            row = capture_one({"id": "a", "url": "https://example.invalid/"}, out, timeout=1, opener=opener, acquire=acquired_late)
        self.assertEqual(row["failure_category"], "timeout")
        self.assertEqual(opener.requests, [])


class RestartBudgetTests(unittest.TestCase):
    def test_identical_restart_carries_failed_attempts_forward(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            observed = []

            def fail(pipeline):
                pipeline.session.acquire("eth_chainId")
                observed.append(pipeline.session.status())
                raise broad_collect.StartFailure({"stage": "chain_check", "category": "timeout", "message": "synthetic timeout"})

            argv = ["broad_collect.py", "start", "--run", str(root), "--chain-id", str(CHAIN), "--address", TOKEN, "--question", "q", "--no-web"]
            with patch.object(sys, "argv", argv), patch("broad_collect.provider_availability", return_value={"status": "ready"}), \
                    patch("broad_collect.configured_transport", return_value=PipelineRpc()), patch.object(broad_collect.Pipeline, "run_all", fail), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(broad_collect.main(), 2)
                self.assertEqual(broad_collect.main(), 2)
            self.assertEqual([s["started_attempts"] for s in observed], [1, 2])
            for key in ("investigation_id", "request_ceiling", "deadline_ceiling_unix", "deadline_unix"):
                self.assertEqual(observed[0][key], observed[1][key])

    def test_archive_preserves_original_session_limits_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = Investigation.create(root / "session.sqlite", 10, 60)
            session.acquire("discovery_web")
            before = session.status()
            session.close()
            (root / "start-failed.json").write_text('{"status":"start_failed"}')
            broad_collect.archive_failed_attempt(root)
            reopened = Investigation(root / "session.sqlite")
            try:
                after = reopened.status()
                for key in ("investigation_id", "started_attempts", "request_limit", "deadline_unix", "request_ceiling", "deadline_ceiling_unix"):
                    self.assertEqual(after[key], before[key])
            finally:
                reopened.close()
            self.assertTrue((root / "failed-attempt-1" / "session.sqlite").is_file())

    def test_refused_existing_directory_is_never_marked_restartable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "evidence.json"
            existing.write_text('{"preserve":true}')
            argv = ["broad_collect.py", "start", "--run", str(root), "--chain-id", str(CHAIN), "--address", TOKEN, "--question", "q"]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(broad_collect.main(), 2)
            self.assertEqual(list(root.iterdir()), [existing])


class DiscoveryBoundaryTests(unittest.TestCase):
    def pipeline(self, root):
        return broad_collect.Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "q", "m", PipelineRpc(), None, None,
                                      fetch=fake_fetch, synthetic=True, registry=REGISTRY)

    def test_missing_market_fields_are_unknown_and_real_zero_remains_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self.pipeline(Path(tmp))
            pipeline.pairs = [{"pair": POOL}]
            result = pipeline.maturity([])
            self.assertIsNone(result["indexed_liquidity_usd"])
            self.assertIsNone(result["indexed_volume_h24_usd"])
            self.assertIsNone(result["indexed_txns_h24"]["sells"])
            pipeline.pairs = [{"pair": POOL, "liquidity_usd": 0, "volume_h24": 0, "txns_h24": {"buys": 0, "sells": 0}}]
            result = pipeline.maturity([])
            self.assertEqual(result["indexed_liquidity_usd"], 0)
            self.assertEqual(result["indexed_txns_h24"]["sells"], 0)

    def test_malformed_indexer_shapes_do_not_abort_pinned_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self.pipeline(Path(tmp))
            for value in (42, None, "error", {"pairs": 4}, {"pairs": [None]}):
                pipeline.parse_pairs(value)
            pair = {"baseToken": {"address": TOKEN}, "quoteToken": {"address": QUOTE}, "pairAddress": POOL,
                    "liquidity": "error", "volume": [], "info": {"websites": [None, 4]}, "txns": {"h24": "error"}}
            pipeline.parse_pairs([pair])
            self.assertIsNone(pipeline.pairs[0]["liquidity_usd"])
            pipeline.pairs = []
            pipeline.parse_pairs([{**pair, "chainId": "another-chain"}])
            self.assertEqual(pipeline.pairs, [])

    def test_creator_transfers_require_exact_asset_and_direction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "discovery").mkdir()
            pipeline = self.pipeline(root)
            pipeline.explorer_base = "https://example.invalid"

            def fetch(items, out):
                records = fake_fetch(items, out)
                body = {"items": [{"from": {"hash": CAROL}},
                                  {"from": {"hash": ALICE}, "to": {"hash": BOB}, "token": {"address": TOKEN}},
                                  {"from": {"hash": ALICE}, "to": {"hash": CAROL}, "token": {"address": TOKEN}}]}
                (out / "explorer-signer-token-transfers.raw").write_text(json.dumps(body))
                return records

            pipeline.fetch = fetch
            pipeline.capture_creator_activity(CAROL)
            self.assertEqual(pipeline.creator_activity["target_outbound"], 0)
            self.assertEqual(pipeline.creator_activity["target_inbound"], 1)

    def test_unavailable_creator_pages_never_report_zero_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "discovery").mkdir()
            pipeline = self.pipeline(root)
            pipeline.explorer_base = "https://example.invalid"

            def fetch(items, out):
                records = fake_fetch(items, out)
                for record in records:
                    record.update(http_status=200, failure_category="timeout", raw=None)
                return records

            pipeline.fetch = fetch
            pipeline.capture_creator_activity(CAROL)
            self.assertEqual(pipeline.creator_activity["status"], "unavailable")
            self.assertIsNone(pipeline.creator_activity["target_outbound"])
            self.assertIsNone(pipeline.creator_activity["calls_to_launch_factory"])


if __name__ == "__main__":
    unittest.main()
