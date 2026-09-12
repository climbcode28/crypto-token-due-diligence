#!/usr/bin/env python3
"""Bounded operational observations and reviewed guidance, never token evidence or policy."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
try:
    import fcntl
except ImportError:  # Optional feedback must not break collection on non-POSIX hosts.
    fcntl = None
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time

from validate_bundle import file_in, integer, need, read_json, sha, utc

SCHEMA = 1
MAX_BYTES, MAX_OBSERVATIONS, MAX_MEMORIES = 32768, 8, 20
COMPONENTS = {"collector", "bootstrap", "source_lookup", "browser", "assembly", "decoder", "validator", "reporting"}
SENSITIVE = re.compile(r"0x[0-9a-fA-F]{40,}|://|/Users/|/home/|\b(?:Bearer|Authorization|password|secret|seed phrase|private.key|api.key|paid|permission)\b|sk-[A-Za-z0-9-]{8,}|ignore.{0,30}instructions|system.prompt|[`${}<>]", re.I)


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def safe_text(value, maximum=300):
    need(isinstance(value, str) and 0 < len(value) <= maximum and not SENSITIVE.search(value), "unsafe/oversized operational text")
    need(all(ord(c) >= 32 or c == "\n" for c in value), "control characters in operational text")
    return value


def identifier(value):
    need(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", value), "invalid operational identifier")
    safe_text(value, 80)
    return value


@contextmanager
def locked(root, timeout=1):
    need(fcntl is not None, "operational locking unavailable on this platform")
    path = Path(root) / ".operational-feedback.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                need(time.monotonic() < deadline, "operational lock unavailable")
                time.sleep(0.01)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def atomic(path, content):
    fd, tmp = tempfile.mkstemp(prefix=".ops-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def artifact_hash(path):
    need(path.stat().st_size <= 32_000_000, "operational artifact byte limit")
    digest, total = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            total += len(chunk)
            need(total <= 32_000_000, "operational artifact byte limit")
            digest.update(chunk)
    return digest.hexdigest()


def validate_observation(root, item):
    fields = {"id", "component", "operation", "category", "access_mode", "tool_version", "observed_at_utc", "symptom",
              "outcome", "recovery", "artifact", "collection_sha256", "impact"}
    need(set(item) in (fields, fields | {"collection_path"}), "unknown/missing observation fields")
    identifier(item["id"])
    need(item["component"] in COMPONENTS, "unknown operational component")
    for key in ("operation", "category", "access_mode", "tool_version"):
        identifier(item[key])
        safe_text(item[key], 80)
    utc(item["observed_at_utc"])
    safe_text(item["symptom"])
    need(item["outcome"] in ("failed", "partial", "recovered", "not_attempted"), "unknown operational outcome")
    recovery = item["recovery"]
    need(set(recovery) == {"action", "status"} and recovery["status"] in ("not_attempted", "proposed", "failed", "succeeded"), "invalid recovery")
    safe_text(recovery["action"])
    need(item["outcome"] != "recovered" or recovery["status"] == "succeeded", "unverified recovery cannot be recovered")
    artifact = item["artifact"]
    need(set(artifact) == {"path", "sha256"}, "artifact provenance missing")
    need(artifact_hash(file_in(Path(root), artifact["path"])) == artifact["sha256"], "operational artifact changed")
    need("collection_path" not in item or item["collection_sha256"] is not None, "collection path requires its digest")
    if item["collection_sha256"] is not None:
        need(artifact_hash(file_in(Path(root), item.get("collection_path", "collection.json"))) == item["collection_sha256"], "collection provenance changed")
    impact = item["impact"]
    need(set(impact) == {"extra_requests", "lost_coverage"} and type(impact["lost_coverage"]) is bool, "invalid impact")
    if impact["extra_requests"] is not None:
        integer(impact["extra_requests"], "extra requests")
        need(impact["extra_requests"] <= 10000, "unbounded impact")
    return item


def read_feedback(root):
    path = file_in(Path(root), "operational-feedback.json")
    need(path.stat().st_size <= MAX_BYTES, "feedback file too large")
    obj = read_json(path)
    need(set(obj) == {"schema_version", "run_id", "observations"} and type(obj["schema_version"]) is int and obj["schema_version"] == SCHEMA, "unsupported feedback schema")
    identifier(obj["run_id"])
    need(isinstance(obj["observations"], list) and len(obj["observations"]) <= MAX_OBSERVATIONS, "too many observations")
    need(len({x["id"] for x in obj["observations"]}) == len(obj["observations"]), "duplicate observation IDs")
    for item in obj["observations"]:
        validate_observation(root, item)
    return obj


def capture(root, item):
    root = Path(root).resolve()
    validate_observation(root, item)
    with locked(root):
        path = root / "operational-feedback.json"
        obj = read_feedback(root) if path.exists() else {"schema_version": SCHEMA, "run_id": "run-" + sha(str(root).encode())[:24], "observations": []}
        existing = next((x for x in obj["observations"] if x["id"] == item["id"]), None)
        if existing is not None:
            need(existing == item, "observation ID conflict")
            return "duplicate"
        need(len(obj["observations"]) < MAX_OBSERVATIONS, "observation limit reached")
        obj["observations"].append(item)
        content = encoded(obj)
        need(len(content) <= MAX_BYTES, "feedback byte limit reached")
        atomic(path, content)
    return "recorded"


def automatic(root, component, operation, category, artifact, collection_sha256=None, access_mode="local", feedback_root=None):
    """Best-effort fixed-language capture; never copies raw errors into reusable guidance."""
    try:
        root = Path(root).resolve()
        original_root = root
        artifact_path = file_in(root, artifact)
        root = Path(feedback_root).resolve() if feedback_root is not None else root
        artifact = str(artifact_path.relative_to(root))
        digest = artifact_hash(artifact_path)
        key = sha(encoded([component, operation, category, access_mode, digest]))[:24]
        observation = {"id": "obs-" + key, "component": component, "operation": operation,
            "category": category, "access_mode": access_mode, "tool_version": "v3.4.0",
            "observed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "symptom": "An operation did not complete: " + category,
            "outcome": "partial", "recovery": {"action": "No successful recovery recorded", "status": "not_attempted"},
            "artifact": {"path": artifact, "sha256": digest}, "collection_sha256": collection_sha256,
            "impact": {"extra_requests": None, "lost_coverage": True}}
        if collection_sha256 is not None:
            observation["collection_path"] = str((original_root / "collection.json").relative_to(root))
        # Repeated coordinator calls are idempotent despite a later wall-clock time.
        path = root / "operational-feedback.json"
        if path.exists():
            existing = next((x for x in read_feedback(root)["observations"] if x["id"] == observation["id"]), None)
            if existing:
                observation["observed_at_utc"] = existing["observed_at_utc"]
        return capture(root, observation)
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error, RecursionError, OverflowError):
        return "feedback_unavailable"  # Never changes token findings or stops delivery.


class OperationsStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=2)
        try:
            tables = {x[0] for x in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            need(not tables or tables <= {"issues", "occurrences"}, "operations store must be separate from RPC/session caches")
            need(self.db.execute("PRAGMA user_version").fetchone()[0] in (0, SCHEMA), "unsupported operations schema")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS issues(key TEXT PRIMARY KEY, context TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS occurrences(issue_key TEXT NOT NULL, run_id TEXT NOT NULL,
                    observation_id TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(run_id,observation_id));
                CREATE INDEX IF NOT EXISTS occurrence_issue ON occurrences(issue_key);
                PRAGMA user_version=1;
            """)
        except Exception:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def ingest(self, root):
        obj = read_feedback(root)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            for item in obj["observations"]:
                context = {k: item[k] for k in ("component", "operation", "category", "access_mode", "tool_version", "symptom")}
                key, digest = sha(encoded(context)), sha(encoded(item))
                previous = self.db.execute("SELECT digest FROM occurrences WHERE run_id=? AND observation_id=?", (obj["run_id"], item["id"])).fetchone()
                need(previous is None or previous[0] == digest, "stored observation conflicts with candidate")
                self.db.execute("INSERT OR IGNORE INTO issues VALUES(?,?)", (key, encoded(context).decode()))
                self.db.execute("INSERT OR IGNORE INTO occurrences VALUES(?,?,?,?,?)", (key, obj["run_id"], item["id"], digest, encoded(item).decode()))

    def recent(self, limit=20):
        integer(limit, "operation retrieval limit", 1)
        need(limit <= 100, "operation retrieval cap is 100")
        return [{"issue_key": k, "context": json.loads(c), "occurrences": n, "distinct_runs": runs} for k, c, n, runs in self.db.execute(
            "SELECT i.key,i.context,count(o.digest),count(DISTINCT o.run_id) FROM issues i JOIN occurrences o ON i.key=o.issue_key GROUP BY i.key ORDER BY max(o.rowid) DESC,i.key LIMIT ?", (limit,))]


