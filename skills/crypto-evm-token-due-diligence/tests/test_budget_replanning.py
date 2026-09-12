"""Bounded continuation survives bad estimates without resetting authorization or usage."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from investigation import Investigation, work_plan
from validate_bundle import DIMENSIONS


def plan(requests=30, seconds=60):
    return {"surfaces": [
        {"dimension": d, "state": "pending" if d == "historical_launch_integrity" else "resolved",
         "next_check": "Reconcile captured flows" if d == "historical_launch_integrity" else "Scoped review reconciled",
         "requests": requests if d == "historical_launch_integrity" else 0} for d in DIMENSIONS],
        "overhead_requests": 8, "contingency_requests": 12, "seconds_required": seconds}


class BudgetReplanningTests(unittest.TestCase):
    def create(self, root, maximum=200, ceiling=500):
        return Investigation.create(root / "session.sqlite", maximum, 600,
                                    request_ceiling=ceiling, timeout_ceiling=1800, limit_basis="analyst_safety")

    def test_exhausted_estimate_continues_same_investigation_and_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.create(Path(tmp))
            worker = Investigation(s.path)
            try:
                original_id = s.id
                for _ in range(200):
                    self.assertTrue(s.acquire("synthetic_read"))
                self.assertFalse(worker.acquire("synthetic_read"))
                review = s.review(plan())
                self.assertEqual(review["action"], "replan")
                self.assertFalse(review["final_delivery_eligible"])
                self.assertEqual(review["projected_total_attempts"], 250)
                s.replan(plan(), "Remaining required work exceeds the initial estimate")
                self.assertTrue(worker.acquire("synthetic_followup"))
                self.assertEqual(worker.id, original_id)
                self.assertEqual(s.status()["started_attempts"], 201)
                self.assertEqual(s.status()["request_ceiling"], 500)
                self.assertEqual(s.db.execute("SELECT count(*) FROM attempts").fetchone()[0], 201)
                self.assertEqual(s.db.execute("SELECT used FROM revisions").fetchone()[0], 200)
            finally:
                worker.close(); s.close()

    def test_shortfall_is_detected_before_exhaustion_including_overhead_and_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.create(Path(tmp), maximum=80)
            try:
                for _ in range(35):
                    s.acquire("synthetic_read")
                s.reserve("headers", 3)
                r = s.review(plan())
                self.assertEqual(r["action"], "replan")
                self.assertEqual(r["projected_total_attempts"], 88)
                s.replan(plan(), "Protect required follow-up and header reservations")
                self.assertEqual(s.counts(), (35, 3))
                self.assertTrue(s.acquire("synthetic_header", owner="headers", reserved=True))
            finally:
                s.close()

    def test_hard_ceiling_is_not_an_external_evidence_boundary_or_renewable_allowance(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.create(Path(tmp), maximum=20, ceiling=40)
            try:
                before = s.status()
                self.assertEqual(s.review(plan())["action"], "limit_review_required")
                with self.assertRaisesRegex(ValueError, "existing ceilings"):
                    s.replan(plan(), "Research remains")
                after = s.status()
                for key in ("request_limit", "request_ceiling", "deadline_unix", "deadline_ceiling_unix", "started_attempts"):
                    self.assertEqual(before[key], after[key])
                self.assertEqual(s.db.execute("SELECT count(*) FROM revisions").fetchone()[0], 0)
            finally:
                s.close()

    def test_operational_timeout_can_extend_but_original_hard_deadline_cannot(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("investigation.time.time", return_value=1000):
                s = Investigation.create(Path(tmp) / "session.sqlite", 80, 10,
                                         request_ceiling=100, timeout_ceiling=100, limit_basis="user")
            try:
                with patch("investigation.time.time", return_value=1020):
                    self.assertFalse(s.acquire("synthetic_read"))
                    self.assertEqual(s.review(plan(seconds=30))["action"], "replan")
                    s.replan(plan(seconds=30), "Continue inside the user deadline")
                    self.assertEqual(s.deadline, 1050)
                    self.assertEqual(s.deadline_ceiling, 1100)
                    self.assertTrue(s.acquire("synthetic_read"))
                with patch("investigation.time.time", return_value=1101):
                    self.assertEqual(s.review(plan(seconds=30))["action"], "limit_review_required")
                    with self.assertRaises(ValueError):
                        s.replan(plan(seconds=30), "Cannot exceed the deadline")
            finally:
                s.close()

    def test_fixed_and_legacy_sessions_keep_their_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Investigation.create(Path(tmp) / "session.sqlite", 20, 600)
            try:
                self.assertEqual(s.review(plan())["action"], "limit_review_required")
                with self.assertRaises(ValueError):
                    s.replan(plan(), "No extra authorization")
                with s.db:
                    s.db.execute("PRAGMA user_version=1")
                s.close()
                s = Investigation(Path(tmp) / "session.sqlite")
                with self.assertRaisesRegex(ValueError, "legacy fixed"):
                    s.review(plan())
                self.assertEqual(s.max_requests, 20)
                self.assertTrue(s.acquire("synthetic_read"))
            finally:
                s.close()

    def test_missing_duplicate_and_understated_surfaces_are_rejected(self):
        for change in ("missing", "duplicate", "negative", "closed_cost", "boolean", "no_time"):
            p = plan()
            if change == "missing": p["surfaces"].pop()
            if change == "duplicate": p["surfaces"][-1] = copy.deepcopy(p["surfaces"][0])
            if change == "negative": p["overhead_requests"] = -1
            if change == "closed_cost": p["surfaces"][0].update(state="resolved", requests=5)
            if change == "boolean": p["contingency_requests"] = True
            if change == "no_time": p["seconds_required"] = 0
            with self.subTest(change=change), self.assertRaises(ValueError):
                work_plan(p)

    def test_zero_request_pending_work_stays_active_and_estimates_never_certify_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.create(Path(tmp))
            try:
                p = plan(0)
                p.update(overhead_requests=0, contingency_requests=0)
                self.assertEqual(s.review(p)["action"], "continue")
                for row in p["surfaces"]: row["state"] = "externally_bounded"
                p["seconds_required"] = 0
                r = s.review(p)
                self.assertEqual(r["action"], "completion_review_required")
                self.assertFalse(r["final_delivery_eligible"])
            finally:
                s.close()

    def test_cli_review_and_replan_keep_charges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = Path(__file__).resolve().parents[1] / "scripts/investigation.py"
            def run(*args):
                return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True)
            path = root / "session.sqlite"
            self.assertEqual(run("init", path, "--max-requests", 20, "--timeout", 300,
                                 "--request-ceiling", 100, "--timeout-ceiling", 600, "--limit-basis", "analyst_safety").returncode, 0)
            self.assertEqual(run("charge", path, "--operation", "synthetic_web", "--count", 10).returncode, 0)
            (root / "plan.json").write_text(json.dumps(plan()))
            review = run("review", path, "--plan", root / "plan.json")
            self.assertEqual(json.loads(review.stdout)["action"], "replan")
            revised = run("replan", path, "--plan", root / "plan.json", "--reason", "Required follow-up")
            self.assertEqual(revised.returncode, 0, revised.stderr)
            self.assertEqual(json.loads(revised.stdout)["started_attempts"], 10)
            self.assertEqual(json.loads(revised.stdout)["request_limit"], 60)
            rejected = run("replan", path, "--plan", root / "plan.json", "--reason", "New estimate", "--request-ceiling", 1000)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn('valid only for init', rejected.stderr)
            unchanged = json.loads(run('status', path).stdout)
            self.assertEqual(unchanged['request_ceiling'], 100)
            self.assertEqual(unchanged['started_attempts'], 10)


if __name__ == "__main__":
    unittest.main()
