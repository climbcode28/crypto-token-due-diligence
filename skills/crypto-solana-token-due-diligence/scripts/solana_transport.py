"""Solana-local bounded HTTP/provider primitives; see runtime-provenance.json.

No imports from EVM, no network at import/preflight. Invocation flags are not host
permissions and never authorize paid access by themselves.
"""
import errno
import http.client
import json
import math
import os
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

from solana_common import need, sha

BROWSER_USER_AGENT = "SolanaDiligence/2.0 (read-only public research)"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def invalid_constant(value):
    raise ValueError("non-finite JSON number")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def validate_endpoint(url):
    need(isinstance(url, str) and not any(ord(c) <= 32 or ord(c) == 127 for c in url), "invalid endpoint")
    parts = urllib.parse.urlsplit(url)
    need(parts.scheme == "https" and bool(parts.hostname) and not parts.username and not parts.password and not parts.fragment,
         "RPC URL must be HTTPS without userinfo or fragment")
    need(parts.port is None or 1 <= parts.port <= 65535, "invalid RPC port")
    return parts


def reject_credential_urls(question, urls):
    """Validate intake before persistence; preserve valid original asks and links."""
    candidates = list(urls)+re.findall(r"https?://[^\s<>]+", question)
    secret_query = re.compile(r"key|token|secret|sig|auth|password|passwd", re.I)
    for url in candidates:
        need(isinstance(url, str), "URL intake entries must be strings")
        try:
            parts = urllib.parse.urlsplit(url)
        except ValueError:
            continue  # Invalid public locators are retained as unattempted intake.
        need(not parts.username and not parts.password, "credential-bearing intake URL refused before persistence")
        pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        pairs += urllib.parse.parse_qsl(parts.fragment, keep_blank_values=True)
        need(not any(secret_query.search(k) for k, _ in pairs), "credential-like intake URL refused before persistence")


