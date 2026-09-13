"""Bounded anonymous public HTTPS captures, owned once under the shared session."""
import base64
import http.client
import ipaddress
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from solana_common import need, sha, write_new
from solana_transport import failure_category
from solana_session import Session, LimitError, TRANSIENT, encoded, label, OWNERS
from solana_transport import NoRedirect, BROWSER_USER_AGENT, validate_endpoint, retry_after

SECRET_QUERY = re.compile(r"key|token|secret|sig|auth|password|passwd", re.I)
RATES = {"api.geckoterminal.com": (10, 60), "api.jup.ag": (30, 60),
         "api.dexscreener.com": (300, 60), "transaction-v1.raydium.io": (120, 60),
         "api.github.com": (60, 3600), "dlmm.datapi.meteora.ag": (30, 1)}


def response_backoff(host, code, headers):
    """Use public rate headers without persisting arbitrary response header text."""
    now = time.time()
    until = retry_after(headers, now) if code in (403, 429, 503) else None
    if host == "api.github.com":
        if headers.get("X-RateLimit-Remaining") == "0":
            reset = headers.get("X-RateLimit-Reset", "")
            if isinstance(reset, str) and reset.isascii() and reset.isdigit() and len(reset) <= 10:
                until = max(until or now, int(reset))
        if code in (403, 429) and until is None:
            until = now+60
    return until


def clean_url(url):
    parts = validate_endpoint(url.split("#", 1)[0] if isinstance(url, str) else url)
    need(not any(SECRET_QUERY.search(k) for k, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)), "credential-like URL query refused")
    host = parts.hostname.lower()
    need(host not in ("localhost",) and not host.endswith((".localhost", ".local", ".internal")), "public host required")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    need(address is None or address.is_global, "public IP required")
    netloc = ("["+host+"]" if ":" in host else host)+(":"+str(parts.port) if parts.port not in (None, 443) else "")
    return urllib.parse.urlunsplit(("https", netloc, parts.path or "/", parts.query, ""))


def public_url(url):
    """Refused original URLs are represented by a redacted locator and digest."""
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname or "invalid"
        query = urllib.parse.urlencode([(k, "[REDACTED]" if SECRET_QUERY.search(k) else v)
                                       for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)])
        return urllib.parse.urlunsplit((parts.scheme, host, parts.path, query, ""))
    except (ValueError, TypeError):
        return "[INVALID_URL]"


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        super().connect()
        # Check the actual connected peer before sending HTTP headers. No proxy,
        # cookies or auth headers are used; this also rejects DNS rebinding to LANs.
        if not ipaddress.ip_address(self.sock.getpeername()[0]).is_global:
            self.close()
            raise ValueError("non-public connected peer refused")


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(PublicHTTPSConnection, req, context=self._context)


DIMENSIONS = ("token_controls", "canonical_lp_principal_custody", "side_pool_removal_risk", "sellability_exit_depth",
              "current_concentration", "historical_launch_integrity", "admin_treasury_reward_custody",
              "reward_accounting_liveness", "utility_redemption_rights", "external_dependencies", "development_disclosure")


