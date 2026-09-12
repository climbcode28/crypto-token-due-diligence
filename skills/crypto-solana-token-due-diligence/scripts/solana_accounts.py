"""Pinned SPL/Token-2022 account facts, with independent base/extension coverage."""
import base64
import math
import struct

from solana_common import (need, natural, pubkey, b58encode, sha, coption_key,
    optional_key, decode_mint as legacy_mint, extension as legacy_extension,
    TOKEN_PROGRAM, TOKEN_2022, target_identity)
from solana_wire import account as wire_account, validate_response, amount

LAYOUT_VERSION = "1.1.0"
ACCOUNT_TYPES = {2, 5, 7, 8, 11, 13, 15, 17, 27}
MINT_TYPES = set(range(1, 29))-ACCOUNT_TYPES
METADATA_STRING_BOUND = 4096
METADATA_PAIR_BOUND = 64


def boolean(value):
    need(value in (0, 1), "invalid extension boolean")
    return bool(value)


def _borsh_string(raw, offset, label):
    need(offset+4 <= len(raw), "truncated token metadata "+label+" length")
    size = int.from_bytes(raw[offset:offset+4], "little")
    need(size <= METADATA_STRING_BOUND and offset+4+size <= len(raw), "token metadata "+label+" exceeds entry")
    try:
        value = raw[offset+4:offset+4+size].decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("token metadata "+label+" is not UTF-8") from None
    return value, offset+4+size


def _token_metadata(raw, address):
    """Token-2022 extension 19 (Borsh): update authority, mint, name, symbol, uri, additional (key, value) pairs.

    Every length is bounded by the TLV entry; the embedded mint must be the account itself when known.
    """
    need(len(raw) >= 80, "token metadata entry too short")
    row = {"authority": optional_key(raw[:32]), "mint": b58encode(raw[32:64])}
    offset = 64
    for label in ("name", "symbol", "uri"):
        row["token_"+label], offset = _borsh_string(raw, offset, label)
    need(offset+4 <= len(raw), "truncated additional metadata count")
    count = int.from_bytes(raw[offset:offset+4], "little")
    need(count <= METADATA_PAIR_BOUND, "additional metadata pairs exceed bound")
    start = offset
    offset += 4
    for _ in range(count):
        _, offset = _borsh_string(raw, offset, "additional key")
        _, offset = _borsh_string(raw, offset, "additional value")
    need(offset == len(raw), "trailing token metadata bytes")
    row.update(additional_metadata_count=count, additional_metadata_sha256=sha(raw[start:]))
    if address is not None:
        need(row["mint"] == pubkey(address), "token metadata mint mismatch")
        row["mint_matches"] = True
    return row


