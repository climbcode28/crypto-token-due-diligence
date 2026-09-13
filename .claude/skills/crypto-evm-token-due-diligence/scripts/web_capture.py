#!/usr/bin/env python3
"""Bounded parallel HTTP capture with provenance. Raw bytes are evidence; summaries are not.

No credentials are sent, no cookies are kept, redirects are followed at most three times
within public https/http destinations and recorded. A 403, JavaScript shell or timeout is a recorded access
gap with the URL and time, never an inference about the token.
"""
import argparse
import http.client
import ipaddress
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from backend_common import BROWSER_USER_AGENT, address, integer, need, sha, stamp
from rpc_collect import NoRedirect, seconds

USER_AGENT = BROWSER_USER_AGENT
TRANSIENT_FAILURES = ("dns_resolution", "timeout", "transport_error", "throttled", "server_error")
PRESETS = {
    "dexscreener": lambda a: [{"id": "dexscreener-pairs", "url": f"https://api.dexscreener.com/token-pairs/v1/{a['slug']}/{a['address']}",
                               "purpose": "Exact-address pool discovery"}],
    "sourcify": lambda a: [{"id": "sourcify-intake", "url": f"https://sourcify.dev/server/v2/contract/{a['chain_id']}/{a['address']}?fields=abi,compilation,runtimeBytecode.onchainBytecode",
                            "purpose": "Verified source/ABI intake"}],
    "blockscout": lambda a: [{"id": "blockscout-address", "url": f"{a['base']}/api/v2/addresses/{a['address']}", "purpose": "Creation transaction, creator, proxy flags"},
                             {"id": "blockscout-token", "url": f"{a['base']}/api/v2/tokens/{a['address']}", "purpose": "Holder count and supply"},
                             {"id": "blockscout-holders", "url": f"{a['base']}/api/v2/tokens/{a['address']}/holders", "purpose": "Top holders page one"}],
    "github-tree": lambda a: [{"id": "github-repo", "url": f"https://api.github.com/repos/{a['repo']}", "purpose": "Repository metadata"},
                              {"id": "github-tree", "url": f"https://api.github.com/repos/{a['repo']}/git/trees/{a.get('ref', 'HEAD')}?recursive=1", "purpose": "Repository tree"},
                              {"id": "github-commits", "url": f"https://api.github.com/repos/{a['repo']}/commits?per_page=30", "purpose": "Recent commits"}],
    "rhscan-token": lambda a: [{"id": "rhscan-token", "url": f"https://rh-scan.com/token/{a['address']}", "purpose": "Explorer token page"}],
    "robinscan-token": lambda a: [{"id": "robinscan-token", "url": f"https://robinscan.io/token/{a['address']}", "purpose": "Explorer token page"}],
}


SECRET_QUERY = re.compile(r"key|token|secret|sig|auth|password|passwd|apikey|api_key", re.I)


class PrivateDestination(ValueError):
    """A web source or connected peer is outside the public Internet."""


def require_public_address(value):
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast:
        raise PrivateDestination("public destination required")


def clean_url(url):
    """Check every initial/redirect URL; the connection also checks its actual peer."""
    need(isinstance(url, str) and not any(ord(c) <= 32 or ord(c) == 127 for c in url), "invalid URL")
    parts = urllib.parse.urlsplit(url)
    need(parts.scheme in ("https", "http") and bool(parts.hostname), "unsupported URL")
    need(parts.port is None or 1 <= parts.port <= 65535, "invalid URL port")
    need(not parts.username and not parts.password, "URL carries credentials")
    need(not any(SECRET_QUERY.search(k) for k, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)),
         "URL carries a credential-like query parameter; captures must not embed keys")
    host = parts.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise PrivateDestination("public destination required")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # DNS names are checked against the connected peer, not a separate lookup.
    else:
        require_public_address(host)
    return url


class PublicHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        super().connect()
        try:
            require_public_address(self.sock.getpeername()[0])
        except ValueError:
            self.close()
            raise


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        super().connect()
        try:
            require_public_address(self.sock.getpeername()[0])
        except ValueError:
            self.close()
            raise


class PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(PublicHTTPConnection, req)


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(PublicHTTPSConnection, req, context=self._context)


def public_opener():
    # Anonymous captures must not inherit proxies, credentials or cookie state.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                      PublicHTTPHandler(), PublicHTTPSHandler())


