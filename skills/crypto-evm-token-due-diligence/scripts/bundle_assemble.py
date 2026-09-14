#!/usr/bin/env python3
"""Incremental offline bundle assembly. Drafts are mutable; evidence and freezes are not."""
import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

from backend_common import address, canonical, file_in, integer, label, load_collection, need, read_json, sha, stamp, write_new
from evm_decode import compare_source
from report_profile import CURRENT_PROFILE, pure_coverage_gap
from validate_bundle import DIMENSIONS, METADATA, decode_metadata, validate

SURFACES = {
    "token_controls": "Mint, seizure, transfer restrictions, proxy and upgrade authority",
    "canonical_lp_principal_custody": "Main-pool principal, position custody and withdrawal authority",
    "side_pool_removal_risk": "Side-pool principal and separately held positions",
    "sellability_exit_depth": "Current routes, sell restrictions and size-dependent exits",
    "current_concentration": "Holder balances, exclusions and circulating denominator",
    "historical_launch_integrity": "Launch allocation, creator sales and prior-launch attribution",
    "admin_treasury_reward_custody": "Treasury, fee recipients, reward custody and admin powers",
    "reward_accounting_liveness": "Reward entitlement, conservation, paid amounts and processing backlog",
    "utility_redemption_rights": "Enforceable holder rights, backing and redemption path",
    "external_dependencies": "Oracles, bridges, offchain operators and dependency failures",
    "development_disclosure": "Delivered work, repositories, claims and contrary project evidence",
}


def save_draft(root, draft):
    """One coordinator owns draft edits; atomic replacement survives interrupted writes."""
    need(not (root / "manifest.json").exists(), "cannot mutate a frozen bundle")
    fd, name = tempfile.mkstemp(prefix=".draft-", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(draft))
        os.replace(name, root / "draft.json")
    finally:
        if os.path.exists(name):
            os.unlink(name)


def intake(root, target, question, materiality, synthetic=False):
    target = {"chain_id": integer(target["chain_id"], "chain ID", 1), "address": address(target["address"])}
    need(type(synthetic) is bool and question.strip() and materiality.strip(), "intake scope missing")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    draft = {"draft_schema_version": 1, "target": target, "synthetic": synthetic, "question": question,
             "materiality": materiality, "started_at_utc": stamp(), "collections": [], "evidence": [],
             "pins": [], "chain_id_evidence": None, "scope": [], "discoveries": [],
             "findings": [], "ratings": [], "summary": [], "report_text": {}, "decision_review": None,
             "coverage_records": [{"dimension": d, "surface": surface, "status": "not_checked",
                 "outcome": "Not checked: " + surface, "gap": "No evidence collected for this surface",
                 "stop_reason": "Intake only", "next_check": "Collect and reconcile " + surface.lower(),
                 "evidence_ids": [], "discovery_ids": [], "finding_ids": []} for d, surface in SURFACES.items()],
             "priorities": ["token_controls", "canonical_lp_principal_custody", "sellability_exit_depth",
                            *[d for d in DIMENSIONS if d not in ("token_controls", "canonical_lp_principal_custody", "sellability_exit_depth")]]}
    save_draft(root, draft)
    return draft


def read_draft(root):
    draft = read_json(Path(root) / "draft.json")
    need(draft["draft_schema_version"] == 1, "unsupported draft schema")
    return draft


def resolve_evidence(draft, alias, scope_address=None, pin_id=None):
    """Resolve an exact ID or original collector ID, never a suffix guess."""
    rows = [e for e in draft["evidence"] if e["id"] == alias]
    if not rows:
        rows = [e for e in draft["evidence"]
                if e.get("collection_provenance", {}).get("evidence_id") == alias]
    if scope_address is not None:
        wanted = address(scope_address)
        rows = [e for e in rows if e["address"] == wanted]
    if pin_id is not None:
        rows = [e for e in rows if e["pin_id"] == pin_id]
    need(len(rows) == 1, "evidence alias must resolve exactly once: " + alias +
         "; candidates=" + ",".join(e["id"] for e in rows))
    return rows[0]


