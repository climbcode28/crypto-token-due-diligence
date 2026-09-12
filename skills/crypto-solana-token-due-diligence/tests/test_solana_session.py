"""Durable multi-process allowances, original deadlines and recoverable attempts."""
import multiprocessing
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from solana_session import Session, LimitError
from solana_common import b58encode

TARGET = {"family": "solana", "genesis_hash": "1"*32, "mint": "1"*32}


def contend(root, start, owner):
    session = Session(root)
    try:
        for number in range(20):
            try:
                ticket = session.acquire(f"r-{start}-{number}", f"f-{start}-{number}", "getGenesisHash", "fixture",
                                         owner=owner, max_response_bytes=10)
                session.finish(ticket["id"], "ok", 5, {"result": "synthetic"})
            except LimitError:
                continue
    finally:
        session.close()


class SessionTests(unittest.TestCase):
    def create(self, **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "run"
        options = dict(question="full original question", received_at=time.time()-20,
                       deadline_at=time.time()+600, reservations={}, max_requests=10, synthetic=True)
        options.update(kwargs)
        session = Session.create(root, TARGET, **options)
        self.addCleanup(session.close)
        return session

    def acquire(self, session, name="one", **kwargs):
        return session.acquire(name, kwargs.pop("family", name), "getGenesisHash", "fixture",
                               max_response_bytes=kwargs.pop("max_response_bytes", 10), **kwargs)

    def test_parallel_processes_cannot_overspend_shared_or_lane_grants(self):
        for owner, grants, cap, expected in (("ordinary", {}, 7, 7), ("liquidity", {"liquidity": 4}, 10, 4)):
            with self.subTest(owner=owner):
                session = self.create(max_requests=cap, reservations=grants)
                context = multiprocessing.get_context("spawn")
                processes = [context.Process(target=contend, args=(str(session.root), i, owner)) for i in range(4)]
                for process in processes:
                    process.start()
                for process in processes:
                    process.join(10)
                    self.assertEqual(process.exitcode, 0)
                self.assertEqual(session.status()["started_attempts"], expected)
                self.assertEqual(session.status()["response_bytes"], expected*5)

    def test_zero_grant_and_reserved_final_capacity(self):
        session = self.create(max_requests=2, reservations={"liquidity": 0, "final": 1})
        with self.assertRaisesRegex(LimitError, "request_budget"):
            self.acquire(session, owner="liquidity")
        first = self.acquire(session)
        session.finish(first["id"], "timeout", 0)
        with self.assertRaisesRegex(LimitError, "request_budget"):
            self.acquire(session, "two")
        final = self.acquire(session, "recheck", owner="final")
        session.finish(final["id"], "ok", 0)
        self.assertEqual(session.status()["reserved_requests"], 0)
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            session.reserve("liquidity", 1)

    def test_retry_eligibility_survives_restart_and_stops_after_one_retry(self):
        session = self.create()
        ticket = self.acquire(session)
        session.finish(ticket["id"], "http_429", 0)
        resumed = Session(session.root, target=TARGET, synthetic=True)
        self.addCleanup(resumed.close)
        ticket = self.acquire(resumed, "retry", family="one", retry=True)
        resumed.finish(ticket["id"], "timeout", 0)
        with self.assertRaisesRegex(LimitError, "retry_ineligible"):
            self.acquire(resumed, "retry-again", family="one", retry=True)
        self.assertEqual(session.status()["investigation_id"], resumed.status()["investigation_id"])
        self.assertEqual(session.status()["received_at"], resumed.status()["received_at"])
        self.assertEqual(session.status()["deadline_at"], resumed.status()["deadline_at"])

    def test_bytes_reserved_before_parallel_send_and_released_at_completion(self):
        session = self.create(max_bytes=15)
        ticket = self.acquire(session)
        with self.assertRaisesRegex(LimitError, "byte_budget"):
            self.acquire(session, "two")
        session.finish(ticket["id"], "ok", 5)
        second = self.acquire(session, "two")
        session.finish(second["id"], "ok", 10)
        with self.assertRaisesRegex(LimitError, "byte_budget"):
            self.acquire(session, "three", max_response_bytes=1)
        self.assertEqual(session.status()["response_bytes"], 15)

    def test_late_response_and_lost_worker_keep_usage(self):
        session = self.create()
        ticket = self.acquire(session)
        with patch("solana_session.time.time", return_value=ticket["deadline"]+1):
            self.assertEqual(session.finish(ticket["id"], "ok", 4, {"fact": "late"}), "timeout")
        lost = self.acquire(session, "lost")
        with patch("solana_session.time.time", return_value=lost["deadline"]+1):
            session.recover_expired()
        self.assertEqual(session.status()["response_bytes"], 14)
        self.assertEqual(session.observations()[1]["status"], "lost_worker")

    def test_early_user_deadline_preserves_delivery_reserve(self):
        session = self.create(received_at=time.time()-20, deadline_at=time.time()+100, user_hard_deadline=True)
        with self.assertRaisesRegex(LimitError, "deadline"):
            self.acquire(session)
        self.assertEqual(session.status()["started_attempts"], 0)

    def test_replan_cannot_reset_bounds_or_usage(self):
        session = self.create()
        self.acquire(session)
        before = session.status()
        session.replan("a new relevant pool", {"optional_pool": "displaced"})
        for field in ("max_requests", "max_bytes", "deadline_at", "received_at", "target"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                session.replan("trigger", {field: 9999})
        self.assertEqual(session.status()["started_attempts"], before["started_attempts"])

    def test_existing_or_finalized_directories_are_unchanged(self):
        session = self.create()
        with self.assertRaises(FileExistsError):
            Session.create(session.root, TARGET, question="q", received_at=time.time(), deadline_at=time.time()+600)
        with self.assertRaisesRegex(ValueError, "target mismatch"):
            Session(session.root, target={**TARGET, "mint": b58encode(bytes([2])*32)})
        session.finalize()
        before = (session.root / "session.sqlite").read_bytes()
        with self.assertRaisesRegex(ValueError, "finalized"):
            self.acquire(session)
        self.assertEqual((session.root / "session.sqlite").read_bytes(), before)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / "keep").write_text("untouched")
            with self.assertRaises(ValueError):
                Session(path)
            self.assertEqual([x.name for x in path.iterdir()], ["keep"])

    def test_concurrency_caps_are_global_and_per_web_origin(self):
        session = self.create()
        for i in range(3):
            self.acquire(session, str(i))
        with self.assertRaisesRegex(LimitError, "concurrency"):
            self.acquire(session, "over")
        for i in range(2):
            self.acquire(session, "web"+str(i), transport_kind="web")
        with self.assertRaisesRegex(LimitError, "concurrency"):
            self.acquire(session, "web-over", transport_kind="web")

    def test_malformed_input_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/"run"
            for ceiling in (True, -1, float("inf"), "120"):
                with self.subTest(ceiling=ceiling), self.assertRaises(ValueError):
                    Session.create(root, TARGET, question="q", received_at=time.time(), deadline_at=time.time()+600, max_requests=ceiling)
                self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