def _extension(kind, raw, holding, address=None):
    row = {"type": kind, "length": len(raw), "sha256": sha(raw), "decoded": False}
    if holding:
        specs = {2: ("transfer_fee_amount", 8), 7: ("immutable_owner", 0),
                 8: ("memo_transfer", 1), 11: ("cpi_guard", 1), 13: ("non_transferable_account", 0),
                 15: ("transfer_hook_account", 1), 17: ("confidential_transfer_fee_amount", 64), 27: ("pausable_account", 0)}
        if kind not in specs:
            return row
        name, size = specs[kind]
        need(len(raw) == size, "invalid holding extension length")
        row.update(name=name, decoded=True)
        if kind == 2:
            row["withheld_atomic"] = str(int.from_bytes(raw, "little"))
        elif kind in (8, 11, 15):
            row[{8: "require_incoming_memo", 11: "lock_cpi", 15: "transferring"}[kind]] = boolean(raw[0])
        elif kind == 17:
            row.update(withheld_atomic=None, visibility="encrypted", ciphertext_sha256=sha(raw))
        return row
    row = legacy_extension(kind, raw)
    if row["decoded"]:
        return row
    if kind == 19:
        row.update(name="token_metadata", decoded=True, **_token_metadata(raw, address))
        return row
    specs = {4: ("confidential_transfer_mint", 65), 10: ("interest_bearing_config", 52),
             16: ("confidential_transfer_fee_config", 129), 18: ("metadata_pointer", 64),
             20: ("group_pointer", 64), 21: ("token_group", 80), 22: ("group_member_pointer", 64),
             23: ("token_group_member", 72), 25: ("scaled_ui_amount", 56), 28: ("permissioned_burn", 32)}
    if kind not in specs:
        return row
    name, size = specs[kind]
    need(len(raw) == size, "invalid mint extension length")
    if kind == 23:
        # A member has no authority of its own; its group is the controlling relationship.
        row.update(name=name, decoded=True, mint=b58encode(raw[:32]), group=b58encode(raw[32:64]),
                   member_number=int.from_bytes(raw[64:72], "little"))
        return row
    row.update(name=name, decoded=True, authority=optional_key(raw[:32]))
    if kind == 21:
        row.update(mint=b58encode(raw[32:64]), size=int.from_bytes(raw[64:72], "little"),
                   max_size=int.from_bytes(raw[72:80], "little"))
    elif kind in (18, 20, 22):
        row["address"] = optional_key(raw[32:64])
    elif kind == 4:
        row.update(auto_approve_new_accounts=boolean(raw[32]), auditor_key_hex=raw[33:].hex(), balance_visibility="encrypted")
    elif kind == 16:
        row.update(withdraw_elgamal_key_hex=raw[32:64].hex(), harvest_to_mint_enabled=boolean(raw[64]),
                   withheld_atomic=None, ciphertext_sha256=sha(raw[65:]))
    elif kind == 10:
        initial, previous_rate, updated, rate = struct.unpack("<qhqh", raw[32:])
        row.update(initialization_timestamp=initial, previous_rate_basis_points=previous_rate,
                   last_update_timestamp=updated, current_rate_basis_points=rate, changes_atomic_supply=False)
    elif kind == 25:
        current, at, scheduled = struct.unpack("<dqd", raw[32:])
        need(math.isfinite(current) and current > 0 and math.isfinite(scheduled) and scheduled > 0, "invalid display multiplier")
        row.update(multiplier=repr(current), new_multiplier_effective_timestamp=at,
                   new_multiplier=repr(scheduled), changes_atomic_supply=False)
    return row


def _extensions(raw, base, owner, holding, address=None):
    rows, errors, seen = [], [], set()
    if owner == TOKEN_PROGRAM or len(raw) == base:
        return rows, errors
    try:
        need(len(raw) >= 166 and raw[165] == (2 if holding else 1), "wrong extension account type")
        if not holding:
            need(not any(raw[82:165]), "nonzero extended mint padding")
        offset = 166
        while offset < len(raw):
            if not any(raw[offset:]):
                break
            need(offset+4 <= len(raw), "truncated extension header")
            kind, size = struct.unpack("<HH", raw[offset:offset+4])
            need(kind != 0 and kind not in seen, "duplicate or invalid extension type")
            seen.add(kind)
            need(kind not in (MINT_TYPES if holding else ACCOUNT_TYPES), "extension on wrong base account type")
            offset += 4
            need(offset+size <= len(raw), "truncated extension payload")
            payload = raw[offset:offset+size]
            try:
                rows.append(_extension(kind, payload, holding, address))
            except ValueError as exc:
                rows.append({"type": kind, "length": size, "sha256": sha(payload), "decoded": False, "error": str(exc)})
                errors.append(str(exc))
            offset += size
    except ValueError as exc:
        errors.append(str(exc))
    return rows, errors


def _raw(account, size):
    wire_account(account)
    need(account is not None and account["executable"] is False, "token data account required")
    need(account["owner"] in (TOKEN_PROGRAM, TOKEN_2022), "unsupported token program")
    raw = base64.b64decode(account["data"][0], validate=True)
    need(len(raw) >= size and len(raw) != 355, "invalid token account length")
    need(account["owner"] != TOKEN_PROGRAM or len(raw) == size, "unexpected original SPL account bytes")
    if account["owner"] == TOKEN_2022 and len(raw) != size:
        need(len(raw) >= 166 and raw[165] == (1 if size == 82 else 2), "wrong extended base account type")
        if size == 82:
            need(not any(raw[82:165]), "nonzero extended mint padding")
    return raw


