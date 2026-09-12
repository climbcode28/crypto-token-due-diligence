#!/usr/bin/env python3
"""Persistent per-investigation request/deadline accounting; never grants permission."""
import argparse
import json
import math
import sqlite3
import sys
import time
import uuid
from pathlib import Path

from validate_bundle import DIMENSIONS, integer, need


def work_plan(plan):
    """Validate estimates, not evidence or research completion. Zero-read work is valid."""
    need(isinstance(plan, dict) and set(plan) == {"surfaces", "overhead_requests", "contingency_requests", "seconds_required"},
         "plan needs all surfaces, overhead, contingency and remaining seconds")
    for key in ("overhead_requests", "contingency_requests", "seconds_required"):
        integer(plan[key], key, 0)
    rows = plan["surfaces"]
    need(isinstance(rows, list) and len(rows) == len(DIMENSIONS), "plan must cover all eleven surfaces")
    seen, pending, requests = set(), [], plan["overhead_requests"] + plan["contingency_requests"]
    for row in rows:
        need(isinstance(row, dict) and set(row) == {"dimension", "state", "next_check", "requests"}, "invalid planned surface")
        dimension = row["dimension"]
        need(isinstance(dimension, str) and dimension in DIMENSIONS and dimension not in seen, "duplicate or unknown planned surface")
        seen.add(dimension)
        need(row["state"] in ("pending", "resolved", "externally_bounded"), "invalid planned state")
        need(isinstance(row["next_check"], str) and 0 < len(row["next_check"].strip()) <= 1000, "planned check/boundary required")
        integer(row["requests"], "planned requests", 0)
        if row["state"] == "pending":
            pending.append(dimension)
        else:
            need(row["requests"] == 0, "closed planned surface cannot reserve more research")
        requests += row["requests"]
    need(not pending or plan["seconds_required"] > 0, "pending work needs a remaining time estimate")
    return requests, pending


