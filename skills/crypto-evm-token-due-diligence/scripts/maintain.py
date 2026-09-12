#!/usr/bin/env python3
"""Append evidence-linked feedback to the local history; never edits rules or scores."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from backend_common import Cache, Invalid, load_collection, need, stamp
from operations import safe_text

KINDS = ("missed_pattern", "decoding_failure", "false_positive", "coverage_gap")


def record_feedback(cache, collection_path, kind, note, evidence_ids, allow_synthetic=False):
    root = Path(collection_path)
    collection, evidence, _ = load_collection(root, allow_synthetic)
    need(kind in KINDS and isinstance(note, str) and note.strip(), "feedback requires a supported kind and a note")
    safe_text(note, 2000)
    need(bool(evidence_ids) and len(evidence_ids) == len(set(evidence_ids))
         and all(x in evidence for x in evidence_ids), "feedback must reference existing unique evidence IDs")
    run_digest = cache.register(root / "collection.json", "collection", collection["engine"])
    with cache.db:
        cache.db.execute("BEGIN IMMEDIATE")
        existing = cache.db.execute("SELECT id FROM feedback WHERE run_digest=? AND kind=? AND note=? AND evidence_ids=?",
                                   (run_digest, kind, note, json.dumps(sorted(evidence_ids)))).fetchone()
        if existing:
            return existing[0]
        cur = cache.db.execute("INSERT INTO feedback(run_digest,kind,note,evidence_ids,recorded_at) VALUES(?,?,?,?,?)",
                               (run_digest, kind, note, json.dumps(sorted(evidence_ids)), stamp()))
    return cur.lastrowid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    sub = p.add_subparsers(dest="action", required=True)
    record = sub.add_parser("record")
    record.add_argument("collection", type=Path)
    record.add_argument("--kind", choices=KINDS, required=True)
    record.add_argument("--note", required=True)
    record.add_argument("--evidence-id", action="append", required=True)
    record.add_argument("--allow-synthetic", action="store_true")
    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)
    args = p.parse_args()
    cache = None
    try:
        cache = Cache(args.cache)
        if args.action == "record":
            value = record_feedback(cache, args.collection, args.kind, args.note, args.evidence_id, args.allow_synthetic)
            print(json.dumps({"feedback_id": value}))
        else:
            need(1 <= args.limit <= 100, "feedback list limit must be 1-100")
            cache.db.row_factory = sqlite3.Row
            print(json.dumps([dict(x) for x in cache.db.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (args.limit,))], indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print("Maintenance failed: " + (str(exc) if isinstance(exc, Invalid) else type(exc).__name__), file=sys.stderr)
        return 2
    finally:
        if cache:
            cache.close()


if __name__ == "__main__":
    sys.exit(main())
