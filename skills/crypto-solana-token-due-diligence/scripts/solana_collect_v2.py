"""Dependency-aware public RPC sampling under one durable investigation budget."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import multiprocessing
from pathlib import Path
import time

from solana_common import need, sha, target_identity, write_new, TOKEN_PROGRAM
from solana_session import Session, TRANSIENT, encoded, label
from solana_transport import HttpTransport, session_request
from solana_wire import validate_response, consistency, STATE
from solana_presets import read, validate_plan, account_batches, mint_baseline, holding_sample, holder_scan
from solana_cache import ObservationCache

MAX_WAIT_SECONDS = 30  # Longest wait for one read's provider window/backoff; remaining time bounds it too.
SLEEP = time.sleep


def block_params(slot):
    return [slot, {"commitment": "finalized", "transactionDetails": "none", "rewards": False}]


def _packets(session, sample):
    rows = []
    for attempt in session.observations():
        intent_path = session.root/"read-intents"/(attempt["request_id"]+".json")
        belongs = intent_path.exists() and json.loads(intent_path.read_text()).get("sample_id") == sample
        if belongs and attempt["response"] is not None:
            packet = json.loads(attempt["response"])
            rows.append({**packet, "attempt_id": attempt["id"], "started_at": attempt["started_at"],
                         "completed_at": attempt["completed_at"], "namespace": attempt["source"],
                         "response_bytes": attempt["response_bytes"]})
    return rows


def execute(session_root, config, sample, row, owner="ordinary", factory=HttpTransport):
    """Resume an explicitly named capture, or send at most its one transient retry."""
    session = Session(session_root)
    try:
        transport = factory(config["url"], config.get("headers", {}), timeout=5, max_bytes=1_000_000)
        family = sample+"_"+row["name"]
        for index in range(2):
            request = {"jsonrpc": "2.0", "id": family+"_"+str(index), "method": row["method"], "params": row["params"]}
            previous = next((r for r in session.observations() if r["request_id"] == request["id"]), None)
            if previous and previous["response"]:
                intent = json.loads((Path(session_root)/"read-intents"/(request["id"]+".json")).read_text())
                need(intent["sample_id"] == sample and intent["owner"] == owner and previous["source"] == transport.namespace,
                     "resume sample, owner or provider changed")
                packet = json.loads(previous["response"])
                need(packet["request"] == request, "resume request changed")
            elif previous:
                return {"request": request, "status": previous["status"], "response": None}
            else:
                # The immutable per-read intent survives termination before finish().
                path = Path(session_root)/"read-intents"/(request["id"]+".json")
                intent = {"request": request, "namespace": transport.namespace, "owner": owner,
                          "sample_id": sample, "investigation_id": session.meta["investigation_id"]}
                if path.exists():
                    need(json.loads(path.read_text()) == intent, "read intent changed")
                else:
                    write_new(path, intent)
                if index == 1:
                    SLEEP(min(1, session.remaining_seconds(owner)))  # The single transient retry is never immediate.
                packet = _send(session, transport, request, family=family, owner=owner, retry=index == 1)
            if packet["status"] not in TRANSIENT:
                return packet
        return packet
    finally:
        session.close()


def _send(session, transport, request, *, family, owner, retry):
    """Wait out a provider backoff or rate window within the remaining time; waiting is never an attempt."""
    waited = 0.0
    while True:
        packet = session_request(session, transport, request, family=family, owner=owner, retry=retry, strict=True)
        until = packet.get("wait_until") if packet.get("status") == "budget_denied" else None
        if until is None:
            return packet
        delay = max(0.05, until - time.time())
        if waited + delay > min(MAX_WAIT_SECONDS, session.remaining_seconds(owner)):
            packet["waited"] = waited
            return packet
        SLEEP(delay)
        waited += delay


def queue(session_root, config, sample, rows, *, owner="ordinary", factory=HttpTransport):
    validate_plan(rows)
    path = Path(session_root)/"queue-plans"/(sample+"_"+sha(encoded(rows).encode())+".json")
    if not path.exists():
        write_new(path, {"sample_id": sample, "reads": rows})
    pending, done, active = {r["name"]: r for r in rows}, {}, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        while pending or active:
            for name, row in list(pending.items()):
                if len(active) == 3:
                    break
                if not set(row["depends"]) <= done.keys():
                    continue
                pending.pop(name)
                if any(done[d]["status"] != "ok" for d in row["depends"]):
                    done[name] = {"status": "dependency_failed", "response": None}
                else:
                    active[pool.submit(execute, session_root, config, sample, row, owner, factory)] = name
            if active:
                completed, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in completed:
                    name = active.pop(future)
                    try:
                        done[name] = future.result()
                    except Exception as exc:
                        done[name] = {"status": "worker_failure", "error_category": type(exc).__name__, "response": None}
    return done


def _checked(packet):
    return validate_response(packet["request"], packet["response"]) if packet.get("status") == "ok" else {}


def _block_time(packet):
    """The comparable value of a header check: a full header's blockTime, or the block-time read itself."""
    result = packet["response"]["result"]
    return result["blockTime"] if packet["request"]["method"] == "getBlock" else result


