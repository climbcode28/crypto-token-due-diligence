"""Bounded loader/controller observations and deliberately separate source assurance."""
import base64
import re

from solana_common import need, pubkey, base58_bytes, b58encode, sha, TOKEN_PROGRAM, TOKEN_2022
from solana_addresses import find_program_address, bytes_are_curve_point
from solana_accounts import decode_mint, decode_holding
from solana_wire import validate_response
from solana_transport import validate_endpoint
from adapters import spl_multisig, squads_v4
from adapters.binary import discriminator

UPGRADEABLE = "BPFLoaderUpgradeab1e11111111111111111111111"
LOADER_V2 = "BPFLoader2111111111111111111111111111111111"
NATIVE = "NativeLoader1111111111111111111111111111111"
SYSTEM = "1"*32


def observed_account(address, packet):
    pubkey(address)
    need(packet.get("status") == "ok", "account observation unsuccessful")
    req = packet["request"]
    checked = validate_response(req, packet["response"])
    need(checked["status"] == "ok" and req["method"] in ("getAccountInfo", "getMultipleAccounts"), "account read required")
    need(address in checked["addresses"], "unrequested account subject")
    values = checked["result"]["value"] if req["method"] == "getMultipleAccounts" else [checked["result"]["value"]]
    value = values[checked["address_indices"][address]]
    settings = req["params"][1]
    sliced = "dataSlice" in settings
    if sliced:
        need(settings["dataSlice"]["offset"] == 0, "metadata reads require an exact prefix")
    return value, {"evidence": [req["id"]], "context_slot": checked["context_slot"], "sliced": sliced,
                   "started_at": packet.get("started_at"), "completed_at": packet.get("completed_at")}


def decode_program(address, packet, programdata_packet=None):
    account, sample = observed_account(address, packet)
    need(account is not None and account["executable"] is True, "executable program account required")
    raw = base64.b64decode(account["data"][0], validate=True)
    owner = account["owner"]
    row = {"kind": "program", "address": address, "loader": owner, **sample,
           "upgradeability": "unknown", "upgrade_authority": None, "programdata_address": None,
           "code_sha256": None, "code_hash_kind": "complete_loader_payload_sha256",
           "code_capture": "unavailable", "deployment_slot": None}
    if owner == UPGRADEABLE:
        need(not sample["sliced"] and len(raw) == 36 and int.from_bytes(raw[:4], "little") == 2, "invalid upgradeable Program layout")
        programdata = b58encode(raw[4:])
        need(find_program_address([base58_bytes(address, 32)], UPGRADEABLE)[0] == programdata, "ProgramData PDA mismatch")
        row["programdata_address"] = programdata
        if programdata_packet is None:
            return row
        data, data_sample = observed_account(programdata, programdata_packet)
        need(data is not None and data["owner"] == UPGRADEABLE and data["executable"] is False, "wrong ProgramData owner/state")
        code = base64.b64decode(data["data"][0], validate=True)
        need(len(code) >= 45 and int.from_bytes(code[:4], "little") == 3, "incomplete ProgramData metadata")
        flag = code[12]
        need(flag in (0, 1), "invalid upgrade authority option")
        slot = int.from_bytes(code[4:12], "little")
        need(slot <= data_sample["context_slot"], "deployment slot after observation")
        row.update(upgradeability="authority_present" if flag else "authority_revoked",
                   upgrade_authority=b58encode(code[13:45]) if flag else None, deployment_slot=slot,
                   programdata_context_slot=data_sample["context_slot"],
                   evidence=sample["evidence"]+data_sample["evidence"],
                   code_capture="metadata_only", completed_at=data_sample["completed_at"])
        if not data_sample["sliced"] and data.get("space") == len(code) and len(code) > 45:
            row.update(code_sha256=sha(code[45:]), code_capture="complete", code_bytes=len(code)-45)
    elif owner == LOADER_V2:
        row["upgradeability"] = "no_upgrade_path_in_recognized_loader"
        if not sample["sliced"] and account.get("space") == len(raw) and raw:
            row.update(code_sha256=sha(raw), code_capture="complete", code_bytes=len(raw))
    elif owner == NATIVE:
        row["upgradeability"] = "runtime_managed"
    return row


def compare_program_recheck(first, fresh):
    need(first["address"] == fresh["address"], "program recheck subject mismatch")
    need(first.get("completed_at") is not None and fresh.get("started_at") is not None and fresh["started_at"] > first["completed_at"], "fresh program request must follow initial completion")
    need(not set(first["evidence"]) & set(fresh["evidence"]), "program recheck reused an evidence request")
    need(fresh["context_slot"] >= first["context_slot"] and fresh.get("programdata_context_slot", 0) >= first.get("programdata_context_slot", 0), "program recheck context moved backwards")
    fields = ("loader", "programdata_address", "deployment_slot", "upgradeability", "upgrade_authority", "code_sha256")
    changed = [key for key in fields if first.get(key) != fresh.get(key)]
    return {"status": "changed" if changed else "agreed", "changed": changed, "evidence": first["evidence"]+fresh["evidence"]}