def retry_after(headers, now=None):
    """Return an absolute provider backoff without persisting header text."""
    now = time.time() if now is None else now
    value = headers.get("Retry-After") if headers else None
    if value is None:
        return None
    try:
        if re.fullmatch(r"[0-9]{1,10}", value.strip()):
            return now+int(value)
        parsed = parsedate_to_datetime(value)
        return max(now, parsed.timestamp()) if parsed.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def seconds(value, name):
    need(type(value) in (float, int) and math.isfinite(value) and value > 0,
         name + " must be positive and finite")
    return float(value)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class HttpTransport:
    synthetic = False

    def __init__(self, url, headers, timeout=20, max_bytes=16_000_000):
        validate_endpoint(url)
        need(isinstance(headers, dict) and all(isinstance(k, str) and re.fullmatch(r"[A-Za-z0-9-]+", k) and isinstance(v, str) and all(32 <= ord(c) <= 126 for c in v) for k, v in headers.items()), "invalid headers")
        need(type(max_bytes) is int and 0 < max_bytes <= 16_000_000, "invalid response byte limit")
        self.url, self.headers = url, dict(headers)
        self.namespace = sha(canonical({"url": url, "headers": headers}))
        self.timeout, self.max_bytes = seconds(timeout, "request timeout"), max_bytes
        self.deadline = None
        self.local = threading.local()
        # No inherited environment proxy: RPC traffic goes only to the validated endpoint.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        parts = urllib.parse.urlsplit(url)
        self.secrets = [url, *headers.values()]
        self.secrets += [v.split(" ", 1)[1] for v in headers.values() if " " in v]
        self.secrets += [x for x in parts.path.split("/") if len(x) >= 16]
        self.secrets += [v for k, v in urllib.parse.parse_qsl(parts.query) if k != "network"]
        self.last_redacted = False

    @property
    def last_redacted(self):
        return getattr(self.local, "redacted", False)

    @last_redacted.setter
    def last_redacted(self, value):
        self.local.redacted = value

    def redact(self, value):
        if isinstance(value, str):
            for secret in sorted(set(self.secrets), key=len, reverse=True):
                if secret and secret in value:
                    self.last_redacted = True
                    value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, list):
            return [self.redact(x) for x in value]
        if isinstance(value, dict):
            return {self.redact(k): self.redact(v) for k, v in value.items()}
        return value

    def request_headers(self):
        """Configured auth headers win; the browser-like agent avoids Cloudflare's generic-client block (error 1010)."""
        return {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": BROWSER_USER_AGENT, **self.headers}

    def __call__(self, request):
        self.local.response_bytes = 0
        self.local.http_status = None
        remaining = self.timeout if self.deadline is None else min(self.timeout, self.deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError("RPC scheduling deadline reached")
        req = urllib.request.Request(self.url, data=canonical(request), method="POST", headers=self.request_headers())
        read_deadline = time.monotonic() + remaining
        with self.opener.open(req, timeout=remaining) as response:
            self.local.http_status = getattr(response, "status", None)
            chunks, size = [], 0
            while size < self.max_bytes:
                if time.monotonic() >= read_deadline:
                    raise TimeoutError("RPC response deadline reached")
                chunk = response.read1(min(65536, self.max_bytes - size))
                size += len(chunk)
                self.local.response_bytes = size
                if time.monotonic() >= read_deadline:
                    raise TimeoutError("RPC response deadline reached")
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
        need(len(raw) < self.max_bytes, "response size limit reached; completeness unknown")
        # Redact known transport secrets even if an upstream server echoes them.
        self.last_redacted = False
        return self.redact(json.loads(raw.decode("utf-8"), parse_constant=invalid_constant, object_pairs_hook=unique_object))

def is_drpc_host(hostname):
    hostname = (hostname or "").rstrip(".")
    return any(hostname == h or hostname.endswith("." + h) for h in ("drpc.org", "drpc.live"))

def credential_free_network_url(parts):
    """The documented dRPC endpoint shapes without a key: /<network> or ?network=<network>; a key-bearing path
    segment or dkey parameter is refused so a credential never reaches a URL, a ledger or a bundle."""
    query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
    network_path = re.fullmatch(r"/[a-z0-9-]+/?", parts.path) is not None and not parts.query
    network_query = (parts.path in ("", "/") and set(query) == {"network"} and len(query["network"]) == 1
                     and re.fullmatch(r"[a-z0-9-]+", query["network"][0]) is not None)
    return network_path or network_query

def configuration_settings(args):
    """Validate local URL/auth formats only; this does not grant execution permission."""
    url = os.environ.get(args.rpc_url_env, "")
    parts = validate_endpoint(url)
    hostname = parts.hostname.rstrip(".")
    drpc = is_drpc_host(hostname)
    headers = {}
    if drpc or args.provider == "drpc":
        # Accept only credential-free documented endpoint shapes.
        need(hostname in ("lb.drpc.org", "lb.drpc.live"), "unsupported dRPC host")
        need(credential_free_network_url(parts), "use a credential-free dRPC network URL")
        key = os.environ.get("DRPC_API_KEY", "")
        need(bool(key.strip()), "DRPC_API_KEY is not configured")
        need(all(32 <= ord(c) <= 126 for c in key), "invalid authentication header value")
        headers["Drpc-Key"] = key
    elif args.auth_env:
        need(re.fullmatch(r"[A-Za-z0-9-]+", args.auth_header), "invalid auth header name")
        key = os.environ.get(args.auth_env, "")
        need(bool(key.strip()), "authentication environment variable is not configured")
        need(all(32 <= ord(c) <= 126 for c in key), "invalid authentication header value")
        headers[args.auth_header] = key
    return url, headers

def invocation_blockers(args, drpc):
    """Flags describe this invocation, not whether the user has standing approval."""
    reasons = []
    if not args.allow_network:
        reasons.append("network_disabled")
    if args.cost_policy not in ("free", "paid"):
        reasons.append("cost_policy_undeclared")
    if (drpc or args.cost_policy == "paid") and (args.cost_policy != "paid" or not args.allow_paid):
        reasons.append("paid_usage_not_authorized")
    return reasons

def transport_settings(args):
    """Enforce invocation gates even when called without the availability helper."""
    url = os.environ.get(args.rpc_url_env, "")
    drpc = args.provider == "drpc" or is_drpc_host(urllib.parse.urlsplit(url).hostname)
    blockers = invocation_blockers(args, drpc)
    need(not blockers, "RPC invocation requires authorized flags: " + ", ".join(blockers))
    return configuration_settings(args)

def provider_availability(args):
    """Choose collector vs. the agent's existing flow without any network or writes.

    Fallback is a workflow decision, not completed research or evidence of token risk.
    Never expose endpoint/credential values in this machine-readable result.
    """
    reason = None
    blockers = []
    try:
        url = os.environ.get(args.rpc_url_env, "")
        drpc = args.provider == "drpc" or is_drpc_host(urllib.parse.urlsplit(url).hostname)
        if drpc and not os.environ.get("DRPC_API_KEY", "").strip():
            reason = "drpc_key_missing"
        elif not url.strip():
            reason = "rpc_endpoint_unconfigured"
        elif not drpc and args.auth_env and not os.environ.get(args.auth_env, "").strip():
            reason = "rpc_authentication_missing"
        else:
            configuration_settings(args)
            blockers = invocation_blockers(args, drpc)
    except ValueError as exc:
        # A key inside the URL is the one misconfiguration worth naming: the fix is to move it to DRPC_API_KEY.
        reason = "rpc_url_carries_credential" if "credential-free" in str(exc) else "rpc_configuration_invalid"
    except TypeError:
        reason = "rpc_configuration_invalid"
    # Configuration absence can select alternatives. Omitted flags first require the
    # agent to consult trusted context; Python cannot infer approval from a saved key.
    status = "fallback" if reason else "invocation_required" if blockers else "ready"
    return {"schema_version": 2, "status": status,
            "reason": reason or (blockers[0] if blockers else None),
            "reason_category": "configuration" if reason else "invocation" if blockers else None,
            "blocking_reasons": [reason] if reason else blockers,
            "network_requests": 0, "provider_tested": False,
            "next_action": {"fallback": "continue_standard_flow",
                            "invocation_required": "review_invocation_context",
                            "ready": "run_collector"}[status]}


READ_METHODS = {"getGenesisHash", "getAccountInfo", "getMultipleAccounts", "getBlock",
    "getBlockTime", "getEpochInfo", "getTokenLargestAccounts", "getTokenSupply",
    "getSignaturesForAddress", "getTransaction", "getProgramAccounts", "getTokenAccountsByOwner"}
# JSON-RPC errors that mean the answering node is behind the requested context, not that the
# request is wrong: minContextSlot not reached, block not yet available, node unhealthy.
NODE_LAG_CODES = {-32016, -32004, -32005}


def failure_category(exc):
    """A coarse, URL-free reason for a failed send. It tells a host that denies the network (not_permitted, dns)
    apart from an endpoint that is down (connection_refused, unreachable) without retaining any message text."""
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, urllib.error.URLError):
        return failure_category(exc.reason) if isinstance(exc.reason, OSError) else "url_error"
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, socket.gaierror):
        return "dns"
    if isinstance(exc, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(exc, ConnectionResetError):
        return "connection_reset"
    if isinstance(exc, PermissionError) or getattr(exc, "errno", None) in (errno.EPERM, errno.EACCES):
        return "not_permitted"
    if getattr(exc, "errno", None) in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ENETDOWN):
        return "unreachable"
    if isinstance(exc, http.client.HTTPException):
        return "http_protocol"
    return "other"


