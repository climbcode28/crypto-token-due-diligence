"""Portable evidence primitives. SHA-256 is an integrity hash, not EVM Keccak."""
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from validate_bundle import (Invalid, address, digest, file_in, integer, need,
                             quantity, read_json, sha)
from rpc_wire import validate_response

ENGINE_VERSION = "3.5.1"
# Public explorers and RPC front doors (Cloudflare) challenge generic client signatures and
# Chrome-style agents that lack Chrome's client hints; a Safari-style agent is answered normally.
BROWSER_USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.4 Safari/605.1.15")
RULE_VERSIONS = {"launch_recipients": "1.0.1", "fee_predicate": "1.0.1"}
LEGACY_SOURCE_FILES = ("backend_common.py", "rpc_collect.py", "detect.py", "maintain.py", "validate_bundle.py")
SOURCE_FILES_3_1 = LEGACY_SOURCE_FILES + ("rpc_wire.py", "report_profile.py", "evm_decode.py",
                                         "bootstrap.py", "bundle_assemble.py", "source_lookup.py", "investigation.py", "operations.py",
                                         "render_report.py", "render_legacy_v1.py", "report_replay.py")
SOURCE_FILES_3_2 = SOURCE_FILES_3_1 + ("keccak.py", "facts.py", "compose.py", "presets.py", "web_capture.py", "broad_collect.py")
SOURCE_FILES_3_3 = SOURCE_FILES_3_2 + ("scaffold.py",)
SOURCE_FILES_3_4 = SOURCE_FILES_3_3 + ("pipeline_note.py",)
SOURCE_FILES = SOURCE_FILES_3_4 + ("sale_decode.py",)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + "\n").encode()


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(value))


def label(value):
    need(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value),
         "IDs and endpoint labels must be 1-80 letters, digits, underscores or hyphens")
    return value


def word(value):
    need(isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", value),
         "expected one ABI word")
    return int(value, 16)


def engine_snapshot(root):
    hashes = {}
    for name in SOURCE_FILES:
        data = Path(__file__).with_name(name).read_bytes()
        target = root / "engine" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        hashes[name] = sha(data)
    return {"version": ENGINE_VERSION, "rules": RULE_VERSIONS,
            "source_sha256": hashes}