def authority_graph(roots, observations, *, vault_links=None, spending_limits=None, max_depth=3, max_accounts=20):
    """Edges come from verified account fields/PDAs, never a claimed controller label."""
    need(type(max_depth) is int and 0 <= max_depth <= 3 and type(max_accounts) is int and 1 <= max_accounts <= 20, "controller graph exceeds ordinary bounds")
    need(isinstance(roots, list) and len(roots) <= 20 and isinstance(observations, dict), "bounded graph inputs required")
    vault_links = vault_links or {}
    spending_limits = spending_limits or {}
    need(isinstance(spending_limits, dict) and all(isinstance(v, list) and len(v) <= 20 for v in spending_limits.values()), "bounded spending limit candidates required")
    nodes, edges, gaps, consumed, discovered = {}, [], [], set(), set()

    def captured(address):
        if address not in discovered:
            need(len(discovered) < max_accounts, "account_limit")
            discovered.add(address)
        if address not in consumed:
            need(len(consumed) < max_accounts, "account_limit")
            consumed.add(address)
        need(address in observations, "controller account not captured")
        return observed_account(address, observations[address])

    def visit(address, depth, ancestors):
        pubkey(address)
        if address in ancestors:
            gaps.append({"address": address, "reason": "cycle"})
            return
        if address in nodes:
            return
        if depth > max_depth or address not in discovered and len(discovered) >= max_accounts:
            gaps.append({"address": address, "reason": "depth_limit" if depth > max_depth else "account_limit"})
            return
        discovered.add(address)
        node = {"address": address, "kind": "unknown", "status": "unresolved", "evidence": []}
        nodes[address] = node
        related = []
        try:
            packet = observations.get(address)
            if packet is None:
                raise ValueError("controller account not captured")
            account, sample = captured(address)
            node.update(sample)
            if address in vault_links:
                link = vault_links[address]
                parent = link["multisig"]
                parent_account, parent_sample = captured(parent)
                multisig = squads_v4.decode(parent, parent_account)
                relation = squads_v4.verify_vault(address, multisig, link["index"])
                node.update(kind="squads_vault", status="observed", evidence=sample["evidence"]+parent_sample["evidence"])
                related.append((relation["role"], parent, "current_controller"))
            elif account is None:
                raise ValueError("null controller account")
            elif account["executable"]:
                raw = base64.b64decode(account["data"][0], validate=True)
                pd = b58encode(raw[4:36]) if account["owner"] == UPGRADEABLE and len(raw) == 36 else None
                if pd in observations:
                    captured(pd)  # ProgramData also consumes the controller-account bound.
                program = decode_program(address, packet, observations.get(pd))
                node.update(program, status="observed" if program["upgradeability"] != "unknown" else "unresolved")
                if program["upgrade_authority"] is not None:
                    related.append(("upgrade_authority", program["upgrade_authority"], "future_program_change"))
            else:
                need(not sample["sliced"], "controller data requires complete account")
                raw = base64.b64decode(account["data"][0], validate=True)
                if account["owner"] in (TOKEN_PROGRAM, TOKEN_2022):
                    if len(raw) == 355:
                        decoded = spl_multisig.decode(address, account)
                        node.update(decoded, status="observed")
                        related.extend(("multisig_signer", k, "current_signer") for k in decoded["signers"])
                    elif len(raw) == 82 or len(raw) >= 166 and raw[165] == 1:
                        decoded = decode_mint(account)
                        node.update(kind="mint", facts=decoded, status="observed")
                        related.extend((role, decoded[role], "current_controller") for role in ("mint_authority", "freeze_authority") if decoded[role] is not None)
                        for ext in decoded["extensions"]:
                            if not ext["decoded"]:
                                gaps.append({"address": address, "reason": "unknown_extension", "type": ext["type"]})
                                continue
                            related.extend((ext["name"]+"_"+role, ext[role], "current_controller") for role in ("authority", "config_authority", "withdraw_authority", "program") if ext.get(role) is not None)
                        if not decoded["extensions_valid"]:
                            gaps.append({"address": address, "reason": "invalid_extensions"})
                    else:
                        decoded = decode_holding(account)
                        node.update(kind="holding", facts=decoded, status="observed")
                        related.extend((role, decoded[role], "current_controller") for role in ("spending_owner", "delegate", "close_authority") if decoded[role] is not None)
                    related.append(("owning_token_program", account["owner"], "program_behavior"))
                elif account["owner"] == squads_v4.PROGRAM:
                    if raw[:8] == discriminator("SpendingLimit"):
                        parent = b58encode(raw[8:40])
                        parent_account, parent_sample = captured(parent)
                        decoded = squads_v4.decode_spending_limit(address, account, squads_v4.decode(parent, parent_account))
                        node.update(decoded, status="observed", evidence=node["evidence"]+parent_sample["evidence"])
                        related.extend(("spending_limit_member", member, "current_spending_bypass") for member in decoded["members"])
                    else:
                        decoded = squads_v4.decode(address, account)
                        node.update(decoded, status="observed")
                        for key in spending_limits.get(address, []):
                            try:
                                limit_account, _ = captured(key)
                                squads_v4.decode_spending_limit(key, limit_account, decoded)
                                related.append(("spending_limit", key, "current_spending_bypass"))
                            except (ValueError, KeyError, TypeError) as exc:
                                gaps.append({"address": key, "reason": "spending_limit_candidate_unverified", "category": type(exc).__name__})
                        related.extend(("member_permissions_"+str(m["permissions"]), m["key"], "current_signer") for m in decoded["members"])
                        if decoded["config_authority"] is not None:
                            related.append(("configuration_bypass", decoded["config_authority"], "current_configuration"))
                        related.append(("controller_program", squads_v4.PROGRAM, "program_behavior"))
                        gaps.append({"address": address, "reason": "spending_limit_sample_not_exhaustive" if address in spending_limits else "spending_limits_not_enumerated"})
                elif account["owner"] == SYSTEM and not raw:
                    node.update(kind="system_key_account" if bytes_are_curve_point(base58_bytes(address, 32)) else "unresolved_pda", status="unresolved")
                else:
                    related.append(("owning_program", account["owner"], "unknown_program_behavior"))
                    raise ValueError("unrecognized controller layout or logic")
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            gaps.append({"address": address, "reason": str(exc) if isinstance(exc, ValueError) else "invalid_controller_observation"})
        for role, destination, capability in related:
            edge = {"from": address, "to": destination, "role": role, "capability_scope": capability, "evidence": node["evidence"]}
            if edge not in edges:
                edges.append(edge)
            visit(destination, depth+1, (*ancestors, address))

    for address in roots:
        visit(address, 0, ())
    return {"roots": roots, "nodes": list(nodes.values()), "edges": edges, "gaps": gaps,
            "status": "partial" if gaps or any(n["status"] == "unresolved" for n in nodes.values()) else "observed_paths",
            "max_depth": max_depth, "max_accounts": max_accounts, "observed_account_count": len(consumed),
            "discovered_account_count": len(discovered), "safe_or_locked_conclusion": None}