def register_urls(session, urls, *, owners=None, dimensions=None, cap=12):
    """Preserve every intake position, dedupe normalized URLs and assign one owner and, optionally, one coverage dimension."""
    need(isinstance(urls, list) and all(isinstance(u, str) for u in urls), "URL list required")
    need(type(cap) is int and 0 <= cap <= 40, "invalid capture-source cap")
    owners = owners or {}
    dimensions = dimensions or {}
    need(all(d in DIMENSIONS for d in dimensions.values()), "unknown capture dimension")
    entries = []
    with session.transaction():
        session.db.execute("CREATE TABLE IF NOT EXISTS web_sources(id TEXT PRIMARY KEY,url TEXT NOT NULL,owner TEXT NOT NULL,status TEXT NOT NULL,original_sha256 TEXT NOT NULL)")
        session.db.execute("CREATE TABLE IF NOT EXISTS web_intake(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL,original_sha256 TEXT NOT NULL)")
        session.db.execute("CREATE TABLE IF NOT EXISTS web_dimensions(source_id TEXT PRIMARY KEY,dimension TEXT NOT NULL)")
        for url in urls:
            digest = sha(url.encode())
            try:
                safe, status = clean_url(url), "pending"
            except ValueError:
                safe, status = public_url(url), "refused_url"
            source_id = sha((safe if status == "pending" else digest).encode())
            owner = owners.get(url, "ordinary")
            need(owner in OWNERS, "invalid capture owner")
            existing = session.db.execute("SELECT * FROM web_sources WHERE id=?", (source_id,)).fetchone()
            if existing:
                need(existing["owner"] == owner, "URL capture already assigned to another owner")
                status = existing["status"]
            else:
                selected = session.db.execute("SELECT count(*) FROM web_sources WHERE status='pending'").fetchone()[0]
                if status == "pending" and selected >= cap:
                    status = "unattempted_cap"
                session.db.execute("INSERT INTO web_sources VALUES(?,?,?,?,?)", (source_id, safe, owner, status, digest))
                if url in dimensions:
                    # The declared coverage surface travels with the source so every dimension can evidence an attempt.
                    session.db.execute("INSERT OR IGNORE INTO web_dimensions VALUES(?,?)", (source_id, dimensions[url]))
            session.db.execute("INSERT INTO web_intake(source_id,original_sha256) VALUES(?,?)", (source_id, digest))
            entries.append({"source_id": source_id, "url": safe, "owner": owner, "status": status, "original_sha256": digest,
                            "dimension": source_dimension(session, source_id)})
    return entries


def _body(response, limit, deadline):
    chunks, size = [], 0
    status = "ok"
    while size < limit:
        if time.monotonic() >= deadline:
            status = "timeout"
            break
        try:
            chunk = response.read1(min(65536, limit-size))
        except (OSError, http.client.HTTPException) as exc:
            status = "timeout" if isinstance(exc, TimeoutError) else "transport_failure"
            break
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if time.monotonic() >= deadline:
            status = "timeout"
            break
    if size == limit and status == "ok":
        status = "response_limit"
    return b"".join(chunks), status


def source_dimension(session, source_id):
    if not session.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_dimensions'").fetchone():
        return None
    row = session.db.execute("SELECT dimension FROM web_dimensions WHERE source_id=?", (source_id,)).fetchone()
    return row[0] if row else None


