#!/usr/bin/env python3
"""Bounded chain/head discovery and token intake. No provider guessing or writes on import."""
import argparse
import json
import sys
import time
from pathlib import Path

from backend_common import Cache, address, integer, need, quantity, read_json, sha, stamp, write_new
from evm_decode import classify_clone
from rpc_collect import Collector, HttpTransport, configured_transport, provider_availability, seconds
from validate_bundle import METADATA


class FixtureTransport:
    synthetic = True

    def __init__(self, path):
        obj = read_json(Path(path))
        need(obj["schema_version"] == 1 and obj["synthetic"] is True, "explicit synthetic RPC fixture required")
        self.namespace = "synthetic-fixture-" + sha(Path(path).read_bytes())
        self.responses = obj["responses"]

    def __call__(self, request):
        rows = [r for r in self.responses if r["method"] == request["method"] and r["params"] == request["params"]]
        need(len(rows) == 1, "synthetic fixture lacks an exact unique request")
        return {**rows[0]["response"], "jsonrpc": "2.0", "id": request["id"]}


def bootstrap(out, target, cache, transport, endpoint_label="research-rpc", max_requests=20, timeout=120, session=None):
    target = {"chain_id": integer(target["chain_id"], "chain ID", 1), "address": address(target["address"])}
    integer(max_requests, "max requests", 10)
    seconds(timeout, "bootstrap timeout")
    need(transport.synthetic or session is not None, "live bootstrap requires an investigation session")
    if session is not None:
        session.ensure(10)
        timeout = min(timeout, session.remaining_seconds())
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    discovery = Collector(out / "discovery", cache, transport, endpoint_label, max_requests=max_requests, timeout=timeout, session=session)
    discovery.root.mkdir()
    discovery.target = target
    discovery.deadline = time.monotonic() + timeout
    if isinstance(transport, HttpTransport):
        transport.deadline = discovery.deadline
    result = {"schema_version": 1, "synthetic": transport.synthetic, "target": target,
              "status": "blocked", "started_at_utc": stamp(), "collection": None}
    try:
        chain = discovery.request("chain", "eth_chainId", [], cached=False)
        need(chain is not None and quantity(chain) == target["chain_id"], "bootstrap chain conflict/unavailable")
        head = discovery.request("head", "eth_blockNumber", [], cached=False)
        number = quantity(head)
        plan = {"schema_version": 1, "target": target, "pins": [{"id": "current", "number": number}],
                "queries": [{"id": "runtime", "pin_id": "current", "method": "eth_getCode", "params": [target["address"]]},
                            *[{"id": "metadata-" + field, "pin_id": "current", "method": "eth_call",
                               "params": [{"to": target["address"], "data": selector}]} for field, selector in METADATA.items()]]}
        write_new(out / "plan.json", plan)
        remaining = discovery.deadline - time.monotonic()
        need(remaining > 0, "bootstrap deadline reached")
        collector = Collector(out / "collection", cache, transport, endpoint_label,
                              max_requests=max_requests - discovery.stats["network_attempts"], timeout=remaining, session=session)
        collection = collector.collect(plan)
        result.update(status=collection["status"], collection="collection", pin_number=number)
        runtime = next((e for e in collection["evidence"] if e["id"] == "runtime"), None)
        if runtime and runtime["observation_status"] == "ok":
            code = read_json(out / "collection" / runtime["artifact"])["response"]["result"]
            result["clone"] = classify_clone(code)
            if code == "0x":
                result.update(status="blocked", reason="target_has_no_code_at_pin")
            implementation = result["clone"]["implementation"]
            if implementation:
                followup = {"schema_version": 1, "target": target, "pins": plan["pins"], "queries": [
                    {"id": "implementation-runtime", "pin_id": "current", "method": "eth_getCode", "params": [implementation]}]}
                write_new(out / "implementation-plan.json", followup)
        result["network_attempts"] = discovery.stats["network_attempts"] + collection["statistics"]["network_attempts"]
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result.update(reason=type(exc).__name__, network_attempts=discovery.stats["network_attempts"])
    result["discovery_evidence"] = [dict(e, artifact="discovery/" + e["artifact"]) for e in discovery.evidence]
    result["coverage_gaps"] = discovery.gaps
    write_new(out / "bootstrap.json", result)
    if result["status"] != "complete":
        from operations import automatic
        automatic(out, "bootstrap", "intake", "incomplete_intake", "bootstrap.json", feedback_root=session.path.parent if session else None)
    return result


def main():
    from rpc_collect import add_provider_arguments
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chain-id", type=int, required=True)
    p.add_argument("--address", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--session", type=Path, required=True, help="shared investigation request/deadline budget")
    p.add_argument("--max-requests", type=int, default=20)
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--fixture", type=Path)
    p.add_argument("--allow-synthetic", action="store_true")
    add_provider_arguments(p)
    args = p.parse_args()
    cache = session = None
    try:
        target = {"chain_id": integer(args.chain_id, "chain ID", 1), "address": address(args.address)}
        integer(args.max_requests, "max requests", 10)
        seconds(args.timeout, "bootstrap timeout")
        from investigation import Investigation
        session = Investigation(args.session)
        session.ensure(10)
        if args.fixture:
            need(args.allow_synthetic, "fixture requires --allow-synthetic")
            transport = FixtureTransport(args.fixture)
        else:
            route = provider_availability(args)
            if route["status"] != "ready":
                print(json.dumps(route))
                return 3
            transport = configured_transport(args)
        cache = Cache(args.cache)
        result = bootstrap(args.out, target, cache, transport, args.endpoint_label, args.max_requests, args.timeout, session)
        print(json.dumps({k: result[k] for k in ("status", "network_attempts", "synthetic")}))
        return 0 if result["status"] == "complete" else 2
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("Bootstrap failed: " + type(exc).__name__, file=sys.stderr)
        return 2
    finally:
        if cache:
            cache.close()
        if session:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