def preflight(root):
    """Check accumulated handoff references in one pass without freezing or claiming completion."""
    root = Path(root)
    d = read_draft(root)
    errors = []
    evidence = {e["id"]: e for e in d["evidence"]}
    scopes = {s["id"]: s for s in d["scope"]}
    pins = {p["id"] for p in d["pins"]}
    findings = {f["id"]: f for f in d["findings"]}

    def check_refs(owner, ids, entries, required=True):
        if not isinstance(ids, list) or required and not ids:
            errors.append(owner + ": missing references")
            return []
        missing = [x for x in ids if x not in entries]
        if missing:
            errors.append(owner + ": unknown references " + ", ".join(map(str, missing)))
        return [entries[x] for x in ids if x in entries]

    for kind in ("evidence", "scope", "findings", "discoveries"):
        ids = [x["id"] for x in d[kind]]
        if len(ids) != len(set(ids)):
            errors.append(kind + ": duplicate IDs")
    for e in evidence.values():
        try:
            data = file_in(root, e["artifact"]).read_bytes()
            need(sha(data) == e["sha256"], "artifact hash mismatch")
        except (ValueError, OSError) as exc:
            errors.append(e["id"] + ": " + str(exc))
        if e["pin_id"] is not None and e["pin_id"] not in pins:
            errors.append(e["id"] + ": unknown pin")
        if e["kind"] == "derived":
            check_refs(e["id"] + " inputs", e.get("input_evidence_ids"), evidence)
    for s in scopes.values():
        prov = check_refs(s["id"] + " provenance", s.get("provenance"), evidence)
        if prov and not any((e["chain_id"], e["address"]) == (s["chain_id"], s["address"]) for e in prov):
            errors.append(s["id"] + ": provenance lacks scope identity")
        runtime = s.get("runtime", {})
        ids = runtime.get("evidence_ids") if runtime.get("status") == "unavailable" else [runtime.get("evidence_id")]
        rows = check_refs(s["id"] + " runtime", ids, evidence)
        if any((e["chain_id"], e["address"], e["pin_id"]) !=
               (s["chain_id"], s["address"], s["pin_id"]) for e in rows):
            errors.append(s["id"] + ": runtime scope/pin mismatch")
    for f in findings.values():
        rows = check_refs(f["id"] + " evidence", f.get("evidence_ids"), evidence)
        check_refs(f["id"] + " subject", [f.get("subject_scope_id")], scopes)
        check_refs(f["id"] + " participants", f.get("participant_scope_ids"), scopes, required=False)
        if rows and not any((e["chain_id"], e["address"], e["pin_id"]) ==
                            (f["chain_id"], f["address"], f["pin_id"]) for e in rows):
            errors.append(f["id"] + ": no evidence at exact subject/pin")
        for support in f.get("support", []):
            check_refs(f["id"] + " support", [support.get("evidence_id")], evidence)
            check_refs(f["id"] + " support scope", [support.get("scope_id")], scopes)
    for c in d["coverage_records"]:
        if c["status"] == "not_checked":
            continue  # Incremental assembly is expected to retain untouched surfaces.
        if not isinstance(c.get("outcome"), str) or not c["outcome"].strip():
            errors.append(c["dimension"] + ": outcome missing")
        check_refs(c["dimension"] + " evidence", c.get("evidence_ids"), evidence)
        check_refs(c["dimension"] + " findings", c.get("finding_ids"), findings)
    return {"status": "errors" if errors else "draft_references_checked", "errors": errors,
            "final_delivery_eligible": False,
            "remaining_surfaces": [c["dimension"] for c in d["coverage_records"] if c["status"] == "not_checked"],
            "scope": "Offline artifact/reference preflight only; final freeze and semantic review remain required"}