def capture_one(session_root, source_id, *, owner="ordinary", opener=None, max_bytes=1_000_000):
    label(source_id)
    need(len(source_id) == 64, "registered source identity required")
    need(type(max_bytes) is int and 0 < max_bytes <= 16_000_000, "invalid capture byte cap")
    session = Session(session_root)
    try:
        source = session.db.execute("SELECT * FROM web_sources WHERE id=?", (source_id,)).fetchone()
        need(source is not None and source["owner"] == owner, "capture owner/source mismatch")
        if source["status"] != "pending":
            return {**dict(source), "status": source["status"], "attempts": [], "raw": None}
        current, history, retried = source["url"], [], False
        opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), PublicHTTPSHandler())
        for hop in range(4):
            current = clean_url(current)
            parts = urllib.parse.urlsplit(current)
            namespace = sha((parts.scheme+"://"+parts.netloc).encode())
            family = "web_"+source_id[:48]+"_"+str(hop)
            for attempt in range(2):
                request_id = family+"_"+str(attempt)
                previous = next((r for r in session.observations() if r["request_id"] == request_id), None)
                if previous and previous["response"]:
                    packet = json.loads(previous["response"])
                    need(packet["url"] == current and packet["owner"] == owner, "capture resume mismatch")
                elif previous:
                    return {"id": source_id, "status": "unfinished_attempt", "attempts": [p["request_id"] for p in history], "raw": None}
                else:
                    try:
                        ticket = session.acquire(request_id, family, "GET", namespace, owner=owner,
                            max_response_bytes=max_bytes, transport_kind="web", retry=attempt == 1,
                            rate_limit=RATES.get(parts.hostname))
                    except LimitError as exc:
                        return {"id": source_id, "status": "budget_denied", "reason": str(exc), "attempts": [p["request_id"] for p in history], "raw": None}
                    packet = {"url": current, "owner": owner, "request_id": request_id,
                              "status": "transport_failure", "http_status": None, "body_base64": "", "location": None}
                    remaining = min(15, session.remaining_seconds(owner), ticket["deadline"]-time.time())
                    body = b""
                    response = None
                    try:
                        if remaining <= 0:
                            packet["status"] = "not_sent_deadline"
                        else:
                            deadline = time.monotonic()+remaining
                            request = urllib.request.Request(current, method="GET", headers={"User-Agent": BROWSER_USER_AGENT,
                                                                "Accept": "application/json, text/html;q=0.9, */*;q=0.5"})
                            try:
                                response = opener.open(request, timeout=remaining)
                            except urllib.error.HTTPError as exc:
                                response = exc
                            packet["http_status"] = response.code if isinstance(response, urllib.error.HTTPError) else response.status
                            packet["content_type"] = response.headers.get("Content-Type", "")
                            code = packet["http_status"]
                            until = response_backoff(parts.hostname, code, response.headers)
                            if until is not None:
                                packet["retry_after"] = until
                                session.defer_source(namespace, until)
                            if code in (301, 302, 303, 307, 308):
                                location = urllib.parse.urljoin(current, response.headers.get("Location", ""))
                                try:
                                    packet["location"] = clean_url(location)
                                    packet["status"] = "redirect"
                                except ValueError:
                                    packet["status"] = "refused_redirect"
                            else:
                                body, status = _body(response, max_bytes, deadline)
                                packet["status"] = status if status != "ok" else "ok" if code == 200 else "http_"+str(code)
                    except (OSError, ValueError, http.client.HTTPException) as exc:
                        packet["status"] = "timeout" if isinstance(exc, TimeoutError) else "transport_failure" if isinstance(exc, OSError) else "invalid_response_or_url"
                        if isinstance(exc, (OSError, http.client.HTTPException)):
                            packet["failure"] = failure_category(exc)
                    finally:
                        if response is not None:
                            response.close()
                    packet.update(body_base64=base64.b64encode(body).decode(), bytes=len(body), sha256=sha(body), captured_at=time.time())
                    packet["status"] = session.finish(ticket["id"], packet["status"], len(body), packet)
                history.append(packet)
                if packet["status"] in TRANSIENT and not retried and attempt == 0:
                    retried = True
                    delay = max(0, packet.get("retry_after", time.time())-time.time())
                    if delay > min(1, session.remaining_seconds(owner)):
                        # Keep the durable failure and backoff; a later bounded batch
                        # may resume once eligible, without resetting its retry grant.
                        break
                    if delay:
                        time.sleep(delay)
                    continue
                break
            if packet["status"] == "redirect":
                current = packet["location"]
                continue
            break
        else:
            packet = {**packet, "status": "redirect_limit"}
        capture_id = packet["request_id"]
        result = {"id": capture_id, "source_id": source_id, "url": source["url"], "final_url": packet["url"], "owner": owner,
                  "dimension": source_dimension(session, source_id),
                  "status": packet["status"], "attempts": [p["request_id"] for p in history], "failure": packet.get("failure"),
                  "http_status": packet.get("http_status"), "content_type": packet.get("content_type"),
                  "captured_at": packet.get("captured_at"), "sha256": packet.get("sha256"),
                  "bytes": packet.get("bytes", 0), "raw": None}
        body = base64.b64decode(packet.get("body_base64", ""), validate=True)
        folder = Path(session_root)/"web-captures"
        folder.mkdir(exist_ok=True)
        raw_path = folder/(capture_id+".raw")
        if body:
            if not raw_path.exists():
                with raw_path.open("xb") as handle:
                    handle.write(body)
            need(raw_path.read_bytes() == body, "capture raw bytes changed")
            result["raw"] = str(raw_path.relative_to(session_root))
            text = body[:4000].decode("utf-8", "replace").lower()
            result["shell_suspected"] = result["status"] == "ok" and "text/html" in (result["content_type"] or "") and (len(body) < 3000 or "<script" in text and "loading" in text)
        path = folder/(capture_id+".json")
        if not path.exists():
            write_new(path, result)
        else:
            need(json.loads(path.read_text()) == result, "capture result changed")
        return result
    finally:
        session.close()


def capture(session_root, source_ids, *, owner="ordinary", opener_factory=None):
    need(isinstance(source_ids, list) and len(source_ids) <= 40, "bounded capture batch required")
    source_ids = list(dict.fromkeys(source_ids))
    # Two workers also respect per-origin concurrency when every URL shares a host.
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(lambda source: capture_one(session_root, source, owner=owner,
            opener=opener_factory() if opener_factory else None), source_ids))
