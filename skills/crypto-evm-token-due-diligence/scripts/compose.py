"""Expand compact analyst notes into the strict report contract.

The note carries judgment (propositions, signals, coverage status, boundaries, decision);
this module supplies the mechanical plumbing the validator requires (support roles,
scope entries, coverage closure, ratings, summary, decision references). It never
invents evidence, never upgrades an unknown, and reports every problem it finds at once.
"""
import copy
import json
import re
from pathlib import Path

from backend_common import address, need, quantity, read_json, sha, stamp
from report_profile import ASSESSMENT_AXES, VERDICT_KINDS, pure_coverage_gap
from validate_bundle import DIMENSIONS, SUMMARY_TOPICS, Invalid

NOTE_SCHEMA = 1
CLAIMS = ("state_observation", "source_analysis", "historical_execution", "inference", "coverage_gap")
STRENGTHS = ("proven_fact", "strongly_supported", "inference", "unknown")
CONFIDENCES = ("high", "medium", "low", "unknown")
IMPACTS = ("benefit", "adverse", "neutral", "unknown")
SEVERITIES = ("critical", "high", "medium", "low", "none", "unknown")
SIGNALS = ("Good", "Potential Risk", "Bad", "Unverified")
COVERAGE_STATUSES = ("checked", "partial", "unavailable", "not_checked", "not_applicable")
BOUNDARIES = ("exhausted", "unavailable", "not_yet_observable", "pending", "out_of_scope", "budget_exhausted")
PRIORITIES = ("decision_critical", "material", "context")
CONCERN_BASES = ("observed_behavior", "reachable_capability", "claim_mismatch", "adverse_inference", "user_requirement")
ACTION_KINDS = ("investigate", "mitigate", "requirement_gate", "use_within_scope")
SEVERITY_ORDER = {"none": 0, "unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
EFFECT_SHAPE = ('; expected shape: [{"kind": "erc20_transfer", "log_index": N, "asset_scope_id": "target", "from_scope_id": "SCOPE", '
                '"to_scope_id": "SCOPE", "amount_raw": "INTEGER", "units": "raw_token_units"}] where every scope id is target or declared in note.scope')

DEFAULT_TOPIC = {
    "token_controls": "token_and_liquidity", "canonical_lp_principal_custody": "token_and_liquidity",
    "side_pool_removal_risk": "token_and_liquidity", "sellability_exit_depth": "token_and_liquidity",
    "current_concentration": "token_economics", "historical_launch_integrity": "creator_trading_and_proceeds",
    "admin_treasury_reward_custody": "token_and_liquidity", "reward_accounting_liveness": "token_economics",
    "utility_redemption_rights": "token_economics", "external_dependencies": "token_and_liquidity",
    "development_disclosure": "real_work_vs_marketing",
}
AXIS_DIMENSIONS = {
    "technical_exposure": ["token_controls", "canonical_lp_principal_custody", "side_pool_removal_risk",
                           "sellability_exit_depth", "admin_treasury_reward_custody", "external_dependencies"],
    "credibility_maturity": ["development_disclosure", "historical_launch_integrity"],
    "token_economics": ["utility_redemption_rights", "reward_accounting_liveness", "current_concentration"],
    "research_confidence": list(DIMENSIONS),
}
CLAIM_BASIS = {
    "state_observation": "Raw pinned JSON-RPC results decoded per the standard ABI; semantics reviewed by the analyst",
    "source_analysis": "Runtime inspection with the linked source-correspondence result; reachability reviewed by the analyst",
    "historical_execution": "Receipt status and decoded standard ERC-20 Transfer logs at the historical pin",
    "inference": "Analyst inference from the linked observations; alternatives retained",
    "coverage_gap": "Linked attempts anchor an explicitly unresolved check; they do not prove this surface",
}


def redact_url(url):
    """Drop credential-like query parameters before a URL enters frozen evidence."""
    if not isinstance(url, str):
        return url
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
    parts = urlsplit(url)
    if parts.username or parts.password:
        parts = parts._replace(netloc=parts.hostname + (":" + str(parts.port) if parts.port else ""))
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not re.search(r"key|token|secret|sig|auth|password|passwd|apikey|api_key", k, re.I)]
    return urlunsplit(parts._replace(query=urlencode(kept)))


class NoteError(Exception):
    """Collected note problems; the draft is left unchanged when any exist."""

    def __init__(self, errors, warnings):
        super().__init__("; ".join(errors))
        self.errors, self.warnings = errors, warnings


def _text(value, field, errors, required=True, maximum=2000):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors.append(field + ": required text")
        return None
    if not isinstance(value, str) or len(value) > maximum:
        errors.append(field + ": must be a string of at most " + str(maximum) + " characters")
        return None
    if re.search(r"\b(TODO|TBD|PLACEHOLDER)\b|<[^>]+>", value, re.I):
        errors.append(field + ": contains an unfinished placeholder")
    return value.strip()


def _choice(value, options, field, errors, default=None):
    if isinstance(value, str) and re.match(r"\s*(TODO|TBD|PLACEHOLDER)\b", value, re.I):
        # A scaffold placeholder: name the choice once and fall back to the first (safest) option so no cascade follows.
        errors.append(field + ": unfinished placeholder; choose one of " + ", ".join(options))
        return default if default is not None else options[0]
    if value is None and default is not None:
        return default
    if value not in options:
        errors.append(field + ": must be one of " + ", ".join(options))
        return default if default is not None else options[-1]
    return value


def current_pin(draft):
    """Same selection rule as assembly: latest runtime-backed pin unless the coordinator chose one."""
    target = draft["target"]
    runtime_pins = {e["pin_id"] for e in draft["evidence"] if e["chain_id"] == target["chain_id"]
                    and e["address"] == target["address"] and e["query"].get("method") == "eth_getCode"}
    candidates = [p for p in draft["pins"] if p["id"] in runtime_pins
                  and (draft.get("current_pin") is None or p["id"] == draft["current_pin"])]
    need(bool(candidates), "draft has no target runtime evidence; import a collection first")
    return max(candidates, key=lambda p: (p["number"], p["timestamp_utc"]))


def find_pin(draft, value):
    if value is None:
        return None
    for pin in draft["pins"]:
        if pin["id"] == value or (type(value) is int and pin["number"] == value) or (isinstance(value, str) and value.isdigit() and pin["number"] == int(value)):
            return pin
    return None


def evidence_failed(root, ev):
    if ev.get("redacted"):
        return True
    status = ev.get("observation_status")
    if status is not None:
        return status != "ok"
    if ev["kind"] != "rpc":
        return False
    try:
        response = read_json(root / ev["artifact"]).get("response", {})
    except (OSError, ValueError, KeyError):
        return True
    return "error" in response or response.get("result") is None