def import_collection(root, collection_root, allow_synthetic=False):
    root, source = Path(root), Path(collection_root)
    d = read_draft(root)
    c, _, _ = load_collection(source, allow_synthetic)
    need(c["target"] == d["target"] and c["synthetic"] == d["synthetic"], "collection target/mode differs from draft")
    digest = sha((source / "collection.json").read_bytes())
    if digest in [x["sha256"] for x in d["collections"]]:
        return d  # Exact repeated import is idempotent.
    prefix = "c-" + digest[:16]
    relative = "imports/" + prefix
    files = {"collection.json", "plan.json", *[e["artifact"] for e in c["evidence"]],
             *["engine/" + name for name in c["engine"]["source_sha256"]]}
    for name in sorted(files):
        data = file_in(source, name).read_bytes()
        dest = root / relative / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write(data)
    ids = {e["id"]: prefix + "-" + e["id"] for e in c["evidence"]}
    pids = {p["id"]: "p-" + str(c["target"]["chain_id"]) + "-" + str(p["number"]) + "-" + p["hash"][2:] for p in c["pins"]}
    for p in c["pins"]:
        pin = next((x for x in d["pins"] if x["id"] == pids[p["id"]]), None)
        if pin is None:
            pin = {**p, "id": pids[p["id"]], "header_evidence": ids[p["header_evidence"]],
                   "state_profile": "numbered_rechecked", "recheck_evidence_ids": []}
            d["pins"].append(pin)
        pin["recheck_evidence_ids"].append(ids["sys-recheck-" + p["id"]])
    for e in c["evidence"]:
        row = copy.deepcopy(e)
        row.update(id=ids[e["id"]], artifact=relative + "/" + e["artifact"],
                   pin_id=pids[e["pin_id"]] if e["pin_id"] is not None else None,
                   provenance_level="state" if e["pin_id"] is not None else "chain",
                   collection_provenance={"artifact": relative + "/collection.json", "sha256": digest, "evidence_id": e["id"]})
        d["evidence"].append(row)
    d["chain_id_evidence"] = ids[c["chain_id_evidence"]]
    d["collections"].append({"artifact": relative + "/collection.json", "sha256": digest})
    save_draft(root, d)
    return d


