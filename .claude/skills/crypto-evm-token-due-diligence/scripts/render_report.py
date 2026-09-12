#!/usr/bin/env python3
"""Render the validated, reconciled JSON source without fetching any new evidence."""
import argparse
import html
import json
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit
from report_profile import ASSESSMENT_AXES, VERDICT_KINDS, CURRENT_PROFILE, LEGACY_PROFILE, pure_coverage_gap
from validate_bundle import Invalid, LIMITS, REPORTING_ENGINE_VERSION, SUMMARY_TOPICS, sha, validate


def safe(value):
    # External metadata and prose remain text, never raw HTML, images or directives.
    text = html.escape(str(value), quote=False)
    for char in "\\`*_{}[]()#+!|":
        text = text.replace(char, "\\" + char)
    return text.replace("\n", " ").replace("\r", " ")



def source_link(url, label="source"):
    """Only explicit public web links; untrusted prose is never interpreted as Markdown."""
    if not isinstance(url, str) or any(ord(c) <= 32 for c in url) or "\\" in url:
        return safe(url)
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return safe(url)
        parsed.port  # Reject malformed port syntax.
    except ValueError:
        return safe(url)
    return "[" + safe(label) + "](<" + quote(url, safe=":/?=&%#@+;,$~-._") + ">)"


def artifact_link(path):
    parts = PurePosixPath(path)
    if parts.is_absolute() or ".." in parts.parts or "\\" in path or any(ord(c) <= 32 for c in path):
        return safe(path)
    # The validator also resolves this path within the actual bundle before rendering.
    return "[" + safe(path) + "](<./" + quote(path, safe="/~-._") + ">)"


def evidence_links(ids, evidence):
    return ", ".join("[" + safe(eid) + "](#evidence-" + str(evidence[eid]) + ")" for eid in ids)


def structured(value):
    return safe(json.dumps(value, sort_keys=True, ensure_ascii=False))


def finding_links(ids, findings):
    return ", ".join("[" + safe(fid) + "](#finding-" + str(findings[fid][0]) + ")" for fid in ids)


def source_urls(evidence):
    """Use recorded provenance only; do not discover or construct destinations."""
    query = evidence.get("query", {})
    urls = [query.get("url")]
    for values in (query.get("source_urls", []),
                   evidence.get("derivation", {}).get("source_urls", [])):
        if isinstance(values, list):
            urls.extend(values)
    return list(dict.fromkeys(u for u in urls if isinstance(u, str)))


def finding_citations(finding, number, evidence):
    """Native Markdown citations from already loaded evidence, with a local fallback.

    Labels contain no emoji or image markup; the client owns any product/favicon
    decoration. Plain text remains the fallback on clients without link icons.

    Keep the frozen finding link even with live sources: a source may change and
    one URL need not support every clause of a composite finding. Failed captures,
    counterevidence and identity-only references are not affirmative citations.
    """
    links = [f"[evidence](#finding-{number})"]
    if pure_coverage_gap(finding):
        return links[0]
    excluded = {s["evidence_id"] for s in finding.get("support", [])
                if s.get("role") in ("failed_attempt", "counterevidence", "identity")}
    seen = set()
    for eid in finding.get("evidence_ids", []):
        e = evidence.get(eid, {})
        if (eid in excluded or e.get("kind") != "document" or e.get("redacted")
                or e.get("observation_status") != "ok"):
            continue
        for url in source_urls(e):
            # Reuse the renderer's existing URL escaping and scheme/auth checks.
            link = source_link(url)
            if not link.startswith("[source](<") or url in seen:
                continue
            host = urlsplit(url).hostname.lower()
            if host in ("github.com", "api.github.com", "raw.githubusercontent.com"):
                label = "Repository"
            elif host == "dexscreener.com" or host.endswith(".dexscreener.com"):
                label = "Market snapshot"
            else:
                label = "Source"
            links.append(source_link(url, label))
            seen.add(url)
            if len(seen) == 2:
                return " · ".join(links)
    return " · ".join(links)


