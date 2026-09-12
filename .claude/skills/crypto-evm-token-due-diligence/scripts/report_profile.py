"""Additive strict report contract. Does not infer financial truth from prose."""
from collections import deque

CURRENT_PROFILE = "evm-evidence-v2"
LEGACY_PROFILE = "legacy-v1"
SUPPORT_ROLES = {"direct", "identity", "source", "calculation", "corroboration", "counterevidence", "failed_attempt"}
ASSESSMENT_AXES = {
    "technical_exposure": "Token and liquidity",
    "credibility_maturity": "Team, delivery and maturity",
    "token_economics": "Token economics",
    "research_confidence": "Research confidence",
}
VERDICT_KINDS = {
    "findings_with_limits": "Supported findings with stated limits",
    "adverse_findings": "Evidence-backed concerns",
    "insufficient_evidence": "Insufficient evidence for an overall assessment",
    "requirement_unverified": "User requirement not established",
}


def pure_coverage_gap(finding):
    """Typed missing evidence only; unknown confidence alone cannot neutralize harm."""
    return (finding.get("claim_type") == "coverage_gap"
            and finding.get("evidence_type") == "unknown"
            and finding.get("confidence") == "unknown"
            and finding.get("impact") == "unknown"
            and finding.get("adverse_severity") == "unknown")


