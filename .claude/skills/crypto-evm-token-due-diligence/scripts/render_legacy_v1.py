#!/usr/bin/env python3
"""Render the validated, reconciled JSON source without fetching any new evidence."""
import argparse
import html
import json
import sys
from pathlib import Path
from validate_bundle import Invalid, sha, validate
REPORTING_ENGINE_VERSION = "1.1.2"
LIMITS = "Passing checks internal consistency only; it does not prove RPC honesty, discovery completeness, source correspondence, economic correctness, or protocol safety."
SUMMARY_TOPICS = {"token_and_liquidity": "Token and liquidity", "real_work_vs_marketing": "Real work vs marketing", "creator_trading_and_proceeds": "Creator trading and proceeds", "prior_launches_and_identity": "Prior launches and identity"}


def safe(value):
    # External metadata and prose remain text, never raw HTML, images or directives.
    text = html.escape(str(value), quote=False)
    for char in "\\`*_{}[]()#+!|":
        text = text.replace(char, "\\" + char)
    return text.replace("\n", " ").replace("\r", " ")


def structured(value):
    return safe(json.dumps(value, sort_keys=True, ensure_ascii=False))


def render_summary(m, r):
    findings = {f["id"]: (n, f) for n, f in enumerate(r["findings"], 1)}
    lines = []
    for chain in m["chains"]:
        pin = next(p for p in chain["pins"] if p["id"] == chain["current_pin"])
        lines += [f"As of: chain {chain['chain_id']}, block {pin['number']}, {pin['timestamp_utc']}."]
    lines += ["", f"Scope: {safe(r['conditions'])}", "",
              "✅ Good = supported positive finding · 🟡 Potential Risk = concern or evidence gap · 🔴 Bad = supported material problem.",
              "Labels apply to the stated findings and time basis; Good is not a safety verdict.", "",
              "| Area | Assessment | Finding |", "| --- | --- | --- |"]
    for item in r["summary"]:
        n, f = findings[item["finding_id"]]
        signal = item["signal"]
        if f["evidence_type"] in ("unknown", "inference"):
            signal += " — " + f["evidence_type"].capitalize()
        elif f["confidence"] == "low":
            signal += " — Low confidence"
        marker = {"Good": "✅", "Potential Risk": "🟡", "Bad": "🔴"}[item["signal"]]
        lines += [f"| {SUMMARY_TOPICS[item['topic']]} | {marker} **{signal}** | "
                  f"{safe(f['proposition'])} ({safe(f['time_basis'])}); [evidence](#finding-{n}). |"]
    lines += ["", f"**Strongest contrary evidence:** {safe(r['strongest_contrary_evidence'])}", "",
              f"**Key limits:** {safe(r['unresolved_questions'])}", "",
              f"**What would change the view:** {safe(r['change_evidence'])}", "",
              "## Evidence and technical detail", "", f"Reporting engine: {REPORTING_ENGINE_VERSION}", ""]
    return lines


def render(m, r, report_sha):
    t = r["target"]
    lines = ["# Crypto EVM token due diligence", ""]
    if r["synthetic"]:
        lines += ["**SYNTHETIC FIXTURE — NOT LIVE TOKEN FINDINGS**", ""]
    lines += [safe(r["verdict"]), "", f"Target: chain {t['chain_id']} · `{t['address']}`", ""]
    if "summary" in r:
        lines += render_summary(m, r)
    lines += [f"Manifest SHA-256: `{r['manifest_sha256']}`", f"Report-source SHA-256: `{report_sha}`", "",
              f"Question: {safe(m['question'])}", f"Conditions: {safe(r['conditions'])}", ""]
    for key, label in (("main_reasons", "Main reasons"), ("strongest_contrary_evidence", "Strongest contrary evidence"),
                       ("unresolved_questions", "Unresolved questions"), ("change_evidence", "Evidence that could change the conclusion")):
        lines += [f"**{label}:** {safe(r[key])}", ""]
    lines += ["## Investigation context", ""]
    for key, value in sorted(m["context"].items()):
        lines += [f"- {safe(key)}: {structured(value)}"]
    lines += ["", "## Target metadata", ""]
    for key, item in sorted(r["metadata"].items()):
        value = item["value"] if item["status"] == "resolved" else "Unresolved: " + item["reason"]
        lines += [f"- {safe(key)}: {safe(value)} ({safe(', '.join(item['evidence_ids']))})"]
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
        lines.append("")
    lines += ["## Discovery coverage", ""]
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
    for e in m["evidence"]:
        lines += [f"- {safe(e['id'])}: chain {e['chain_id']} · `{e['address']}` · pin {safe(e['pin_id'])} · "
                  f"transaction {safe(e.get('tx_hash') or 'none')} · {safe(e['kind'])} · {safe(e['artifact'])} · SHA-256 `{e['sha256']}`. "
                  f"Query: {structured(e['query'])}. Decoding: {safe(e['decoding_basis'])}. Coverage: {safe(e['coverage'])}."]
    lines += ["", "## Limitations and execution boundaries", "", f"Materiality: {safe(m['materiality'])}", ""]
    lines += [f"- {safe(x)}" for x in m["limitations"]]
    lines += ["", structured(r["safety"]), "", LIMITS, ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    p.add_argument("--allow-synthetic", action="store_true")
    args = p.parse_args()
    try:
        m, r = validate(args.bundle, args.allow_synthetic)
        path = args.bundle / "report.md"
        path.write_text(render(m, r, sha((args.bundle / "report.json").read_bytes())), encoding="utf-8")
        print(path.resolve())
    except (Invalid, KeyError, TypeError, ValueError, OSError, IndexError, AttributeError, OverflowError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