def public_url(url):
    """Do not persist userinfo, fragments or credential-like query values, including redirects."""
    try:
        parts = urllib.parse.urlsplit(url)
        netloc = parts.netloc.rsplit("@", 1)[-1]
        query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
                                       if not SECRET_QUERY.search(k)])
        return parts._replace(netloc=netloc, query=query, fragment="").geturl()
    except (ValueError, TypeError):
        return None


def prepare_budget(out, count, deadline):
    """Persist an already-charged lane allowance; retries and redirects share it across calls."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "web-budget.sqlite"
    integer(count, "prepaid web requests", 0)
    with path.open("xb"):
        pass
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE budget(singleton INTEGER PRIMARY KEY, remaining INTEGER NOT NULL, deadline REAL NOT NULL)")
        db.execute("INSERT INTO budget VALUES(1,?,?)", (count, deadline))
    return path


def prepaid_acquire(path):
    with closing(sqlite3.connect(str(Path(path).resolve().as_uri()) + "?mode=rw", uri=True, timeout=2)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT remaining,deadline FROM budget WHERE singleton=1").fetchone()
        if row is None or row[0] <= 0 or time.time() >= row[1]:
            return False
        db.execute("UPDATE budget SET remaining=remaining-1 WHERE singleton=1")
    return True


def session_acquire(path, operation):
    # Each worker owns its connection; Investigation.acquire serializes budget mutations.
    from investigation import Investigation
    session = Investigation(path)
    try:
        return session.acquire(operation)
    finally:
        session.close()


def capture_one(item, out, timeout=20, max_bytes=16_000_000, opener=None, retries=1, acquire=None, deadline=None):
    """Capture one URL; a transient transport failure (DNS, timeout, 429, 5xx, connection) is retried once."""
    record = None
    started = time.monotonic()
    deadline = min(deadline, started + timeout) if deadline is not None else started + timeout
    attempts = 0
    for attempt in range(retries + 1):
        record = capture_attempt(item, out, timeout, max_bytes, opener, write=False, acquire=acquire, deadline=deadline)
        attempts += record["requests_used"]
        if record.get("failure_category") not in TRANSIENT_FAILURES or attempt == retries or time.monotonic() + 0.75 >= deadline:
            break
        time.sleep(0.75 * (attempt + 1))
    record["retries"] = attempt
    record["requests_used"] = attempts
    record["duration_seconds"] = round(time.monotonic() - started, 3)
    if record.get("raw") and record.get("_body"):
        (out / record["raw"]).write_bytes(record["_body"])
    record.pop("_body", None)
    (out / (record["id"] + ".json")).write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return record


def capture_attempt(item, out, timeout=20, max_bytes=16_000_000, opener=None, write=True, acquire=None, deadline=None):
    url = item["url"]
    record = {"id": item["id"], "url": url, "final_url": url, "purpose": item.get("purpose"), "address": item.get("address"),
              "http_status": None, "bytes": 0, "sha256": None, "content_type": None, "captured_at_utc": stamp(),
              "duration_seconds": None, "failure_category": None, "redirects": [], "raw": item["id"] + ".raw",
              "host": None, "requests_used": 0}
    started = time.monotonic()
    deadline = min(deadline, started + timeout) if deadline is not None else started + timeout
    client = opener or public_opener()
    body = b""
    try:
        clean_url(url)
        record["host"] = urllib.parse.urlsplit(url).hostname
        for _ in range(4):
            clean_url(record["final_url"])
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                record["failure_category"] = "timeout"
                break
            if acquire is not None and not acquire():
                record["failure_category"] = "budget_exhausted"
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                record["failure_category"] = "timeout"
                break
            request = urllib.request.Request(record["final_url"], method="GET",
                                             headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9, */*;q=0.5",
                                                      "Accept-Language": "en-US,en;q=0.8"})
            try:
                record["requests_used"] += 1
                with client.open(request, timeout=remaining) as response:
                    record["http_status"] = getattr(response, "status", None)
                    record["content_type"] = response.headers.get("Content-Type")
                    chunks, size = [], 0
                    while size <= max_bytes:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("response deadline reached")
                        chunk = response.read1(min(65536, max_bytes + 1 - size))
                        if time.monotonic() >= deadline:
                            raise TimeoutError("response deadline reached")
                        if not chunk:
                            break
                        chunks.append(chunk)
                        size += len(chunk)
                    need(size <= max_bytes, "response exceeded byte cap")
                    body = b"".join(chunks)
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                    record["redirects"].append(record["final_url"])
                    record["final_url"] = urllib.parse.urljoin(record["final_url"], exc.headers["Location"])
                    exc.close()
                    continue
                record["http_status"] = exc.code
                record["failure_category"] = {401: "authentication", 403: "access_denied", 404: "not_found", 429: "throttled"}.get(
                    exc.code, "server_error" if 500 <= exc.code < 600 else "http_error")
                try:
                    chunks, size = [], 0
                    while size < max_bytes and time.monotonic() < deadline:
                        chunk = exc.read1(min(65536, max_bytes - size))
                        if time.monotonic() >= deadline:
                            raise TimeoutError("error response deadline reached")
                        if not chunk:
                            break
                        chunks.append(chunk)
                        size += len(chunk)
                    body = b"".join(chunks)
                except (OSError, ValueError, http.client.HTTPException):
                    body = b""
                finally:
                    exc.close()
                break
        else:
            record["failure_category"] = "too_many_redirects"
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as exc:
        if isinstance(exc, PrivateDestination):
            record["failure_category"] = "refused_private_url"
        elif isinstance(exc, ValueError) and "credential" in str(exc):
            record["failure_category"] = "refused_credential_url"
        elif isinstance(exc, ValueError):
            record["failure_category"] = "invalid_response_or_url"
        else:
            record["failure_category"] = "timeout" if isinstance(exc, TimeoutError) else "dns_resolution" if "gaierror" in type(getattr(exc, "reason", exc)).__name__ else "transport_error"
    record["url"] = public_url(record["url"])
    record["final_url"] = public_url(record["final_url"])
    record["redirects"] = [public_url(value) for value in record["redirects"]]
    record["duration_seconds"] = round(time.monotonic() - started, 3)
    if body:
        if write:
            (out / record["raw"]).write_bytes(body)
        else:
            record["_body"] = body
        record["bytes"], record["sha256"] = len(body), sha(body)
        text = body[:4000].decode("utf-8", "replace").lower()
        if record["http_status"] == 200 and "text/html" in (record["content_type"] or "") and ("<script" in text and "loading" in text or len(body) < 3000):
            record["shell_suspected"] = True
    else:
        record["raw"] = None
    if write:
        (out / (record["id"] + ".json")).write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return record


def capture(items, out, timeout=20, max_bytes=16_000_000, workers=4, session=None, operation="web_capture"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    integer(workers, "workers", 1)
    need(workers <= 4, "at most four concurrent captures")
    timeout = seconds(timeout, "capture timeout")
    integer(max_bytes, "capture byte cap", 1)
    seen = set()
    for item in items:
        need(isinstance(item, dict) and re.fullmatch(r"[A-Za-z0-9_-]{1,60}", str(item.get("id"))) and isinstance(item.get("url"), str), "capture items need id and url")
        need(item["id"] not in seen and not (out / (item["id"] + ".json")).exists(), "duplicate capture id " + item["id"])
        seen.add(item["id"])
        if item.get("address"):
            item["address"] = address(item["address"])
    acquire, deadline = None, None
    if session is not None:
        acquire = lambda: session_acquire(session.path, operation)
        deadline = time.monotonic() + session.remaining_seconds()
    elif (out / "web-budget.sqlite").is_file():
        path = out / "web-budget.sqlite"
        with closing(sqlite3.connect(path)) as db:
            row = db.execute("SELECT deadline FROM budget WHERE singleton=1").fetchone()
        need(row is not None, "prepaid capture budget is incomplete")
        deadline = time.monotonic() + max(0, row[0] - time.time())
        acquire = lambda: prepaid_acquire(path)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(lambda item: capture_one(item, out, timeout, max_bytes, acquire=acquire, deadline=deadline), items))


def register(draft_root, records, lane=None, default_address=None):
    """Register captures as document evidence bound to the draft's current pin."""
    from bundle_assemble import add_artifact, read_draft
    from compose import current_pin
    draft = read_draft(draft_root)
    pin = current_pin(draft)
    registered = []
    for record in records:
        eid = ("doc-" + lane + "-" if lane else "doc-") + record["id"]
        if eid in {e["id"] for e in draft["evidence"]}:
            continue
        out = Path(draft_root).parent / "lanes" / lane if lane else None
        source_dir = Path(record["_dir"]) if "_dir" in record else out
        need(source_dir is not None, "capture directory unknown")
        source_dir = source_dir.resolve()
        raw_name = record.get("raw")
        need(raw_name is None or (isinstance(raw_name, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,60}\.raw", raw_name)), "capture raw file name is not a plain <id>.raw")
        source = (source_dir / raw_name) if raw_name else (source_dir / (record["id"] + ".json"))
        need(source.resolve().parent == source_dir, "capture files must live in the capture directory")
        descriptor = {"id": eid, "kind": "document", "target": dict(draft["target"]), "chain_id": draft["target"]["chain_id"],
                      "address": address(record.get("address") or default_address or draft["target"]["address"]), "pin_id": pin["id"], "tx_hash": None,
                      "captured_at_utc": record["captured_at_utc"], "endpoint_label": re.sub(r"[^A-Za-z0-9_-]", "-", str(record.get("host") or "web"))[:80] or "web",
                      "query": {"operation": "web_capture", "url": record["url"], "final_url": record["final_url"], "http_status": record["http_status"],
                                "capture_mode": "downloaded_response", "source_urls": [record["url"]], "purpose": record.get("purpose")},
                      "decoding_basis": "Raw HTTP response bytes preserved with provenance; attributed source material, not verified onchain fact",
                      "coverage": "Single bounded capture at the recorded retrieval time",
                      "observation_status": "ok" if record["http_status"] == 200 and not record.get("failure_category") else "unavailable"}
        add_artifact(draft_root, source, descriptor)
        registered.append(eid)
    return registered


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True, help="directory for <id>.raw and <id>.json provenance")
    p.add_argument("--urls", type=Path, help="JSON list of {id, url, purpose?, address?}")
    p.add_argument("--url", action="append", default=[], help="ID=URL; repeatable")
    p.add_argument("--preset", choices=sorted(PRESETS))
    p.add_argument("--address")
    p.add_argument("--chain-id", type=int)
    p.add_argument("--slug", help="Dexscreener chain slug for the dexscreener preset")
    p.add_argument("--base", help="explorer base URL for the blockscout preset")
    p.add_argument("--repo", help="owner/name for the github-tree preset")
    p.add_argument("--ref", default="HEAD")
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("--max-bytes", type=int, default=16_000_000)
    p.add_argument("--session", type=Path, help="charge each HTTP attempt, including retries/redirects, to this session")
    p.add_argument("--operation", default="web_capture")
    p.add_argument("--register", type=Path, help="draft directory; register captures as document evidence")
    p.add_argument("--lane", help="lane name used for evidence ids and the lanes/<lane> directory")
    args = p.parse_args()
    session = None
    try:
        items = []
        if args.urls:
            items += json.loads(args.urls.read_text(encoding="utf-8"))
        for spec in args.url:
            need("=" in spec, "--url needs ID=URL")
            item_id, url = spec.split("=", 1)
            items.append({"id": item_id, "url": url})
        if args.preset:
            params = {"address": address(args.address) if args.address else None, "chain_id": args.chain_id, "slug": args.slug,
                      "base": (args.base or "").rstrip("/"), "repo": args.repo, "ref": args.ref}
            need(args.preset != "dexscreener" or (params["slug"] and params["address"]), "dexscreener preset needs --slug and --address")
            need(args.preset != "sourcify" or (params["chain_id"] and params["address"]), "sourcify preset needs --chain-id and --address")
            need(args.preset != "blockscout" or (params["base"] and params["address"]), "blockscout preset needs --base and --address")
            need(args.preset != "github-tree" or params["repo"], "github-tree preset needs --repo owner/name")
            need(args.preset not in ("rhscan-token", "robinscan-token") or params["address"], "explorer preset needs --address")
            items += PRESETS[args.preset](params)
        need(bool(items), "nothing to capture")
        if args.address:
            for item in items:
                item.setdefault("address", args.address)
        if args.session:
            from investigation import Investigation
            session = Investigation(args.session)
        records = capture(items, args.out, args.timeout, args.max_bytes, session=session, operation=args.operation)
        for record in records:
            record["_dir"] = str(args.out)
        result = {"captured": [{k: r.get(k) for k in ("id", "http_status", "bytes", "failure_category", "final_url", "shell_suspected", "requests_used")} for r in records],
                  "out": str(args.out), "requests_used": sum(r["requests_used"] for r in records)}
        if args.register:
            result["registered"] = register(args.register, records, args.lane, args.address)
        print(json.dumps(result, sort_keys=True))
        return 0 if all(r["http_status"] == 200 and not r["failure_category"] for r in records) else 2
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print("Capture failed: " + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__), file=sys.stderr)
        return 2
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