class Cache:
    """Only successful non-null RPC responses are reusable; attempts remain separate."""

    def __init__(self, path):
        self.db = sqlite3.connect(path)
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.db.close()
            raise Invalid("unsupported cache schema; use a separate database")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS responses (
                key TEXT PRIMARY KEY, payload BLOB NOT NULL, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY, key TEXT NOT NULL, status TEXT NOT NULL,
                captured_at TEXT NOT NULL, payload BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS runs (
                digest TEXT PRIMARY KEY, kind TEXT NOT NULL, engine TEXT NOT NULL,
                path TEXT NOT NULL, recorded_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY, run_digest TEXT NOT NULL,
                kind TEXT NOT NULL, note TEXT NOT NULL, evidence_ids TEXT NOT NULL,
                recorded_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS context (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            PRAGMA user_version=1;
        """)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO context VALUES('investigation_id',?)", (str(uuid.uuid4()),))
        self.investigation_id = self.db.execute("SELECT value FROM context WHERE key='investigation_id'").fetchone()[0]

    def close(self):
        self.db.close()

    def get(self, key):
        row = self.db.execute("SELECT payload, digest FROM responses WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        need(sha(row[0]) == row[1], "cache integrity mismatch")
        return json.loads(row[0])

    def record(self, key, record, reusable):
        payload = canonical(record)
        with self.db:
            cursor = self.db.execute("INSERT INTO attempts(key,status,captured_at,payload) VALUES(?,?,?,?)",
                                     (key, record["status"], record["captured_at_utc"], payload))
            if reusable:
                self.db.execute("INSERT OR REPLACE INTO responses VALUES(?,?,?)",
                                (key, payload, sha(payload)))
        return cursor.lastrowid

    def attempt(self, attempt_id):
        row = self.db.execute("SELECT payload FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        need(row is not None, "cached attempt missing")
        return json.loads(row[0])

    def register(self, path, kind, engine):
        path = Path(path).resolve()
        value = sha(path.read_bytes())
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO runs VALUES(?,?,?,?,?)",
                            (value, kind, json.dumps(engine, sort_keys=True), str(path), stamp()))
        return value

    def evict(self, keys):
        with self.db:
            self.db.executemany("DELETE FROM responses WHERE key=?", ((key,) for key in keys))


def load_collection(root, allow_synthetic=False):
    root = Path(root)
    collection = read_json(root / "collection.json")
    need(collection["schema_version"] == 1, "unsupported collection schema")
    need(type(collection["synthetic"]) is bool, "synthetic must be boolean")
    need(allow_synthetic or not collection["synthetic"], "synthetic collection requires --allow-synthetic")
    need(collection["status"] in ("complete", "partial"), "collection is not usable (pin or chain failure)")
    integer(collection["target"]["chain_id"], "chain ID", 1)
    address(collection["target"]["address"])
    saved_files = set(collection["engine"]["source_sha256"])
    need(saved_files == set(SOURCE_FILES) or
         (collection["engine"]["version"] in ("3.4.0", "3.4.1") and saved_files == set(SOURCE_FILES_3_4)) or
         (collection["engine"]["version"] == "3.3.0" and saved_files == set(SOURCE_FILES_3_3)) or
         (collection["engine"]["version"] == "3.2.0" and saved_files == set(SOURCE_FILES_3_2)) or
         (collection["engine"]["version"] in ("3.0.0", "3.1.0") and saved_files == set(SOURCE_FILES_3_1)) or
         (collection["engine"]["version"] in ("2.0.0", "2.1.0") and saved_files == set(LEGACY_SOURCE_FILES)),
         "incomplete/unsupported engine snapshot")
    for name, expected in collection["engine"]["source_sha256"].items():
        need(sha(file_in(root, "engine/" + name).read_bytes()) == expected, "engine snapshot changed")
    need(sha(file_in(root, "plan.json").read_bytes()) == collection["plan_sha256"], "plan changed")
    evidence = {}
    for row in collection["evidence"]:
        label(row["id"])
        need(row["id"] not in evidence, "duplicate evidence ID")
        need(row["target"] == collection["target"] and row["chain_id"] == collection["target"]["chain_id"],
             "evidence target/chain mismatch")
        data = file_in(root, row["artifact"]).read_bytes()
        need(sha(data) == row["sha256"], "evidence integrity mismatch")
        obj = read_json(file_in(root, row["artifact"]))
        need(obj["request"] == row["query"], "evidence request mismatch")
        if row["kind"] == "rpc":
            try:
                validate_response(obj["request"], obj["response"],
                                  legacy=saved_files == set(LEGACY_SOURCE_FILES), redacted=row.get("redacted", False))
            except ValueError as exc:
                raise Invalid("invalid collection RPC: " + str(exc)) from exc
        evidence[row["id"]] = (row, obj)
    pins = {}
    for pin in collection["pins"]:
        need(pin["id"] not in pins, "duplicate pin")
        pins[pin["id"]] = pin
        row, obj = evidence[pin["header_evidence"]]
        need(row["kind"] == "rpc" and "error" not in obj["response"], "pin header unavailable")
        header = obj["response"]["result"]
        need(row["query"]["method"] == "eth_getBlockByNumber" and
             row["query"]["params"] == [hex(pin["number"]), False], "pin header query mismatch")
        need(quantity(header["number"]) == pin["number"] and header["hash"].lower() == pin["hash"], "pin header mismatch")
        digest(pin["hash"], "pin hash", prefix=True)
        digest(header["parentHash"], "parent hash", prefix=True)
        digest(header["stateRoot"], "state root", prefix=True)
        timestamp = datetime.fromtimestamp(quantity(header["timestamp"]), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        need(pin["timestamp_utc"] == timestamp and pin["parent_hash"] == header["parentHash"].lower(), "pin timestamp/parent mismatch")
        # A partial collection is usable only if every final live pin check succeeded.
        after_row, after_obj = evidence["sys-recheck-" + pin["id"]]
        need(after_row["kind"] == "rpc" and after_row["query"]["method"] == "eth_getBlockByNumber"
             and after_row["query"]["params"] == [hex(pin["number"]), False], "missing final pin check")
        after = after_obj["response"].get("result")
        need(isinstance(after, dict) and after["hash"].lower() == pin["hash"]
             and quantity(after["number"]) == pin["number"], "final pin check mismatches frozen header")
    chain_row, chain_obj = evidence[collection["chain_id_evidence"]]
    need(chain_row["query"]["method"] == "eth_chainId" and
         quantity(chain_obj["response"]["result"]) == collection["target"]["chain_id"], "chain evidence mismatch")
    by_number = {p["number"]: p for p in pins.values()}
    for row, obj in evidence.values():
        if row["kind"] != "rpc" or not validate_response(obj["request"], obj["response"],
                legacy=saved_files == set(LEGACY_SOURCE_FILES), redacted=row.get("redacted", False)):
            continue
        method, result = row["query"]["method"], obj["response"]["result"]
        if method == "eth_chainId":
            need(quantity(result) == collection["target"]["chain_id"], "contradictory chain observation")
        if method in ("eth_getBlockByNumber", "eth_getBlockByHash"):
            pin = by_number.get(quantity(result["number"]))
            selected = evidence[pin["header_evidence"]][1]["response"]["result"] if pin else {}
            need(pin is not None and result["hash"].lower() == pin["hash"]
                 and all(result[x].lower() == selected[x].lower() for x in ("parentHash", "stateRoot", "timestamp")),
                 "contradictory header observation")
            params = row["query"]["params"]
            need(params == ([hex(pin["number"]), False] if method == "eth_getBlockByNumber" else [pin["hash"], False]),
                 "header request conflicts with response")
    return collection, evidence, pins
