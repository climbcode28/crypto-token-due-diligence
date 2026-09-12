#!/usr/bin/env python3
"""Scaffold the coordinator note from facts.json and the composed lane notes.

The analyst supplies judgement (findings, statuses, texts); the structure, scope entries,
eleven coverage keys, lane attempts and evidence-alias suggestions are generated here.
Every value that needs judgement is a TODO marker, which compose rejects until replaced.
"""
import argparse
import json
import sys
from pathlib import Path

from backend_common import Invalid, need, read_json

FINAL_BOUNDARIES = ("exhausted", "unavailable", "not_yet_observable")
STATUS_TODO = "TODO: checked | partial | unavailable | not_applicable"
BOUNDARY_TODO = "TODO: exhausted | unavailable | not_yet_observable (delete boundary, gap, basis, priority and decision_impact when status is checked or not_applicable)"


def alias_hints(facts):
    """Evidence aliases most likely to support each dimension, read from facts.json."""
    controls = facts.get("controls") or {}
    getters = list((controls.get("getters") or {}).keys())
    source_evidence = list((facts.get("source") or {}).get("evidence") or [])
    token = ["runtime", *("token-" + g for g in getters[:12]), *source_evidence,
             *("token-eip1967-" + k for k in (controls.get("eip1967") or {}))]
    pools = [p for p in facts.get("pools") or [] if p.get("prefix")]
    pool_aliases = [f"{p['prefix']}-liquidity" for p in pools[:6] if p.get("evidence", {}).get("liquidity")] + [f"bal-{p['prefix']}" for p in pools[:6]]
    positions = [v for p in facts.get("positions") or [] for v in (p.get("evidence") or {}).values()]
    quotes = [q.get("evidence") for q in facts.get("quotes") or [] if q.get("evidence")]
    balance_items = facts.get("balances") or {}
    balances = ([balance_items["dead"]["evidence"]] if "dead" in balance_items and balance_items["dead"].get("evidence") else []) \
        + [(h.get("evidence") or {}).get("balance") for h in facts.get("top_holders") or []] \
        + [b.get("evidence") for k, b in balance_items.items() if k != "dead" and b.get("evidence")]
    receipts = [r.get("evidence") for r in facts.get("receipts") or [] if r.get("evidence")]
    architecture = facts.get("architecture") or []
    arch = [v for a in architecture if not a.get("label", "").startswith("quote-") for v in (a.get("evidence") or {}).values()]
    quote_arch = [v for a in architecture if a.get("label", "").startswith("quote-") for v in (a.get("evidence") or {}).values()]
    owners = [v for o in (facts.get("owners") or {}).values() for v in (o.get("evidence") or {}).values()]
    actors = [a.get("evidence") for a in (facts.get("actors") or {}).values() if a.get("evidence")]
    docs = list(facts.get("document_evidence") or [])
    return {
        "token_controls": token,
        "canonical_lp_principal_custody": pool_aliases[:4] + positions,
        "side_pool_removal_risk": pool_aliases,
        "sellability_exit_depth": quotes + pool_aliases[:2],
        "current_concentration": balances,
        "historical_launch_integrity": receipts + actors,
        "admin_treasury_reward_custody": arch + owners,
        "reward_accounting_liveness": token[:3],
        "utility_redemption_rights": token[:3] + docs[:4],
        "external_dependencies": quote_arch,
        "development_disclosure": source_evidence + docs,
    }


