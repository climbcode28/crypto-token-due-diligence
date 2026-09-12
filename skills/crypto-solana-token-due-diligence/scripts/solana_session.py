"""Durable finite Solana investigation grants; no network or implicit authorization."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import uuid

from solana_common import need, target_identity

SCHEMA = 1
TRANSIENT = {"timeout", "transport_failure", "http_429", "http_502", "http_503", "http_504"}
OWNERS = {"ordinary", "liquidity", "project", "final", "contingency"}


class LimitError(ValueError):
    """A typed refusal, never a passing research check."""


def integer(value, name, minimum=0, maximum=2**63-1):
    need(type(value) is int and minimum <= value <= maximum, "invalid " + name)
    return value


def label(value):
    need(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value), "invalid label")
    return value


def epoch(value):
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        need(parsed.tzinfo is not None, "time requires timezone")
        value = parsed.timestamp()
    need(type(value) in (int, float) and math.isfinite(value) and value >= 0, "invalid absolute time")
    return float(value)


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Session:
    def __init__(self, root, *, target=None, synthetic=None):
        self.root = Path(root).resolve()
        path = self.root / "session.sqlite"
        need(path.is_file() and not path.is_symlink(), "existing session required")
        # mode=rw refuses creation; construction never writes to an unrelated file.
        self.db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        try:
            need(self.db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA, "unsupported session")
            row = self.db.execute("SELECT * FROM session WHERE singleton=1").fetchone()
            need(row is not None, "incomplete session")
            self.meta = json.loads(row["metadata"])
            if target is not None:
                need(target_identity(target) == self.meta["target"], "session target mismatch")
            if synthetic is not None:
                need(type(synthetic) is bool and synthetic == self.meta["synthetic"], "session mode mismatch")
            self._monotonic_end = time.monotonic() + max(0, self.meta["deadline_unix"] - time.time())
        except Exception:
            self.db.close()
            raise

    @classmethod
    def create(cls, root, target, *, question, received_at, deadline_at, target_at=None,
               max_requests=120, max_bytes=64*1024*1024, reservations=None,
               synthetic=False, user_hard_deadline=False, focus=None, urls=None,
               scope="broad", rpc_concurrency=3, web_origin_concurrency=2):
        target = target_identity(target)
        received, deadline = epoch(received_at), epoch(deadline_at)
        desired = min(received + 420, deadline) if target_at is None else epoch(target_at)
        need(received <= desired <= deadline and deadline > time.time(), "expired or unordered request timing")
        need(isinstance(question, str) and question.strip(), "original request required")
        need(type(synthetic) is type(user_hard_deadline) is bool, "invalid session flags")
        need(scope in ("broad", "focused"), "invalid research scope")
        integer(max_requests, "request ceiling", maximum=10000)
        integer(max_bytes, "byte ceiling", maximum=1024**3)
        integer(rpc_concurrency, "RPC concurrency", 1, 3)
        integer(web_origin_concurrency, "web concurrency", 1, 2)
        grants = {"liquidity": 15, "project": 15, "final": 8, "contingency": 4} if reservations is None else dict(reservations)
        need(set(grants) <= OWNERS - {"ordinary"}, "invalid reservation owner")
        for amount in grants.values():
            integer(amount, "grant")
        need(sum(grants.values()) <= max_requests, "initial reservations exceed ceiling")
        need(focus is None or isinstance(focus, list), "focus must be a list")
        need(urls is None or isinstance(urls, list), "URLs must be a list")
        from solana_transport import reject_credential_urls
        reject_credential_urls(question, urls or [])
        metadata = {"schema_version": SCHEMA, "investigation_id": str(uuid.uuid4()), "target": target,
            "question": question, "focus": focus or [], "urls": urls or [], "scope": scope,
            "received_at": utc(received), "target_at": utc(desired), "deadline_at": utc(deadline),
            "deadline_unix": deadline, "collection_cutoff": min(received + 480, deadline - 120),
            "lane_cutoff": min(received + 240, deadline - 120), "synthetic": synthetic,
            "user_hard_deadline": user_hard_deadline, "max_requests": max_requests, "max_bytes": max_bytes,
            "rpc_concurrency": rpc_concurrency, "web_origin_concurrency": web_origin_concurrency}
        raw = encoded(metadata)  # Validate serializability before creating a directory.
        root = Path(root)
        root.mkdir(parents=True, exist_ok=False)
        db = sqlite3.connect(root / "session.sqlite")
        try:
            db.executescript("""
                CREATE TABLE session(singleton INTEGER PRIMARY KEY CHECK(singleton=1), metadata TEXT NOT NULL,
                                     status TEXT NOT NULL DEFAULT 'active');
                CREATE TABLE grants(owner TEXT PRIMARY KEY, total INTEGER NOT NULL, remaining INTEGER NOT NULL);
                CREATE TABLE attempts(id INTEGER PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                    family TEXT NOT NULL, method TEXT NOT NULL, source TEXT NOT NULL, owner TEXT NOT NULL,
                    transport_kind TEXT NOT NULL, accounts INTEGER NOT NULL, started_at REAL NOT NULL,
                    deadline REAL NOT NULL, status TEXT NOT NULL, byte_grant INTEGER NOT NULL,
                    response_bytes INTEGER NOT NULL DEFAULT 0, response TEXT, completed_at REAL);
                CREATE TABLE marks(id INTEGER PRIMARY KEY, phase TEXT NOT NULL, at REAL NOT NULL,
                                   used INTEGER NOT NULL, details TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
            with db:
                db.execute("INSERT INTO session(singleton,metadata) VALUES(1,?)", (raw,))
                db.executemany("INSERT INTO grants VALUES(?,?,?)", [(k, v, v) for k, v in grants.items()])
        finally:
            db.close()
        return cls(root, target=target, synthetic=synthetic)

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            need(self.db.execute("SELECT status FROM session").fetchone()[0] == "active", "session already finalized")
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def remaining_seconds(self, owner="ordinary"):
        cutoff = self.meta["collection_cutoff"]
        if owner in ("liquidity", "project"):
            cutoff = self.meta["lane_cutoff"]
        return max(0, min(cutoff - time.time(), self._monotonic_end - time.monotonic()))

    def counts(self):
        row = self.db.execute("SELECT count(*),coalesce(sum(response_bytes),0),"
            "coalesce(sum(CASE WHEN status='started' THEN byte_grant ELSE 0 END),0),"
            "coalesce(sum(accounts),0) FROM attempts").fetchone()
        reserved = self.db.execute("SELECT coalesce(sum(remaining),0) FROM grants").fetchone()[0]
        return {"started_attempts": row[0], "response_bytes": row[1], "reserved_bytes": row[2],
                "account_reads": row[3], "reserved_requests": reserved}

    def status(self):
        # Single read transaction gives a coherent snapshot while other processes acquire.
        self.db.execute("BEGIN")
        try:
            counts = self.counts()
            return {**self.meta, **counts, "status": self.db.execute("SELECT status FROM session").fetchone()[0],
                "remaining_requests": max(0, self.meta["max_requests"]-counts["started_attempts"]-counts["reserved_requests"]),
                "grants": [dict(r) for r in self.db.execute("SELECT * FROM grants ORDER BY owner")],
                "failures": {r[0]: r[1] for r in self.db.execute("SELECT status,count(*) FROM attempts WHERE status NOT IN ('ok','started') GROUP BY status")},
                "phases": [dict(r) for r in self.db.execute("SELECT * FROM marks ORDER BY id")]}
        finally:
            self.db.rollback()

    def reserve(self, owner, count):
        need(owner in OWNERS - {"ordinary"}, "invalid reserved owner")
        integer(count, "grant")
        with self.transaction():
            counts = self.counts()
            need(self.remaining_seconds(owner) > 0, "deadline reached")
            need(counts["started_attempts"] + counts["reserved_requests"] + count <= self.meta["max_requests"], "reservation exceeds ceiling")
            # INSERT, never replace: repeated lane batches cannot replenish a grant.
            self.db.execute("INSERT INTO grants VALUES(?,?,?)", (owner, count, count))

    def acquire(self, request_id, family, method, source, *, owner="ordinary", accounts=0,
                max_response_bytes=1_000_000, transport_kind="rpc", retry=False, rate_limit=None):
        for value in (request_id, family, method, source):
            label(value)
        need(owner in OWNERS and transport_kind in ("rpc", "web"), "invalid acquisition role")
        need(type(retry) is bool, "invalid retry flag")
        integer(accounts, "account count", 0, 100)
        integer(max_response_bytes, "response byte allowance", 1, 16_000_000)
        if rate_limit is not None:
            need(isinstance(rate_limit, tuple) and len(rate_limit) == 2, "invalid source rate window")
            integer(rate_limit[0], "source rate ceiling", 1, 1000)
            integer(rate_limit[1], "source rate window seconds", 1, 3600)
        with self.transaction():
            remaining = self.remaining_seconds(owner)
            if remaining <= 0:
                raise LimitError("deadline")
            previous = self.db.execute("SELECT status FROM attempts WHERE family=? ORDER BY id", (family,)).fetchall()
            if previous and not (retry and len(previous) == 1 and previous[0][0] in TRANSIENT):
                raise LimitError("retry_ineligible")
            if retry and not previous:
                raise LimitError("retry_without_attempt")
            counts = self.counts()
            own = self.db.execute("SELECT remaining FROM grants WHERE owner=?", (owner,)).fetchone()
            permitted = counts["started_attempts"] < self.meta["max_requests"]
            permitted &= counts["started_attempts"] + counts["reserved_requests"] < self.meta["max_requests"] if owner == "ordinary" else bool(own and own[0] > 0)
            if not permitted:
                raise LimitError("request_budget")
            if counts["response_bytes"] + counts["reserved_bytes"] + max_response_bytes > self.meta["max_bytes"]:
                raise LimitError("byte_budget")
            if transport_kind == "rpc":
                running = self.db.execute("SELECT count(*) FROM attempts WHERE status='started' AND transport_kind='rpc'").fetchone()[0]
                limit = self.meta["rpc_concurrency"]
            else:
                running = self.db.execute("SELECT count(*) FROM attempts WHERE status='started' AND transport_kind='web' AND source=?", (source,)).fetchone()[0]
                limit = self.meta["web_origin_concurrency"]
            if running >= limit:
                raise LimitError("concurrency")
            started = time.time()
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_backoff'").fetchone():
                blocked = self.db.execute("SELECT until FROM source_backoff WHERE source=?", (source,)).fetchone()
                if blocked and blocked[0] > started:
                    raise LimitError("source_backoff")
            # Conservative public mainnet limits, shared across processes/restarts.
            # A fallback is not a fresh allowance: RPC totals span namespaces.
            if transport_kind == "rpc":
                recent = self.db.execute("SELECT method FROM attempts WHERE transport_kind='rpc' AND started_at>?", (started-10,)).fetchall()
                # HttpTransport opens a connection for each request; the public
                # connection-rate ceiling (40/10s) is lower than total RPC 100/10s.
                if len(recent) >= 40:
                    raise LimitError("connection_rate_window")
                if len(recent) >= 100 or sum(r[0] == method for r in recent) >= 40:
                    raise LimitError("rate_window")
            if rate_limit is not None:
                recent = self.db.execute("SELECT count(*) FROM attempts WHERE source=? AND started_at>?", (source, started-rate_limit[1])).fetchone()[0]
                if recent >= rate_limit[0]:
                    raise LimitError("source_rate_window")
            deadline = min(started + remaining, self.meta["collection_cutoff"])
            cursor = self.db.execute("INSERT INTO attempts(request_id,family,method,source,owner,transport_kind,accounts,started_at,deadline,status,byte_grant) VALUES(?,?,?,?,?,?,?,?,?,'started',?)",
                (request_id, family, method, source, owner, transport_kind, accounts, started, deadline, max_response_bytes))
            if owner != "ordinary":
                self.db.execute("UPDATE grants SET remaining=remaining-1 WHERE owner=?", (owner,))
            return {"id": cursor.lastrowid, "request_id": request_id, "deadline": deadline, "max_bytes": max_response_bytes}

    def ensure_final_reserve(self, count, trigger):
        """Allocate additional final checks from unspent ordinary capacity, never refill a lane."""
        integer(count, "final checks")
        need(isinstance(trigger, str) and 0 < len(trigger.strip()) <= 1000, "reservation trigger required")
        with self.transaction():
            need(self.remaining_seconds("final") > 0, "deadline reached")
            row = self.db.execute("SELECT remaining FROM grants WHERE owner='final'").fetchone()
            additional = max(0, count - (row[0] if row else 0))
            counts = self.counts()
            need(counts["started_attempts"]+counts["reserved_requests"]+additional <= self.meta["max_requests"], "final reservation exceeds ceiling")
            if additional:
                self.db.execute("INSERT INTO grants VALUES('final',?,?) ON CONFLICT(owner) DO UPDATE SET total=total+excluded.total,remaining=remaining+excluded.remaining", (additional, additional))
                self.db.execute("INSERT INTO marks(phase,at,used,details) VALUES('final_reservation',?,?,?)", (time.time(), counts["started_attempts"], encoded({"trigger": trigger, "additional": additional})))

    def defer_source(self, source, until):
        label(source)
        until = min(epoch(until), self.meta["deadline_unix"])
        with self.transaction():
            self.db.execute("CREATE TABLE IF NOT EXISTS source_backoff(source TEXT PRIMARY KEY,until REAL NOT NULL)")
            self.db.execute("INSERT INTO source_backoff VALUES(?,?) ON CONFLICT(source) DO UPDATE SET until=max(until,excluded.until)", (source, until))

    def finish(self, attempt_id, status, response_bytes, response=None):
        label(status)
        need(status != "started", "completion status required")
        integer(response_bytes, "response bytes")
        with self.transaction():
            row = self.db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
            need(row is not None and row["status"] == "started", "attempt already completed or missing")
            need(response_bytes <= row["byte_grant"], "response exceeded reserved byte allowance")
            if time.time() >= row["deadline"] and status == "ok":
                status = "timeout"
            if isinstance(response, dict) and "status" in response:
                response = {**response, "status": status}
            raw = None if response is None else encoded(response)
            self.db.execute("UPDATE attempts SET status=?,response_bytes=?,response=?,completed_at=? WHERE id=?",
                            (status, response_bytes, raw, time.time(), attempt_id))
        return status

    def recover_expired(self):
        """Lost workers remain charged; pessimistically account their entire byte grant."""
        with self.transaction():
            self.db.execute("UPDATE attempts SET status='lost_worker',response_bytes=byte_grant,completed_at=? WHERE status='started' AND deadline<=?",
                            (time.time(), time.time()))

    def observations(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM attempts ORDER BY id")]

    def mark(self, phase, details=None):
        label(phase)
        with self.transaction():
            self.db.execute("INSERT INTO marks(phase,at,used,details) VALUES(?,?,?,?)",
                (phase, time.time(), self.counts()["started_attempts"], encoded(details or {})))

    def replan(self, trigger, plan):
        need(isinstance(trigger, str) and 0 < len(trigger.strip()) <= 1000, "explicit replan trigger required")
        # Only planning changes: original time, identities and finite ceilings are immutable.
        need(isinstance(plan, dict) and not set(plan) & {"deadline_at", "deadline_unix", "received_at", "max_requests", "max_bytes", "target"}, "replan cannot change bounds or identity")
        self.mark("replan", {"trigger": trigger, "plan": plan})

    def finalize(self):
        with self.transaction():
            need(not self.db.execute("SELECT 1 FROM attempts WHERE status='started'").fetchone(), "unfinished attempts")
            self.db.execute("UPDATE session SET status='finalized'")
