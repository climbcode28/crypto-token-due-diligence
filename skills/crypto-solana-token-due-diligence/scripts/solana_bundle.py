#!/usr/bin/env python3
"""Initialize, validate and render explicitly versioned Solana evidence bundles."""
import argparse
import json
from pathlib import Path
import sys

import solana_legacy_v1 as legacy

DEFAULT_PROFILE = "solana-evidence-v2"
PROFILES = ("legacy-v1", "solana-evidence-v2")
DIMENSIONS = legacy.DIMENSIONS
SAFETY = legacy.SAFETY
need = legacy.need
artifact = legacy.artifact


def implementation(profile):
    need(profile in PROFILES, "unknown Solana profile")
    if profile == "legacy-v1":
        return legacy
    import solana_profile
    return solana_profile


def collection(root, name="summary.json", allow_synthetic=False, *, profile=DEFAULT_PROFILE):
    return implementation(profile).collection(root, name, allow_synthetic)


def initialize(root, target=None, use_collection=False, allow_synthetic=False, *, profile=DEFAULT_PROFILE):
    return implementation(profile).initialize(root, target, use_collection, allow_synthetic)


def validate(root, allow_synthetic=False, *, profile=DEFAULT_PROFILE):
    return implementation(profile).validate(root, allow_synthetic)


def render(manifest, report, *, profile=DEFAULT_PROFILE):
    return implementation(profile).render(manifest, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("init", "validate", "render", "facts", "scaffold", "compose", "finalize", "checkpoint", "read", "verify", "replay"))
    p.add_argument("root", type=Path)
    p.add_argument("--profile", choices=PROFILES, default=DEFAULT_PROFILE)
    p.add_argument("--from-collection", action="store_true")
    p.add_argument("--mint")
    p.add_argument("--genesis-hash")
    p.add_argument("--allow-synthetic", action="store_true")
    p.add_argument("--rendered", type=Path)
    p.add_argument("--category", action="append")
    p.add_argument("--owner", choices=("coordinator", "liquidity", "project"), default="coordinator")
    p.add_argument("--note", default="notes/coordinator.json")
    p.add_argument("--liquidity-note")
    p.add_argument("--project-note")
    p.add_argument("--check", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--trust-frozen-code", action="store_true")
    args = p.parse_args()
    try:
        if args.action in ("finalize", "checkpoint", "read", "verify", "replay"):
            need(args.profile == "solana-evidence-v2", "Frozen delivery commands require the v2 profile.")
            import solana_replay
            if args.action in ("finalize", "checkpoint"):
                need(args.out is not None, "Use --out with a new directory.")
                result = solana_replay.finalize(args.root,args.out,note_name=args.note,allow_synthetic=args.allow_synthetic,checkpoint=args.action=="checkpoint")
            elif args.action == "replay":
                result = solana_replay.replay(args.root,trust_frozen_code=args.trust_frozen_code,allow_synthetic=args.allow_synthetic)
            else:
                result = getattr(solana_replay,args.action)(args.root,args.allow_synthetic)
                result.pop("receipt",None)
            print(json.dumps(result,ensure_ascii=False));return 0
        if args.action in ("compose", "scaffold"):
            need(args.profile == "solana-evidence-v2", "note authoring requires the v2 profile")
            if args.action == "compose":
                from solana_compose import compose
                lanes = {o:n for o,n in (("liquidity",args.liquidity_note),("project",args.project_note)) if n}
                result = compose(args.root, args.note, lane_names=lanes, allow_synthetic=args.allow_synthetic, check_only=args.check)
                result.pop("report")
            else:
                from solana_scaffold import scaffold, write
                result = (scaffold if args.check else write)(args.root, args.owner, args.allow_synthetic)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.action == "facts":
            need(args.profile == "solana-evidence-v2", "facts requires the v2 profile")
            from solana_pipeline_note import generate
            from solana_facts import build, compact
            facts = build(args.root, args.allow_synthetic)
            display = compact(facts, args.category)
            if not args.check:  # --check is a read-only view; nothing is written.
                generate(args.root, args.allow_synthetic, facts=facts)
            print(display, end="")
            return 0
        if args.action == "init":
            target = {"family": "solana", "mint": args.mint, "genesis_hash": args.genesis_hash}
            if args.profile == "solana-evidence-v2" and not args.mint and not args.genesis_hash:
                target = None
            initialize(args.root, target,
                       args.from_collection, args.allow_synthetic, profile=args.profile)
        manifest, report = validate(args.root, args.allow_synthetic, profile=args.profile)
        if args.action == "render":
            rendered = render(manifest, report, profile=args.profile)
            with (args.root / "report.md").open("x") as handle:
                handle.write(rendered)
        if args.rendered:
            need(args.rendered.read_text() == render(manifest, report, profile=args.profile), "rendered output differs from frozen source")
        print(json.dumps({"valid": True, "status": report.get("research_status",report.get("status")), "synthetic": report["synthetic"],
                          "meaning": "internal consistency only; not completeness, source truth or token safety"}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        if args.profile == "solana-evidence-v2":
            p.exit(2, json.dumps({"valid":False,"errors":getattr(exc,"errors",[{"path":"bundle","message":str(exc)}])})+"\n")
        p.exit(2, "Invalid or incomplete Solana bundle; check schema, identity, evidence hashes and coverage.\n")


if __name__ == "__main__":
    sys.exit(main())