def validate_profile(m, r, evidence, objects, pins, scope, findings, ratings, discoveries, root):
    # Lazy import keeps the standalone validator and collector snapshot import-safe.
    from validate_bundle import (DIMENSIONS, address, identity, need, nonempty,
                                 quantity, refs, rpc_result, rpc_unavailable, utc, file_in, read_json, sha)
    profile = m.get("validation_profile", LEGACY_PROFILE)
    need(profile in (LEGACY_PROFILE, CURRENT_PROFILE), "unsupported validation profile")
    need(r.get("validation_profile", LEGACY_PROFILE) == profile, "report/manifest profile mismatch")
    if "closure_review_version" in r:
        need(profile == CURRENT_PROFILE, "stopping review requires the strict profile")
    if "decision_review_version" in r or "decision_review" in r:
        need(profile == CURRENT_PROFILE, "decision review requires the strict profile")
    if "completion_review_version" in r or "completion_status" in r or "delivery_status" in r:
        need(profile == CURRENT_PROFILE, "completion review requires the strict profile")

    # Dependencies are enforced whenever declared, including legacy imports.
    graph = {}
    for eid, ev in evidence.items():
        if ev["kind"] != "derived":
            continue
        if profile == LEGACY_PROFILE and "input_evidence_ids" not in ev:
            continue
        refs(ev["input_evidence_ids"], evidence, eid + " derivation inputs")
        graph[eid] = ev["input_evidence_ids"]
        derivation = ev["derivation"]
        need(derivation["input_sha256"] == {x: evidence[x]["sha256"] for x in ev["input_evidence_ids"]},
             eid + ": derivation input digest changed")
        for key in ("tool", "version", "operation"):
            nonempty(derivation[key], eid + " derivation " + key)
        need(isinstance(derivation["parameters"], dict), "derivation parameters must be explicit")
        need(isinstance(derivation["source_urls"], list), "derivation source URLs must be explicit")
        for url in derivation["source_urls"]:
            nonempty(url, "source URL")
        if derivation["operation"] == "source_correspondence":
            from evm_decode import compare_source
            params = derivation["parameters"]
            runtime_id, source_id = params["runtime_id"], params["source_id"]
            need(set(ev["input_evidence_ids"]) == {runtime_id, source_id}, "source comparison inputs differ")
            runtime_ev, source_ev = evidence[runtime_id], evidence[source_id]
            need(identity(ev) == identity(runtime_ev) == identity(source_ev)
                 and ev["pin_id"] == runtime_ev["pin_id"] == source_ev["pin_id"], "source comparison scope/pin mismatch")
            runtime = rpc_result(evidence, objects, runtime_id, "eth_getCode")
            source = read_json(file_in(root, source_ev["artifact"]))
            if "body" in source:
                need(source["status"] == "ok", "source lookup unavailable")
                source = source["body"]
            reproduced = compare_source(runtime, source, ev["chain_id"], ev["address"], derivation["version"])
            need(reproduced == read_json(file_in(root, ev["artifact"])), "source comparison output differs from bound inputs")
    # Linear dependency validation, with unavailability propagated through derivations.
    unavailable = {eid for eid, ev in evidence.items() if
                   (ev["kind"] == "rpc" and rpc_unavailable(ev, objects[eid]["response"]))
                   or ev.get("observation_status", "ok") != "ok"}
    degree, children = {}, {}
    for eid, inputs in graph.items():
        degree[eid] = len(set(inputs).intersection(graph))
        for parent in inputs:
            children.setdefault(parent, []).append(eid)
    queue = deque(eid for eid, degree_value in degree.items() if degree_value == 0)
    visited = 0
    while queue:
        eid = queue.popleft()
        visited += 1
        if any(parent in unavailable for parent in graph[eid]):
            unavailable.add(eid)
        for child in children.get(eid, []):
            degree[child] -= 1
            if degree[child] == 0:
                queue.append(child)
    need(visited == len(graph), "cyclic derived evidence dependencies")
    if profile == LEGACY_PROFILE:
        return

    imported = {}
    for ev in evidence.values():
        provenance = ev.get("collection_provenance")
        if provenance is None:
            continue
        path = file_in(root, provenance["artifact"])
        need(sha(path.read_bytes()) == provenance["sha256"], "imported collection changed")
        if path not in imported:
            imported[path] = read_json(path)
        collection = imported[path]
        rows = {x["id"]: x for x in collection["evidence"]}
        original = rows[provenance["evidence_id"]]
        need(all(ev[k] == original[k] for k in ("query", "sha256", "captured_at_utc", "kind", "chain_id", "address", "target")),
             "imported evidence differs from collection provenance")

    need(bool(discoveries), "strict broad report requires bounded discovery records")
    need("summary" in r, "strict report requires an evidence-linked summary")
    for pid, (_, pin) in pins.items():
        state_profile = pin["state_profile"]
        need(state_profile in ("numbered_rechecked", "canonical_hash"), "unsupported pin state profile")
        reads = [(eid, ev) for eid, ev in evidence.items() if ev["pin_id"] == pid and ev["kind"] == "rpc"
                 and ev["query"]["method"] in ("eth_call", "eth_getCode", "eth_getBalance", "eth_getStorageAt")]
        if state_profile == "canonical_hash":
            for eid, ev in reads:
                position = 2 if ev["query"]["method"] == "eth_getStorageAt" else 1
                block = ev["query"]["params"][position]
                need(isinstance(block, dict) and block.get("requireCanonical") is True,
                     eid + ": canonical profile requires canonical block-hash reads")
        else:
            refs(pin["recheck_evidence_ids"], evidence, pid + " rechecks")
            latest_read = max((utc(ev["captured_at_utc"]) for _, ev in reads), default=0)
            for eid in pin["recheck_evidence_ids"]:
                ev = evidence[eid]
                need(ev["pin_id"] == pid and eid != pin["header_evidence"]
                     and ev["artifact"] != evidence[pin["header_evidence"]]["artifact"],
                     "recheck must be a distinct observation")
                rpc_result(evidence, objects, eid, "eth_getBlockByNumber")
                need(not ev.get("cache_hit", False) and utc(ev["captured_at_utc"]) >= latest_read,
                     "recheck must be fresh and follow state acquisition")

    for fid, f in findings.items():
        sid = f["subject_scope_id"]
        need(sid in scope and identity(scope[sid]) == identity(f), fid + ": subject scope mismatch")
        refs(f["participant_scope_ids"], scope, fid + " participants", required=False)
        allowed_scopes = {sid, *f["participant_scope_ids"]}
        need(f["claim_type"] in ("state_observation", "source_analysis", "historical_execution", "inference", "coverage_gap"),
             fid + ": unsupported claim type")
        need(f["claim_type"] != "coverage_gap" or f["evidence_type"] == "unknown", "coverage gap cannot be resolved")
        need(f["claim_type"] != "inference" or f["evidence_type"] == "inference", "inference cannot be a proven fact")
        need(f["impact"] in ("benefit", "adverse", "neutral", "unknown"), "finding impact missing")
        severity = f["adverse_severity"]
        need(severity in ("critical", "high", "medium", "low", "none", "unknown"), "finding severity missing")
        need((f["impact"] == "adverse") == (severity in ("critical", "high", "medium", "low")),
             "adverse impact and severity disagree")
        support = f["support"]
        need(isinstance(support, list) and bool(support), fid + ": typed support missing")
        seen, direct = set(), False
        for item in support:
            need(set(item) == {"evidence_id", "role", "scope_id"}, "support requires evidence, role and scope")
            eid, role, item_scope = item["evidence_id"], item["role"], item["scope_id"]
            need(eid in evidence and role in SUPPORT_ROLES and item_scope in allowed_scopes, "invalid support binding")
            key = (eid, role, item_scope)
            need(key not in seen, "duplicate support binding")
            seen.add(key)
            ev = evidence[eid]
            need(identity(ev) == identity(scope[item_scope]), "support scope differs from evidence identity")
            failed = eid in unavailable
            if role == "direct":
                need(not failed and ev["pin_id"] == f["pin_id"], "direct evidence unavailable or at wrong pin")
                direct |= item_scope == sid
            if role in ("source", "calculation") and f["evidence_type"] in ("proven_fact", "strongly_supported"):
                need(not failed, "resolved finding has unavailable required input")
        need({x["evidence_id"] for x in support} == set(f["evidence_ids"]), "flat/typed evidence references differ")
        need(f["evidence_type"] in ("unknown", "inference") or direct, fid + ": resolved subject lacks direct evidence")
        if f["claim_type"] == "historical_execution":
            execution = f["execution"]
            need(isinstance(execution, dict) and {"receipt_evidence_id", "result", "effects"} <= set(execution),
                 fid + ": execution needs receipt_evidence_id, result and effects")
            eid = execution["receipt_evidence_id"]
            need(eid in f["evidence_ids"], "execution receipt is not finding evidence")
            receipt = rpc_result(evidence, objects, eid, "eth_getTransactionReceipt")
            need(evidence[eid]["pin_id"] == f["pin_id"], "execution receipt pin mismatch")
            need(execution["result"] in ("success", "reverted"), "execution outcome missing")
            need(quantity(receipt["status"]) == (1 if execution["result"] == "success" else 0),
                 "execution outcome contradicts receipt status")
            effects = execution["effects"]
            need(isinstance(effects, list), "execution effects must be explicit")
            need(execution["result"] != "success" or bool(effects), "successful target execution lacks decoded effects")
            need(execution["result"] != "reverted" or not effects, "reverted execution cannot assert persisted effects")
            target_effect = False
            effect_logs = set()
            for effect in effects:
                need(effect["kind"] == "erc20_transfer", "unsupported effect decoder; preserve as inference")
                asset = effect["asset_scope_id"]
                need(asset in allowed_scopes and effect["units"] == "raw_token_units", "effect asset/units missing")
                need(scope[asset]["chain_id"] == f["chain_id"], "effect asset crosses chains")
                need(type(effect["log_index"]) is int and effect["log_index"] not in effect_logs, "duplicate/invalid effect log")
                effect_logs.add(effect["log_index"])
                logs = [x for x in receipt["logs"] if quantity(x["logIndex"]) == effect["log_index"]]
                need(len(logs) == 1, "effect does not select one receipt log")
                log = logs[0]
                need(address(log["address"]) == address(scope[asset]["address"]), "effect asset differs from raw log")
                need(len(log["topics"]) == 3 and log["topics"][0].lower() ==
                     "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                     "effect is not a standard Transfer event")
                for position, key in ((1, "from_scope_id"), (2, "to_scope_id")):
                    actor = effect[key]
                    need(actor in allowed_scopes and scope[actor]["chain_id"] == f["chain_id"]
                         and log["topics"][position][2:26] == "0" * 24
                         and "0x" + log["topics"][position][-40:].lower() == address(scope[actor]["address"]),
                         "effect actor differs from raw log; transaction sender is not assumed seller")
                need(isinstance(effect["amount_raw"], str) and re_unsigned(effect["amount_raw"])
                     and len(log["data"]) == 66 and int(effect["amount_raw"]) == int(log["data"], 16),
                     "effect amount differs from raw log")
                target_effect |= asset == sid or sid in (effect["from_scope_id"], effect["to_scope_id"])
            need(execution["result"] != "success" or target_effect, "execution has no decoded effect on its subject")

    coverage = r["coverage_records"]
    need(isinstance(coverage, list) and len(coverage) == len(DIMENSIONS), "one coverage record per dimension required")
    need({c["dimension"] for c in coverage} == set(DIMENSIONS), "coverage dimensions missing/duplicated")
    for c in coverage:
        dimension = c["dimension"]
        need(c["status"] in ("checked", "partial", "unavailable", "not_checked", "not_applicable"), "coverage status missing")
        expected_coverage = {"checked": "complete", "partial": "partial", "unavailable": "unavailable",
                             "not_checked": "unavailable", "not_applicable": "not_applicable"}[c["status"]]
        need(ratings[dimension]["coverage"] == expected_coverage, "coverage/rating status mismatch")
        for key in ("surface", "outcome", "gap", "stop_reason", "next_check"):
            nonempty(c[key], dimension + " " + key)
        refs(c["evidence_ids"], evidence, dimension + " coverage evidence", required=c["status"] != "not_checked")
        refs(c["discovery_ids"], discoveries, dimension + " discovery coverage")
        refs(c["finding_ids"], findings, dimension + " coverage findings")
        need(set(c["finding_ids"]) == set(ratings[dimension]["finding_ids"]), "coverage/rating finding mismatch")
        if ratings[dimension]["status"] == "pass":
            need(c["status"] == "checked", "pass lacks completed dimension coverage")
        if ratings[dimension]["status"] == "concern":
            adverse = [findings[x] for x in c["finding_ids"] if findings[x]["impact"] == "adverse"]
            need(bool(adverse), "concern lacks an explicit adverse finding")
            order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            need(max(order[f["adverse_severity"]] for f in adverse) >= order[ratings[dimension]["severity"]],
                 "dimension severity exceeds its adverse findings")
    validate_stopping_review(r, evidence, findings)
    validate_completion_review(r)
    summary = {item["finding_id"]: item["signal"] for item in r["summary"]}
    for fid, f in findings.items():
        if f["impact"] == "adverse" and f["adverse_severity"] in ("high", "critical"):
            need(summary.get(fid) in ("Potential Risk", "Bad"), "summary omits individual high/critical adverse finding")
        need(summary.get(fid) != "Good" or f["impact"] in ("benefit", "neutral"), "Good contradicts finding impact")
        need(summary.get(fid) != "Bad" or f["impact"] == "adverse", "Bad requires an adverse finding")
    validate_decision_review(r, findings, ratings)


def validate_decision_review(report, findings, ratings):
    """Bind decision types to evidence; free-text truth still requires human review."""
    from validate_bundle import need, nonempty, refs
    if "decision_review_version" not in report:
        need("decision_review" not in report, "decision review requires its version marker")
        need(not (report.get("completion_review_version") == 2 and report.get("completion_status") == "complete"),
             "completed report requires its decision review")
        return  # Older frozen reports make no retrospective decision-review claim.
    need(type(report["decision_review_version"]) is int and report["decision_review_version"] in (1, 2),
         "unsupported decision review version")
    review = report.get("decision_review")
    need(isinstance(review, dict), "decision review missing")
    need(set(review) == {"requirements", "verdict", "synthesis", "actions"}, "invalid decision review fields")
    requirements = review["requirements"]
    need(isinstance(requirements, list), "explicit user requirements must be a list")
    reqs = {}
    for req in requirements:
        need(isinstance(req, dict) and set(req) == {"id", "text", "user_quote"}, "invalid user requirement")
        for key in req:
            nonempty(req[key], "user requirement " + key)
        need(req["id"] not in reqs, "duplicate user requirement")
        reqs[req["id"]] = req
    # Requirements document the user's actual words; the validator cannot verify
    # conversation provenance or infer preferences from analyst-selected exit sizes.
    adverse = {fid for fid, f in findings.items() if f["impact"] == "adverse" and not pure_coverage_gap(f)}
    severe = {fid for fid in adverse if findings[fid]["adverse_severity"] in ("high", "critical")}
    affirmative = {fid for fid, f in findings.items() if f["impact"] in ("benefit", "neutral")
                   and f["evidence_type"] in ("proven_fact", "strongly_supported")
                   and f["confidence"] in ("high", "medium")}
    concern_findings = {fid for rating in ratings.values() if rating["status"] == "concern"
                        for fid in rating["finding_ids"]}.intersection(adverse)
    for fid in adverse:
        concern = findings[fid].get("concern")
        need(isinstance(concern, dict) and set(concern) ==
             {"basis", "mechanism", "consequence", "requirement_ids"}, fid + ": concern mechanism missing")
        need(concern["basis"] in ("observed_behavior", "reachable_capability", "claim_mismatch",
                                  "adverse_inference", "user_requirement"), "invalid concern basis")
        nonempty(concern["mechanism"], "concern mechanism")
        nonempty(concern["consequence"], "concern holder consequence")
        refs(concern["requirement_ids"], reqs, "concern requirements",
             required=concern["basis"] == "user_requirement")
        need(findings[fid]["evidence_type"] != "unknown", "missing evidence cannot establish an adverse concern")
        need(any(s["role"] == "direct" and s["scope_id"] == findings[fid]["subject_scope_id"]
                 for s in findings[fid]["support"]), "adverse concern needs an observed subject-specific basis")
        need((concern["basis"] == "adverse_inference") == (findings[fid]["evidence_type"] == "inference"),
             "adverse inference must retain its evidence class and concern basis")
    verdict = review["verdict"]
    need(isinstance(verdict, dict) and set(verdict) ==
         {"kind", "scope", "finding_ids", "requirement_ids"}, "invalid verdict basis")
    kind = verdict["kind"]
    need(kind in VERDICT_KINDS, "invalid verdict kind")
    nonempty(verdict["scope"], "bounded verdict scope")
    refs(verdict["finding_ids"], findings, "verdict findings")
    refs(verdict["requirement_ids"], reqs, "verdict requirements", required=kind == "requirement_unverified")
    selected = set(verdict["finding_ids"])
    need(severe <= selected, "verdict omits high/critical adverse findings")
    need(not severe or kind == "adverse_findings", "high/critical concerns require an adverse verdict basis")
    if kind == "findings_with_limits":
        need(bool(selected & affirmative), "supported verdict requires affirmative evidence")
    elif kind == "adverse_findings":
        need(bool(selected & concern_findings), "adverse verdict requires an assessed adverse finding")
    elif kind == "requirement_unverified":
        need(any(pure_coverage_gap(findings[fid]) for fid in selected), "unverified requirement needs a coverage gap")
    coverage = {c["dimension"]: c for c in report["coverage_records"]}
    incomplete = {dim for dim, c in coverage.items() if c["status"] in ("partial", "not_checked", "unavailable")}
    synthesis = review["synthesis"]
    need(isinstance(synthesis, list) and len(synthesis) == len(ASSESSMENT_AXES)
         and {s["axis"] for s in synthesis} == set(ASSESSMENT_AXES), "four separate assessment axes required")
    synthesized = set()
    for item in synthesis:
        need(set(item) == {"axis", "conclusion", "finding_ids", "coverage_dimensions"}, "invalid synthesis fields")
        nonempty(item["conclusion"], "synthesis conclusion")
        refs(item["finding_ids"], findings, "synthesis findings")
        refs(item["coverage_dimensions"], coverage, "synthesis coverage")
        need(set(item["finding_ids"]) <= {fid for dim in item["coverage_dimensions"]
             for fid in coverage[dim]["finding_ids"]}, "synthesis findings differ from referenced coverage")
        synthesized.update(item["finding_ids"])
    need(severe <= synthesized, "synthesis omits high/critical adverse findings")
    actions = review["actions"]
    minimum = 1 if report["decision_review_version"] == 1 else 0
    need(isinstance(actions, list) and minimum <= len(actions) <= 3,
         "one to three prioritized actions required" if minimum else "at most three justified actions permitted")
    seen, mitigated = set(), set()
    for action in actions:
        need(isinstance(action, dict) and set(action) == {"id", "kind", "action", "reason", "finding_ids",
             "coverage_dimensions", "requirement_ids", "changes_view_if"}, "invalid decision action")
        for key in ("id", "action", "reason", "changes_view_if"):
            nonempty(action[key], "action " + key)
        need(action["id"] not in seen, "duplicate decision action")
        seen.add(action["id"])
        refs(action["finding_ids"], findings, "action findings")
        refs(action["coverage_dimensions"], coverage, "action coverage")
        linked = {fid for dim in action["coverage_dimensions"] for fid in coverage[dim]["finding_ids"]}
        need(set(action["finding_ids"]) <= linked, "action findings differ from referenced coverage")
        action_kind = action["kind"]
        need(action_kind in ("investigate", "mitigate", "requirement_gate", "use_within_scope"), "invalid action kind")
        if report["decision_review_version"] == 2 and report.get("completion_status") == "complete":
            need(action_kind != "investigate",
                 "completed report cannot delegate research: perform feasible checks; put externally unavailable facts in coverage")
        refs(action["requirement_ids"], reqs, "action requirements", required=action_kind == "requirement_gate")
        if action_kind == "mitigate":
            supporting = set(action["finding_ids"]) & concern_findings
            need(bool(supporting), "mitigation requires an assessed adverse finding, not missing research")
            mitigated.update(supporting)
        elif action_kind == "use_within_scope":
            need(bool(set(action["finding_ids"]) & affirmative), "scoped use requires affirmative evidence")
            need(not (set(action["coverage_dimensions"]) & incomplete), "scoped use requires completed declared coverage")
            need(all(ratings[dim]["status"] in ("pass", "not_applicable") for dim in action["coverage_dimensions"])
                 and not (linked & adverse), "scoped use cannot replace mitigation of a concern in its declared scope")
        else:
            need(bool(set(action["coverage_dimensions"]) & incomplete), "investigation/gate needs incomplete coverage")
            need(any(pure_coverage_gap(findings[fid]) for fid in action["finding_ids"]),
                 "investigation/gate needs an explicit coverage gap")
    need(severe <= mitigated, "actions omit high/critical adverse findings")


def validate_stopping_review(report, evidence, findings):
    """Check recorded stopping decisions, not the truth/exhaustiveness of research."""
    from validate_bundle import need, nonempty, refs
    coverage = report["coverage_records"]
    if "closure_review_version" not in report:
        need(not any("closure" in c for c in coverage), "stopping review requires its version marker")
        return  # Older strict reports have no retrospective stopping-review claim.
    need(type(report["closure_review_version"]) is int and report["closure_review_version"] == 1,
         "unsupported stopping review version")
    for c in coverage:
        incomplete = c["status"] in ("partial", "unavailable", "not_checked")
        has_gap = any(findings[fid]["evidence_type"] == "unknown" for fid in c["finding_ids"])
        need(incomplete or not has_gap, "closed coverage cannot retain an unresolved finding")
        if not incomplete:
            need("closure" not in c, "closed coverage must remove its stale stopping review")
            continue
        closure = c.get("closure")
        need(isinstance(closure, dict), c["dimension"] + ": stopping review missing")
        need(set(closure) == {"priority", "decision_impact", "attempts", "next_route"}, "invalid stopping review fields")
        priority = closure["priority"]
        need(priority in ("decision_critical", "material", "context"), "stopping priority missing")
        nonempty(closure["decision_impact"], "stopping decision impact")
        need(c["stop_reason"].strip().lower() != "intake only", "intake placeholder is not a stopping reason")
        attempts = closure["attempts"]
        need(isinstance(attempts, list), "surface attempts must be explicit")
        need(c["status"] != "not_checked" or not attempts, "not_checked cannot claim surface attempts")
        need(c["status"] == "not_checked" or bool(attempts), "attempted coverage requires captured surface attempts")
        attempted = set()
        for attempt in attempts:
            need(isinstance(attempt, dict) and set(attempt) == {"check", "outcome", "evidence_ids"}, "invalid surface attempt")
            nonempty(attempt["check"], "attempt check")
            nonempty(attempt["outcome"], "attempt outcome")
            refs(attempt["evidence_ids"], evidence, "attempt evidence")
            need(set(attempt["evidence_ids"]) <= set(c["evidence_ids"]), "attempt references must belong to surface coverage")
            attempted.update(attempt["evidence_ids"])
        route = closure["next_route"]
        need(isinstance(route, dict) and set(route) == {"check", "disposition", "basis", "evidence_ids"}, "invalid next route")
        nonempty(route["check"], "next route check")
        nonempty(route["basis"], "next route stopping basis")
        disposition = route["disposition"]
        checkpoint = report.get("completion_review_version") in (1, 2) and report.get("completion_status") == "checkpoint"
        need(disposition != "pending" or checkpoint, "next route remains pending; continue or document the actual boundary")
        need(disposition in ("pending", "exhausted", "unavailable", "budget_exhausted", "out_of_scope", "not_yet_observable"), "invalid stopping disposition")
        refs(route["evidence_ids"], evidence, "next route evidence",
             required=disposition in ("exhausted", "unavailable", "not_yet_observable"))
        if disposition == "exhausted":
            need(bool(attempted), "exhausted route requires captured attempts")
            need(set(route["evidence_ids"]) <= attempted, "exhausted route evidence must belong to attempts")
        if disposition == "out_of_scope":
            need(priority != "decision_critical", "decision-critical gap cannot be out of scope")
            need(c["status"] == "not_checked", "scope exclusion must be an explicitly not-checked surface")


def validate_completion_review(report):
    """Separate unfinished work from a finished review with irreducible evidence limits."""
    from validate_bundle import need
    if "completion_review_version" not in report:
        need("completion_status" not in report, "completion status requires its version marker")
        need("delivery_status" not in report, "delivery status requires completion review version 2")
        return  # Frozen older reports retain their original completion semantics.
    need(type(report["completion_review_version"]) is int and report["completion_review_version"] in (1, 2),
         "unsupported completion review version")
    need(report.get("closure_review_version") == 1, "completion review requires stopping review")
    need(report.get("completion_status") in ("complete", "checkpoint"), "invalid completion status")
    if report["completion_review_version"] == 2:
        expected = "internal_checkpoint" if report["completion_status"] == "checkpoint" else "final_report"
        need(report.get("delivery_status") == expected, "delivery status contradicts research completion")
    else:
        need("delivery_status" not in report, "delivery status requires completion review version 2")
    if report["completion_status"] == "checkpoint":
        return
    for surface in report["coverage_records"]:
        dimension = surface["dimension"]
        need(surface["status"] != "not_checked", dimension + ": required surface not investigated; continue before final delivery")
        if surface["status"] in ("partial", "unavailable"):
            route = surface["closure"]["next_route"]
            need(route["disposition"] in ("exhausted", "unavailable", "not_yet_observable"),
                 dimension + ": unfinished work cannot be a completed report; continue research; internal saves do not permit final delivery")
            need(bool(surface["closure"]["attempts"]) and bool(route["evidence_ids"]),
                 dimension + ": completed review needs evidenced attempts and an external evidence boundary")
            need(set(route["evidence_ids"]) <= set(surface["evidence_ids"]),
                 dimension + ": completion boundary evidence must belong to this surface")


def re_unsigned(value):
    import re
    return re.fullmatch(r"0|[1-9][0-9]*", value) is not None