def collect(session_root, out, config, sample, rows, *, factory=HttpTransport, expand_largest=False):
    """All outputs are observations; collection success never implies research completion."""
    label(sample)
    need(len(sample) <= 16, "sample ID too long")
    validate_plan(rows)
    need(all(len(r["name"]) <= 45 for r in rows), "read name too long")
    need(all(r["name"] not in ("network", "renetwork", "holderscan") and not r["name"].startswith(("critical_", "header_", "reheader_", "holdings_")) for r in rows), "reserved collector read name")
    session = Session(session_root)
    try:
        session.recover_expired()  # A lost worker from an earlier process must not hold a concurrency slot.
        # Reserve worst-case distinct state/header contexts before discretionary sends.
        critical = list(dict.fromkeys(a for r in rows if r["critical"] for a in
            (r["params"][0] if r["method"] == "getMultipleAccounts" else [r["params"][0]])))
        need(all(r["method"] in ("getAccountInfo", "getMultipleAccounts") and "dataSlice" not in r["params"][1]
                 for r in rows if r["critical"]), "critical checks require full accounts")
        need(session.meta["target"]["mint"] in critical, "critical target mint read required")
        # One recheck batch per initial critical read, so several leads in one sample each keep
        # their own fresh recheck instead of sharing a single deduplicated batch.
        critical_rows = [r for r in rows if r["critical"]]
        critical_reads = [b for i, r in enumerate(critical_rows) for b in account_batches(
            r["params"][0] if r["method"] == "getMultipleAccounts" else [r["params"][0]], prefix="critical_"+str(i))]
        states = sum(r["method"] in STATE or r["method"] in ("getTransaction", "getEpochInfo") for r in rows)
        # Fresh critical batches, their headers, initial context headers and genesis.
        identity = {"sample_id": sample, "reads": rows, "expand_largest": expand_largest,
                    "target": session.meta["target"], "synthetic": session.meta["synthetic"],
                    "provider_namespace": factory(config["url"], config.get("headers", {}), timeout=5, max_bytes=1_000_000).namespace}
        manifest = Path(session_root)/"sample-plans"/(sample+".json")
        if manifest.exists():
            need(json.loads(manifest.read_text()) == identity, "named sample plan changed")
        else:
            session.ensure_final_reserve(states+2*len(critical_reads)+1+2*int(expand_largest), "sample "+sample+" planned state/header rechecks")
            write_new(manifest, identity)
        genesis = execute(session_root, config, sample, read("network", "getGenesisHash", []), factory=factory)
        if _checked(genesis).get("result") != session.meta["target"]["genesis_hash"]:
            session.mark("collection", {"sample": sample, "status": "network_unresolved"})
            return
        result = queue(session_root, config, sample, rows, factory=factory)
        if expand_largest:
            mint = session.meta["target"]["mint"]
            largest = result.get("largest", {})
            discovery = largest if _checked(largest).get("status") == "ok" else None
            refused = largest.get("status") == "method_unavailable" or largest.get("reason") == "method_unavailable"
            mint_value = (_checked(result.get("mint", {})).get("result") or {}).get("value") or {}
            if discovery is None and refused and mint_value.get("owner") == TOKEN_PROGRAM:
                # The public tier refuses largest accounts: a bounded census of fixed-size SPL
                # holdings is the discovery lead instead. Token-2022 keeps an explicit gap.
                scan = queue(session_root, config, sample, [holder_scan(mint)], factory=factory)
                result.update(scan)
                if _checked(scan.get("holderscan", {})).get("status") == "ok":
                    discovery = scan["holderscan"]
            if discovery is not None:
                derived = holding_sample(mint, discovery)
                result.update(queue(session_root, config, sample, derived, factory=factory))
        floor = max((_checked(p).get("context_slot", 0) for p in result.values()), default=0)
        rechecks = [b for i, r in enumerate(critical_rows) for b in account_batches(
            r["params"][0] if r["method"] == "getMultipleAccounts" else [r["params"][0]], prefix="critical_"+str(i), floor=floor)]
        result.update(queue(session_root, config, sample, rechecks, owner="final", factory=factory))
        slots = sorted({v for p in result.values() for c in [_checked(p)]
                        for v in [c.get("context_slot", c.get("historical_slot"))] if v is not None})
        headers = [read("header_"+str(slot), "getBlock", block_params(slot)) for slot in slots]
        queue(session_root, config, sample, headers, factory=factory)
        # The recheck of a finalized header only needs its time; getBlockTime has twice the public window.
        fresh = [read("reheader_"+str(slot), "getBlockTime", [slot]) for slot in slots]
        fresh.append(read("renetwork", "getGenesisHash", []))
        queue(session_root, config, sample, fresh, owner="final", factory=factory)
        session.mark("collection", {"sample": sample, "status": "schedule_finished"})
        packets = _packets(session, sample)
        try:
            consistency(packets, session.meta["target"])
            captured_headers = {p["request"]["params"][0]: _checked(p)["result"] for p in packets
                                if p["status"] == "ok" and p["request"]["method"] == "getBlock"}
            cache = ObservationCache(Path(session_root)/"observations", investigation_id=session.meta["investigation_id"],
                        namespace=identity["provider_namespace"], target=session.meta["target"], synthetic=session.meta["synthetic"])
            for packet in packets:
                if packet["status"] != "ok":
                    continue
                checked = _checked(packet)
                slot = checked.get("context_slot", checked.get("historical_slot"))
                if slot is None or slot not in captured_headers:
                    continue
                name = packet["request"]["id"]
                if not (cache.root/(name+".json")).exists():
                    cache.capture(name, packet, captured_at=packet["completed_at"], block=captured_headers[slot])
        except (ValueError, KeyError, TypeError, IndexError):
            session.mark("cache", {"sample": sample, "status": "consistency_unresolved"})
    finally:
        session.close()