def render_decision_review(r, findings):
    if r.get("decision_review_version") not in (1, 2):
        return []
    review = r["decision_review"]
    lines = ["", "### Assessment", ""]
    for item in review["synthesis"]:
        lines += [f"- **{ASSESSMENT_AXES[item['axis']]}:** {safe(item['conclusion'])} "
                  f"({finding_links(item['finding_ids'], findings)})"]
    if review["requirements"]:
        lines += ["", "**Explicit user requirements:**"]
        for req in review["requirements"]:
            lines += [f"- {safe(req['text'])}. User wording: “{safe(req['user_quote'])}”"]
    else:
        lines += ["", "Scope is general diligence; no additional user acceptance requirements were supplied."]
    if review["actions"]:
        lines += ["", "### Decision-useful next steps", ""]
    labels = {"investigate": "Resolve uncertainty", "mitigate": "Address an evidenced concern",
              "requirement_gate": "Check an explicit requirement", "use_within_scope": "Use within the checked scope"}
    for n, action in enumerate(review["actions"], 1):
        lines += [f"{n}. **{labels[action['kind']]} — {safe(action['action'])}** "
                  f"{safe(action['reason'])} What changes the assessment: {safe(action['changes_view_if'])} "
                  f"({finding_links(action['finding_ids'], findings)})"]
    lines += [""]
    return lines


def render_summary(m, r):
    findings = {f["id"]: (n, f) for n, f in enumerate(r["findings"], 1)}
    evidence = {e["id"]: e for e in m["evidence"]}
    lines = []
    for chain in m["chains"]:
        pin = next(p for p in chain["pins"] if p["id"] == chain["current_pin"])
        lines += [f"As of: chain {chain['chain_id']}, block {pin['number']}, {pin['timestamp_utc']}."]
    lines += ["", f"Scope: {safe(r['conditions'])}"]
    lines += render_decision_review(r, findings)
    lines += ["",
              "✅ Good = supported positive finding · 🟡 Potential Risk = observed concern or adverse inference · 🔴 Bad = supported material problem.",
              "⚪ Unverified = a research gap, not an observed defect or a passing check.",
              "Labels apply to the stated findings and time basis; Good is not a safety verdict."]
    gaps = []
    assessed_count = 0
    for item in r["summary"]:
        n, f = findings[item["finding_id"]]
        if pure_coverage_gap(f):
            # Older strict sources used Potential Risk for gaps. Keep their stored
            # signal intact while the current reading layer separates uncertainty.
            gaps.append((item, n, f))
            continue
        signal = item["signal"]
        if assessed_count == 0:
            lines += ["", "| Area | Assessment | Finding |", "| --- | --- | --- |"]
        assessed_count += 1
        if f["evidence_type"] in ("unknown", "inference"):
            signal += " — " + f["evidence_type"].capitalize()
        elif f["confidence"] == "low":
            signal += " — Low confidence"
        marker = {"Good": "✅", "Potential Risk": "🟡", "Bad": "🔴"}[item["signal"]]
        lines += [f"| {SUMMARY_TOPICS[item['topic']]} | {marker} **{signal}** | "
                  f"{safe(f['proposition'])} ({safe(f['time_basis'])}); {finding_citations(f, n, evidence)}. |"]
    if not r["summary"]:
        lines += ["", "No summary assessment has been composed; the evidence below is saved as an internal research checkpoint."]
    elif len(gaps) == len(r["summary"]):
        lines += ["", "No assessed findings were selected; the research gaps below do not establish a favorable or adverse token verdict."]
    if gaps:
        lines += ["", "### Research gaps", "",
                  "These checks limit research confidence and may prevent a decision; they do not add observed-risk counts.", "",
                  "| Area | Coverage | Missing evidence |", "| --- | --- | --- |"]
        for item, n, f in gaps:
            lines += [f"| {SUMMARY_TOPICS[item['topic']]} | ⚪ **Unverified** | "
                      f"{safe(f['proposition'])} ({safe(f['time_basis'])}); {finding_citations(f, n, evidence)}. |"]
    if r.get("closure_review_version") == 1:
        critical = sum(c.get("closure", {}).get("priority") == "decision_critical" for c in r["coverage_records"])
        if critical:
            lines += ["", f"**Coverage limits:** {critical} decision-critical coverage gaps affect specific conclusions; "
                      "they are research priorities, not an overall adverse verdict. See the [stopping review](#stopping-review)."]
    lines += ["", f"**Material counterevidence and mitigations:** {safe(r['strongest_contrary_evidence'])}", "",
              f"**Key limits:** {safe(r['unresolved_questions'])}", "",
              f"**What would change the view:** {safe(r['change_evidence'])}", "",
              "## Evidence and technical detail", "", f"Reporting engine: {REPORTING_ENGINE_VERSION}", ""]
    return lines