def memory_payload(path, today=None):
    today = today or datetime.now(timezone.utc).date()
    need(Path(path).stat().st_size <= MAX_BYTES, "memory file too large")
    text = Path(path).read_text(encoding="utf-8")
    payloads = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    need(len(payloads) == 1, "memory requires exactly one JSON payload")
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            need(k not in obj, "duplicate memory key")
            obj[k] = v
        return obj
    obj = json.loads(payloads[0], object_pairs_hook=unique)
    need(set(obj) == {"schema_version", "entries"} and type(obj["schema_version"]) is int and obj["schema_version"] == SCHEMA, "unsupported memory schema")
    need(isinstance(obj["entries"], list) and len(obj["entries"]) <= MAX_MEMORIES, "memory entry limit")
    seen = set()
    for entry in obj["entries"]:
        need(set(entry) == {"id", "status", "component", "operation", "versions", "action", "limitations", "verification", "reviewed_on", "expires_on", "superseded_by", "review_provenance"}, "invalid memory fields")
        identifier(entry["id"])
        need(entry["id"] not in seen, "duplicate memory ID")
        seen.add(entry["id"])
        need(entry["status"] in ("active", "superseded", "retired"), "unreviewed candidate cannot be active guidance")
        need(entry["component"] in COMPONENTS, "unknown memory component")
        identifier(entry["operation"])
        need(isinstance(entry["versions"], list) and 0 < len(entry["versions"]) <= 8, "memory applicability versions required")
        for version in entry["versions"]:
            identifier(version)
        safe_text(entry["action"], 600)
        safe_text(entry["limitations"], 500)
        need(isinstance(entry["verification"], list) and 0 < len(entry["verification"]) <= 4, "memory verification required")
        for value in entry["verification"]:
            safe_text(value, 300)
        need(all(isinstance(entry[k], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry[k]) for k in ("reviewed_on", "expires_on")), "noncanonical memory date")
        reviewed, expiry = date.fromisoformat(entry["reviewed_on"]), date.fromisoformat(entry["expires_on"])
        need(reviewed <= today and expiry > reviewed, "invalid memory review/expiry dates")
        if entry["superseded_by"] is not None:
            identifier(entry["superseded_by"])
        need(entry["status"] != "active" or entry["superseded_by"] is None, "active memory cannot be superseded")
        review = entry["review_provenance"]
        need(set(review) == {"review_sha256", "observation_sha256", "observation_id"}, "review provenance required")
        for key in ("review_sha256", "observation_sha256"):
            need(isinstance(review[key], str) and re.fullmatch(r"[0-9a-f]{64}", review[key]), "invalid review digest")
        identifier(review["observation_id"])
    for entry in obj["entries"]:
        need(entry["superseded_by"] is None or entry["superseded_by"] in seen, "supersession target absent")
    return text, obj


