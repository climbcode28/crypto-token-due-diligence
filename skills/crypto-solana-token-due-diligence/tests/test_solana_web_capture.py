import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_web_capture import register_urls, capture_one, capture, clean_url, response_backoff, RATES
from solana_session import Session
from solana_fixture import TARGET


class Response(io.BytesIO):
    def __init__(self, body, code=200, headers=None, delay=0):
        super().__init__(body)
        self.status, self.headers, self.delay = code, headers or {"Content-Type": "application/json"}, delay

    def read1(self, count):
        time.sleep(self.delay)
        return super().read(count)


class Opener:
    def __init__(self, responses, delay=0):
        self.responses, self.calls, self.delay = list(responses), [], delay
        self.lock = threading.Lock()

    def open(self, request, timeout):
        with self.lock:
            self.calls.append(request)
            code, body, headers = self.responses.pop(0)
        response = Response(body, code, headers, self.delay)
        if code != 200:
            raise urllib.error.HTTPError(request.full_url, code, "synthetic", response.headers, response)
        return response


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.question = "Check all controls and the original project https://example.org/project and its audit."
        self.session = Session.create(self.root/"session", TARGET, question=self.question,
            urls=["https://example.org/project", "https://example.org/audit"], received_at=time.time()-1,
            deadline_at=time.time()+600, synthetic=True, reservations={"liquidity": 4, "project": 2, "final": 2})
        self.addCleanup(self.session.close)

    def source(self, url="https://example.org/start", owner="ordinary"):
        return register_urls(self.session, [url], owners={url: owner})[0]["source_id"]

    def test_redirect_retry_and_repeated_batch_share_one_finite_ledger(self):
        source = self.source(owner="liquidity")
        opener = Opener([(302, b"", {"Location": "/end"}), (429, b"slow", {}), (200, b'{"ok":true}', {})])
        first = capture_one(self.session.root, source, owner="liquidity", opener=opener)
        self.assertEqual(first["status"], "ok")
        self.assertEqual(len(first["attempts"]), 3)
        self.assertEqual(self.session.status()["started_attempts"], 3)
        self.assertEqual(self.session.status()["response_bytes"], 15)
        again = capture_one(self.session.root, source, owner="liquidity", opener=opener)
        self.assertEqual(first, again)
        self.assertEqual(len(opener.calls), 3)
        self.assertEqual(next(g["remaining"] for g in self.session.status()["grants"] if g["owner"] == "liquidity"), 1)
        self.assertTrue(all("Authorization" not in r.headers for r in opener.calls))

    def test_zero_grants_and_owner_mismatch_send_nothing(self):
        self.session.reserve("contingency", 0)
        source = self.source(owner="contingency")
        opener = Opener([])
        self.assertEqual(capture_one(self.session.root, source, owner="contingency", opener=opener)["status"], "budget_denied")
        with self.assertRaises(ValueError):
            capture_one(self.session.root, source, owner="ordinary", opener=opener)
        self.assertEqual(opener.calls, [])

    def test_secret_urls_and_redirects_do_not_persist_credentials(self):
        secret = "never-persist-this-private-secret-123"
        for url in ("https://user:"+secret+"@example.org", "https://example.org?api_key="+secret):
            source = self.source(url)
            self.assertEqual(capture_one(self.session.root, source, opener=Opener([]))["status"], "refused_url")
        source = self.source()
        opener = Opener([(302, b"", {"Location": "https://example.org?auth="+secret})])
        self.assertEqual(capture_one(self.session.root, source, opener=opener)["status"], "refused_redirect")
        for path in self.session.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(secret.encode(), path.read_bytes(), path)
        with self.assertRaises(ValueError):
            Session.create(self.root/"unsafe", TARGET, question="See https://example.org?api_key="+secret,
                received_at=time.time(), deadline_at=time.time()+600)
        self.assertFalse((self.root/"unsafe").exists())

    def test_all_asks_links_and_cap_statuses_survive_deduplication(self):
        urls = self.session.meta["urls"]+["https://EXAMPLE.org:443/project#section", "https://example.org/extra"]
        entries = register_urls(self.session, urls, cap=1)
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[0]["source_id"], entries[2]["source_id"])
        self.assertEqual(entries[1]["status"], "unattempted_cap")
        self.assertEqual(entries[3]["status"], "unattempted_cap")
        self.assertEqual(self.session.meta["question"], self.question)
        self.assertEqual(self.session.db.execute("SELECT count(*) FROM web_intake").fetchone()[0], 4)
        with self.assertRaises(ValueError):
            register_urls(self.session, [urls[0]], owners={urls[0]: "project"})

    def test_error_raw_bytes_and_javascript_shell_are_access_evidence(self):
        source = self.source()
        result = capture_one(self.session.root, source, opener=Opener([(403, b"denied", {})]))
        self.assertEqual(result["status"], "http_403")
        self.assertEqual((self.session.root/result["raw"]).read_bytes(), b"denied")
        source = self.source("https://example.org/shell")
        result = capture_one(self.session.root, source, opener=Opener([(200, b"<script>loading</script>", {"Content-Type": "text/html"})]))
        self.assertTrue(result["shell_suspected"])

    def test_response_bytes_never_overflow_and_redirects_are_bounded(self):
        source = self.source()
        result = capture_one(self.session.root, source, opener=Opener([(200, b"123456", {})]), max_bytes=4)
        self.assertEqual(result["status"], "response_limit")
        self.assertEqual(result["bytes"], 4)
        source = self.source("https://example.org/loop")
        opener = Opener([(302, b"", {"Location": "/loop"})]*4)
        result = capture_one(self.session.root, source, opener=opener)
        self.assertEqual(result["status"], "redirect_limit")
        self.assertEqual(len(opener.calls), 4)

    def test_public_url_validation_and_parallel_capture(self):
        for url in ("http://example.org", "https://127.0.0.1", "https://[::1]", "https://localhost", "https://host.local"):
            with self.assertRaises(ValueError):
                clean_url(url)
        ids = [self.source("https://example.org/"+str(i)) for i in range(4)]
        opener = Opener([(200, b"{}", {})]*4, delay=.01)
        results = capture(self.session.root, ids, opener_factory=lambda: opener)
        self.assertTrue(all(r["status"] == "ok" for r in results))
        self.assertEqual(len(opener.calls), 4)

    def test_provider_window_is_shared_and_no_new_deadline_reads(self):
        sources = [self.source("https://api.geckoterminal.com/"+str(i)) for i in range(11)]
        opener = Opener([(200, b"{}", {})]*10)
        results = [capture_one(self.session.root, source, opener=opener) for source in sources]
        self.assertEqual(results[-1]["status"], "budget_denied")
        self.assertEqual(len(opener.calls), 10)
        source = self.source("https://example.org/late")
        with patch("solana_session.time.time", return_value=self.session.meta["collection_cutoff"]+1):
            result = capture_one(self.session.root, source, opener=opener)
        self.assertEqual(result["status"], "budget_denied")
        self.assertEqual(len(opener.calls), 10)

    def test_retry_after_survives_restart_and_retains_both_failure_and_success(self):
        source = self.source()
        opener = Opener([(429, b"slow", {"Retry-After": "30"}), (200, b"{}", {})])
        first = capture_one(self.session.root, source, opener=opener)
        self.assertEqual(first["status"], "http_429")
        original = (self.session.root/first["raw"]).read_bytes()
        denied = capture_one(self.session.root, source, opener=opener)
        self.assertEqual(denied["status"], "http_429")
        self.assertEqual(len(opener.calls), 1)
        with patch("solana_web_capture.time.time", return_value=time.time()+31):
            later = capture_one(self.session.root, source, opener=opener)
        self.assertEqual(later["status"], "ok")
        self.assertEqual(len(opener.calls), 2)
        self.assertNotEqual(later["raw"], first["raw"])
        self.assertEqual((self.session.root/first["raw"]).read_bytes(), original)

    def test_github_exhaustion_on_success_defers_other_paths_without_probe(self):
        source = self.source("https://api.github.com/repos/example/one")
        next_source = self.source("https://api.github.com/repos/example/two")
        reset = int(time.time())+180
        opener = Opener([(200, b"{}", {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)})])
        self.assertEqual(capture_one(self.session.root, source, opener=opener)["status"], "ok")
        denied = capture_one(self.session.root, next_source, opener=opener)
        self.assertEqual(denied["reason"], "source_backoff")
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(RATES["api.github.com"], (60, 3600))
        with patch("solana_web_capture.time.time", return_value=100):
            self.assertEqual(response_backoff("api.github.com", 403, {}), 160)
            self.assertEqual(response_backoff("api.github.com", 429, {"Retry-After": "30"}), 130)
            self.assertEqual(response_backoff("api.github.com", 403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "200"}), 200)
            self.assertIsNone(response_backoff("example.org", 403, {}))


if __name__ == "__main__":
    unittest.main()