def render_stopping_review(r, evidence):
    if r.get("closure_review_version") != 1:
        return []
    lines = ["## Stopping review", "",
             "Recorded attempts and boundaries explain remaining gaps. Structural validation does not establish exhaustive research.", ""]
    reviewed = [c for c in r["coverage_records"] if "closure" in c]
    if not reviewed:
        lines += ["No incomplete coverage surfaces are declared; completed coverage still requires its stated evidence.", ""]
    for c in reviewed:
        closure, route = c["closure"], c["closure"]["next_route"]
        lines += [f"### {safe(c['surface'])}", "",
                  f"Priority: {safe(closure['priority'].replace('_', ' '))}. {safe(closure['decision_impact'])}", "",
                  f"Missing evidence: {safe(c['gap'])}", ""]
        if not closure["attempts"]:
            lines += ["No surface verification attempted; this is a disclosed coverage limit.", ""]
        for attempt in closure["attempts"]:
            lines += [f"- Attempt: {safe(attempt['check'])}. Outcome: {safe(attempt['outcome'])}. "
                      f"{evidence_links(attempt['evidence_ids'], evidence)}"]
        lines += ["", f"Stopped because: {safe(c['stop_reason'])}", "",
                  f"Next useful route: {safe(route['check'])}. Status: {safe(route['disposition'].replace('_', ' '))}. "
                  f"Basis: {safe(route['basis'])}. {evidence_links(route['evidence_ids'], evidence)}", "",
                  f"To resolve: {safe(c['next_check'])}", ""]
    return lines