class Composer:
    def __init__(self, root, draft, lane=None, final=True):
        from bundle_assemble import resolve_evidence
        self.root, self.d, self.lane, self.final = Path(root), draft, lane, final
        self.resolve_fn = resolve_evidence
        self.errors, self.warnings = [], []
        self.target = draft["target"]
        self.pin = current_pin(draft)
        self.by_id = {e["id"]: e for e in draft["evidence"]}
        self.scopes = {s["id"]: s for s in draft["scope"]}
        self.scope_by_address = {s["address"]: s["id"] for s in draft["scope"]}
        self.scope_by_address.setdefault(self.target["address"], "target")
        self.index = draft.setdefault("note_index", {})
        self.registered = []
        self.staged = []

    # ----- evidence -----------------------------------------------------------------
    def evidence(self, spec, field):
        alias, addr, pin, role = spec, None, None, None
        if isinstance(spec, dict):
            alias, addr, pin, role = spec.get("id"), spec.get("address"), spec.get("pin"), spec.get("role")
        elif isinstance(spec, str):
            if "#" in spec:
                alias, role = spec.rsplit("#", 1)
            if "@" in alias:
                alias, addr = alias.split("@", 1)
        if not isinstance(alias, str) or not alias:
            self.errors.append(field + ": evidence reference must be an alias string or {id, address, pin, role}")
            return None, None
        pin_id = find_pin(self.d, pin)["id"] if pin is not None and find_pin(self.d, pin) else pin
        try:
            row = self.resolve_fn(self.d, alias, addr, pin_id)
        except Invalid:
            row = self.register_capture(alias, addr)
            if row is None:
                self.errors.append(field + ": evidence alias not found or ambiguous: " + alias
                                   + " (use bundle_assemble.py facts to list aliases; add @address to disambiguate)")
                return None, None
        if role is not None and role not in ("direct", "identity", "source", "calculation", "corroboration", "counterevidence", "failed_attempt"):
            self.errors.append(field + ": unsupported support role " + str(role))
            role = None
        return row, role

    def register_capture(self, alias, addr):
        """Lane captures saved by web_capture.py become document evidence on first reference.

        Registration is staged: the evidence row is added to the in-memory draft and the
        payload is copied only when the whole note is accepted (see commit_captures).
        """
        if self.lane is None or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", str(self.lane)) or not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", alias):
            return None
        lane_dir = (self.root.parent / "lanes" / self.lane).resolve()
        provenance = lane_dir / (alias + ".json")
        if not provenance.is_file():
            return None
        try:
            meta = read_json(provenance)
            raw_name = meta.get("raw") or (alias + ".raw")
            need(isinstance(raw_name, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,60}\.raw", raw_name), "capture raw file name is not a plain <id>.raw")
            raw = (lane_dir / raw_name).resolve()
            need(raw.parent == lane_dir and provenance.resolve().parent == lane_dir, "capture files must live in the lane directory")
            source = raw if raw.is_file() else provenance
            eid = "doc-" + self.lane + "-" + alias
            if eid in self.by_id:
                return self.by_id[eid]
            capture_address = address(addr or meta.get("address") or self.target["address"])
            ok = meta.get("http_status") == 200 and meta.get("failure_category") is None
            url = redact_url(meta.get("url"))
            descriptor = {"id": eid, "kind": "document", "target": dict(self.target), "chain_id": self.target["chain_id"],
                          "address": capture_address, "pin_id": self.pin["id"], "tx_hash": None,
                          "captured_at_utc": meta.get("captured_at_utc") or stamp(),
                          "endpoint_label": re.sub(r"[^A-Za-z0-9_-]", "-", str(meta.get("host") or "web"))[:80] or "web",
                          "query": {"operation": "web_capture", "url": url, "final_url": redact_url(meta.get("final_url")),
                                    "http_status": meta.get("http_status"), "capture_mode": "downloaded_response",
                                    "source_urls": [url], "lane": self.lane},
                          "decoding_basis": "Raw HTTP response bytes preserved with provenance; attributed source material, not verified onchain fact",
                          "coverage": "Single bounded capture at the recorded retrieval time",
                          "observation_status": "ok" if ok else "unavailable"}
            payload = source.read_bytes()
            row = dict(descriptor, artifact="evidence/" + eid + source.suffix, sha256=sha(payload))
            self.d["evidence"].append(row)
            self.by_id[row["id"]] = row
            self.staged.append((row, payload))
            self.registered.append(row["id"])
            return row
        except (Invalid, ValueError, OSError, KeyError) as exc:
            self.errors.append(alias + ": lane capture could not be registered: " + str(exc))
            return None

    def commit_captures(self):
        """Write staged capture payloads after the note is accepted."""
        if getattr(self, "dry_run", False):
            return
        for row, payload in self.staged:
            dest = self.root / row["artifact"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                need(dest.read_bytes() == payload, "capture artifact already exists with different bytes")
            else:
                with dest.open("xb") as stream:
                    stream.write(payload)

    def receipt_status(self, row):
        try:
            receipt = read_json(self.root / row["artifact"])["response"]["result"]
            return "success" if quantity(receipt.get("status", "0x0")) == 1 else "reverted"
        except (OSError, ValueError, KeyError, TypeError, Invalid):
            return None

    def derive_effects(self, receipt_row, subject_id, subject_addr, participants):
        """Decode the receipt's target-token Transfer logs into effects whose parties are known scopes.

        Only logs that touch the finding's subject are used, so the strict profile's subject-effect
        rule holds; parties without any pinned evidence row are reported, never invented.
        """
        try:
            receipt = read_json(self.root / receipt_row["artifact"])["response"]["result"]
        except (OSError, ValueError, KeyError, TypeError):
            return [], []
        asset_id = self.ensure_target_scope()
        effects, skipped = [], []
        for log in receipt.get("logs") or []:
            topics = log.get("topics") or []
            try:
                if not (len(topics) == 3 and str(topics[0]).lower() == TRANSFER_TOPIC and address(log["address"]) == self.target["address"]
                        and isinstance(log.get("data"), str) and len(log["data"]) == 66):
                    continue
                parties = {}
                for position, key in ((1, "from_scope_id"), (2, "to_scope_id")):
                    party = address("0x" + str(topics[position])[-40:])
                    parties[key] = "target" if party == self.target["address"] else self.scope_by_address.get(party) or self.scope_for(party, {"pin_id": receipt_row["pin_id"]}, quiet=True)
                    if parties[key] is None:
                        skipped.append(party)
                if None in parties.values():
                    continue
                if subject_id != asset_id and subject_id not in parties.values():
                    continue
                effects.append({"kind": "erc20_transfer", "log_index": quantity(log["logIndex"]), "asset_scope_id": asset_id, **parties,
                                "amount_raw": str(int(log["data"], 16)), "units": "raw_token_units"})
            except (Invalid, ValueError, KeyError, TypeError):
                continue
        return effects, sorted(set(skipped))

    # ----- scope --------------------------------------------------------------------
    def scope_for(self, addr, hint=None, note_scope=None, quiet=False):
        addr = address(addr)
        if addr in self.scope_by_address:
            return self.scope_by_address[addr]
        rows = [e for e in self.d["evidence"] if e["address"] == addr and e["chain_id"] == self.target["chain_id"] and e["pin_id"]]
        if not rows:
            if not quiet:
                self.errors.append("scope for " + addr + ": no pinned evidence row at this address; collect a code or getter read first")
            return None
        code_rows = [e for e in rows if e["query"].get("method") == "eth_getCode" and not evidence_failed(self.root, e)]
        preferred_pin = (hint or {}).get("pin_id") or self.pin["id"]
        chosen = [e for e in code_rows if e["pin_id"] == preferred_pin] or code_rows or [e for e in rows if e["pin_id"] == preferred_pin] or rows
        chosen = max(chosen, key=lambda e: e["captured_at_utc"])
        pin_id = chosen["pin_id"]
        at_pin = [e for e in rows if e["pin_id"] == pin_id]
        sid = (note_scope or {}).get("id") or ("addr-" + addr[2:10])
        base = sid
        counter = 2
        while sid in self.scopes:
            sid = base + "-" + str(counter)
            counter += 1
        runtime = {"status": "unavailable", "reason": "Runtime bytes were not read at this pin", "evidence_ids": [e["id"] for e in at_pin]}
        if chosen["query"].get("method") == "eth_getCode" and not evidence_failed(self.root, chosen):
            code = read_json(self.root / chosen["artifact"])["response"]["result"]
            raw = bytes.fromhex(code[2:])
            from keccak import keccak256_hex
            runtime = {"status": "no_code" if code == "0x" else "captured", "evidence_id": chosen["id"],
                       "sha256": sha(raw), "keccak256": keccak256_hex(raw)}
        proxy = {"status": "unresolved", "basis": "Proxy and upgrade authority for this referenced contract were not reconciled in this note",
                 "evidence_ids": [e["id"] for e in at_pin], "implementation_scope_ids": [], "authority_scope_ids": []}
        entry = {"id": sid, "chain_id": self.target["chain_id"], "address": addr,
                 "roles": list((note_scope or {}).get("roles") or ["referenced contract or account"]),
                 "material": bool((note_scope or {}).get("material", False)), "pin_id": pin_id,
                 "provenance": [e["id"] for e in at_pin], "runtime": runtime, "proxy": proxy}
        self.scopes[sid] = entry
        self.scope_by_address[addr] = sid
        self.d["scope"].append(entry)
        return sid

    def apply_note_scope(self, entries):
        for n, item in enumerate(entries or []):
            field = "scope[" + str(n) + "]"
            if not isinstance(item, dict) or not (item.get("address") or item.get("id") == "target" or item.get("id") in self.scopes):
                self.errors.append(field + ": needs an address, id target, or the id of an existing scope")
                continue
            addr = self.target["address"] if item.get("id") == "target" else item.get("address") or self.scopes[item["id"]]["address"]
            try:
                addr = address(addr)
            except Invalid as exc:
                self.errors.append(field + ": " + str(exc))
                continue
            sid = self.scope_by_address.get(addr)
            if sid is None or sid == "target":
                if sid == "target":
                    sid = self.ensure_target_scope()
                else:
                    sid = self.scope_for(addr, note_scope=item)
                if sid is None:
                    continue
            wanted = item.get("id")
            if wanted and wanted != sid and sid != "target":
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", str(wanted)) or wanted in self.scopes:
                    self.errors.append(field + ": scope id " + str(wanted) + " is invalid or already used by another address")
                    continue
                self.rename_scope(sid, wanted)
                sid = wanted
            entry = self.scopes[sid]
            if item.get("roles"):
                entry["roles"] = list(dict.fromkeys([*entry["roles"], *item["roles"]])) if sid == "target" else list(item["roles"])
            if "material" in item:
                entry["material"] = bool(item["material"])
            proxy = item.get("proxy")
            if isinstance(proxy, dict):
                status = _choice(proxy.get("status"), ("none_found", "resolved", "unresolved", "not_applicable"), field + ".proxy.status", self.errors)
                basis = _text(proxy.get("basis"), field + ".proxy.basis", self.errors)
                impl = [self.scope_for(x) for x in proxy.get("implementation", [])] if isinstance(proxy.get("implementation"), list) else ([self.scope_for(proxy["implementation"])] if proxy.get("implementation") else [])
                auth = [self.scope_for(x) for x in proxy.get("authority", [])]
                if status == "resolved" and not impl:
                    self.errors.append(field + ".proxy: resolved requires an implementation address")
                entry["proxy"].update(status=status, basis=basis or entry["proxy"]["basis"],
                                      implementation_scope_ids=[x for x in impl if x], authority_scope_ids=[x for x in auth if x])
                extra = [self.evidence(x, field + ".proxy.evidence")[0] for x in proxy.get("evidence", [])]
                entry["proxy"]["evidence_ids"] = list(dict.fromkeys([*entry["proxy"]["evidence_ids"], *[e["id"] for e in extra if e]]))

    def apply_signals(self, signals, findings_by_id):
        """Give existing findings (typically the pipeline's) a summary topic and signal without restating them."""
        if signals is None:
            return
        if not isinstance(signals, dict):
            self.errors.append("signals: must map finding id -> {topic, signal}")
            return
        for fid, spec in signals.items():
            field = "signals." + str(fid)
            f = findings_by_id.get(fid)
            if f is None:
                self.errors.append(field + ": unknown finding id (compose the pipeline or lane note first)")
                continue
            if not isinstance(spec, dict):
                self.errors.append(field + ": must be {topic, signal}")
                continue
            if any(isinstance(spec.get(k), str) and re.match(r"\s*TODO\b", spec[k]) for k in ("topic", "signal")):
                self.errors.append(field + ": replace the TODO topic/signal (Good or Potential Risk with one of " + ", ".join(SUMMARY_TOPICS) + ") or delete the entry")
                continue
            topic = _choice(spec.get("topic"), tuple(SUMMARY_TOPICS), field + ".topic", self.errors)
            signal = _choice(spec.get("signal"), SIGNALS, field + ".signal", self.errors)
            if topic is None or signal is None:
                continue
            impact, strength, confidence = f["impact"], f["evidence_type"], f["confidence"]
            if signal == "Good" and (impact not in ("benefit", "neutral") or strength not in ("proven_fact", "strongly_supported") or confidence not in ("high", "medium")):
                self.errors.append(field + ": Good needs a resolved benefit/neutral finding with high/medium confidence; this one is " + impact + "/" + strength + "/" + confidence)
            if signal == "Bad" and (impact != "adverse" or strength not in ("proven_fact", "strongly_supported") or SEVERITY_ORDER.get(f.get("adverse_severity"), 0) < 2):
                self.errors.append(field + ": Bad needs an adverse, resolved finding of at least medium severity; write an adverse finding instead")
            if signal == "Unverified" and f["claim_type"] != "coverage_gap":
                self.errors.append(field + ": Unverified is only for coverage gaps; use Potential Risk for an observed concern")
            if signal in ("Good", "Bad") and any(evidence_failed(self.root, self.by_id[e]) for e in f["evidence_ids"] if e in self.by_id):
                self.errors.append(field + ": Good/Bad cannot rest on failed evidence")
            entry = self.index.setdefault(fid, {"dimensions": [d for d in DIMENSIONS if d in self.dimensions_of(f)], "order": len(self.index)})
            entry.update(topic=topic, signal=signal)

    def dimensions_of(self, finding):
        for record in self.d.get("coverage_records", []):
            if finding["id"] in record.get("finding_ids", []):
                yield record["dimension"]

    def rename_scope(self, old, new):
        """Give an auto-generated scope the analyst's readable id, updating every reference in the draft."""
        entry = self.scopes.pop(old)
        entry["id"] = new
        self.scopes[new] = entry
        self.scope_by_address[entry["address"]] = new
        for scope in self.d["scope"]:
            for key in ("implementation_scope_ids", "authority_scope_ids"):
                scope["proxy"][key] = [new if x == old else x for x in scope["proxy"].get(key, [])]
        for finding in self.d["findings"]:
            if finding.get("subject_scope_id") == old:
                finding["subject_scope_id"] = new
            finding["participant_scope_ids"] = [new if x == old else x for x in finding.get("participant_scope_ids", [])]
            for support in finding.get("support", []):
                if support.get("scope_id") == old:
                    support["scope_id"] = new
            for effect in (finding.get("execution") or {}).get("effects", []) if isinstance(finding.get("execution"), dict) else []:
                for key in ("asset_scope_id", "from_scope_id", "to_scope_id"):
                    if effect.get(key) == old:
                        effect[key] = new

    def ensure_target_scope(self):
        if "target" in self.scopes:
            return "target"
        rows = [e for e in self.d["evidence"] if e["address"] == self.target["address"] and e["pin_id"] == self.pin["id"]]
        runtime_rows = [e for e in rows if e["query"].get("method") == "eth_getCode"]
        need(bool(runtime_rows), "target runtime evidence missing at the current pin")
        runtime_row = runtime_rows[-1]
        code = read_json(self.root / runtime_row["artifact"]).get("response", {}).get("result")
        runtime = {"status": "unavailable", "reason": "Runtime RPC unavailable", "evidence_ids": [runtime_row["id"]]}
        if isinstance(code, str):
            from keccak import keccak256_hex
            raw = bytes.fromhex(code[2:])
            runtime = {"status": "no_code" if code == "0x" else "captured", "evidence_id": runtime_row["id"], "sha256": sha(raw), "keccak256": keccak256_hex(raw)}
        entry = {"id": "target", **self.target, "roles": ["target token"], "material": True, "pin_id": self.pin["id"],
                 "provenance": [runtime_row["id"]], "runtime": runtime,
                 "proxy": {"status": "unresolved", "basis": "Architecture/authority review has not been reconciled",
                           "evidence_ids": [runtime_row["id"]], "implementation_scope_ids": [], "authority_scope_ids": []}}
        self.scopes["target"] = entry
        self.d["scope"].append(entry)
        return "target"

    # ----- findings -----------------------------------------------------------------
    def finding(self, item, n):
        field = "findings[" + str(n) + "]"
        if not isinstance(item, dict):
            self.errors.append(field + ": must be an object")
            return None
        fid = item.get("id")
        if not isinstance(fid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", fid):
            self.errors.append(field + ": id must be 1-60 letters, digits, hyphens or underscores")
            return None
        field = "finding " + fid
        dimensions = item.get("dimensions") or ([item["dimension"]] if item.get("dimension") else [])
        if not dimensions or any(d not in DIMENSIONS for d in dimensions):
            self.errors.append(field + ": dimension(s) must name one of the eleven risk dimensions")
            dimensions = [d for d in dimensions if d in DIMENSIONS]
        claim = _choice(item.get("claim"), CLAIMS, field + ".claim", self.errors)
        if item.get("claim") in STRENGTHS and item.get("claim") not in CLAIMS:
            self.errors.append(field + ".claim: " + str(item["claim"]) + " is a strength value; claim names the kind of observation "
                               "(state_observation for pinned reads, source_analysis for matched source, historical_execution for a receipt, "
                               "inference for documents, coverage_gap for a gap)")
        strength = _choice(item.get("strength"), STRENGTHS, field + ".strength", self.errors,
                           default="unknown" if claim == "coverage_gap" else "inference" if claim == "inference" else None)
        confidence = _choice(item.get("confidence"), CONFIDENCES, field + ".confidence", self.errors,
                             default="unknown" if strength == "unknown" else None)
        impact = _choice(item.get("impact"), IMPACTS, field + ".impact", self.errors, default="unknown" if claim == "coverage_gap" else None)
        severity = item.get("severity")
        if severity is None:
            severity = "unknown" if impact == "unknown" else "none"
        severity = _choice(severity, SEVERITIES, field + ".severity", self.errors)
        if (impact == "adverse") != (severity in ("critical", "high", "medium", "low")):
            self.errors.append(field + ": adverse impact requires severity low/medium/high/critical, and only adverse findings carry one")
        if claim == "coverage_gap" and not pure_coverage_gap({"claim_type": claim, "evidence_type": strength, "confidence": confidence, "impact": impact, "adverse_severity": severity}):
            self.errors.append(field + ": a coverage gap must have unknown strength, confidence, impact and severity")
        if claim == "inference" and strength != "inference":
            self.errors.append(field + ": an inference cannot be a proven or strongly supported fact")
        if strength == "unknown" and confidence != "unknown" or strength != "unknown" and confidence == "unknown":
            self.errors.append(field + ": unknown strength and unknown confidence go together")
        text = _text(item.get("text"), field + ".text", self.errors)
        pin = find_pin(self.d, item.get("pin")) if item.get("pin") is not None else None
        if item.get("pin") is not None and pin is None:
            self.errors.append(field + ".pin: unknown pin id or block number")
        subject_spec = item.get("subject", "target")
        try:
            subject_addr = self.target["address"] if subject_spec in (None, "target") else (
                self.scopes[subject_spec]["address"] if subject_spec in self.scopes else address(subject_spec))
        except Invalid:
            self.errors.append(field + ".subject: use 'target', an existing scope id or an address")
            subject_addr = self.target["address"]
        evidence_rows, roles, seen = [], [], set()
        for spec in item.get("evidence") or []:
            row, role = self.evidence(spec, field + ".evidence")
            if row and row["id"] not in seen:
                seen.add(row["id"])
                evidence_rows.append((row, role))
        for spec in item.get("counterevidence") or []:
            row, _ = self.evidence(spec, field + ".counterevidence")
            if row and row["id"] not in seen:
                seen.add(row["id"])
                evidence_rows.append((row, "counterevidence"))
        if not evidence_rows:
            self.errors.append(field + ": at least one evidence alias is required")
            return None
        if claim == "historical_execution":
            receipts = [r for r, _ in evidence_rows if r["query"].get("method") == "eth_getTransactionReceipt" and not evidence_failed(self.root, r)]
            if not receipts:
                self.errors.append(field + ": historical execution needs a successful receipt evidence alias")
            elif pin is None:
                pin = find_pin(self.d, receipts[0]["pin_id"])
        pin = pin or self.pin
        subject_id = self.ensure_target_scope() if subject_addr == self.target["address"] else self.scope_for(subject_addr, {"pin_id": pin["id"]})
        if subject_id is None:
            return None
        participants, support, evidence_ids, has_direct = [], [], [], False
        for row, role in evidence_rows:
            row_scope = self.scope_for(row["address"], {"pin_id": row["pin_id"]}) if row["address"] != self.target["address"] else self.ensure_target_scope()
            if row_scope is None:
                continue
            if row_scope != subject_id and row_scope not in participants:
                participants.append(row_scope)
            failed = evidence_failed(self.root, row)
            if role is None:
                if failed:
                    role = "failed_attempt"
                elif row["kind"] == "derived":
                    role = "source" if row["query"].get("operation") == "source_correspondence" else "calculation"
                elif row["kind"] == "document":
                    role = "source" if "source" in str(row["query"].get("operation", "")) else "corroboration"
                elif row_scope == subject_id and row["pin_id"] == pin["id"] and row["query"].get("method") not in ("eth_chainId", "eth_getBlockByNumber", "eth_getBlockByHash"):
                    role = "direct"
                elif row["query"].get("method") == "eth_getCode":
                    role = "identity"
                else:
                    role = "corroboration"
            if role == "direct" and (failed or row["kind"] != "rpc" or row["pin_id"] != pin["id"] or row["query"].get("method") in ("eth_chainId", "eth_getBlockByNumber", "eth_getBlockByHash")):
                self.errors.append(field + ": " + row["id"] + " cannot be direct evidence (must be a successful RPC state/receipt read of the subject at the finding pin)")
            if role in ("source", "calculation") and failed and strength in ("proven_fact", "strongly_supported"):
                self.errors.append(field + ": " + row["id"] + " is a failed input; a resolved finding cannot rely on it")
            has_direct |= role == "direct" and row_scope == subject_id
            support.append({"evidence_id": row["id"], "role": role, "scope_id": row_scope})
            evidence_ids.append(row["id"])
        if strength in ("proven_fact", "strongly_supported") and not has_direct:
            self.errors.append(field + ": a resolved finding needs one successful RPC read of its subject at pin "
                               + str(pin["number"]) + " (for example the runtime, a getter, balance or receipt alias)")
        if not any(row["address"] == subject_addr and row["pin_id"] == pin["id"] for row, _ in evidence_rows):
            self.errors.append(field + ": cite at least one evidence row at the subject address and pin " + str(pin["number"])
                               + " (the validator requires evidence at the finding's exact scope/pin, even for gaps and inferences)")
        if item.get("discovery") is not None and item["discovery"] not in {x["id"] for x in self.d["discoveries"]} | {"intake"}:
            self.errors.append(field + ".discovery: unknown discovery id " + str(item["discovery"]))
        if impact == "adverse":
            concern = item.get("concern")
            if not isinstance(concern, dict):
                self.errors.append(field + ": adverse findings need concern {basis, mechanism, consequence}")
                concern = {}
            basis = _choice(concern.get("basis"), CONCERN_BASES, field + ".concern.basis", self.errors,
                            default="adverse_inference" if strength == "inference" else None)
            if (basis == "adverse_inference") != (strength == "inference"):
                self.errors.append(field + ": adverse_inference basis goes with inference strength, and only then")
            _text(concern.get("mechanism"), field + ".concern.mechanism", self.errors)
            _text(concern.get("consequence"), field + ".concern.consequence", self.errors)
            if not has_direct:
                self.errors.append(field + ": an adverse finding needs a direct observed lead at its subject")
        finding = {"id": fid, **self.target, "address": subject_addr, "pin_id": pin["id"],
                   "subject_scope_id": subject_id, "participant_scope_ids": participants,
                   "proposition": text or "", "evidence_ids": evidence_ids, "support": support,
                   "claim_type": claim, "impact": impact, "adverse_severity": severity,
                   "evidence_type": strength, "confidence": confidence,
                   "decoding_basis": item.get("basis") or CLAIM_BASIS[claim],
                   "alternatives": item.get("alternatives") or ("Alternative explanations were reviewed against the linked evidence and counterevidence" if claim != "coverage_gap" else "Fresh surface evidence could establish a benefit, concern or non-applicability"),
                   "coverage": item.get("coverage") or ("Bounded to the stated proposition, subject and pin" if claim != "coverage_gap" else "Named check unresolved within this investigation"),
                   "time_basis": item.get("time_basis") or ("Pinned " + pin["timestamp_utc"] + (" (historical pin)" if pin["id"] != self.pin["id"] else "")),
                   "stale_when": item.get("stale_when") or ("The named check is completed" if claim == "coverage_gap" else "Relevant code, authority, balances, liquidity or policy change after the pin"),
                   "discovery_claim": bool(item.get("discovery")), "discovery_ids": [item["discovery"]] if item.get("discovery") else []}
        if impact == "adverse":
            finding["concern"] = {"basis": basis, "mechanism": concern.get("mechanism", ""), "consequence": concern.get("consequence", ""),
                                  "requirement_ids": list(concern.get("requirements", []))}
        if item.get("execution") is not None or claim == "historical_execution":
            execution = copy.deepcopy(item.get("execution") or {})
            if not isinstance(execution, dict):
                self.errors.append(field + ".execution: must be an object {receipt_evidence_id, result, effects}")
                execution = {}
            if "status" in execution and "result" not in execution:
                execution["result"] = execution.pop("status")
            receipt_rows = [r for r, _ in evidence_rows if r["query"].get("method") == "eth_getTransactionReceipt" and not evidence_failed(self.root, r)]
            receipt_row = None
            if isinstance(execution.get("receipt_evidence_id"), str):
                receipt_row, _ = self.evidence(execution["receipt_evidence_id"], field + ".execution.receipt_evidence_id")
            elif len(receipt_rows) == 1:
                receipt_row = receipt_rows[0]
            elif claim == "historical_execution":
                self.errors.append(field + ".execution.receipt_evidence_id: name the receipt alias"
                                   + (" (candidates: " + ", ".join(r["id"] for r in receipt_rows) + ")" if receipt_rows else " and list it in the finding's evidence"))
            if receipt_row is not None:
                execution["receipt_evidence_id"] = receipt_row["id"]
                if receipt_row["id"] not in evidence_ids:
                    self.errors.append(field + ".execution: the receipt must also be listed in the finding's evidence")
            if claim == "historical_execution":
                receipt_status = self.receipt_status(receipt_row) if receipt_row is not None else None
                if execution.get("result") is None and receipt_status is not None:
                    execution["result"] = receipt_status
                if execution.get("result") not in ("success", "reverted"):
                    self.errors.append(field + ".execution.result: must be success or reverted, matching the receipt status")
                elif receipt_status is not None and execution["result"] != receipt_status:
                    self.errors.append(field + ".execution.result: " + execution["result"] + " contradicts the receipt status (" + receipt_status + ")")
                if not isinstance(execution.get("effects"), list):
                    if execution.get("result") == "reverted":
                        execution["effects"] = []
                    elif receipt_row is not None:
                        execution["effects"], skipped = self.derive_effects(receipt_row, subject_id, subject_addr, participants)
                        if not execution["effects"]:
                            self.errors.append(field + ".execution.effects: no Transfer log of the target token touching the subject could be attributed to declared scopes"
                                               + (" (parties without a scope: " + ", ".join(skipped) + "; declare them under note.scope after a code read)" if skipped else "") + EFFECT_SHAPE)
                        else:
                            self.warnings.append(field + ".execution.effects: derived " + str(len(execution["effects"])) + " target-token transfer(s) from the receipt"
                                                 + ("; parties without a scope were skipped: " + ", ".join(skipped) if skipped else ""))
            for effect in (execution.get("effects") or []) if isinstance(execution.get("effects"), list) else []:
                for key in ("asset_scope_id", "from_scope_id", "to_scope_id"):
                    sid_value = effect.get(key) if isinstance(effect, dict) else None
                    if sid_value is not None and sid_value not in {subject_id, *participants}:
                        if sid_value in self.scopes:
                            participants.append(sid_value)
                        else:
                            self.errors.append(field + ".execution: effect scope " + str(sid_value) + " must be an existing scope id (declare it under note.scope)")
            finding["participant_scope_ids"] = participants
            finding["execution"] = execution
        topic, signal = item.get("topic"), item.get("signal")
        if topic is not None and topic not in SUMMARY_TOPICS:
            self.errors.append(field + ".topic: must be one of " + ", ".join(SUMMARY_TOPICS))
        if signal is not None and signal not in SIGNALS:
            self.errors.append(field + ".signal: must be Good, Potential Risk, Bad or Unverified")
        if topic is not None and signal is None:
            self.errors.append(field + ": a summary topic needs a signal")
        if signal == "Good" and (impact not in ("benefit", "neutral") or strength not in ("proven_fact", "strongly_supported") or confidence not in ("high", "medium")):
            self.errors.append(field + ": Good needs benefit/neutral impact, proven or strongly supported strength and high/medium confidence")
        if signal == "Bad" and (impact != "adverse" or strength not in ("proven_fact", "strongly_supported") or confidence not in ("high", "medium") or SEVERITY_ORDER[severity] < 2):
            self.errors.append(field + ": Bad needs an adverse, proven/strongly supported, high/medium confidence finding of at least medium severity")
        if signal == "Unverified" and claim != "coverage_gap":
            self.errors.append(field + ": Unverified is only for coverage gaps; observed concerns use Potential Risk")
        if signal in ("Good", "Bad") and any(evidence_failed(self.root, r) for r, _ in evidence_rows):
            self.errors.append(field + ": Good/Bad findings cannot list failed evidence; move failed attempts to a coverage row or gap finding")
        self.index[fid] = {"dimensions": dimensions, "topic": topic, "signal": signal, "order": len(self.index) if fid not in self.index else self.index[fid]["order"]}
        return finding

    # ----- coverage and ratings -----------------------------------------------------
    def coverage(self, dimension, item, findings):
        from bundle_assemble import SURFACES
        field = "coverage." + dimension
        item = item or {}
        gaps = [f for f in findings if f["evidence_type"] == "unknown"]
        status = item.get("status")
        if status is None:
            status = "partial" if findings else None
            if findings and not gaps:
                self.warnings.append(field + ": status defaulted to partial; set status checked explicitly when the surface is complete")
        status = _choice(status, COVERAGE_STATUSES, field + ".status", self.errors)
        if status in ("partial", "unavailable", "not_checked") and not findings:
            self.errors.append(field + ": incomplete coverage still needs at least one finding for this dimension, typically a coverage_gap finding citing the attempts")
        gap_ids = ", ".join(f["id"] for f in gaps)
        if status == "checked" and gaps:
            if item.get("boundary") in ("exhausted", "unavailable", "not_yet_observable") or (not self.final and item.get("boundary") is None):
                # The weaker claim is always safe: keep the note's attempts/boundary, default attempts to the gaps themselves.
                self.warnings.append(field + ": downgraded from checked to partial because gap findings remain: " + gap_ids)
                status = "partial"
                item = {**item, "gap": item.get("gap") or "; ".join(f["proposition"][:120] for f in gaps),
                        "basis": item.get("basis") or (None if self.final else "Gap findings remain open; the coordinator's note closes this surface"),
                        "attempts": item.get("attempts") or [{"check": f["proposition"][:200], "outcome": "Unresolved in this run", "evidence": list(f["evidence_ids"])} for f in gaps]}
            else:
                self.errors.append(field + ": gap findings " + gap_ids + " remain, so this surface is partial, not checked. Either resolve/remove those gap "
                                   "findings, or set status partial with boundary exhausted|unavailable|not_yet_observable plus basis (attempts default to the gap findings)")
        elif status == "not_applicable" and gaps:
            self.errors.append(field + ": completed coverage cannot keep unresolved gap findings " + gap_ids)
        if status in ("checked", "not_applicable") and not findings:
            self.errors.append(field + ": " + status + " coverage needs at least one finding for this dimension"
                               + (" (a neutral finding stating the affirmative evidence, e.g. no reward contract among the getters)" if status == "not_applicable" else ""))
        if status == "not_checked" and findings and not all(f["evidence_type"] == "unknown" for f in findings):
            self.errors.append(field + ": not_checked cannot carry resolved findings; use partial")
        evidence_ids = list(dict.fromkeys(eid for f in findings for eid in f["evidence_ids"]))
        for spec in item.get("evidence") or []:
            row, _ = self.evidence(spec, field + ".evidence")
            if row and row["id"] not in evidence_ids:
                evidence_ids.append(row["id"])
        record = {"dimension": dimension, "surface": SURFACES[dimension], "status": status,
                  "outcome": _text(item.get("outcome"), field + ".outcome", self.errors, required=False)
                  or (findings[0]["proposition"][:240] if findings else "No observations for this surface"),
                  "gap": _text(item.get("gap"), field + ".gap", self.errors, required=status not in ("checked", "not_applicable"))
                  or ("None identified within the inspected scope and pin" if status == "checked" else "Not applicable within the inspected architecture" if status == "not_applicable" else ""),
                  "stop_reason": _text(item.get("stop_reason"), field + ".stop_reason", self.errors, required=False)
                  or ("Scoped checks completed" if status == "checked" else "Affirmative not-applicable evidence recorded" if status == "not_applicable" else "Relevant permitted routes reached the recorded boundary"),
                  "next_check": _text(item.get("next_check"), field + ".next_check", self.errors, required=False)
                  or ("Re-verify if code, authority, liquidity state or policy changes" if status in ("checked", "not_applicable") else ""),
                  "evidence_ids": evidence_ids, "discovery_ids": list(item.get("discoveries") or ["intake"]),
                  "finding_ids": [f["id"] for f in findings]}
        if status not in ("checked", "not_applicable"):
            attempts = []
            attempted = set()
            for n, attempt in enumerate(item.get("attempts") or []):
                afield = field + ".attempts[" + str(n) + "]"
                if not isinstance(attempt, dict):
                    self.errors.append(afield + ": must be {check, outcome, evidence}")
                    continue
                ids = []
                for spec in attempt.get("evidence") or []:
                    row = self.by_id.get(spec) if isinstance(spec, str) and spec in self.by_id else None
                    if row is None:
                        row, _ = self.evidence(spec, afield + ".evidence")
                    if row:
                        ids.append(row["id"])
                        if row["id"] not in evidence_ids:
                            evidence_ids.append(row["id"])
                attempts.append({"check": _text(attempt.get("check"), afield + ".check", self.errors) or "",
                                 "outcome": _text(attempt.get("outcome"), afield + ".outcome", self.errors) or "", "evidence_ids": ids})
                attempted.update(ids)
            boundary = item.get("boundary")
            if boundary is None:
                boundary = "pending" if status != "not_checked" else "out_of_scope"
            boundary = _choice(boundary, BOUNDARIES, field + ".boundary", self.errors)
            priority = _choice(item.get("priority"), PRIORITIES, field + ".priority", self.errors, default="material")
            if status == "not_checked" and attempts:
                self.errors.append(field + ": not_checked cannot claim attempts; use partial or unavailable")
            if status != "not_checked" and not attempts:
                self.errors.append(field + ": " + status + " coverage needs at least one attempt {check, outcome, evidence}")
            if self.final and boundary not in ("exhausted", "unavailable", "not_yet_observable"):
                self.errors.append(field + ": a completed report needs boundary exhausted, unavailable or not_yet_observable; "
                                   + boundary + " only fits an internal checkpoint (compose with --checkpoint) or more research")
            if boundary == "out_of_scope" and priority == "decision_critical":
                self.errors.append(field + ": a decision-critical gap cannot be out of scope")
            route_ids = []
            for spec in item.get("route_evidence") or []:
                row, _ = self.evidence(spec, field + ".route_evidence")
                if row:
                    route_ids.append(row["id"])
                    if row["id"] not in evidence_ids:
                        evidence_ids.append(row["id"])
            if not route_ids and boundary in ("exhausted", "unavailable", "not_yet_observable"):
                route_ids = sorted(attempted)
            if boundary == "exhausted" and not set(route_ids) <= attempted:
                self.errors.append(field + ": exhausted route evidence must come from the recorded attempts")
            if boundary in ("exhausted", "unavailable", "not_yet_observable") and not route_ids:
                self.errors.append(field + ": boundary " + boundary + " needs captured evidence (attempt evidence or route_evidence)")
            record["closure"] = {"priority": priority,
                                 "decision_impact": _text(item.get("decision_impact"), field + ".decision_impact", self.errors, required=False)
                                 or ("Unresolved " + SURFACES[dimension].lower() + " limits the related conclusions"),
                                 "attempts": attempts,
                                 "next_route": {"check": _text(item.get("route_check"), field + ".route_check", self.errors, required=False) or record["next_check"] or SURFACES[dimension],
                                                "disposition": boundary,
                                                "basis": _text(item.get("basis"), field + ".basis", self.errors, required=status != "not_checked") or "Named scope boundary; nothing was attempted for this surface",
                                                "evidence_ids": route_ids}}
            if not record["next_check"]:
                record["next_check"] = record["closure"]["next_route"]["check"]
            if not item.get("decision_impact"):
                self.warnings.append(field + ": decision_impact defaulted; state the specific consequence for the decision")
        rating = self.rating(dimension, status, findings, item.get("rating") or {}, record)
        return record, rating

    def rating(self, dimension, status, findings, override, record):
        field = "coverage." + dimension + ".rating"
        adverse = [f for f in findings if f["impact"] == "adverse"]
        resolved = all(f["evidence_type"] in ("proven_fact", "strongly_supported") and f["confidence"] in ("high", "medium") for f in findings)
        failed = any(evidence_failed(self.root, self.by_id[e]) for f in findings for e in f["evidence_ids"] if e in self.by_id and self.by_id[e]["kind"] == "rpc")
        coverage = {"checked": "complete", "partial": "partial", "unavailable": "unavailable", "not_checked": "unavailable", "not_applicable": "not_applicable"}[status]
        confidence = min((f["confidence"] for f in findings), key=lambda c: CONFIDENCE_ORDER[c], default="unknown")
        if adverse:
            status_value = "concern"
            severity = max((f["adverse_severity"] for f in adverse), key=lambda s: SEVERITY_ORDER[s])
            likelihood = "observed" if any(f["claim_type"] in ("state_observation", "historical_execution", "source_analysis") for f in adverse) else "possible"
            confidence = min((f["confidence"] for f in adverse), key=lambda c: CONFIDENCE_ORDER[c])
            confidence = confidence if confidence != "unknown" else "low"
            for f in adverse:
                if self.index.get(f["id"], {}).get("signal") == "Bad":
                    if status in ("unavailable", "not_checked"):
                        self.errors.append(field + ": a Bad finding needs partial or complete coverage of its dimension, not " + status)
                    if CONFIDENCE_ORDER[confidence] < 2:
                        self.errors.append(field + ": a Bad finding needs medium/high confidence across the dimension's adverse findings")
        elif status == "checked" and findings and resolved and not failed:
            status_value, severity, likelihood = "pass", "none", "unlikely"
        elif status == "not_applicable" and findings and resolved and not failed:
            status_value, severity, likelihood = "not_applicable", "none", "not_applicable"
        else:
            status_value, severity, likelihood, confidence = "unknown", "unknown", "unknown", "unknown"
            if status == "checked" and findings:
                self.warnings.append(field + ": checked coverage rates unknown, not pass, because a finding cites a failed/reverted read or is inference/low confidence")
        if override:
            if override.get("status") == "pass" and status_value != "pass":
                self.errors.append(field + ": pass requires checked coverage and only resolved high/medium findings without failed reads")
            elif override.get("status") in ("concern", "unknown", "not_applicable") and override.get("status") != status_value and not (override.get("status") == "unknown" and status_value == "pass"):
                self.errors.append(field + ": requested status " + str(override.get("status")) + " conflicts with the findings (" + status_value + ")")
            if override.get("status") == "unknown" and status_value == "pass":
                status_value, severity, likelihood, confidence = "unknown", "unknown", "unknown", "unknown"
            if status_value == "concern":
                if override.get("likelihood") in ("observed", "likely", "possible", "unlikely"):
                    likelihood = override["likelihood"]
                if override.get("severity") in ("critical", "high", "medium", "low"):
                    if SEVERITY_ORDER[override["severity"]] <= SEVERITY_ORDER[severity]:
                        severity = override["severity"]
                    else:
                        self.errors.append(field + ": rating severity cannot exceed the highest adverse finding severity (" + severity + ")")
        return {"id": dimension, "status": status_value, "severity": severity, "likelihood": likelihood,
                "confidence": confidence, "coverage": coverage, "time_basis": self.pin["timestamp_utc"],
                "finding_ids": [f["id"] for f in findings],
                "rationale": _text(override.get("rationale"), field + ".rationale", self.errors, required=False) or record["outcome"]}

    # ----- decision -----------------------------------------------------------------
    def decision(self, note_decision, findings_by_id, coverage_by_dim, summary):
        field = "decision"
        if not isinstance(note_decision, dict):
            self.errors.append(field + ": must be an object with verdict, synthesis and optional actions/requirements")
            return None
        reqs = []
        for n, req in enumerate(note_decision.get("requirements") or []):
            rfield = field + ".requirements[" + str(n) + "]"
            if not isinstance(req, dict) or not all(isinstance(req.get(k), str) and req[k].strip() for k in ("id", "text", "user_quote")):
                self.errors.append(rfield + ": needs id, text and the user's actual words in user_quote")
                continue
            reqs.append({"id": req["id"], "text": req["text"], "user_quote": req["user_quote"]})
        req_ids = {r["id"] for r in reqs}
        adverse = {fid for fid, f in findings_by_id.items() if f["impact"] == "adverse" and not pure_coverage_gap(f)}
        severe = {fid for fid in adverse if findings_by_id[fid]["adverse_severity"] in ("high", "critical")}
        affirmative = {fid for fid, f in findings_by_id.items() if f["impact"] in ("benefit", "neutral")
                       and f["evidence_type"] in ("proven_fact", "strongly_supported") and f["confidence"] in ("high", "medium")}
        verdict = note_decision.get("verdict") or {}
        if isinstance(verdict, str):
            verdict = {"kind": verdict}
        kind = _choice(verdict.get("kind"), tuple(VERDICT_KINDS), field + ".verdict.kind", self.errors)
        scope_text = _text(verdict.get("scope"), field + ".verdict.scope", self.errors, required=False) or ("General diligence on the exact target at the pinned block")
        selected = list(dict.fromkeys([*(verdict.get("findings") or [s["finding_id"] for s in summary]), *sorted(severe)]))
        unknown_ids = [x for x in selected if x not in findings_by_id]
        if unknown_ids:
            self.errors.append(field + ".verdict.findings: unknown finding ids " + ", ".join(unknown_ids))
            selected = [x for x in selected if x in findings_by_id]
        if severe and kind != "adverse_findings":
            self.errors.append(field + ".verdict.kind: high/critical adverse findings (" + ", ".join(sorted(severe)) + ") require kind adverse_findings")
        if kind == "findings_with_limits" and not set(selected) & affirmative:
            self.errors.append(field + ".verdict: findings_with_limits needs at least one resolved benefit/neutral finding in the summary or verdict.findings")
        if kind == "adverse_findings" and not set(selected) & adverse:
            self.errors.append(field + ".verdict: adverse_findings needs an assessed adverse finding")
        if kind == "requirement_unverified" and not any(pure_coverage_gap(findings_by_id[x]) for x in selected):
            self.errors.append(field + ".verdict: requirement_unverified needs a coverage-gap finding")
        verdict_req = list(verdict.get("requirements") or [])
        if kind == "requirement_unverified" and not verdict_req:
            self.errors.append(field + ".verdict.requirements: name the explicit user requirement")
        synthesis_in = note_decision.get("synthesis") or {}
        if isinstance(synthesis_in, list):
            synthesis_in = {x.get("axis"): x for x in synthesis_in if isinstance(x, dict)}
        synthesis = []
        for axis in ASSESSMENT_AXES:
            entry = synthesis_in.get(axis)
            conclusion = entry if isinstance(entry, str) else (entry or {}).get("conclusion")
            dims = (entry or {}).get("dimensions") if isinstance(entry, dict) else None
            dims = [d for d in (dims or AXIS_DIMENSIONS[axis]) if d in coverage_by_dim] or list(coverage_by_dim)
            fids = [fid for d in dims for fid in coverage_by_dim[d]["finding_ids"]]
            if isinstance(entry, dict) and entry.get("findings"):
                fids = [x for x in entry["findings"] if x in fids] or fids
            synthesis.append({"axis": axis, "conclusion": _text(conclusion, field + ".synthesis." + axis, self.errors) or "",
                              "finding_ids": list(dict.fromkeys(fids)), "coverage_dimensions": dims})
        actions, mitigated, action_ids = [], set(), set()
        incomplete = {dim for dim, c in coverage_by_dim.items() if c["status"] in ("partial", "not_checked", "unavailable")}
        for n, action in enumerate(note_decision.get("actions") or []):
            afield = field + ".actions[" + str(n) + "]"
            if not isinstance(action, dict):
                self.errors.append(afield + ": must be an object")
                continue
            akind = _choice(action.get("kind"), ACTION_KINDS, afield + ".kind", self.errors)
            if akind == "investigate" and self.final:
                self.errors.append(afield + ": a completed report cannot delegate research; run the check or record its boundary in coverage")
            requested = list(action.get("findings") or [])
            unknown_fids = [x for x in requested if x not in findings_by_id]
            if unknown_fids:
                self.errors.append(afield + ".findings: unknown finding ids " + ", ".join(map(str, unknown_fids)))
            fids = [x for x in requested if x in findings_by_id]
            dims = [d for d in action.get("dimensions") or [] if d in coverage_by_dim] or list(dict.fromkeys(d for fid in fids for d in self.index.get(fid, {}).get("dimensions", [])))
            if not fids or not dims:
                self.errors.append(afield + ": needs at least one existing finding and one coverage dimension")
            linked = {fid for d in dims for fid in coverage_by_dim[d]["finding_ids"]}
            if not set(fids) <= linked:
                self.errors.append(afield + ": findings must belong to the named coverage dimensions")
            action_id = action.get("id") or ("action-" + str(n + 1))
            if action_id in action_ids:
                self.errors.append(afield + ": duplicate action id " + str(action_id))
            action_ids.add(action_id)
            if akind == "mitigate":
                if not set(fids) & adverse:
                    self.errors.append(afield + ": mitigation needs an assessed adverse finding")
                mitigated.update(set(fids) & adverse)
            elif akind == "use_within_scope":
                if not set(fids) & affirmative:
                    self.errors.append(afield + ": use_within_scope needs an affirmative resolved finding")
                if set(dims) & incomplete:
                    self.errors.append(afield + ": use_within_scope needs completed coverage for every named dimension")
                if any(self.ratings_for(coverage_by_dim, d) not in ("pass", "not_applicable") for d in dims) or (linked & adverse):
                    self.errors.append(afield + ": use_within_scope cannot cover a dimension with a concern or unknown rating")
            else:
                if not set(dims) & incomplete:
                    self.errors.append(afield + ": investigate/requirement_gate needs an incomplete coverage dimension")
                if not any(pure_coverage_gap(findings_by_id[fid]) for fid in fids):
                    self.errors.append(afield + ": investigate/requirement_gate needs an explicit coverage_gap finding")
            action_reqs = list(action.get("requirements") or [])
            if akind == "requirement_gate" and not action_reqs:
                self.errors.append(afield + ": requirement_gate needs the explicit requirement id")
            if not set(action_reqs) <= req_ids:
                self.errors.append(afield + ": unknown requirement ids")
            def sentence(value):
                return value if not value or value.rstrip()[-1:] in ".!?" else value.rstrip() + "."
            actions.append({"id": action_id, "kind": akind,
                            "action": sentence(_text(action.get("action"), afield + ".action", self.errors) or ""),
                            "reason": sentence(_text(action.get("reason"), afield + ".reason", self.errors) or ""),
                            "finding_ids": fids, "coverage_dimensions": dims, "requirement_ids": action_reqs,
                            "changes_view_if": sentence(_text(action.get("changes_view_if"), afield + ".changes_view_if", self.errors) or "")})
        if len(actions) > 3:
            self.errors.append(field + ".actions: at most three actions")
        if severe - mitigated:
            self.errors.append(field + ".actions: high/critical findings need a mitigate action: " + ", ".join(sorted(severe - mitigated)))
        return {"requirements": reqs, "verdict": {"kind": kind, "scope": scope_text, "finding_ids": selected, "requirement_ids": verdict_req},
                "synthesis": synthesis, "actions": actions}

    def ratings_for(self, coverage_by_dim, dimension):
        for rating in self.d.get("ratings", []):
            if rating["id"] == dimension:
                return rating["status"]
        return "unknown"

    # ----- orchestration -------------------------------------------------------------
    def apply(self, note):
        need(isinstance(note, dict) and note.get("note_schema_version", NOTE_SCHEMA) == NOTE_SCHEMA, "unsupported note schema")
        unknown = set(note) - {"note_schema_version", "lane", "requests_used", "scope", "findings", "coverage", "decision", "text", "discoveries", "leads_for_coordinator", "signals"}
        if unknown:
            self.errors.append("unknown note fields: " + ", ".join(sorted(unknown)))
        # An explicit --lane on the command line wins, so the coordinator can compose a lane note it wrote itself.
        self.lane = self.lane or note.get("lane")
        if note.get("leads_for_coordinator") is not None:
            self.d.setdefault("lane_leads", {})[note.get("lane") or self.lane or "coordinator"] = copy.deepcopy(note["leads_for_coordinator"])
        self.ensure_target_scope()
        self.apply_note_scope(note.get("scope"))
        for n, disc in enumerate(note.get("discoveries") or []):
            if isinstance(disc, dict) and disc.get("id"):
                for spec in list(disc.get("evidence", [])):
                    row, _ = self.evidence(spec, "discoveries[" + str(n) + "].evidence")
                    if row:
                        disc.setdefault("evidence_ids", []).append(row["id"])
                disc.pop("evidence", None)
                disc.setdefault("chain_id", self.target["chain_id"])
                disc.setdefault("block_ranges", [[self.pin["number"], self.pin["number"]]])
                self.d["discoveries"] = [x for x in self.d["discoveries"] if x["id"] != disc["id"]] + [disc]
        new_findings = [f for f in (self.finding(item, n) for n, item in enumerate(note.get("findings") or [])) if f]
        findings_by_id = {f["id"]: f for f in self.d["findings"]}
        for f in new_findings:
            findings_by_id[f["id"]] = f
        self.apply_signals(note.get("signals"), findings_by_id)
        coverage_notes = note.get("coverage") or {}
        if not isinstance(coverage_notes, dict):
            self.errors.append("coverage: must map dimension -> {status, ...}")
            coverage_notes = {}
        for d in coverage_notes:
            if d not in DIMENSIONS:
                self.errors.append("coverage: unknown dimension " + str(d))
        touched = set(coverage_notes) & set(DIMENSIONS)
        touched.update(dim for f in new_findings for dim in self.index[f["id"]]["dimensions"])
        # Dimensions already carrying note-indexed findings must be rebuilt when their findings change.
        existing_coverage = {c["dimension"]: c for c in self.d["coverage_records"]}
        existing_ratings = {r["id"]: r for r in self.d["ratings"]}
        for dimension in touched:
            dim_findings = [findings_by_id[fid] for fid, meta in self.index.items() if dimension in meta["dimensions"] and fid in findings_by_id]
            dim_findings.sort(key=lambda f: self.index[f["id"]]["order"])
            item = coverage_notes.get(dimension)
            if item is None and dim_findings:
                # A lane reported observations without declaring the surface complete. Record them as
                # attempts on a partial surface with a pending route; the coordinator's final note must
                # close it (checked, not_applicable or an external boundary).
                item = {"status": "partial", "gap": "Coverage status not yet declared for this surface",
                        "priority": "material", "decision_impact": "Undeclared completion for " + dimension.replace("_", " "),
                        "attempts": [{"check": f["proposition"][:200], "outcome": "Recorded observation", "evidence": list(f["evidence_ids"])} for f in dim_findings],
                        "boundary": "pending", "basis": "Awaiting the coordinator's coverage decision"}
                if self.final:
                    self.errors.append("coverage." + dimension + ": findings exist but no coverage status was declared; add coverage."
                                       + dimension + " with status checked, not_applicable, or partial/unavailable plus an external boundary")
                else:
                    self.warnings.append("coverage." + dimension + ": status defaulted to partial/pending; the coordinator must close this surface")
            record, rating = self.coverage(dimension, item, dim_findings)
            existing_coverage[dimension] = record
            existing_ratings[dimension] = rating
        if self.final:
            # The final note must leave every surface deliverable; report all leftovers here rather than at freeze.
            for dimension, record in existing_coverage.items():
                if dimension in touched:
                    continue
                if record["status"] == "not_checked":
                    self.errors.append("coverage." + dimension + ": surface untouched; a completed report needs every surface checked, not_applicable, or bounded with attempts")
                disposition = (record.get("closure") or {}).get("next_route", {}).get("disposition")
                if disposition in ("pending", "budget_exhausted", "out_of_scope"):
                    self.errors.append("coverage." + dimension + ": earlier note left boundary " + disposition + "; the final note must close this surface")
        else:
            # Checkpoint mode: untouched intake surfaces get an explicit not-checked review so the save validates.
            for dimension, record in existing_coverage.items():
                if dimension not in touched and record["status"] == "not_checked" and "closure" not in record:
                    record["stop_reason"] = "Not yet investigated in this run"
                    record["closure"] = {"priority": "material", "decision_impact": "Unresolved " + record["surface"].lower() + " limits the related conclusions",
                                         "attempts": [], "next_route": {"check": record["next_check"], "disposition": "pending",
                                                                        "basis": "No attempt recorded yet; the surface remains open work", "evidence_ids": []}}
        summary = []
        for fid, meta in sorted(self.index.items(), key=lambda kv: kv[1]["order"]):
            if fid in findings_by_id and meta.get("topic"):
                applicable = [d for d in meta["dimensions"] if existing_ratings.get(d, {}).get("status") != "not_applicable"]
                if not applicable:
                    self.errors.append("finding " + fid + ": a finding whose only surface is not_applicable cannot be a summary row; "
                                       "drop its topic/signal or attach it to an applicable dimension")
                    continue
                summary.append({"finding_id": fid, "topic": meta["topic"], "signal": meta["signal"]})
        for fid, f in findings_by_id.items():
            if f["impact"] == "adverse" and f["adverse_severity"] in ("high", "critical") and fid not in {s["finding_id"] for s in summary}:
                dims = self.index.get(fid, {}).get("dimensions") or ["token_controls"]
                summary.append({"finding_id": fid, "topic": DEFAULT_TOPIC[dims[0]], "signal": "Potential Risk"})
                self.warnings.append("finding " + fid + ": high/critical adverse finding added to the summary as Potential Risk; set topic/signal explicitly if Bad is warranted")
        if not summary and self.final and (self.d.get("note_decision") is not None or "decision" in note):
            self.errors.append("summary: no finding carries a topic/signal; give at least one finding a summary topic (Unverified rows are fine for all-gap packets)")
        if "decision" in note:
            self.d["note_decision"] = copy.deepcopy(note["decision"])
        if "text" in note:
            text = note["text"] or {}
            if not isinstance(text, dict) or set(text) - {"verdict", "conditions", "main_reasons", "strongest_contrary_evidence", "unresolved_questions", "change_evidence"}:
                self.errors.append("text: allowed fields are verdict, conditions, main_reasons, strongest_contrary_evidence, unresolved_questions, change_evidence")
            else:
                for key, value in text.items():
                    if _text(value, "text." + key, self.errors) is not None:
                        self.d["report_text"][key] = value.strip()
        if self.final and self.d.get("note_decision") is None and "decision" not in note and note.get("lane") in (None, "coordinator"):
            self.warnings.append("no decision recorded yet; the coordinator note must supply decision.verdict and decision.synthesis before finalize")
        decision = None
        if self.d.get("note_decision") is not None:
            previous_ratings = self.d.get("ratings", [])
            self.d["ratings"] = [existing_ratings[dim] for dim in DIMENSIONS if dim in existing_ratings]
            decision = self.decision(self.d["note_decision"], findings_by_id, existing_coverage, summary)
            self.d["ratings"] = previous_ratings
        if self.final:
            for key in ("verdict", "main_reasons", "strongest_contrary_evidence", "unresolved_questions", "change_evidence"):
                if key not in self.d["report_text"] and decision is not None:
                    self.errors.append("text." + key + ": required for a completed report (write it in the coordinator note)")
        if "conditions" not in self.d["report_text"]:
            self.d["report_text"]["conditions"] = ("Exact token " + self.target["address"] + " on RPC-verified chain " + str(self.target["chain_id"])
                                                    + ". Snapshot block " + str(self.pin["number"]) + ", hash " + self.pin["hash"] + ", UTC " + self.pin["timestamp_utc"] + ".")
        if self.errors:
            raise NoteError(self.errors, self.warnings)
        self.commit_captures()
        self.d["findings"] = list(findings_by_id.values())
        self.d["coverage_records"] = [existing_coverage[dim] for dim in DIMENSIONS]
        self.d["ratings"] = [existing_ratings[dim] for dim in DIMENSIONS if dim in existing_ratings]
        self.d["summary"] = summary
        if decision is not None:
            self.d["decision_review"] = decision
        remaining = [c["dimension"] for c in self.d["coverage_records"] if c["status"] == "not_checked"]
        if remaining and self.final:
            self.warnings.append("surfaces still not_checked (a final freeze will reject them): " + ", ".join(remaining))
        return {"status": "composed", "findings": [f["id"] for f in new_findings], "dimensions": sorted(touched),
                "summary_rows": len(summary), "registered_captures": self.registered, "remaining_surfaces": remaining,
                "warnings": self.warnings}


def compose(root, note_path, lane=None, final=True, check=False):
    """Expand a note into the draft; with check=True validate only and write nothing."""
    from bundle_assemble import read_draft, save_draft
    root = Path(root)
    draft = read_draft(root)
    note = read_json(Path(note_path))
    lane_name = lane or (note.get("lane") if isinstance(note, dict) else None)
    if lane_name not in (None, "coordinator"):
        final = False  # lane notes contribute observations; only the coordinator note closes the report
    composer = Composer(root, draft, lane=lane, final=final)
    composer.dry_run = check
    try:
        result = composer.apply(note)
    except NoteError as exc:
        return {"status": "errors", "errors": exc.errors, "warnings": exc.warnings, "final_delivery_eligible": False, **({"mode": "check"} if check else {})}
    if check:
        result.update(errors=[], final_delivery_eligible=False, mode="check", note="valid; nothing written (run without --check to apply)")
        return result
    data = Path(note_path).read_bytes()
    notes = root / "notes-applied"
    notes.mkdir(exist_ok=True)
    destination = notes / (sha(data) + ".json")
    if not destination.exists():
        with destination.open("xb") as stream:
            stream.write(data)
    save_draft(root, draft)
    result["errors"] = []
    result["final_delivery_eligible"] = False
    result["leads_for_coordinator"] = draft.get("lane_leads", {})
    return result
