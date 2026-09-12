#!/usr/bin/env python3
"""Bounded read-only Sourcify v2 lookup. Never submits verification jobs."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from backend_common import address, integer, need, stamp, write_new
from rpc_collect import NoRedirect, seconds

FIELDS = {"intake": "abi,compilation,runtimeBytecode.onchainBytecode",
          "correspondence": "compilation,sources,runtimeBytecode,stdJsonInput,stdJsonOutput"}


def lookup(chain_id, contract_address, out, profile="intake", allow_network=False, timeout=20,
           max_bytes=16_000_000, opener=None, session=None):
    integer(chain_id, "chain ID", 1)
    contract_address = address(contract_address)
    need(profile in FIELDS and allow_network, "lookup requires a supported profile and --allow-network")
    need(session is not None, "source lookup requires an investigation session")
    seconds(timeout, "lookup timeout")
    integer(max_bytes, "response byte limit", 1)
    need(max_bytes <= 16_000_000, "lookup response cap cannot exceed 16 MB")
    need(not Path(out).exists(), "lookup output must be new")
    url = f"https://sourcify.dev/server/v2/contract/{chain_id}/{contract_address}?fields={FIELDS[profile]}"
    result = {"schema_version": 1, "operation": "sourcify_v2_contract_lookup", "access_mode": "public_api",
              "source_urls": [url], "captured_at_utc": stamp(), "status": "unavailable", "http_status": None,
              "bytes": 0, "body": None, "profile": profile}
    start = time.monotonic()
    try:
        if session is not None:
            need(session.acquire("source_lookup", reserve=0), "investigation limit reached")
            timeout = min(timeout, session.remaining_seconds())
        deadline = time.monotonic() + timeout
        client = opener or urllib.request.build_opener(NoRedirect())
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with client.open(request, timeout=timeout) as response:
            result["http_status"] = response.status
            chunks, size = [], 0
            while size <= max_bytes:
                need(time.monotonic() < deadline, "lookup deadline reached")
                chunk = response.read1(min(65536, max_bytes + 1 - size))
                need(time.monotonic() < deadline, "lookup deadline reached")
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            result["bytes"] = size
            need(size <= max_bytes, "lookup byte limit reached")
            result["body"] = json.loads(b"".join(chunks).decode("utf-8"))
        need(isinstance(result["body"], dict) and int(result["body"]["chainId"]) == chain_id
             and address(result["body"]["address"]) == contract_address, "source API identity mismatch")
        result["status"] = "ok"
    except (ValueError, KeyError, TypeError, OSError, urllib.error.URLError) as exc:
        result["failure_category"] = type(exc).__name__
        if isinstance(exc, urllib.error.HTTPError):
            result["http_status"] = exc.code
    result["duration_seconds"] = round(time.monotonic() - start, 6)
    write_new(out, result)
    if result["status"] != "ok":
        from operations import automatic
        automatic(Path(out).parent, "source_lookup", "contract_lookup", "source_unavailable", Path(out).name, access_mode="public_api", feedback_root=session.path.parent)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chain-id", type=int, required=True)
    p.add_argument("--address", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--profile", choices=FIELDS, default="intake")
    p.add_argument("--allow-network", action="store_true")
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("--session", type=Path, required=True)
    args = p.parse_args()
    session = None
    try:
        from investigation import Investigation
        session = Investigation(args.session)
        result = lookup(args.chain_id, args.address, args.out, args.profile, args.allow_network, args.timeout, session=session)
        print(json.dumps({k: result[k] for k in ("status", "http_status", "bytes", "duration_seconds")}))
        return 0 if result["status"] == "ok" else 2
    except (ValueError, OSError) as exc:
        print("Lookup failed: " + type(exc).__name__, file=sys.stderr)
        return 2
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
