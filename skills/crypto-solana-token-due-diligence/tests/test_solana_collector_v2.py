import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_collect_v2 import collect, summarize, run_bounded, queue, execute
from solana_presets import mint_baseline, read, settings, account_batches
from solana_session import Session, LimitError
from solana_wire import validate_response
from solana_fixture import Rpc, TARGET, KEY, OTHER


def terminated_worker(out, config, sample, rows, largest):
    execute(config["session"], config, sample, read("done", "getGenesisHash", []), factory=Rpc)
    session = Session(config["session"])
    session.acquire(sample+"_lost_0", sample+"_lost", "getAccountInfo", "synthetic", max_response_bytes=100)
    session.close()
    time.sleep(20)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        Rpc.calls, Rpc.active, Rpc.peak, Rpc.mode, Rpc.delay, Rpc.stamp = [], 0, 0, "normal", 0, int(time.time())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = Session.create(self.root/"session", TARGET, question="original", received_at=time.time()-1,
            deadline_at=time.time()+600, synthetic=True, max_requests=120, reservations={"final": 8})
        self.addCleanup(self.session.close)
        self.config = {"url": "https://synthetic.invalid", "headers": {}, "session": str(self.session.root)}

    def collect(self, sample="baseline"):
        collect(self.session.root, self.root, self.config, sample, mint_baseline(KEY), factory=Rpc, expand_largest=True)
        return summarize(self.session.root, sample)

    def test_batch_samples_have_exact_indices_mixed_slots_and_fresh_rechecks(self):
        Rpc.delay = .01
        packet = self.collect()
        self.assertEqual(packet["collection_status"], "captured", packet["gaps"])
        self.assertEqual({s["context_slot"] for s in packet["samples"]}, {100, 101, 102, 103})
        self.assertLessEqual(Rpc.peak, 3)
        self.assertGreater(Rpc.peak, 1)
        holdings = next(s for s in packet["samples"] if "holdings" in s["observation_id"])
        self.assertEqual(holdings["address_indices"], {KEY: 0, OTHER: 1})
        headers = [p for p in packet["observations"] if p["request"]["method"] == "getBlock"]
        self.assertEqual(len(headers), 8)
        for slot in (100, 101, 102, 103):
            initial, fresh = [p for p in headers if p["request"]["params"][0] == slot]
            self.assertGreater(fresh["started_at"], initial["completed_at"])
            self.assertNotEqual(fresh["attempt_id"], initial["attempt_id"])
        self.assertEqual(packet["research_status"], "unjudged")

    def test_wrong_network_stops_expansion_and_wrong_ids_never_become_facts(self):
        for mode in ("wrong_network", "wrong_id"):
            Rpc.mode = mode
            packet = self.collect(mode)
            self.assertEqual(packet["collection_status"], "partial")
            self.assertEqual(packet["samples"], [])
            self.assertTrue(all(p["request"]["method"] == "getGenesisHash" for p in packet["observations"]))

    def test_short_batch_changed_headers_and_changed_critical_state_are_partial(self):
        for mode, expected in (("short_batch", "critical account missing"), ("changed_header", "contradictory block"), ("changed_mint", "critical account changed")):
            self.session = Session.create(self.root/mode, TARGET, question="original", received_at=time.time()-1,
                deadline_at=time.time()+600, synthetic=True, max_requests=120, reservations={"final": 8})
            self.addCleanup(self.session.close)
            self.config["session"] = str(self.session.root)
            Rpc.mode, Rpc.calls = mode, []
            packet = self.collect(mode)
            self.assertEqual(packet["collection_status"], "partial", mode)
            self.assertTrue(any(expected in g.get("detail", "") for g in packet["gaps"]), packet["gaps"])

    def test_restart_resumes_named_capture_without_replenishing_retries(self):
        Rpc.mode = "timeout"
        row = read("network", "getGenesisHash", [])
        a = execute(self.session.root, self.config, "retry", row, factory=Rpc)
        b = execute(self.session.root, self.config, "retry", row, factory=Rpc)
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(len(Rpc.calls), 2)
        self.assertEqual(self.session.status()["started_attempts"], 2)

    def test_completed_sample_resume_preserves_grants_and_cached_bytes(self):
        first = self.collect()
        grants = self.session.status()["grants"]
        captures = {p.name: p.read_bytes() for p in (self.session.root/"observations").glob("*.json")}
        self.assertTrue(captures)
        second = self.collect()
        self.assertEqual(second["collection_status"], "captured", second["gaps"])
        self.assertEqual(first["observations"], second["observations"])
        self.assertEqual(self.session.status()["grants"], grants)
        self.assertEqual({p.name: p.read_bytes() for p in (self.session.root/"observations").glob("*.json")}, captures)

    def test_summary_failure_still_returns_partial_and_keeps_durable_replies(self):
        with patch("solana_collect_v2.summarize", side_effect=ValueError("synthetic summary failure")):
            packet = run_bounded(self.root/"out", self.config, TARGET, seconds=.6, sample="failed", worker_target=terminated_worker)
        self.assertEqual(packet["collection_status"], "partial")
        self.assertEqual(packet["gaps"][0]["reason"], "summary_failure")
        self.assertEqual(self.session.status()["started_attempts"], 2)
        self.assertIsNotNone(self.session.observations()[0]["response"])

    def test_sequential_and_batched_reads_return_identical_requested_facts(self):
        sequential = [read("a", "getAccountInfo", [KEY, settings()]),
                      read("b", "getAccountInfo", [OTHER, settings()], depends=["a"])]
        batches = account_batches([KEY, OTHER])
        def facts(result):
            facts = {}
            for packet in result.values():
                checked = validate_response(packet["request"], packet["response"])
                values = checked["result"]["value"]
                if packet["request"]["method"] == "getAccountInfo":
                    values = [values]
                facts.update({a: (checked["context_slot"], v) for a, v in zip(checked["addresses"], values)})
            return facts
        a = queue(self.session.root, self.config, "sequential", sequential, factory=Rpc)
        b = queue(self.session.root, self.config, "batched", batches, factory=Rpc)
        self.assertEqual(facts(a), facts(b))
        self.assertEqual(len(Rpc.calls), 3)

    def test_killed_worker_keeps_completed_reply_and_inflight_attempt(self):
        packet = run_bounded(self.root/"out", self.config, TARGET, seconds=.6, sample="killed", worker_target=terminated_worker)
        self.assertTrue(packet["timed_out"])
        self.assertEqual(packet["collection_status"], "partial")
        self.assertEqual(len(packet["observations"]), 1)
        self.assertEqual(self.session.status()["started_attempts"], 2)
        self.assertTrue((self.session.root/"read-intents"/"killed_done_0.json").exists())
        self.assertEqual(self.session.observations()[1]["status"], "started")
        with patch("solana_session.time.time", return_value=self.session.meta["collection_cutoff"]+1):
            with self.assertRaisesRegex(LimitError, "deadline"):
                self.session.acquire("late", "late", "getAccountInfo", "synthetic")
            self.session.recover_expired()
        self.assertEqual(self.session.observations()[1]["status"], "lost_worker")

    def test_public_rate_window_shared_across_restart_and_provider_namespaces(self):
        for i in range(40):
            ticket = self.session.acquire("r"+str(i), "f"+str(i), "getBlock", "first", max_response_bytes=1)
            self.session.finish(ticket["id"], "ok", 0)
        resumed = Session(self.session.root)
        try:
            with self.assertRaisesRegex(LimitError, "rate_window"):
                resumed.acquire("over", "over", "getBlock", "fallback", max_response_bytes=1)
        finally:
            resumed.close()

    def test_final_capacity_cannot_raise_ceiling_and_reservations_precede_reads(self):
        with self.assertRaises(ValueError):
            self.session.ensure_final_reserve(200, "too many contexts")
        self.assertEqual(self.session.status()["started_attempts"], 0)
        self.session.ensure_final_reserve(12, "four additional context checks")
        self.assertEqual(next(g["remaining"] for g in self.session.status()["grants"] if g["owner"] == "final"), 12)
        self.assertEqual(self.session.status()["max_requests"], 120)


if __name__ == "__main__":
    unittest.main()
