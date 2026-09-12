#!/usr/bin/env python3
"""Bounded, read-only Solana mint observations. No trades or safety certification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import multiprocessing
import os
from pathlib import Path
import sys
import threading
import time

from solana_common import ENGINE_VERSION, decode_mint, natural, need, pubkey, sha, target_identity

BACKEND = Path(__file__).resolve().parents[2] / "crypto-evm-token-due-diligence" / "scripts"
sys.path.insert(0, str(BACKEND))
try:
    from rpc_collect import HttpTransport, provider_availability, transport_settings
except ImportError:
    HttpTransport = provider_availability = transport_settings = None


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_atomic(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("x") as handle:
        json.dump(value, handle, sort_keys=True, allow_nan=False)
    os.replace(temporary, path)


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


def worker(root, config, target, largest, cap, factory=None):
    root, attempts = Path(root), 0
    factory = factory or HttpTransport
    lock = threading.Lock()

    def rpc(eid, method, params):
        nonlocal attempts
        request = {"jsonrpc": "2.0", "id": eid, "method": method, "params": params}
        with lock:
            if attempts >= cap:
                return None
            attempts += 1
            write_atomic(root / "attempts" / (eid + ".json"), {"request": request, "started_at_utc": stamp()})
        record = {"request": request, "status": "unavailable"}
        result = None
        try:
            transport = factory(config["url"], config["headers"], timeout=5, max_bytes=1_000_000)
            response = transport(request)
            record["response"] = response
            valid = (isinstance(response, dict) and response.get("jsonrpc") == "2.0"
                     and response.get("id") == eid and (("result" in response) != ("error" in response)))
            if not valid or getattr(transport, "last_redacted", False):
                record["status"] = "invalid_or_redacted"
            elif response.get("result") is not None:
                record["status"] = "ok"
                result = response["result"]
        except Exception as exc:
            record.update(status="transport_failure", error_category=type(exc).__name__)
        record["captured_at_utc"] = stamp()
        write_atomic(root / "evidence" / (eid + ".json"), record)
        return result

    try:
        if rpc("genesis", "getGenesisHash", []) != target["genesis_hash"]:
            return
        first = rpc("mint", "getAccountInfo", account_params(target["mint"]))
        first_slot = slot_of(first)
        decode_mint(first["value"])
        rpc("block", "getBlock", block_params(first_slot))
        if largest:
            rpc("largest", "getTokenLargestAccounts", [target["mint"], {"commitment": "finalized"}])
        last = rpc("mint_recheck", "getAccountInfo", account_params(target["mint"], first_slot))
        last_slot = slot_of(last)
        rpc("end_block", "getBlock", block_params(last_slot))
        reads = [("block_recheck", "getBlock", block_params(first_slot)),
                 ("end_block_recheck", "getBlock", block_params(last_slot)),
                 ("genesis_recheck", "getGenesisHash", [])]
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(lambda args: rpc(*args), reads))
    except (ValueError, KeyError, TypeError, IndexError):
        return


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


def run_bounded(root, config, target, largest=False, seconds=30, max_requests=24, worker_target=worker):
    target = target_identity(target)
    need(type(seconds) in (int, float) and math.isfinite(seconds) and 0 < seconds <= 55, "invalid seconds")
    need(type(max_requests) is int and 9 <= max_requests <= 24, "requests must be 9–24")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    for folder in ("attempts", "evidence", "engine"):
        (root / folder).mkdir()
    sources = [Path(__file__).resolve(), Path(__file__).with_name("solana_common.py"),
               BACKEND / "rpc_collect.py", BACKEND / "backend_common.py", BACKEND / "validate_bundle.py"]
    hashes = {}
    for source in sources:
        raw = source.read_bytes()
        (root / "engine" / source.name).write_bytes(raw)
        hashes[source.name] = sha(raw)
    write_atomic(root / "engine" / "snapshot.json", {"engine_version": ENGINE_VERSION, "sha256": hashes})
    started = time.monotonic()
    process = multiprocessing.get_context("spawn").Process(target=worker_target,
        args=(str(root), config, target, largest, max_requests))
    process.start()
    timed_out = False
    try:
        process.join(max(0, seconds - (time.monotonic() - started)))
        timed_out = process.is_alive()
    finally:
        if process.is_alive():
            process.terminate()
            process.join(0.5)
            if process.is_alive():
                process.kill()
                process.join(0.5)
    captured = stamp()
    summary = summarize(root, target, largest, datetime.fromisoformat(captured).timestamp())
    summary.update(schema_version=1, engine_version=ENGINE_VERSION, captured_at_utc=captured,
                   elapsed_seconds=round(time.monotonic()-started, 3), timed_out=timed_out,
                   worker_exit_code=process.exitcode, synthetic=worker_target is not worker,
                   include_largest=largest, request_limit=max_requests,
                   attempt_upper_bound=len(list((root / "attempts").glob("*.json"))))
    summary["artifact_sha256"] = {str(p.relative_to(root)): sha(p.read_bytes())
        for folder in ("attempts", "evidence", "engine") for p in sorted((root / folder).glob("*")) if p.suffix != ".tmp"}
    write_atomic(root / "summary.json", summary)
    return summary


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mint")
    p.add_argument("--genesis-hash", help="expected network genesis from independent identity evidence")
    p.add_argument("--out", type=Path)
    p.add_argument("--include-largest", action="store_true")
    p.add_argument("--seconds", type=float, default=30)
    p.add_argument("--max-requests", type=int, default=24)
    p.add_argument("--rpc-url-env", default="SOLANA_RPC_URL")
    p.add_argument("--provider", choices=("generic", "drpc"), default="generic")
    p.add_argument("--auth-env")
    p.add_argument("--auth-header", default="Authorization")
    p.add_argument("--allow-network", action="store_true")
    p.add_argument("--cost-policy", choices=("free", "paid"))
    p.add_argument("--allow-paid", action="store_true")
    p.add_argument("--check-availability", action="store_true")
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        route = provider_availability(args) if provider_availability else {
            "status": "fallback", "reason": "sibling_transport_missing", "network_requests": 0,
            "next_action": "continue_standard_flow"}
        if args.check_availability or route["status"] != "ready":
            print(json.dumps(route, sort_keys=True))
            return 0 if args.check_availability else 3
        if not args.mint or not args.genesis_hash or args.out is None:
            p.error("requires --mint, --genesis-hash and a new --out directory")
        url, headers = transport_settings(args)
        summary = run_bounded(args.out, {"url": url, "headers": headers},
            {"family": "solana", "genesis_hash": args.genesis_hash, "mint": args.mint},
            args.include_largest, args.seconds, args.max_requests)
        print(json.dumps(summary, sort_keys=True))
        return 2 if summary["timed_out"] or not summary["sample_fresh"] else 0
    except (ValueError, TypeError, OSError, KeyError):
        p.exit(2, "Solana collection failed: invalid input, configuration or output. No secret values logged.\n")


if __name__ == "__main__":
    sys.exit(main())