def scope_entries(facts, draft):
    """Material contracts the pipeline read, as note.scope entries with readable ids and proxy status."""
    known = {s["address"] for s in draft.get("scope", [])}
    used_ids = {s["id"] for s in draft.get("scope", [])}
    actors = {a["address"]: name for name, a in (facts.get("actors") or {}).items() if a.get("code_bytes") is not None}
    entries = []

    def add(entry):
        if entry["address"] in known or entry["id"] in used_ids:
            return
        known.add(entry["address"])
        used_ids.add(entry["id"])
        entries.append(entry)

    for p in facts.get("pools") or []:
        if p.get("is_pool_id") or not p.get("prefix") or p.get("code_bytes") is None:
            continue
        add({"id": p["prefix"], "address": p["pair"], "material": True,
             "roles": [f"{p.get('dex')} {p.get('version')} pool versus {p.get('counter_symbol')}, indexed liquidity USD {p.get('liquidity_usd')}"]})
    for a in facts.get("architecture") or []:
        if not a.get("code_bytes"):
            continue
        ev = a.get("evidence") or {}
        impl = a.get("eip1967_implementation")
        raw_impl = a.get("eip1967_implementation_raw")
        zero_read = a.get("implementation_status") == "ok" and type(raw_impl) is int and raw_impl == 0
        proxy = {"status": "none_found" if zero_read else "unresolved",
                 "basis": ("The EIP-1967 implementation slot is zero at the pin; other proxy patterns were not ruled out" if zero_read else
                           f"The EIP-1967 implementation slot points to {impl}; implementation source and upgrade authority were not reconciled" if impl else
                           "The EIP-1967 implementation slot was not successfully resolved; proxy and upgrade authority remain unverified"),
                 "evidence": [eid for eid in [ev.get("implementation_slot") or ev.get("code")] if eid]}
        role = ("quote asset " + str(a.get("symbol") or a["label"])) if a["label"].startswith("quote-") else (a["label"] + " (contract named by a token getter)")
        add({"id": a["label"], "address": a["address"], "roles": [role], "material": True, "proxy": proxy})
    for name, o in (facts.get("owners") or {}).items():
        role = f"owner of {name}"
        if o.get("safe_owners"):
            role += f" (getOwners reports {o.get('safe_owner_count') or len(o['safe_owners'])} addresses, threshold {o.get('safe_threshold')}; implementation identity unverified)"
        elif o.get("code_bytes") == 0:
            role += " (no runtime code at the pin)"
        add({"id": "owner-" + name, "address": o["address"], "roles": [role], "material": True})
    for p in facts.get("positions") or []:
        owner = p.get("owner")
        if owner and owner in actors:
            add({"id": f"pos-{p['id']}-owner", "address": owner, "roles": [f"owner of liquidity position {p['id']}"], "material": True})
    creator = (facts.get("creation") or {}).get("creator")
    if creator and creator in actors:
        add({"id": "creator", "address": creator, "roles": ["indexed creator/deployer; transaction signer requires receipt attribution"], "material": True})
    return entries


def coverage_entries(draft, hints):
    from bundle_assemble import DIMENSIONS
    records = {c["dimension"]: c for c in draft.get("coverage_records", [])}
    out = {}
    for dim in DIMENSIONS:
        rec = records.get(dim) or {}
        closure = rec.get("closure") or {}
        route = closure.get("next_route") or {}
        status = rec.get("status", "not_checked")
        suggested = [a for a in hints.get(dim, []) if a][:6]
        if status == "not_checked":
            out[dim] = {"status": STATUS_TODO, "outcome": "TODO: one sentence on what the pinned evidence established",
                        "attempts": [{"check": "TODO: what was checked", "outcome": "TODO: what it showed", "evidence": suggested}],
                        "boundary": BOUNDARY_TODO, "gap": "TODO: what remains unknown", "basis": "TODO: why the permitted sources stop here",
                        "priority": "material", "decision_impact": "TODO: consequence for the decision"}
            continue
        entry = {"status": status, "outcome": rec.get("outcome")}
        if status in ("checked", "not_applicable"):
            out[dim] = entry
            continue
        final = route.get("disposition") in FINAL_BOUNDARIES
        attempts = [{"check": a.get("check"), "outcome": a.get("outcome"), "evidence": list(a.get("evidence_ids") or [])} for a in closure.get("attempts") or []]
        entry.update(gap=rec.get("gap") or "TODO: what remains unknown", priority=closure.get("priority") or "material",
                     decision_impact=closure.get("decision_impact") or "TODO: consequence for the decision",
                     attempts=attempts or [{"check": "TODO: what was checked", "outcome": "TODO: what it showed", "evidence": suggested}],
                     boundary=route.get("disposition") if final else BOUNDARY_TODO,
                     basis=route.get("basis") if final else "TODO: why the permitted sources stop here")
        if route.get("check"):
            entry["route_check"] = route["check"]
        out[dim] = entry
    return out