def decode_mint(account, *, address=None):
    """`address`, when known, binds embedded self-references (token metadata) to this account."""
    raw = _raw(account, 82)
    # Decode base observations independently, so bad TLV evidence cannot erase them.
    base = {**account, "data": [base64.b64encode(raw[:82]).decode(), "base64"], "space": 82}
    row = legacy_mint(base)
    rows, errors = _extensions(raw, 82, account["owner"], False, address)
    row.update(data_sha256=sha(raw), layout_version=LAYOUT_VERSION, extensions=rows,
               extension_errors=errors, extensions_valid=not errors,
               unknown_extensions=[r["type"] for r in rows if not r["decoded"]])
    return row


def decode_holding(account, *, mint=None, token_program=None):
    raw = _raw(account, 165)
    actual_mint, owner = b58encode(raw[:32]), b58encode(raw[32:64])
    if mint is not None:
        need(actual_mint == pubkey(mint), "holding mint mismatch")
    if token_program is not None:
        need(account["owner"] == token_program, "holding token program mismatch")
    state = raw[108]
    need(state in (0, 1, 2), "invalid holding state")
    native_tag = int.from_bytes(raw[109:113], "little")
    need(native_tag in (0, 1), "invalid native reserve COption")
    rows, errors = _extensions(raw, 165, account["owner"], True)
    return {"layout_version": LAYOUT_VERSION, "program": account["owner"], "mint": actual_mint,
        "spending_owner": owner, "amount_atomic": str(int.from_bytes(raw[64:72], "little")),
        "delegate": coption_key(raw[72:108]), "state": ("uninitialized", "initialized", "frozen")[state],
        "delegated_amount_atomic": str(int.from_bytes(raw[121:129], "little")),
        "close_authority": coption_key(raw[129:165]),
        "native_reserve_lamports": str(int.from_bytes(raw[113:121], "little")) if native_tag else None,
        "data_sha256": sha(raw), "extensions": rows, "extensions_valid": not errors,
        "extension_errors": errors, "unknown_extensions": [r["type"] for r in rows if not r["decoded"]],
        "confidential_balance_atomic": None if any(r["type"] == 5 for r in rows) else "not_applicable"}


def active_transfer_fee(mint, epoch_packet, *, mint_context_slot=None):
    if not mint["extensions_valid"]:
        return {"status": "unresolved", "current": None, "scheduled": None}
    fees = [r for r in mint["extensions"] if r["type"] == 1 and r["decoded"]]
    if not fees:
        return {"status": "absent" if mint["extensions_valid"] else "unresolved", "current": None, "scheduled": None}
    if epoch_packet is None or epoch_packet.get("status") != "ok":
        return {"status": "epoch_unresolved", "current": None, "scheduled": None}
    req = epoch_packet["request"]
    need(req["method"] == "getEpochInfo", "epoch evidence required")
    checked = validate_response(req, epoch_packet["response"])
    need(checked["status"] == "ok", "epoch response unresolved")
    info = checked["result"]
    epoch_start = info["absoluteSlot"]-info["slotIndex"]
    if mint_context_slot is None or not epoch_start <= natural(mint_context_slot) < epoch_start+info["slotsInEpoch"]:
        return {"status": "epoch_scope_unresolved", "current": None, "scheduled": None}
    fee = fees[0]
    epoch = checked["result"]["epoch"]
    newer = epoch >= fee["newer"]["epoch"]
    return {"status": "observed", "epoch": epoch, "epoch_observation": req["id"],
            "epoch_context_slot": checked["context_slot"], "current": fee["newer" if newer else "older"],
            "scheduled": None if newer else fee["newer"]}