def relevant_memories(path, component, operation, version, today=None):
    try:
        today = today or datetime.now(timezone.utc).date()
        _, obj = memory_payload(path, today)
        entries = [e for e in obj["entries"] if e["status"] == "active" and e["component"] == component
                   and e["operation"] == operation and version in e["versions"] and today < date.fromisoformat(e["expires_on"])]
        return sorted(entries, key=lambda e: e["id"])[:5]
    except (ValueError, OSError, KeyError, TypeError, RecursionError, OverflowError):
        return []


def promote(path, entry, observation_root, observation_id, review_artifact):
    """Explicit maintenance only. Review artifact is local provenance, not authority."""
    observations = read_feedback(observation_root)["observations"]
    observed = next((x for x in observations if x["id"] == observation_id), None)
    need(observed and observed["recovery"]["status"] == "succeeded", "unverified recovery cannot be promoted")
    need(Path(review_artifact).is_file(), "review artifact missing")
    review_digest = artifact_hash(Path(review_artifact))
    entry = dict(entry, review_provenance={"review_sha256": review_digest,
        "observation_sha256": sha(encoded(observed)), "observation_id": observed["id"]})
    need(entry["component"] == observed["component"] and entry["operation"] == observed["operation"]
         and observed["tool_version"] in entry["versions"], "promotion applicability differs from observation")
    need(entry["status"] == "active", "promotion requires an independently reviewed active entry")
    path = Path(path)
    with locked(path.parent):
        text, obj = memory_payload(path)
        need(entry["id"] not in {e["id"] for e in obj["entries"]}, "memory ID already exists; review edits explicitly")
        obj["entries"].append(entry)
        rendered = re.sub(r"```json\s*\n.*?\n```", lambda _: "```json\n" + encoded(obj).decode().rstrip() + "\n```", text, flags=re.S)
        with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
            candidate = Path(tmp) / "memories.md"
            candidate.write_text(rendered, encoding="utf-8")
            memory_payload(candidate)
        atomic(path, rendered.encode())
    return {"status": "promoted", "review_sha256": review_digest}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    record = sub.add_parser("capture")
    record.add_argument("root", type=Path)
    record.add_argument("observation", type=Path)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("root", type=Path)
    ingest.add_argument("--store", type=Path, required=True)
    recent = sub.add_parser("recent")
    recent.add_argument("--store", type=Path, required=True)
    recent.add_argument("--limit", type=int, default=20)
    read = sub.add_parser("read")
    read.add_argument("memories", type=Path)
    for name in ("component", "operation", "version"):
        read.add_argument("--" + name, required=True)
    promote_cmd = sub.add_parser("promote")
    for name in ("memories", "entry", "observation-root", "review-artifact"):
        promote_cmd.add_argument("--" + name, type=Path, required=True)
    promote_cmd.add_argument("--observation-id", required=True)
    args = p.parse_args()
    store = None
    try:
        if args.action == "capture":
            need(args.observation.stat().st_size <= MAX_BYTES, "candidate file too large")
            result = capture(args.root, read_json(args.observation))
        elif args.action == "read":
            result = relevant_memories(args.memories, args.component, args.operation, args.version)
        elif args.action == "promote":
            need(args.entry.stat().st_size <= MAX_BYTES, "promotion entry too large")
            result = promote(args.memories, read_json(args.entry), args.observation_root, args.observation_id, args.review_artifact)
        else:
            store = OperationsStore(args.store)
            result = store.ingest(args.root) if args.action == "ingest" else store.recent(args.limit)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error, RecursionError, OverflowError) as exc:
        print("Operational feedback unavailable: " + type(exc).__name__, file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    sys.exit(main())