def summarize(session_root, sample):
    session = Session(session_root)
    try:
        packets = _packets(session, sample)
        manifest_path = Path(session_root)/"sample-plans"/(sample+".json")
        plan = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        gaps, samples = [], []
        by_name = {p["request"]["id"].rsplit("_", 1)[0][len(sample)+1:]: p for p in packets}
        try:
            consistency(packets, session.meta["target"])
            need(plan is not None, "sample plan missing")
            need(all(p["namespace"] == plan["provider_namespace"] for p in packets), "provider namespace changed within sample")
            for first, last in [("network", "renetwork")]+[("header_"+str(slot), "reheader_"+str(slot))
                    for slot in sorted({v for p in packets if p["status"] == "ok" for c in [_checked(p)]
                        for v in [c.get("context_slot", c.get("historical_slot"))] if v is not None})]:
                a, b = by_name.get(first, {}), by_name.get(last, {})
                need(a.get("status") == b.get("status") == "ok", "fresh network/header check missing")
                need(b["started_at"] > a["completed_at"] and a["attempt_id"] != b["attempt_id"], "recheck is not later independent request")
                need(_block_time(a) == _block_time(b), "recheck changed")
            current_slots = {_checked(p)["context_slot"] for p in packets if p["status"] == "ok" and "context_slot" in _checked(p)}
            for slot in current_slots:
                block_time = by_name["header_"+str(slot)]["response"]["result"]["blockTime"]
                need(block_time is not None and -60 <= time.time()-block_time <= 300, "current sample header is stale or undated")
            critical_initial, critical_final = [], {}
            for row in plan["reads"]:
                if row["critical"]:
                    p = by_name.get(row["name"], {})
                    need(p.get("status") == "ok", "critical initial account missing")
                    checked = _checked(p)
                    values = checked["result"]["value"] if row["method"] == "getMultipleAccounts" else [checked["result"]["value"]]
                    critical_initial.extend((a, v, p) for a, v in zip(checked["addresses"], values))
            for name, p in by_name.items():
                if name.startswith("critical_") and p["status"] == "ok":
                    checked = _checked(p)
                    critical_final.update({a: (v, p) for a, v in zip(checked["addresses"], checked["result"]["value"])})
            for address, value, original in critical_initial:
                need(address in critical_final and value is not None, "critical account missing")
                fresh, packet = critical_final[address]
                need(packet["started_at"] > original["completed_at"], "critical recheck is not later")
                need(fresh == value, "critical account changed between samples")
            for p in packets:
                if p["status"] == "ok":
                    checked = _checked(p)
                    if "context_slot" in checked or "historical_slot" in checked:
                        samples.append({"observation_id": p["request"]["id"], "context_slot": checked.get("context_slot"),
                            "historical_slot": checked.get("historical_slot"), "addresses": checked.get("addresses", []),
                            "address_indices": checked.get("address_indices", {}), "missing_indices": checked.get("missing_indices", [])})
            for row in plan["reads"]:
                if by_name.get(row["name"], {}).get("status") != "ok":
                    gaps.append({"read": row["name"], "reason": "read_incomplete"})
            for path in (Path(session_root)/"queue-plans").glob(sample+"_*.json"):
                queue_plan = json.loads(path.read_text())
                if queue_plan["sample_id"] == sample:
                    for row in queue_plan["reads"]:
                        if by_name.get(row["name"], {}).get("status") != "ok" and not any(g.get("read") == row["name"] for g in gaps):
                            gaps.append({"read": row["name"], "reason": "read_incomplete"})
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            gaps.append({"reason": "sample_consistency_unresolved", "detail": str(exc) if isinstance(exc, ValueError) else type(exc).__name__})
        pending = [a["request_id"] for a in session.observations() if a["request_id"].startswith(sample+"_") and a["status"] == "started"]
        if pending:
            gaps.append({"reason": "unfinished_attempts", "requests": pending})
        return {"schema_version": 2, "profile": "solana-evidence-v2", "collector_version": "2.1.0",
                "target": session.meta["target"], "investigation_id": session.meta["investigation_id"],
                "synthetic": session.meta["synthetic"], "sample_id": sample, "observations": packets,
                "samples": samples, "collection_status": "partial" if gaps else "captured",
                "research_status": "unjudged", "gaps": gaps, "session": session.status()}
    finally:
        session.close()