def ratio(numerator, denominator, places=4):
    need(type(numerator) is type(denominator) is int and 0 <= numerator <= denominator, "invalid supply ratio")
    need(type(places) is int and 0 <= places <= 9, "invalid display precision")
    if denominator == 0:
        return None
    scale = 10**places
    rounded = (numerator*100*scale*2+denominator)//(2*denominator)
    return {"numerator_atomic": str(numerator), "denominator_atomic": str(denominator),
            "percent_display": str(rounded//scale)+"."+str(rounded%scale).zfill(places),
            "rounding": "half_up", "places": places}


def controls(mint_packet, target, *, epoch_packet=None):
    """Evidence-bound observed powers, without a safe/complete control verdict."""
    target = target_identity(target)
    need(mint_packet.get("status") == "ok", "successful mint observation required")
    req = mint_packet["request"]
    checked = validate_response(req, mint_packet["response"])
    need(checked["status"] == "ok" and req["method"] in ("getAccountInfo", "getMultipleAccounts"), "mint account observation required")
    need("dataSlice" not in req["params"][1] and target["mint"] in checked["addresses"], "full exact-mint observation required")
    values = checked["result"]["value"] if req["method"] == "getMultipleAccounts" else [checked["result"]["value"]]
    mint = decode_mint(values[checked["address_indices"][target["mint"]]], address=target["mint"])
    powers = [{"role": role, "controller": mint[role], "evidence": [req["id"]], "controller_status": "unresolved" if mint[role] is not None else "absent_in_sample"}
              for role in ("mint_authority", "freeze_authority")]
    for extension in mint["extensions"]:
        if extension["decoded"]:
            for field in ("authority", "config_authority", "withdraw_authority"):
                if field in extension:
                    controller = extension[field]
                    powers.append({"role": extension["name"]+"_"+field, "controller": controller,
                        "evidence": [req["id"]], "controller_status": "unresolved" if controller is not None else "absent_in_sample"})
    return {"target": target, "context_slot": checked["context_slot"], "evidence": [req["id"]],
            "mint": mint, "powers": powers, "transfer_fee": active_transfer_fee(mint, epoch_packet, mint_context_slot=checked["context_slot"]),
            "coverage": "partial", "remaining": ["controller and upgrade paths", "relevant frozen holdings", "hook behavior and dependencies", "ordinary-holder execution"]}


CONTROLLER_FIELDS = ("program",)  # the transfer-hook program; extension authorities are already powers


def controllers_of(result):
    """Every controller a controls fact names: its powers plus the decoded extensions' hook programs."""
    rows = [(p["role"], p["controller"]) for p in result["powers"]]
    for extension in result["mint"]["extensions"]:
        if extension.get("decoded"):
            rows += [(extension["name"]+"_"+field, extension[field]) for field in CONTROLLER_FIELDS if field in extension]
    return sorted(rows, key=str)


def newer_unpinned_note(newer_packet, pinned_packet, target):
    """Whether a newer, unpinned mint read still names every controller of the pinned snapshot it supersedes.
    Deterministic from the two retained packets, so a validator recomputes it without making the newer read an input."""
    try:
        match = controllers_of(controls(newer_packet, target)) == controllers_of(controls(pinned_packet, target))
        return {"authorities_match": match, "reason": None}
    except (ValueError, KeyError, TypeError) as exc:
        return {"authorities_match": None, "reason": "comparison failed: "+(str(exc) if isinstance(exc, ValueError) else type(exc).__name__)}


def aggregate_holders(discovery, sample, target, *, custody_exclusions=None):
    """Largest ranks are discovery leads; balances/denominator share one later batch context."""
    target = target_identity(target)
    need(discovery.get("status") == sample.get("status") == "ok", "successful discovery and sample required")
    d, s = validate_response(discovery["request"], discovery["response"]), validate_response(sample["request"], sample["response"])
    need(d["status"] == s["status"] == "ok", "valid discovery and sample required")
    from solana_presets import discovery_leads, LEAD_LIMIT
    method = discovery["request"]["method"]
    scanned = discovery_leads(target["mint"], discovery["request"], d, limit=None)  # binds the discovery to the exact mint
    leads = scanned[:LEAD_LIMIT]
    need(sample["request"]["method"] == "getMultipleAccounts" and "dataSlice" not in sample["request"]["params"][1], "full same-context batch required")
    need(s["context_slot"] >= d["context_slot"], "holdings sample predates rank discovery")
    indexed = dict(zip(s["addresses"], s["result"]["value"]))
    need(target["mint"] in indexed, "same-sample supply denominator missing")
    mint = decode_mint(indexed[target["mint"]])
    supply, owners, accounts, missing = amount(mint["supply_atomic"]), {}, [], []
    custody_exclusions = custody_exclusions or {}
    need(isinstance(custody_exclusions, dict) and set(custody_exclusions) <= indexed.keys(), "unrequested custody exclusion")
    for address, evidence in custody_exclusions.items():
        need(isinstance(evidence, dict) and set(evidence) == {"reason", "evidence"} and evidence["reason"] and isinstance(evidence["evidence"], list) and evidence["evidence"], "custody exclusion requires evidence")
    discovered = {r["address"]: (i+1, r) for i, r in enumerate(leads)}
    if method == "getTokenLargestAccounts":
        need(all(r["decimals"] == mint["decimals"] for r in d["result"]["value"]), "discovery decimals disagree with mint")
    need(set(indexed)-{target["mint"]} <= discovered.keys(), "unrequested holdings account")
    observed_total, excluded_total, withheld_total = 0, 0, 0
    withheld_unknown = False
    for address, (rank, lead) in discovered.items():
        value = indexed.get(address)
        if value is None:
            missing.append({"address": address, "reason": "not_sampled" if address not in indexed else "null_account"})
            continue
        try:
            holding = decode_holding(value, mint=target["mint"], token_program=mint["program"])
            need(holding["state"] != "uninitialized", "uninitialized holding")
        except (ValueError, KeyError, TypeError) as exc:
            missing.append({"address": address, "reason": str(exc) if isinstance(exc, ValueError) else "invalid_account"})
            continue
        quantity = amount(holding["amount_atomic"])
        observed_total += quantity
        excluded = address in custody_exclusions
        if excluded:
            excluded_total += quantity
        else:
            owner = holding["spending_owner"]
            owners.setdefault(owner, {"amount": 0, "accounts": []})
            owners[owner]["amount"] += quantity
            owners[owner]["accounts"].append(address)
        for extension in holding["extensions"]:
            if extension["type"] == 2 and extension["decoded"]:
                withheld_total += amount(extension["withheld_atomic"])
            if extension["type"] in (5, 17) or not extension["decoded"]:
                withheld_unknown = True
        if not holding["extensions_valid"]:
            withheld_unknown = True
        accounts.append({"address": address, "rank_at_discovery": rank, "discovery_amount_atomic": lead["amount"],
            "balance_changed_since_discovery": lead["amount"] != holding["amount_atomic"],
            "custody_exclusion": custody_exclusions.get(address), **holding})
    need(observed_total+withheld_total <= supply, "sample amounts exceed same-context supply")
    # Only holding-side unknowns can hide balances; an unknown mint extension is a control gap, not a quantity gap.
    return {"target": target, "status": "partial" if missing or withheld_unknown or not mint["extensions_valid"] else "sampled",
        "discovery_slot": d["context_slot"], "sample_slot": s["context_slot"],
        "discovery": {"method": method, "leads": len(leads),
            "accounts_scanned": len(scanned) if method == "getProgramAccounts" else None,
            "scanned_amount_atomic": str(sum(int(r["amount"]) for r in scanned)) if method == "getProgramAccounts" else None,
            "scope": "provider-reported census of fixed-size SPL accounts at the discovery slot" if method == "getProgramAccounts" else "largest-account sample of at most 20 token accounts"},
        "evidence": [discovery["request"]["id"], sample["request"]["id"]], "mint": mint,
        "supply_atomic": str(supply), "observed_base_amount_atomic": str(observed_total),
        "known_withheld_amount_atomic": str(withheld_total), "additional_withheld_or_confidential_unknown": withheld_unknown,
        "custody_excluded_amount_atomic": str(excluded_total), "coverage_share": ratio(observed_total, supply),
        "accounts": accounts, "missing": missing, "owners": [{"spending_owner": owner,
            "amount_atomic": str(values["amount"]), "accounts": values["accounts"], "supply_share": ratio(values["amount"], supply)}
            for owner, values in sorted(owners.items(), key=lambda row: (-row[1]["amount"], row[0]))],
        "scope": "sampled token-account spending owners; beneficial ownership and circulating supply unresolved",
        "burned_amount_atomic": None}