def source_assurance(program, *, publication=None, third_party=None, reproduction=None):
    """Publication, remote claims and independently compared bytes are separate levels."""
    row = {"program": program["address"], "evidence": program["evidence"],
           "publication": "not_observed", "third_party_verification": "not_observed",
           "byte_correspondence": "unavailable", "independent_reproduction": "not_performed",
           "pool_configuration_proven": False, "deployment_slot": program["deployment_slot"]}
    if publication is not None:
        parts = validate_endpoint(publication.get("url"))
        need(not parts.query, "source publication URL must not contain credentials or query tokens")
        revision = publication.get("revision")
        need(isinstance(revision, str) and re.fullmatch("[0-9a-f]{40}", revision), "immutable source revision required")
        need(isinstance(publication.get("evidence"), list) and publication["evidence"], "captured publication evidence required")
        row.update(publication="published", source_url=publication["url"], source_revision=revision)
        row["evidence"] = row["evidence"]+publication["evidence"]
    if third_party is not None:
        need(third_party.get("program") == program["address"] and isinstance(third_party.get("evidence"), list) and third_party["evidence"], "third-party verification subject/evidence required")
        status = third_party.get("status")
        need(status in ("verified", "mismatch", "unavailable", "unsupported"), "invalid verification service status")
        row["third_party_verification"] = status
        row["evidence"] = row["evidence"]+third_party["evidence"]
        if status == "verified" and program["code_capture"] == "complete" and third_party.get("hash_kind") == program["code_hash_kind"]:
            row["byte_correspondence"] = "remote_hash_matches_captured_bytes" if third_party.get("code_sha256") == program["code_sha256"] else "mismatch"
    if program["code_capture"] != "complete":
        row["byte_correspondence"] = "incomplete_executable_bytes"
    if reproduction is not None:
        need(publication is not None and reproduction.get("source_revision") == publication["revision"], "reproduction source revision mismatch")
        need(reproduction.get("program") == program["address"] and reproduction.get("build_id") and reproduction.get("evidence"), "reproduction build/subject evidence required")
        need(type(reproduction.get("bytes")) is bytes and len(reproduction["bytes"]) <= 16_000_000, "bounded reproduced bytes required")
        row["build_id"] = reproduction["build_id"]
        row["independent_reproduction"] = "produced_artifact"
        if program["code_capture"] == "complete":
            matched = sha(reproduction["bytes"]) == program["code_sha256"]
            row["independent_reproduction"] = "artifact_match_reproduction_unproven" if matched else "mismatch"
            row["byte_correspondence"] = "local_artifact_matches_captured_bytes" if matched else "mismatch"
            row["reproduction_limit"] = "matching supplied artifact bytes alone does not prove an independent build from the claimed source"
    return row