def worker(root, config, sample, rows, expand_largest):
    collect(config["session"], root, config, sample, rows, expand_largest=expand_largest)


def run_bounded(out, config, target, *, rows=None, sample="baseline", seconds=55,
                largest=True, worker_target=worker):
    target = target_identity(target)
    need(type(seconds) in (int, float) and 0 < seconds <= 55, "invalid bounded collection duration")
    label(sample)
    rows = mint_baseline(target["mint"], largest=largest) if rows is None else rows
    validate_plan(rows)
    session = Session(config["session"], target=target)
    try:
        need(session.status()["status"] == "active", "session finalized")
        need(worker_target is worker or session.meta["synthetic"], "test worker requires synthetic session")
        duration = min(seconds, session.remaining_seconds())
        need(duration > 0, "collection deadline reached")
        out = Path(out)
        out.mkdir(parents=True, exist_ok=False)
        write_new(out/"invocation.json", {"sample_id": sample, "reads": rows, "target": target,
                                        "investigation_id": session.meta["investigation_id"]})
    finally:
        session.close()
    start = time.monotonic()
    process = multiprocessing.get_context("spawn").Process(target=worker_target,
                args=(str(out), config, sample, rows, largest))
    process.start()
    try:
        process.join(max(0, duration-(time.monotonic()-start)))
        timed_out = process.is_alive()
    finally:
        if process.is_alive():
            process.terminate()
            process.join(.5)
            if process.is_alive():
                process.kill()
                process.join(.5)
    try:
        packet = summarize(config["session"], sample)
    except (ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        session = Session(config["session"], target=target)
        try:
            packet = {"schema_version": 2, "profile": "solana-evidence-v2", "target": target,
                "investigation_id": session.meta["investigation_id"], "sample_id": sample,
                "synthetic": session.meta["synthetic"], "collection_status": "partial",
                "research_status": "unjudged", "session": session.status(), "observations": [], "samples": [],
                "gaps": [{"reason": "summary_failure", "error_category": type(exc).__name__}]}
        finally:
            session.close()
    packet.update(timed_out=timed_out, worker_exit_code=process.exitcode,
                  elapsed_seconds=round(time.monotonic()-start, 3))
    if timed_out or process.exitcode != 0:
        packet["collection_status"] = "partial"
        packet["gaps"].append({"reason": "worker_timeout" if timed_out else "worker_exit"})
    write_new(out/"summary.json", packet)
    return packet