class Investigation:
    def __init__(self, path):
        self.path = Path(path).resolve()
        need(self.path.is_file(), "investigation session does not exist; initialize a fresh session")
        self.db = sqlite3.connect(self.path, timeout=10)
        self.schema = self.db.execute("PRAGMA user_version").fetchone()[0]
        need(self.schema in (1, 2, 3), "unsupported investigation schema")
        self._refresh()

    def _refresh(self):
        row = self.db.execute("SELECT id,max_requests,deadline FROM session WHERE singleton=1").fetchone()
        need(row is not None, "session is incomplete")
        previous = getattr(self, "deadline", None)
        self.id, self.max_requests, self.deadline = row
        if previous != self.deadline:
            self.monotonic_deadline = time.monotonic() + max(0, self.deadline - time.time())
        if self.schema >= 2:
            self.request_ceiling, self.deadline_ceiling, self.limit_basis = self.db.execute(
                "SELECT request_ceiling,deadline_ceiling,limit_basis FROM bounds WHERE singleton=1").fetchone()
        else:
            self.request_ceiling, self.deadline_ceiling, self.limit_basis = self.max_requests, self.deadline, "legacy_fixed"

    @classmethod
    def create(cls, path, max_requests, timeout, *, request_ceiling=None, timeout_ceiling=None, limit_basis=None):
        integer(max_requests, "investigation request limit", 1)
        need(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0, "invalid investigation timeout")
        planned = request_ceiling is not None or timeout_ceiling is not None or limit_basis is not None
        if planned:
            integer(request_ceiling, "request ceiling", max_requests)
            need(type(timeout_ceiling) in (int, float) and math.isfinite(timeout_ceiling) and timeout_ceiling >= timeout,
                 "timeout ceiling must cover the operational timeout")
            need(limit_basis in ("user", "provider", "analyst_safety"), "explicit ceiling basis required")
        else:
            request_ceiling, timeout_ceiling, limit_basis = max_requests, timeout, "fixed"
        started = time.time()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb"):
            pass
        db = sqlite3.connect(path)
        try:
            db.executescript("""
                CREATE TABLE session(singleton INTEGER PRIMARY KEY CHECK(singleton=1), id TEXT NOT NULL,
                                     max_requests INTEGER NOT NULL, deadline REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE attempts(id INTEGER PRIMARY KEY, operation TEXT NOT NULL, started_at REAL NOT NULL);
                CREATE TABLE reservations(owner TEXT PRIMARY KEY, count INTEGER NOT NULL CHECK(count>=0));
                CREATE TABLE bounds(singleton INTEGER PRIMARY KEY CHECK(singleton=1), request_ceiling INTEGER NOT NULL,
                                    deadline_ceiling REAL NOT NULL, limit_basis TEXT NOT NULL);
                CREATE TABLE reviews(id INTEGER PRIMARY KEY, recorded_at REAL NOT NULL, used INTEGER NOT NULL,
                                     plan TEXT NOT NULL, assessment TEXT NOT NULL);
                CREATE TABLE revisions(id INTEGER PRIMARY KEY, recorded_at REAL NOT NULL, used INTEGER NOT NULL,
                                       reason TEXT NOT NULL, plan TEXT NOT NULL, before_limits TEXT NOT NULL, after_limits TEXT NOT NULL);
                CREATE TABLE timeline(id INTEGER PRIMARY KEY, phase TEXT NOT NULL, recorded_at REAL NOT NULL, used INTEGER NOT NULL);
                PRAGMA user_version=3;
            """)
            with db:
                db.execute("INSERT INTO session(singleton,id,max_requests,deadline) VALUES(1,?,?,?)", (str(uuid.uuid4()), max_requests, started + timeout))
                db.execute("INSERT INTO bounds VALUES(1,?,?,?)", (request_ceiling, started + timeout_ceiling, limit_basis))
        finally:
            db.close()
        return cls(path)

    def close(self):
        self.db.close()

    def remaining_seconds(self):
        self._refresh()
        return max(0, min(self.deadline - time.time(), self.monotonic_deadline - time.monotonic()))

    def counts(self):
        used = self.db.execute("SELECT used FROM session WHERE singleton=1").fetchone()[0]
        reserved = self.db.execute("SELECT coalesce(sum(count),0) FROM reservations").fetchone()[0]
        return used, reserved

    def ensure(self, minimum):
        integer(minimum, "required reads", 0)
        used, reserved = self.counts()
        need(self.remaining_seconds() > 0 and used + reserved + minimum <= self.max_requests,
             "investigation budget/deadline cannot cover required reads")

    def reserve(self, owner, count):
        integer(count, "reserved requests")
        try:
            self.db.execute("BEGIN IMMEDIATE")
            used, reserved = self.counts()
            need(self.remaining_seconds() > 0 and used + reserved + count <= self.max_requests, "investigation reserve unavailable")
            self.db.execute("INSERT INTO reservations VALUES(?,?)", (owner, count))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def release(self, owner):
        with self.db:
            self.db.execute("DELETE FROM reservations WHERE owner=?", (owner,))

    def acquire(self, operation, reserve=0, owner=None, reserved=False):
        """Count each started method, including errors; reserved rechecks consume their lease."""
        need(isinstance(operation, str) and 0 < len(operation) <= 80 and operation.replace("_", "").isalnum(), "invalid operation label")
        integer(reserve, "reserve")
        try:
            self.db.execute("BEGIN IMMEDIATE")
            used, held = self.counts()
            own = self.db.execute("SELECT count FROM reservations WHERE owner=?", (owner,)).fetchone() if reserved else None
            permitted = self.remaining_seconds() > 0 and used < self.max_requests
            permitted &= bool(own and own[0] > 0) if reserved else used + held + reserve < self.max_requests
            if permitted:
                self.db.execute("INSERT INTO attempts(operation,started_at) VALUES(?,?)", (operation, time.time()))
                self.db.execute("UPDATE session SET used=used+1 WHERE singleton=1")
                if reserved:
                    self.db.execute("UPDATE reservations SET count=count-1 WHERE owner=?", (owner,))
            self.db.commit()
            return bool(permitted)
        except Exception:
            self.db.rollback()
            raise

    def mark(self, phase):
        """Record a wall-clock phase boundary for the run's own benchmark; never a budget change."""
        need(self.schema >= 3, "phase timeline requires investigation schema 3")
        need(isinstance(phase, str) and 0 < len(phase) <= 40 and phase.replace("_", "").isalnum(), "invalid phase label")
        with self.db:
            used, _ = self.counts()
            self.db.execute("INSERT INTO timeline(phase,recorded_at,used) VALUES(?,?,?)", (phase, time.time(), used))
        return self.timeline()

    def timeline(self):
        if self.schema < 3:
            return []
        rows = self.db.execute("SELECT phase,recorded_at,used FROM timeline ORDER BY id").fetchall()
        origin = rows[0][1] if rows else None
        return [{"phase": phase, "recorded_at": round(at, 3), "elapsed_seconds": round(at - origin, 3), "used": used}
                for phase, at, used in rows]

    def status(self):
        self._refresh()
        used, reserved = self.counts()
        return {"schema_version": self.schema, "investigation_id": self.id, "request_limit": self.max_requests,
                "started_attempts": used, "reserved_requests": reserved,
                "remaining_requests": max(0, self.max_requests - used - reserved),
                "remaining_seconds": round(self.remaining_seconds(), 3), "deadline_unix": self.deadline,
                "request_ceiling": self.request_ceiling, "deadline_ceiling_unix": self.deadline_ceiling,
                "limit_basis": self.limit_basis,
                "replanning_available": self.schema >= 2 and (self.max_requests < self.request_ceiling or self.deadline < self.deadline_ceiling),
                "phases": self.timeline(),
                "authorization": "Current trusted policy and invocation gates remain required"}

    def _assess(self, plan):
        requests, pending = work_plan(plan)
        s = self.status()
        projected = s["started_attempts"] + s["reserved_requests"] + requests
        duration = plan["seconds_required"]
        ceiling_fits = projected <= self.request_ceiling and time.time() + duration <= self.deadline_ceiling
        active_fits = projected <= self.max_requests and duration <= s["remaining_seconds"]
        action = "continue" if active_fits else "replan" if ceiling_fits else "limit_review_required"
        if not pending and requests == 0:
            action = "completion_review_required"
        return {"action": action, "projected_total_attempts": projected, "remaining_request_need": requests,
                "pending_dimensions": pending, "session": s,
                "final_delivery_eligible": False}  # Estimates can never certify completion.

    def review(self, plan):
        need(self.schema >= 2, "legacy fixed sessions cannot be replanned; retain their original limits")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            result = self._assess(plan)
            self.db.execute("INSERT INTO reviews(recorded_at,used,plan,assessment) VALUES(?,?,?,?)",
                            (time.time(), result["session"]["started_attempts"], json.dumps(plan), json.dumps(result)))
        return result

    def replan(self, plan, reason):
        """Coordinator-only explicit revision inside immutable bounds; never resets usage."""
        need(self.schema >= 2, "legacy fixed sessions cannot be replanned; retain their original limits")
        need(isinstance(reason, str) and 0 < len(reason.strip()) <= 1000, "bounded replanning reason required")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            result = self._assess(plan)
            need(result["action"] == "replan", "replan requires a shortfall that fits the existing ceilings; review limits otherwise")
            before = {"max_requests": self.max_requests, "deadline": self.deadline}
            after = {"max_requests": max(self.max_requests, result["projected_total_attempts"]),
                     "deadline": max(self.deadline, time.time() + plan["seconds_required"])}
            need(after["max_requests"] <= self.request_ceiling and after["deadline"] <= self.deadline_ceiling,
                 "replan cannot increase an immutable ceiling")
            self.db.execute("UPDATE session SET max_requests=?,deadline=? WHERE singleton=1", (after["max_requests"], after["deadline"]))
            self.db.execute("INSERT INTO revisions(recorded_at,used,reason,plan,before_limits,after_limits) VALUES(?,?,?,?,?,?)",
                            (time.time(), result["session"]["started_attempts"], reason, json.dumps(plan), json.dumps(before), json.dumps(after)))
        return self.status()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("init", "status", "charge", "review", "replan", "mark"))
    p.add_argument("path", type=Path)
    p.add_argument("--max-requests", type=int)
    p.add_argument("--timeout", type=float)
    p.add_argument("--request-ceiling", type=int)
    p.add_argument("--timeout-ceiling", type=float)
    p.add_argument("--limit-basis", choices=("user", "provider", "analyst_safety"))
    p.add_argument("--plan", type=Path, help="remaining broad work estimates; never token evidence")
    p.add_argument("--reason", help="sanitized explanation of an explicit operational revision")
    p.add_argument("--operation", help="sanitized label for an external API/browser operation")
    p.add_argument("--count", type=int)
    p.add_argument("--phase", help="phase label for mark (intake, discovery, phase1, phase2, lanes_spawned, lanes_returned, composed, frozen, delivered)")
    args = p.parse_args()
    session = None
    try:
        if args.action != "init":
            need(all(value is None for value in (args.max_requests, args.timeout, args.request_ceiling, args.timeout_ceiling, args.limit_basis)),
                 "initial limit options are valid only for init; use reviewed replan for operational changes")
        need(args.plan is None or args.action in ("review", "replan"), "--plan is valid only for review/replan")
        need(args.reason is None or args.action == "replan", "--reason is valid only for replan")
        need((args.operation is None and args.count is None) or args.action == "charge", "operation/count are valid only for charge")
        need((args.phase is None) == (args.action != "mark"), "--phase is required for mark and valid only there")
        session = Investigation.create(args.path, args.max_requests, args.timeout, request_ceiling=args.request_ceiling,
                                       timeout_ceiling=args.timeout_ceiling, limit_basis=args.limit_basis) if args.action == "init" else Investigation(args.path)
        if args.action in ("review", "replan"):
            need(args.plan is not None and args.plan.stat().st_size <= 65536, "bounded plan file required")
            plan = json.loads(args.plan.read_text())
            result = session.review(plan) if args.action == "review" else session.replan(plan, args.reason)
            print(json.dumps(result, sort_keys=True))
            return 0
        if args.action == "mark":
            print(json.dumps(session.mark(args.phase), sort_keys=True))
            return 0
        if args.action == "charge":
            args.count = 1 if args.count is None else args.count
            integer(args.count, "external request count", 1)
            need(args.count <= 100, "charge at most 100 external requests at once")
            owner = str(uuid.uuid4())
            session.reserve(owner, args.count)
            try:
                for _ in range(args.count):
                    need(session.acquire(args.operation, owner=owner, reserved=True), "external operation budget exhausted")
            finally:
                session.release(owner)
        print(json.dumps(session.status(), sort_keys=True))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print("Investigation failed: " + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__), file=sys.stderr)
        return 2
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