def scaffold_note(draft_dir, out=None, force=False):
    from bundle_assemble import DIMENSIONS, read_draft
    draft_dir = Path(draft_dir)
    run = draft_dir.resolve().parent
    facts_path = run / "facts.json"
    need(facts_path.is_file(), "facts.json not found next to the draft; run broad_collect.py start first")
    facts = read_json(facts_path)
    draft = read_draft(draft_dir)
    out = Path(out) if out else run / "notes" / "coordinator.json"
    need(force or not out.exists(), str(out) + " exists; pass --force to replace it")
    hints = alias_hints(facts)
    pin = facts.get("pin") or {}
    symbol = (facts.get("metadata") or {}).get("symbol") or facts["target"]["address"]
    pipeline_ids = [fid for fid, meta in (draft.get("note_index") or {}).items() if fid.startswith("pipeline-") and fid in {f["id"] for f in draft.get("findings", [])}]
    note = {
        "note_schema_version": 1, "lane": "coordinator", "requests_used": 0,
        "scope": scope_entries(facts, draft),
        "signals": {fid: {"topic": "TODO: token_and_liquidity | token_economics | creator_trading_and_proceeds | prior_launches_and_identity | adoption_and_maturity | real_work_vs_marketing",
                          "signal": "TODO: Good | Potential Risk (or delete this entry to keep the finding out of the summary)"} for fid in pipeline_ids},
        "findings": [],
        "coverage": coverage_entries(draft, hints),
        "decision": {"requirements": [],
                     "verdict": {"kind": "TODO: findings_with_limits | adverse_findings | insufficient_evidence | requirement_unverified",
                                 "scope": f"General diligence on {symbol} ({facts['target']['address']}) at chain {facts['target']['chain_id']} block {pin.get('number')}",
                                 "findings": []},
                     "synthesis": {k: "TODO" for k in ("technical_exposure", "credibility_maturity", "token_economics", "research_confidence")},
                     "actions": []},
        "text": {k: "TODO" for k in ("verdict", "main_reasons", "strongest_contrary_evidence", "unresolved_questions", "change_evidence")},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lane_findings = {}
    for f in draft.get("findings", []):
        for dim in (draft.get("note_index", {}).get(f["id"], {}).get("dimensions") or []):
            lane_findings.setdefault(dim, []).append(f["id"])
    if not note["signals"]:
        note.pop("signals")
    todo = sum(json.dumps(v).count("TODO") for v in note.values())
    intake = read_json(run / "intake.json") if (run / "intake.json").is_file() else {}
    return {"note": str(out), "todo_markers": todo,
            "user_focus": intake.get("focus") or "", "user_urls": list(intake.get("user_urls") or []),
            "scope_ids": [s["id"] for s in note["scope"]],
            "coverage_prefilled": sorted(d for d, c in note["coverage"].items() if not str(c.get("status", "")).startswith("TODO")),
            "coverage_todo": sorted(d for d, c in note["coverage"].items() if str(c.get("status", "")).startswith("TODO")),
            "lane_findings_by_dimension": lane_findings,
            "lane_leads": draft.get("lane_leads", {}),
            "alias_hints": {d: [a for a in hints[d] if a][:8] for d in DIMENSIONS},
            "pipeline_findings": pipeline_ids,
            "next": "Edit the note: give each pipeline finding a topic/signal in `signals` (Good when the pinned observation is favorable, Potential Risk "
                    "when it shows a concern; delete entries that should not be summary rows), add your own findings for adverse concerns and lane "
                    "conclusions, replace every TODO, then run bundle_assemble.py finalize with --note on this file. Compose rejects leftover TODOs by field."
                    + (" The user asked something beyond the address (user_focus): answer it explicitly in text.verdict or a finding, labeled by evidence strength." if intake.get("focus") or intake.get("user_urls") else "")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("draft", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(scaffold_note(args.draft, args.out, args.force), sort_keys=True, indent=1))
        return 0
    except (Invalid, ValueError, OSError, KeyError) as exc:
        print("Scaffold failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