def session_request(session, transport, request, *, family=None, owner="ordinary", retry=False, strict=False):
    """One accounted wire attempt. Callers explicitly schedule at most one retry.

    The sanitized response is durable in SQLite before downstream file/summary work.
    The method-specific evidence validator runs in the v2 collector (Phase 3).
    """
    from solana_session import LimitError
    need(request.get("method") in READ_METHODS, "method outside read-only allowlist")
    need(request.get("jsonrpc") == "2.0" and isinstance(request.get("params"), list), "invalid RPC request")
    if strict:
        from solana_wire import validate_request, validate_response
        validate_request(request)
    # Provider namespaces contain only a hash, never endpoint or auth values.
    family = family or sha(canonical({"method": request["method"], "params": request["params"]}))
    accounts = len(request["params"][0]) if request["method"] == "getMultipleAccounts" else int(request["method"] == "getAccountInfo")
    try:
        ticket = session.acquire(request["id"], family, request["method"], transport.namespace,
            owner=owner, accounts=accounts, max_response_bytes=transport.max_bytes, retry=retry)
    except LimitError as exc:
        # Refused before any send, so not an attempt; `wait_until` lets the caller wait out a window.
        return {"request": request, "status": "budget_denied", "reason": str(exc), "wait_until": exc.until, "response": None}
    status, response, failure = "transport_failure", None, None
    transport.local.response_bytes = 0
    try:
        remaining = min(session.remaining_seconds(owner), ticket["deadline"] - time.time())
        if remaining <= 0:
            status = "not_sent_deadline"
        else:
            transport.deadline = time.monotonic() + remaining
            response = transport(request)
            status = "redacted" if transport.last_redacted else "ok"
            if strict and status == "ok":
                status = validate_response(request, response)["status"]
            if isinstance(response, dict) and isinstance(response.get("error"), dict) and response["error"].get("code") in NODE_LAG_CODES:
                status = "node_lag"  # Transient: the collector paces a few retries, each after the slot-gap wait.
    except urllib.error.HTTPError as exc:
        status = "http_" + str(exc.code)
        if exc.code in (429, 503):
            limit = exc.headers.get("x-ratelimit-method-limit") if exc.headers is not None else None
            if exc.code == 429 and isinstance(limit, str) and limit.strip() == "0":
                # This tier refuses the method outright; other methods on the source continue.
                session.disable_method(transport.namespace, request["method"])
                status = "method_unavailable"
            else:
                # Public providers limit per method: back off only this method, never the source,
                # and only for the wait the provider states; the collector paces its own retry.
                until = retry_after(exc.headers)
                if until is not None:
                    session.defer_source(transport.namespace, until, method=request["method"])
        exc.close()
    except (OSError, http.client.HTTPException) as exc:
        # Network and HTTP-protocol failures; retain only categories, never URL-bearing messages.
        status = "timeout" if isinstance(exc, TimeoutError) else "transport_failure"
        failure = failure_category(exc)
    except (ValueError, TypeError, UnicodeError, KeyError, IndexError):
        status = "invalid"
    finally:
        # Every acquired attempt is finished, so an unexpected failure never strands a concurrency slot.
        packet = {"request": request, "status": status, "response": response}
        if failure:
            packet["failure"] = failure
        status = session.finish(ticket["id"], status, getattr(transport.local, "response_bytes", 0), packet)
        packet["status"] = status
    return packet
