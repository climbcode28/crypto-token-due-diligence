"""Frozen installed schema-1 reader, engine 1.0.0; stdlib only.

Origin: fc60201, solana_common.py, deterministic collector functions and bundle
functions. See baseline.json for exact source hashes. Function bodies are retained
verbatim. This reader does not repair or execute historical engine snapshots.
Do not change schema-1 semantics when evolving the v2 implementation.
"""
from datetime import datetime
import re
import time
import base64
import hashlib
import json
from pathlib import Path
import struct

ENGINE_VERSION = "1.0.0"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def b58encode(raw):
    number, out = int.from_bytes(raw, "big"), ""
    while number:
        number, remainder = divmod(number, 58)
        out = ALPHABET[remainder] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + out


def pubkey(value):
    need(isinstance(value, str) and 32 <= len(value) <= 44, "invalid public key")
    number = 0
    for char in value:
        need(char in ALPHABET, "invalid base58")
        number = number * 58 + ALPHABET.index(char)
    raw = b"\0" * (len(value) - len(value.lstrip("1")))
    raw += number.to_bytes((number.bit_length() + 7) // 8, "big")
    need(len(raw) == 32 and b58encode(raw) == value, "public key must encode 32 bytes")
    return value  # Case sensitive: never normalize Solana public keys.


def natural(value):
    need(type(value) is int and 0 <= value < 2**64, "invalid unsigned integer")
    return value


def target_identity(target):
    need(target.get("family") == "solana", "not a Solana target")
    return {"family": "solana", "genesis_hash": pubkey(target["genesis_hash"]),
            "mint": pubkey(target["mint"])}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(obj, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def optional_key(raw):
    need(len(raw) == 32, "invalid optional key")
    return b58encode(raw) if any(raw) else None


def coption_key(raw):
    need(len(raw) == 36, "invalid COption")
    tag = int.from_bytes(raw[:4], "little")
    need(tag in (0, 1), "invalid COption discriminator")
    # A present all-zero key is still Some(pubkey), not revoked authority.
    return b58encode(raw[4:]) if tag else None


def extension(kind, raw):
    """Decode a deliberately bounded set; preserve everything else as unknown."""
    supported = {1: ("transfer_fee_config", 108), 3: ("mint_close_authority", 32),
                 6: ("default_account_state", 1), 9: ("non_transferable", 0),
                 12: ("permanent_delegate", 32), 14: ("transfer_hook", 64),
                 26: ("pausable", 33)}
    row = {"type": kind, "length": len(raw), "sha256": sha(raw), "decoded": False}
    if kind not in supported:
        return row
    name, size = supported[kind]
    need(len(raw) == size, "invalid extension length")
    row.update(name=name, decoded=True)
    if kind in (3, 12):
        row["authority"] = optional_key(raw)
    elif kind == 14:
        row.update(authority=optional_key(raw[:32]), program=optional_key(raw[32:]))
    elif kind == 6:
        need(raw[0] in (1, 2), "invalid initialized default account state")
        row["state"] = "frozen" if raw[0] == 2 else "initialized"
    elif kind == 26:
        need(raw[32] in (0, 1), "invalid pause flag")
        row.update(authority=optional_key(raw[:32]), paused=bool(raw[32]))
    elif kind == 1:
        row.update(config_authority=optional_key(raw[:32]),
                   withdraw_authority=optional_key(raw[32:64]),
                   withheld_atomic=str(int.from_bytes(raw[64:72], "little")))
        for label, start in (("older", 72), ("newer", 90)):
            epoch, cap, bps = struct.unpack("<QQH", raw[start:start+18])
            need(bps <= 10000, "invalid fee basis points")
            row[label] = {"epoch": epoch, "maximum_fee_atomic": str(cap), "basis_points": bps}
        # Selecting an active fee requires epoch evidence; don't invent it here.
    return row


def decode_mint(account):
    need(isinstance(account, dict) and account.get("executable") is False, "not a data account")
    owner = account.get("owner")
    need(owner in (TOKEN_PROGRAM, TOKEN_2022), "unsupported mint owner program")
    data = account.get("data")
    need(isinstance(data, list) and len(data) == 2 and data[1] == "base64", "raw base64 required")
    raw = base64.b64decode(data[0], validate=True)
    need(len(raw) >= 82 and len(raw) != 355, "invalid mint length")
    need(raw[45] == 1, "mint not initialized")
    if "space" in account:
        need(type(account["space"]) is int and account["space"] == len(raw), "space mismatch")
    row = {"program": owner, "data_sha256": sha(raw),
           "mint_authority": coption_key(raw[:36]),
           "supply_atomic": str(int.from_bytes(raw[36:44], "little")),
           "decimals": raw[44], "freeze_authority": coption_key(raw[46:82]),
           "extensions": []}
    if owner == TOKEN_PROGRAM:
        need(len(raw) == 82, "legacy mint has unexpected data")
    elif len(raw) != 82:
        need(len(raw) >= 166 and not any(raw[82:165]) and raw[165] == 1,
             "invalid extended mint padding or account type")
        offset, seen = 166, set()
        while offset < len(raw):
            if not any(raw[offset:]):
                break  # Zero padding, including the multisig-length avoidance padding.
            need(len(raw) - offset >= 4, "truncated TLV")
            kind, size = struct.unpack("<HH", raw[offset:offset+4])
            need(kind != 0 and kind not in seen, "duplicate or invalid extension")
            need(kind not in {2, 5, 7, 8, 11, 13, 15, 17, 27}, "account extension on mint")
            seen.add(kind)
            offset += 4
            need(offset + size <= len(raw), "truncated extension")
            row["extensions"].append(extension(kind, raw[offset:offset+size]))
            offset += size
    row["unknown_extensions"] = [x["type"] for x in row["extensions"] if not x["decoded"]]
    return row


def account_params(mint, floor=None):
    config = {"encoding": "base64", "commitment": "finalized"}
    if floor is not None:
        config["minContextSlot"] = floor
    return [mint, config]

def block_params(slot):
    return [slot, {"commitment": "finalized", "transactionDetails": "none", "rewards": False}]

def slot_of(value):
    return natural(value["context"]["slot"])

def block(value, slot):
    need(isinstance(value, dict), "block missing")
    result = {"slot": natural(slot), "blockhash": pubkey(value["blockhash"]),
              "previous_blockhash": pubkey(value["previousBlockhash"]),
              "parent_slot": natural(value["parentSlot"]), "block_time": natural(value["blockTime"])}
    need(result["parent_slot"] < slot or slot == 0, "invalid parent slot")
    return result

def summarize(root, target, largest=False, now=None):
    """Reproduce observations from request-bound evidence; never trust a scanner verdict."""
    root, target = Path(root), target_identity(target)
    records = {p.stem: json.loads(p.read_text()) for p in (root / "evidence").glob("*.json")}
    observations, gaps = [], []

    def result(eid, method, params):
        record = records.get(eid, {})
        req = {"jsonrpc": "2.0", "id": eid, "method": method, "params": params}
        response = record.get("response", {})
        if record.get("request") == req and record.get("status") == "ok" and \
                isinstance(response, dict) and response.get("jsonrpc") == "2.0" and \
                response.get("id") == eid and "result" in response and "error" not in response:
            return response["result"]
        return None

    def observe(text, *eids):
        observations.append({"text": text, "evidence": ["evidence/" + e + ".json" for e in eids]})

    identity, consistent, fresh, decoded = "unresolved", False, False, None
    samples, changed = [], False
    try:
        genesis = result("genesis", "getGenesisHash", [])
        if genesis is not None:
            identity = "network_matched" if pubkey(genesis) == target["genesis_hash"] else "network_mismatch"
        need(identity == "network_matched", "network identity unresolved or mismatched")
        need(result("genesis_recheck", "getGenesisHash", []) == target["genesis_hash"], "network recheck missing")
        first = result("mint", "getAccountInfo", account_params(target["mint"]))
        first_slot = slot_of(first)
        last = result("mint_recheck", "getAccountInfo", account_params(target["mint"], first_slot))
        last_slot = slot_of(last)
        need(last_slot >= first_slot, "context slot moved backwards")
        for eid, slot in (("block", first_slot), ("end_block", last_slot)):
            header = block(result(eid, "getBlock", block_params(slot)), slot)
            need(header == block(result(eid + "_recheck", "getBlock", block_params(slot)), slot), "block changed or unavailable")
            samples.append(header)
        first_mint, last_mint = decode_mint(first["value"]), decode_mint(last["value"])
        changed = first_mint != last_mint
        need(not changed, "mint data or owning program changed between samples")
        consistent = True
        now = time.time() if now is None else now
        fresh = all(-60 <= now - x["block_time"] <= 300 for x in samples)
        need(fresh, "sample blocks are stale or future-dated")
        decoded = last_mint
        observe("Mint bytes and owning program agree at the two sampled finalized contexts; this is not an atomic historical-state pin.",
                "genesis", "genesis_recheck", "mint", "mint_recheck", "block", "block_recheck", "end_block", "end_block_recheck")
        for role in ("mint_authority", "freeze_authority"):
            observe(role + ": " + (decoded[role] if decoded[role] is not None else "absent in sampled mint")
                    + ". Other authorities and holder-account state still require review.", "mint_recheck")
        observe("Supply " + decoded["supply_atomic"] + " atomic units; decimals " + str(decoded["decimals"])
                + ". This is not circulating supply or a market-cap denominator.", "mint_recheck")
        for ext in decoded["extensions"]:
            observe("Token-2022 extension: " + json.dumps(ext, sort_keys=True)
                    + ". Presence is a control/behavior observation, not proof of fraud.", "mint_recheck")
        if decoded["unknown_extensions"]:
            gaps.append("Unsupported extensions remain unresolved; do not conclude complete authority or transfer coverage.")
    except (ValueError, KeyError, TypeError, IndexError):
        gaps.append("Mint/network/time consistency not established; use raw evidence to resolve the gap.")
    if largest and "largest" in records:
        gaps.append("Largest-account response is a separate context: top 20 token accounts are not top 20 beneficial holders; ownership and denominators need reconciliation.")
    gaps += ["Ordinary-holder sale execution, fees and restrictions not established by this collector.",
             "Pool identity, exit depth, LP principal custody and withdrawal paths require protocol-specific evidence.",
             "Program upgrades, authority controllers, launch behavior and beneficial ownership not fully resolved."]
    return {"target": target, "identity": identity, "samples": samples,
            "sample_consistent": consistent, "sample_fresh": fresh, "mint_changed": changed,
            "mint": decoded, "verdict": "insufficient_evidence", "observations": observations,
            "critical_unknowns": gaps, "coverage": {"identity_and_mint": "partial" if decoded else "unknown",
                "transfer_and_exit": "unknown", "privileged_controls": "partial" if decoded else "unknown",
                "liquidity_and_custody": "unknown"}}

DIMENSIONS = ("token_controls", "canonical_lp_principal_custody", "side_pool_removal_risk",
    "sellability_exit_depth", "current_concentration", "historical_launch_integrity",
    "admin_treasury_reward_custody", "reward_accounting_liveness", "utility_redemption_rights",
    "external_dependencies", "development_disclosure")

SAFETY = {"no_real_keys": True, "no_real_signing": True, "no_broadcast": True}

def artifact(root, name, digest):
    need(isinstance(name, str) and name and not Path(name).is_absolute(), "relative artifact path required")
    root = Path(root).resolve()
    path = (root / name).resolve()
    need(path.is_relative_to(root) and path.is_file(), "artifact must remain inside bundle")
    raw = path.read_bytes()
    need(isinstance(digest, str) and sha(raw) == digest, "artifact hash mismatch")
    return raw

def collection(root, name="summary.json", allow_synthetic=False):
    root = Path(root)
    summary = json.loads((root / name).read_text())
    need(type(summary["synthetic"]) is bool and (allow_synthetic or not summary["synthetic"]), "synthetic collection requires explicit flag")
    need(summary["schema_version"] == 1 and summary["engine_version"] == ENGINE_VERSION, "unsupported collection version")
    paths = summary["artifact_sha256"]
    actual = {str(p.relative_to(root)) for folder in ("attempts", "evidence", "engine")
              for p in (root / folder).glob("*") if p.suffix != ".tmp"}
    need(set(paths) == actual, "collection inventory mismatch")
    for path, digest in paths.items():
        artifact(root, path, digest)
    need(type(summary["include_largest"]) is bool, "invalid collection options")
    captured = datetime.fromisoformat(summary["captured_at_utc"])
    need(captured.tzinfo is not None, "capture time needs timezone")
    replay = summarize(root, summary["target"], summary["include_largest"], captured.timestamp())
    need(all(summary.get(k) == v for k, v in replay.items()), "summary does not reproduce from evidence")
    need(summary["attempt_upper_bound"] == len(list((root / "attempts").glob("*.json"))), "attempt count mismatch")
    need(9 <= summary["request_limit"] <= 24 and summary["attempt_upper_bound"] <= summary["request_limit"], "request limit exceeded")
    return summary

def initialize(root, target=None, use_collection=False, allow_synthetic=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    need(not (root / "manifest.json").exists() and not (root / "report.json").exists(), "bundle already initialized")
    summary = collection(root, allow_synthetic=allow_synthetic) if use_collection else None
    target = target_identity(summary["target"] if summary else target)
    evidence = []
    if summary:
        for path, digest in summary["artifact_sha256"].items():
            if path.startswith("evidence/"):
                evidence.append({"id": Path(path).stem, "artifact": path, "sha256": digest,
                    "kind": "collector", "source": "request and response in artifact",
                    "subject": target, "time_basis": "See response context slot and collection samples; no exact-state pin."})
    manifest = {"schema_version": 1, "engine_version": ENGINE_VERSION, "target": target,
        "synthetic": summary["synthetic"] if summary else False, "safety": SAFETY,
        "collection_sha256": sha((root / "summary.json").read_bytes()) if summary else None,
        "identity_evidence": [], "evidence": evidence,
        "limitations": ["Initial packet only; all broad dimensions need research and reconciliation."]}
    report = {"schema_version": 1, "target": target, "synthetic": manifest["synthetic"],
        "safety": SAFETY, "status": "partial", "question": "Broad token diligence",
        "verdict": "Insufficient evidence; initialized packet is not completed diligence.",
        "strongest_contrary_evidence": "Not yet investigated.", "change_evidence": "Resolve the listed coverage gaps.",
        "unresolved_questions": ["All broad dimensions require review."], "findings": [],
        "ratings": [{"dimension": name, "status": "unknown", "coverage": "unknown",
            "severity": "unknown", "likelihood": "unknown", "confidence": "low",
            "time_basis": "unresolved", "basis": "Not yet investigated.", "evidence_ids": []} for name in DIMENSIONS]}
    write_new(root / "manifest.json", manifest)
    report["manifest_sha256"] = sha((root / "manifest.json").read_bytes())
    write_new(root / "report.json", report)

def validate(root, allow_synthetic=False):
    root = Path(root)
    raw = (root / "manifest.json").read_bytes()
    manifest, report = json.loads(raw), json.loads((root / "report.json").read_text())
    target = target_identity(manifest["target"])
    need(report["target"] == target and report["manifest_sha256"] == sha(raw), "report identity or manifest binding mismatch")
    need(manifest["schema_version"] == report["schema_version"] == 1 and manifest["engine_version"] == ENGINE_VERSION, "unsupported bundle version")
    need(type(manifest["synthetic"]) is bool and manifest["synthetic"] == report["synthetic"] and
         (allow_synthetic or not manifest["synthetic"]), "synthetic bundle requires explicit flag")
    need(manifest["safety"] == report["safety"] == SAFETY and
         all(manifest["safety"][k] is True and report["safety"][k] is True for k in SAFETY), "invalid safety declaration")
    summary = None
    if manifest["collection_sha256"] is not None:
        artifact(root, "summary.json", manifest["collection_sha256"])
        summary = collection(root, allow_synthetic=allow_synthetic)
        need(summary["target"] == target and summary["synthetic"] == manifest["synthetic"], "collection identity mismatch")
    rows, identity_genesis, identity_mint = {}, False, False
    state_rows = []
    for row in manifest["evidence"]:
        eid = row["id"]
        need(isinstance(eid, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", eid) and eid not in rows, "invalid or duplicate evidence ID")
        need(row["kind"] in ("collector", "rpc", "document", "derived", "simulation"), "invalid evidence kind")
        need(isinstance(row["source"], str) and row["source"].strip() and
             isinstance(row["time_basis"], str) and row["time_basis"].strip(), "evidence provenance and time required")
        subject = row["subject"]
        need(subject.get("family") == "solana", "separate external-chain packet required")
        pubkey(subject["genesis_hash"])
        pubkey(subject.get("address", subject.get("mint")))
        content = artifact(root, row["artifact"], row["sha256"])
        if row["kind"] == "collector":
            need(summary is not None and summary["artifact_sha256"].get(row["artifact"]) == row["sha256"]
                 and row["artifact"].startswith("evidence/") and subject == target, "collector row not bound")
        if row["kind"] == "simulation":
            need(row.get("counterfactual") is True and row.get("disposable_local_validator") is True
                 and row.get("synthetic_accounts_only") is True, "simulation isolation declarations required")
        if row["kind"] == "rpc" or eid in manifest["identity_evidence"]:
            packet = json.loads(content)
            req, resp = packet["request"], packet["response"]
            need(req.get("jsonrpc") == resp.get("jsonrpc") == "2.0" and req["id"] == resp["id"]
                 and (("result" in resp) != ("error" in resp)), "invalid RPC envelope")
            need(req["method"] in {"getGenesisHash", "getAccountInfo", "getMultipleAccounts", "getBlock",
                "getBlockTime", "getEpochInfo", "getTokenLargestAccounts", "getTokenSupply",
                "getSignaturesForAddress", "getTransaction", "getProgramAccounts"}, "unsupported read method")
            if row["kind"] == "rpc" and "result" in resp and resp["result"] is not None and req["method"] in {
                    "getAccountInfo", "getMultipleAccounts", "getTokenLargestAccounts", "getTokenSupply"}:
                value = resp["result"]
                natural(value["context"]["slot"])
                need(len(req["params"]) == 2 and req["params"][1].get("commitment") == "finalized",
                     "state RPC needs explicit finalized commitment")
                subject_key = subject.get("address", subject.get("mint"))
                queried = req["params"][0]
                need(subject_key in queried if isinstance(queried, list) else subject_key == queried,
                     "state RPC subject mismatch")
                state_rows.append((row, value["context"]["slot"]))
            if eid in manifest["identity_evidence"]:
                need(subject == target and packet.get("status", "ok") == "ok", "identity evidence unavailable or wrong subject")
                if req["method"] == "getGenesisHash" and req["params"] == []:
                    identity_genesis |= resp.get("result") == target["genesis_hash"]
                if req["method"] == "getAccountInfo":
                    need(req["params"][0] == target["mint"] and req["params"][1]["commitment"] == "finalized"
                         and req["params"][1]["encoding"] == "base64", "identity mint query mismatch")
                    natural(resp["result"]["context"]["slot"])
                    decode_mint(resp["result"]["value"])
                    identity_mint = True
        rows[eid] = row
    need(isinstance(manifest["identity_evidence"], list) and set(manifest["identity_evidence"]) <= rows.keys(), "identity evidence references missing")
    for row, slot in state_rows:
        state = row["state"]
        need(state["slot"] == slot and state["commitment"] == "finalized", "state context mismatch")
        headers, header_artifacts, header_requests = [], [], []
        for key in ("block_evidence_id", "block_recheck_evidence_id"):
            header_row = rows[state[key]]
            need(header_row["kind"] == "rpc" and header_row["subject"]["genesis_hash"] == row["subject"]["genesis_hash"],
                 "header belongs to another network or evidence kind")
            packet = json.loads(artifact(root, header_row["artifact"], header_row["sha256"]))
            req = packet["request"]
            need(packet.get("status", "ok") == "ok", "header evidence unavailable")
            need(req["method"] == "getBlock" and req["params"] == block_params(slot), "wrong header slot or config")
            headers.append(block(packet["response"]["result"], slot))
            header_artifacts.append(header_row["artifact"])
            header_requests.append(req["id"])
        need(state["block_evidence_id"] != state["block_recheck_evidence_id"] and headers[0] == headers[1],
             "state headers not independently rechecked or differ")
        need(header_artifacts[0] != header_artifacts[1] and header_requests[0] != header_requests[1],
             "duplicate evidence cannot be a header recheck")

    def links(item):
        refs = item["evidence_ids"]
        need(isinstance(refs, list) and len(refs) == len(set(refs)) and set(refs) <= rows.keys(), "finding evidence missing or duplicated")
        return bool(refs)

    need(report["status"] in ("completed", "partial", "blocked"), "invalid completion status")
    for key in ("question", "verdict", "strongest_contrary_evidence", "change_evidence"):
        need(isinstance(report[key], str) and report[key].strip(), "missing report explanation")
    for value in (manifest["limitations"], report["unresolved_questions"]):
        need(isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value), "invalid gap list")
    seen_findings = set()
    for finding in report["findings"]:
        need(finding["id"] not in seen_findings, "duplicate finding ID")
        seen_findings.add(finding["id"])
        need(finding["class"] in ("fact", "supported", "inference", "unknown"), "invalid evidence class")
        need(links(finding) or finding["class"] == "unknown", "finding lacks evidence")
        for key in ("text", "time_basis", "alternatives", "coverage"):
            need(isinstance(finding[key], str) and finding[key].strip(), "finding context required")
    ratings = report["ratings"]
    need(len(ratings) == len(DIMENSIONS) and {x["dimension"] for x in ratings} == set(DIMENSIONS), "all eleven dimensions required")
    for row in ratings:
        need(row["status"] in ("unknown", "concern", "no_issue_detected", "not_applicable"), "invalid rating status")
        need(row["coverage"] in ("complete", "partial", "unknown"), "invalid coverage")
        has_evidence = links(row)
        for key in ("basis", "time_basis", "severity", "likelihood", "confidence"):
            need(isinstance(row[key], str) and row[key].strip(), "rating context missing")
        if row["status"] != "unknown":
            need(has_evidence, "non-unknown rating lacks evidence")
        if row["status"] in ("no_issue_detected", "not_applicable"):
            need(row["coverage"] == "complete", "incomplete check cannot pass or become N/A")
    if report["status"] == "completed":
        need(all(x["status"] != "unknown" and x["coverage"] == "complete" for x in ratings), "unknown coverage cannot be completed")
        need(identity_genesis and identity_mint, "completed report requires raw network and mint identity evidence")
        if summary:
            need(summary["sample_fresh"] and summary["sample_consistent"], "inconsistent collection cannot support completed report")
    return manifest, report

def render(manifest, report):
    # JSON blocks preserve arbitrary untrusted strings without interpreting them as instructions.
    def section(title, value):
        encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)
        fence = "`" * max(3, max((len(x) for x in re.findall(r"`+", encoded)), default=0) + 1)
        return "\n## " + title + "\n\n" + fence + "json\n" + encoded + "\n" + fence + "\n"
    text = "# Solana token diligence\n\n" + ("SYNTHETIC — " if report["synthetic"] else "") + report["status"].upper() + "\n"
    text += section("Target", report["target"])
    text += section("Assessment", {k: report[k] for k in ("question", "verdict", "strongest_contrary_evidence", "change_evidence", "unresolved_questions")})
    text += section("Dimensions", report["ratings"]) + section("Findings", report["findings"])
    text += section("Evidence and limitations", manifest)
    return text