def add_artifact(root, source, descriptor):
    root, source = Path(root), Path(source)
    d = read_draft(root)
    row = copy.deepcopy(descriptor)
    label(row["id"])
    need(row["id"] not in {x["id"] for x in d["evidence"]}, "duplicate evidence ID")
    need(row["kind"] in ("document", "derived", "simulation"), "RPC artifacts must come from a verified collection")
    need(row["target"] == d["target"], "artifact report target mismatch")
    address(row["address"])
    need(row["pin_id"] in {p["id"] for p in d["pins"]}, "artifact pin missing")
    payload = source.read_bytes()
    row.update(artifact="evidence/" + row["id"] + source.suffix, sha256=sha(payload))
    if row["kind"] == "derived":
        entries = {x["id"]: x for x in d["evidence"]}
        need(bool(row["input_evidence_ids"]) and all(x in entries for x in row["input_evidence_ids"]), "derived inputs not registered")
        row["derivation"]["input_sha256"] = {x: entries[x]["sha256"] for x in row["input_evidence_ids"]}
    dest = root / row["artifact"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("xb") as stream:
        stream.write(payload)
    d["evidence"].append(row)
    save_draft(root, d)
    return row


def source_match(root, runtime_id, source_id, evidence_id):
    root = Path(root)
    d = read_draft(root)
    entries = {x["id"]: x for x in d["evidence"]}
    runtime, source = entries[runtime_id], entries[source_id]
    need(runtime["kind"] == "rpc" and runtime["query"]["method"] == "eth_getCode", "source match requires raw runtime")
    need((source["chain_id"], source["address"], source["pin_id"]) ==
         (runtime["chain_id"], runtime["address"], runtime["pin_id"]), "source match scope/pin mismatch")
    raw = read_json(file_in(root, runtime["artifact"]))["response"]["result"]
    src = read_json(file_in(root, source["artifact"]))
    if "body" in src:  # Read-only lookup capture envelope, not a presumed API success.
        need(src["status"] == "ok", "source lookup did not succeed")
        src = src["body"]
    result = compare_source(raw, src, runtime["chain_id"], runtime["address"])
    row = {**runtime, "id": evidence_id, "kind": "derived", "query": {"operation": "source_correspondence"},
           "captured_at_utc": stamp(), "decoding_basis": result["compilation_basis"], "coverage": result["limitations"],
           "input_evidence_ids": [runtime_id, source_id], "observation_status": "ok",
           "derivation": {"tool": "evm_decode.compare_source", "version": result["version"],
              "operation": "source_correspondence", "parameters": {"runtime_id": runtime_id, "source_id": source_id},
              "source_urls": source["query"].get("source_urls", [])}}
    row.pop("collection_provenance", None)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "comparison.json"
        write_new(path, result)
        return add_artifact(root, path, row)


def handoff(root, lane_path):
    root = Path(root)
    d, lane = read_draft(root), read_json(Path(lane_path))
    need(set(lane) <= {"scope", "discoveries", "findings", "ratings", "coverage_records", "summary", "report_text", "decision_review"}, "unsupported lane field")
    for f in lane.get("findings", []):
        need(all(k in f for k in ("subject_scope_id", "participant_scope_ids", "support", "claim_type", "evidence_type",
                                  "confidence", "impact", "adverse_severity")), "lane must explicitly supply finding semantics")
    for key in ("scope", "discoveries", "findings", "ratings", "coverage_records", "summary"):
        id_key = "dimension" if key == "coverage_records" else "finding_id" if key == "summary" else "id"
        entries = {x[id_key]: x for x in d[key]}
        incoming = lane.get(key, [])
        need(len({x[id_key] for x in incoming}) == len(incoming), "duplicate lane entry")
        entries.update({x[id_key]: x for x in incoming})
        d[key] = list(entries.values())
    d["report_text"].update(lane.get("report_text", {}))
    if "decision_review" in lane:
        d["decision_review"] = copy.deepcopy(lane["decision_review"])
    data = Path(lane_path).read_bytes()
    destination = root / "handoffs" / (sha(data) + ".json")
    if not destination.exists():
        destination.parent.mkdir(exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
    save_draft(root, d)
    return d


def access_route_record(run):
    """The access route start recorded beside the draft (`provider.json`: endpoint class and basis, never a URL or key), when
    it is present and well-formed; otherwise nothing, so the report never claims a route it cannot show."""
    path = Path(run) / "provider.json"
    if not path.is_file():
        return None
    try:
        record = read_json(path)
    except (ValueError, OSError):
        return None
    if not (isinstance(record, dict) and all(isinstance(record.get(k), str) and record[k] for k in ("provider", "endpoint_source", "text"))):
        return None
    # Closed vocabularies and a bounded sentence: a hand-edited record cannot carry an endpoint or credential into the report.
    if record["provider"] not in ("drpc", "configured_rpc", "public", "fixture", "unrecorded") \
            or record["endpoint_source"] not in ("configured", "builtin_public", "builtin_public_key_missing", "fixture", "unrecorded") \
            or len(record["text"]) > 200 or "://" in record["text"] or "@" in record["text"] \
            or record.get("provider_flag") not in (None, "generic", "auto", "drpc", "public") or record.get("cost_policy") not in (None, "free", "paid"):
        return None
    return {k: record.get(k) for k in ("provider", "endpoint_source", "provider_flag", "cost_policy", "text")}


def assemble(root, checkpoint=False):
    root = Path(root)
    d = read_draft(root)
    context = {"collections": d["collections"]}
    route = access_route_record(root.parent)
    if route:
        context["access_route"] = route
    need(d["pins"] and d["chain_id_evidence"], "draft has no verified chain/pins")
    target = d["target"]
    # A later receipt/header import must not move the state snapshot and force
    # unrelated runtime/metadata reads. Coordinators may explicitly select a pin.
    runtime_pins = {e["pin_id"] for e in d["evidence"] if e["chain_id"] == target["chain_id"]
                    and e["address"] == target["address"] and e["query"].get("method") == "eth_getCode"}
    candidates = [p for p in d["pins"] if p["id"] in runtime_pins
                  and (d.get("current_pin") is None or p["id"] == d["current_pin"])]
    need(candidates, "selected current pin needs target runtime evidence")
    current = max(candidates, key=lambda p: (p["number"], p["timestamp_utc"]))
    pid = current["id"]
    evidence = {e["id"]: e for e in d["evidence"]}
    for pin in d["pins"]:
        # Earlier rechecks are still validated raw observations; select the latest
        # successful acquisition as the final check for the merged pin.
        pin["recheck_evidence_ids"] = [max(pin["recheck_evidence_ids"], key=lambda x: evidence[x]["captured_at_utc"])]
    rows = [e for e in d["evidence"] if e["chain_id"] == target["chain_id"] and e["address"] == target["address"] and e["pin_id"] == pid]
    runtime_rows = [e for e in rows if e["query"].get("method") == "eth_getCode"]
    need(bool(runtime_rows), "current target runtime has not been attempted")
    runtime = runtime_rows[-1]
    obj = read_json(file_in(root, runtime["artifact"])).get("response", {})
    code = obj.get("result") if runtime["kind"] == "rpc" and not runtime.get("redacted") else None
    runtime_info = {"status": "unavailable", "reason": "Runtime RPC unavailable", "evidence_ids": [runtime["id"]]}
    if isinstance(code, str):
        runtime_info = {"status": "no_code" if code == "0x" else "captured", "evidence_id": runtime["id"],
                        "sha256": sha(bytes.fromhex(code[2:])), "keccak256": None}
    metadata = {}
    for field, selector in METADATA.items():
        attempts = [e for e in rows if e["query"].get("method") == "eth_call"
                    and e["query"]["params"][0].get("data", "").lower() == selector]
        item = {"status": "unresolved", "value": None, "evidence_ids": [e["id"] for e in attempts],
                "reason": "Metadata not attempted" if not attempts else "Unavailable or nonstandard ABI metadata"}
        for e in reversed(attempts):
            try:
                need(e["kind"] == "rpc" and not e.get("redacted"), "unusable metadata")
                value = decode_metadata(field, read_json(file_in(root, e["artifact"]))["response"]["result"])
                item.update(status="resolved", value=value, evidence_ids=[e["id"]], reason=None)
                break
            except (ValueError, KeyError, TypeError):
                pass
        metadata[field] = item
    target_scope = {"id": "target", **target, "roles": ["target token"], "material": True, "pin_id": pid,
                    "provenance": [runtime["id"]], "runtime": runtime_info,
                    "proxy": {"status": "unresolved", "basis": "Architecture/authority review has not been reconciled",
                              "evidence_ids": [runtime["id"]], "implementation_scope_ids": [], "authority_scope_ids": []}}
    scopes = {"target": target_scope, **{s["id"]: s for s in d["scope"]}}
    discovery = {"id": "intake", "chain_id": target["chain_id"], "universe": "Exact requested token and imported explicit reads",
                 "pagination": "No enumeration implied", "inclusion_rules": "Requested identity and declared query plans",
                 "exclusions": "Surrounding system discovery remains incomplete", "materiality": d["materiality"],
                 "coverage": "Intake and imported reads only", "block_ranges": [[current["number"], current["number"]]],
                 "evidence_ids": [runtime["id"]]}
    discoveries = {"intake": discovery, **{x["id"]: x for x in d["discoveries"]}}
    findings, ratings = {f["id"]: f for f in d["findings"]}, {x["id"]: x for x in d["ratings"]}
    summary = copy.deepcopy(d["summary"])
    for coverage in d["coverage_records"]:
        dimension = coverage["dimension"]
        if checkpoint and coverage["status"] == "not_checked" and "closure" not in coverage:
            # A focused or interrupted run can be saved before any analyst note.
            # This records unfinished work without inventing attempts or a boundary.
            coverage["stop_reason"] = "Not yet investigated in this run"
            coverage["closure"] = {"priority": "material",
                "decision_impact": "Unresolved " + coverage["surface"].lower() + " limits the related conclusions",
                "attempts": [], "next_route": {"check": coverage["next_check"], "disposition": "pending",
                    "basis": "No attempt recorded yet; the surface remains open work", "evidence_ids": []}}
        if dimension in ratings:
            continue
        fid = "gap-" + dimension
        findings[fid] = {"id": fid, **target, "pin_id": pid, "subject_scope_id": "target", "participant_scope_ids": [],
            "proposition": coverage["outcome"], "evidence_ids": [runtime["id"]], "support": [{"evidence_id": runtime["id"], "role": "identity", "scope_id": "target"}],
            "claim_type": "coverage_gap", "impact": "unknown", "adverse_severity": "unknown", "evidence_type": "unknown", "confidence": "unknown",
            "decoding_basis": "Identity evidence anchors an explicitly unperformed check; it does not prove this surface",
            "alternatives": "Fresh surface evidence could establish a benefit, concern or non-applicability", "coverage": coverage["gap"],
            "stale_when": "The named check is completed", "time_basis": current["timestamp_utc"], "discovery_claim": False, "discovery_ids": ["intake"]}
        ratings[dimension] = {"id": dimension, "status": "unknown", "severity": "unknown", "likelihood": "unknown", "confidence": "unknown",
                              "coverage": "unavailable", "time_basis": current["timestamp_utc"], "finding_ids": [fid], "rationale": coverage["gap"]}
        coverage.update(finding_ids=[fid], discovery_ids=["intake"])
    if not summary:
        if checkpoint:
            from compose import DEFAULT_TOPIC
            gap_rows = [{"finding_id": fid, "topic": DEFAULT_TOPIC[c["dimension"]], "signal": "Unverified"}
                        for c in d["coverage_records"] if ratings[c["dimension"]]["status"] != "not_applicable"
                        for fid in c["finding_ids"] if pure_coverage_gap(findings[fid])]
            summary = gap_rows[:1]  # An actual unresolved check; never grade an unjudged observation.
        else:
            summary = [{"finding_id": "gap-token_controls", "topic": "token_and_liquidity", "signal": "Unverified"}]
    for item in summary:
        if item["signal"] == "Potential Risk" and pure_coverage_gap(findings.get(item["finding_id"], {})):
            item["signal"] = "Unverified"
    safety = {"no_real_keys": True, "no_real_signing": True, "no_broadcast": True, "simulation": {"used": False}}
    manifest = {"schema_version": 1, "validation_profile": CURRENT_PROFILE, "synthetic": d["synthetic"], "mode": "broad",
                "question": d["question"], "materiality": d["materiality"], "limitations": ["Collection and assembly do not complete a broad investigation."],
                "target": {"requested": target, "observed": target, "metadata": metadata}, "context": context,
                "chains": [{"chain_id": target["chain_id"], "label": "RPC-verified chain", "chain_id_evidence": d["chain_id_evidence"], "current_pin": pid, "pins": d["pins"]}],
                "scope": list(scopes.values()), "evidence": d["evidence"], "discoveries": list(discoveries.values()), "safety": safety}
    report = {"schema_version": 1, "validation_profile": CURRENT_PROFILE, "closure_review_version": 1,
              "completion_review_version": 2, "completion_status": "checkpoint" if checkpoint else "complete",
              "delivery_status": "internal_checkpoint" if checkpoint else "final_report",
              "decision_review_version": 2, "decision_review": copy.deepcopy(d.get("decision_review")),
              "synthetic": d["synthetic"], "manifest_sha256": "", "target": target,
              "metadata": metadata, "safety": safety, "findings": list(findings.values()), "ratings": list(ratings.values()), "coverage_records": d["coverage_records"], "summary": summary,
              "verdict": "Research checkpoint: required work remains unfinished." if checkpoint else
                         "Review completed within the documented evidence limits; see the supported findings.", "conditions": d["question"],
              "main_reasons": "See the separate surface outcomes and remaining evidence gaps",
              "strongest_contrary_evidence": "See the evidence-linked findings and decision review for contrary evidence and limits",
              "unresolved_questions": "Required checks remain unfinished" if checkpoint else
                                      "See specific unavailable facts and their documented external evidence boundaries",
              "change_evidence": "Complete the named next checks and reconcile findings" if checkpoint else
                                 "New evidence, access or events identified in the decision review could change the assessment"}
    need(set(d["report_text"]) <= {"verdict", "conditions", "main_reasons", "strongest_contrary_evidence", "unresolved_questions", "change_evidence"}, "unsupported report text field")
    report.update(d["report_text"])
    if checkpoint and d.get("decision_review") is None:
        # Internal storage may precede judgment. Do not fabricate a verdict,
        # favorable/risk signals or mitigation actions just to save the evidence.
        report.pop("decision_review_version")
        report.pop("decision_review")
    return manifest, report


def freeze(root, out, allow_synthetic=False, checkpoint=False):
    root, out = Path(root), Path(out)
    need(not out.exists(), "freeze output must be new")
    m, r = assemble(root, checkpoint=checkpoint)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".freeze-", dir=out.parent) as temp:
        staging = Path(temp) / "bundle"
        staging.mkdir()
        files = {e["artifact"] for e in m["evidence"]}
        for entry in m["context"]["collections"]:
            path = entry["artifact"]
            collection = read_json(file_in(root, path))
            directory = str(Path(path).parent)
            files.update({path, directory + "/plan.json", *[directory + "/engine/" + name for name in collection["engine"]["source_sha256"]]})
        for name in sorted(files):
            source = file_in(root, name)  # Reject escaping symlinks before copying.
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write(source.read_bytes())
        write_new(staging / "manifest.json", m)
        r["manifest_sha256"] = sha((staging / "manifest.json").read_bytes())
        write_new(staging / "report.json", r)
        validate(staging, allow_synthetic, required_profile=CURRENT_PROFILE)
        from render_report import render
        (staging / "report.md").write_text(render(m, r, sha((staging / "report.json").read_bytes())), encoding="utf-8")
        validate(staging, allow_synthetic, staging / "report.md", required_profile=CURRENT_PROFILE)
        from report_replay import freeze_snapshot
        freeze_snapshot(staging)
        staging.rename(out)
    return out


def delivery_reading_checklist(report):
    """Keep coverage visible even when the analyst omitted its optional summary signal.

    Returned in the existing delivery call; no extra files, requests, or model turn.
    Finding ids refer to the frozen report the coordinator already reads.
    """
    return [{"dimension": c["dimension"], "status": c["status"],
             "finding_ids": c.get("finding_ids", []), "gap": c.get("gap")}
            for c in report.get("coverage_records", [])]


def deliver(root, allow_synthetic=False):
    """A saved checkpoint is valid storage, never a successful final-delivery result."""
    root = Path(root)
    _, report = validate(root, allow_synthetic, root / "report.md", required_profile=CURRENT_PROFILE)
    need(report.get("completion_review_version") == 2 and report.get("completion_status") == "complete"
         and report.get("delivery_status") == "final_report",
         "not eligible for final delivery: continue required work; a checkpoint is internal storage only")
    return {"status": "ready_for_final_delivery", "report": str((root / "report.md").resolve()),
            "reading_checklist": delivery_reading_checklist(report)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    init = sub.add_parser("intake")
    init.add_argument("draft", type=Path)
    init.add_argument("--chain-id", type=int, required=True)
    init.add_argument("--address", required=True)
    init.add_argument("--question", required=True)
    init.add_argument("--materiality", required=True)
    init.add_argument("--synthetic", action="store_true")
    delivery = sub.add_parser("deliver")
    delivery.add_argument("draft", type=Path, help="frozen completed bundle")
    delivery.add_argument("--allow-synthetic", action="store_true")
    check = sub.add_parser("check", help="read-only early artifact/reference preflight; not final validation")
    check.add_argument("draft", type=Path)
    compose_cmd = sub.add_parser("compose", help="expand a compact analyst note into strict findings, coverage, ratings, summary and decision")
    compose_cmd.add_argument("draft", type=Path)
    compose_cmd.add_argument("note", type=Path)
    compose_cmd.add_argument("--lane", help="lane name; enables registration of lanes/<lane>/ captures referenced by alias")
    compose_cmd.add_argument("--checkpoint", action="store_true", help="allow pending/budget boundaries for an internal checkpoint")
    compose_cmd.add_argument("--check", action="store_true", help="validate the note and print the result; write nothing")
    scaffold_cmd = sub.add_parser("scaffold", help="write a coordinator note skeleton from facts.json and the composed lane notes")
    scaffold_cmd.add_argument("draft", type=Path)
    scaffold_cmd.add_argument("--out", type=Path, help="default <run>/notes/coordinator.json; refuses to overwrite without --force")
    scaffold_cmd.add_argument("--force", action="store_true")
    facts_cmd = sub.add_parser("facts", help="compact decoded view of the draft's evidence; read this instead of raw JSON")
    facts_cmd.add_argument("draft", type=Path)
    facts_cmd.add_argument("--limit", type=int, default=400)
    facts_cmd.add_argument("--json", action="store_true")
    final_cmd = sub.add_parser("finalize", help="compose optional notes, preflight, freeze and deliver in one step")
    final_cmd.add_argument("draft", type=Path)
    final_cmd.add_argument("--out", type=Path, required=True)
    final_cmd.add_argument("--note", type=Path, action="append", default=[])
    final_cmd.add_argument("--lane", help="lane name for capture registration when composing --note files")
    final_cmd.add_argument("--allow-synthetic", action="store_true")
    final_cmd.add_argument("--checkpoint", action="store_true")
    resolve = sub.add_parser("resolve-evidence", help="resolve an exact current-run collector alias")
    resolve.add_argument("draft", type=Path)
    resolve.add_argument("alias")
    resolve.add_argument("--address")
    resolve.add_argument("--pin-id")
    for name in ("import", "handoff", "artifact", "source-match", "freeze"):
        command = sub.add_parser(name)
        command.add_argument("draft", type=Path)
        if name in ("import", "handoff", "artifact"):
            command.add_argument("source", type=Path)
        if name == "artifact":
            command.add_argument("--descriptor", type=Path, required=True)
        if name == "source-match":
            for flag in ("runtime-id", "source-id", "evidence-id"):
                command.add_argument("--" + flag, required=True)
        if name in ("import", "freeze"):
            command.add_argument("--allow-synthetic", action="store_true")
        if name == "freeze":
            command.add_argument("--out", type=Path, required=True)
            command.add_argument("--checkpoint", action="store_true",
                                 help="preserve unfinished work as a labeled checkpoint, not a completed report")
    p.add_argument("--feedback-root", type=Path, help="fresh investigation root for the shared eight-observation cap")
    args = p.parse_args()
    try:
        if args.action == "check":
            result = preflight(args.draft)
            print(json.dumps(result, sort_keys=True))
            return 2 if result["errors"] else 0
        elif args.action == "compose":
            from compose import compose
            result = compose(args.draft, args.note, lane=args.lane, final=not args.checkpoint, check=args.check)
            print(json.dumps(result, sort_keys=True))
            return 2 if result["errors"] else 0
        elif args.action == "scaffold":
            from scaffold import scaffold_note
            print(json.dumps(scaffold_note(args.draft, args.out, force=args.force), sort_keys=True, indent=1))
            return 0
        elif args.action == "facts":
            from facts import facts_view, render_text
            names_path = args.draft.resolve().parent / "getter-names.json"
            names = read_json(names_path) if names_path.is_file() else None
            view = facts_view(args.draft, read_draft(args.draft), names)
            print(json.dumps(view, sort_keys=True, default=str) if args.json else render_text(view, args.limit))
            return 0
        elif args.action == "finalize":
            from compose import compose
            for note in args.note:
                result = compose(args.draft, note, lane=args.lane, final=not args.checkpoint)
                if result["errors"]:
                    print(json.dumps({"stage": "compose", "note": str(note), **result}, sort_keys=True))
                    return 2
            result = preflight(args.draft)
            if result["errors"]:
                print(json.dumps({"stage": "check", **result}, sort_keys=True))
                return 2
            def mark(phase):
                session_path = args.draft.resolve().parent / "session.sqlite"
                if session_path.is_file():
                    try:
                        from investigation import Investigation
                        session = Investigation(session_path)
                        try:
                            session.mark(phase)
                        finally:
                            session.close()
                    except (ValueError, OSError):
                        pass
            mark("composed")
            try:
                out = freeze(args.draft, args.out, args.allow_synthetic, checkpoint=args.checkpoint)
            except (ValueError, KeyError, TypeError) as exc:
                print(json.dumps({"stage": "freeze", "status": "errors", "errors": [str(exc)],
                                  "hint": "Fix the note and rerun finalize; compose reports most contract errors earlier, so this is worth a regression"}, sort_keys=True))
                return 2
            if args.checkpoint:
                print(json.dumps({"stage": "freeze", "status": "internal_checkpoint", "report": str(out.resolve()),
                                  "note": "Required work remains active; final delivery is not eligible."}, sort_keys=True))
                return 0
            result = deliver(out, args.allow_synthetic)
            mark("delivered")
            print(json.dumps({"stage": "deliver", **result}, sort_keys=True))
            return 0
        elif args.action == "resolve-evidence":
            print(json.dumps(resolve_evidence(read_draft(args.draft), args.alias, args.address, args.pin_id), sort_keys=True))
            return 0
        elif args.action == "intake":
            intake(args.draft, {"chain_id": args.chain_id, "address": args.address}, args.question, args.materiality, args.synthetic)
        elif args.action == "import":
            import_collection(args.draft, args.source, args.allow_synthetic)
        elif args.action == "handoff":
            handoff(args.draft, args.source)
        elif args.action == "artifact":
            add_artifact(args.draft, args.source, read_json(args.descriptor))
        elif args.action == "source-match":
            source_match(args.draft, args.runtime_id, args.source_id, args.evidence_id)
        else:
            if args.action == "deliver":
                print(json.dumps(deliver(args.draft, args.allow_synthetic), sort_keys=True))
                return 0
            freeze(args.draft, args.out, args.allow_synthetic, checkpoint=args.checkpoint)
            if args.checkpoint:
                print("Saved internal checkpoint. Required work remains active; final delivery is not eligible.")
                return 0
        print("Completed " + args.action)
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        if args.action not in ("deliver", "check", "resolve-evidence", "facts", "scaffold") and args.draft.is_dir() and not (args.draft / "manifest.json").exists():
            from operations import automatic
            marker = {"operation": args.action, "failure_category": type(exc).__name__}
            filename = "assembly-observation-" + sha(canonical(marker))[:16] + ".json"
            try:
                if not (args.draft / filename).exists():
                    write_new(args.draft / filename, marker)
                automatic(args.draft, "assembly", args.action.replace("-", "_"), "assembly_failed", filename, feedback_root=args.feedback_root)
            except OSError:
                pass
        print("Assembly failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