def render(m, r, report_sha):
    if r.get("validation_profile", LEGACY_PROFILE) == LEGACY_PROFILE:
        from render_legacy_v1 import render as legacy_render
        return legacy_render(m, r, report_sha)
    evidence = {e["id"]: n for n, e in enumerate(m["evidence"], 1)}
    t = r["target"]
    lines = ["# Crypto EVM token due diligence", ""]
    if r["synthetic"]:
        lines += ["**SYNTHETIC FIXTURE — NOT LIVE TOKEN FINDINGS**", ""]
    if r.get("decision_review_version") in (1, 2):
        v = r["decision_review"]["verdict"]
        lines += [f"**{VERDICT_KINDS[v['kind']]}** · {safe(v['scope'])}", ""]
    if r.get("completion_review_version") in (1, 2):
        lines += ["**Research checkpoint — required work remains unfinished.**" if r["completion_status"] == "checkpoint"
                  else "**Review completed within the documented evidence limits.**", ""]
        if r.get("delivery_status") == "internal_checkpoint":
            lines += ["Internal save only; required research remains active. This is not a final deliverable.", ""]
    lines += [safe(r["verdict"]), "", f"Target: chain {t['chain_id']} · `{t['address']}`", ""]
    if "summary" in r:
        lines += render_summary(m, r)
    lines += [f"Manifest SHA-256: `{r['manifest_sha256']}`", f"Report-source SHA-256: `{report_sha}`", "",
              f"Question: {safe(m['question'])}", f"Conditions: {safe(r['conditions'])}", ""]
    for key, label in (("main_reasons", "Main reasons"), ("strongest_contrary_evidence", "Strongest contrary evidence"),
                       ("unresolved_questions", "Unresolved questions"), ("change_evidence", "Evidence that could change the conclusion")):
        lines += [f"**{label}:** {safe(r[key])}", ""]
    lines += render_stopping_review(r, evidence)
    lines += ["## Investigation context", ""]
    for key, value in sorted(m["context"].items()):
        lines += [f"- {safe(key)}: {structured(value)}"]
    lines += ["", "## Target metadata", ""]
    for key, item in sorted(r["metadata"].items()):
        value = item["value"] if item["status"] == "resolved" else "Unresolved: " + item["reason"]
        lines += [f"- {safe(key)}: {safe(value)} ({evidence_links(item['evidence_ids'], evidence)})"]
    lines += ["", "## Pins", ""]
    for chain in m["chains"]:
        for pin in chain["pins"]:
            lines += [f"- Chain {chain['chain_id']}, {safe(pin['id'])}: block {pin['number']}, `{pin['hash']}`, {pin['timestamp_utc']}."]
    lines += ["", "## Separate risk dimensions", "",
              "| Dimension | Status | Severity | Likelihood | Confidence | Coverage | Time basis | Findings |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for x in r["ratings"]:
        values = [x[k] for k in ("id", "status", "severity", "likelihood", "confidence", "coverage", "time_basis")]
        lines += ["| " + " | ".join(safe(v) for v in values + [", ".join(x["finding_ids"])]) + " |"]
    for x in r["ratings"]:
        lines += ["", f"**{safe(x['id'])}:** {safe(x['rationale'])}"]
    lines += ["", "## Finding-to-evidence ledger", ""]
    for n, f in enumerate(r["findings"], 1):
        if "summary" in r:
            lines += [f'<a id="finding-{n}"></a>', ""]
        lines += [f"### {safe(f['id'])}", "", safe(f["proposition"]), "",
                  f"Chain {f['chain_id']} · `{f['address']}` · pin {safe(f['pin_id'])} · {safe(f['time_basis'])}", ""]
        for k in ("evidence_type", "confidence", "evidence_ids", "decoding_basis", "alternatives", "coverage", "discovery_ids", "stale_when"):
            value = ", ".join(f[k]) if isinstance(f[k], list) else f[k]
            lines += [f"- {safe(k)}: {safe(value)}"]
        lines += [f"- Subject: {safe(f['subject_scope_id'])}; participants: {safe(', '.join(f['participant_scope_ids']) or 'none')}",
                  f"- Claim: {safe(f['claim_type'])}; impact: {safe(f['impact'])}; adverse severity: {safe(f['adverse_severity'])}"]
        for support in f["support"]:
            lines += [f"- {safe(support['role'])} for {safe(support['scope_id'])}: {evidence_links([support['evidence_id']], evidence)}"]
        if "execution" in f:
            lines += ["- Execution and decoded effects: " + structured(f["execution"])]
        lines.append("")
    lines += ["## Coverage by surface", "", "| Surface | Outcome | Gap / stop | Next check | Evidence |", "| --- | --- | --- | --- | --- |"]
    for c in r["coverage_records"]:
        lines += ["| " + " | ".join([safe(c["surface"]), safe(c["status"] + ": " + c["outcome"]),
                  safe(c["gap"] + "; " + c["stop_reason"]), safe(c["next_check"]), evidence_links(c["evidence_ids"], evidence)]) + " |"]
    lines += ["", "## Discovery coverage", ""]
    for d in m["discoveries"]:
        lines += [f"- {safe(d['id'])}, chain {d['chain_id']}: " + structured({k: v for k, v in d.items() if k not in ('id', 'chain_id')})]
    if not m["discoveries"]:
        lines += ["No discovery claims registered; this does not establish discovery completeness."]
    lines += ["", "## Material scope and runtime", ""]
    for s in m["scope"]:
        lines += [f"- {safe(s['id'])}: chain {s['chain_id']} · `{s['address']}` · roles {safe(', '.join(s['roles']))} · "
                  f"pin {safe(s['pin_id'])} · runtime {structured(s['runtime'])} · proxy {structured(s['proxy'])} · "
                  f"provenance {safe(', '.join(s['provenance']))}"]
    lines += ["", "## Evidence artifacts and reproducible queries", ""]
    for n, e in enumerate(m["evidence"], 1):
        lines += [f'<a id="evidence-{n}"></a>', ""]
        lines += [f"- {safe(e['id'])}: chain {e['chain_id']} · `{e['address']}` · pin {safe(e['pin_id'])} · "
                  f"transaction {safe(e.get('tx_hash') or 'none')} · {safe(e['kind'])} · {artifact_link(e['artifact'])} · SHA-256 `{e['sha256']}`. "
                  f"Query: {structured(e['query'])}. Decoding: {safe(e['decoding_basis'])}. Coverage: {safe(e['coverage'])}."]
        if e.get("input_evidence_ids"):
            lines += ["  Derived inputs: " + evidence_links(e["input_evidence_ids"], evidence)]
        for url in source_urls(e):
            lines += ["  " + source_link(url)]
    lines += ["", "## Limitations and execution boundaries", "", f"Materiality: {safe(m['materiality'])}", ""]
    lines += [f"- {safe(x)}" for x in m["limitations"]]
    lines += ["", structured(r["safety"]), "", LIMITS, ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    p.add_argument("--allow-synthetic", action="store_true")
    p.add_argument("--profile", choices=(CURRENT_PROFILE, LEGACY_PROFILE), default=CURRENT_PROFILE)
    p.add_argument("--output", type=Path, help="optional new output path for offline replay")
    args = p.parse_args()
    try:
        m, r = validate(args.bundle, args.allow_synthetic, required_profile=args.profile)
        path = args.output or args.bundle / "report.md"
        path.write_text(render(m, r, sha((args.bundle / "report.json").read_bytes())), encoding="utf-8")
        print(path.resolve())
    except (Invalid, KeyError, TypeError, ValueError, OSError, IndexError, AttributeError, OverflowError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
