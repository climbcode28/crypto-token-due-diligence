#!/usr/bin/env python3
"""Bounded, explicitly enabled read-only RPC collector. No signing or broadcasting."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import http.client
import json
import math
import os
import re
import sqlite3
import socket
import sys
import threading
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from backend_common import (BROWSER_USER_AGENT, Cache, Invalid, address, canonical, digest, engine_snapshot,
                            integer, label, need, quantity, read_json, sha, stamp, write_new)
from rpc_wire import validate_response

STATE = {"eth_getCode": 1, "eth_getBalance": 1, "eth_getStorageAt": 2, "eth_call": 1}
TRANSACTIONS = {"eth_getTransactionReceipt", "eth_getTransactionByHash",
                "debug_traceTransaction", "trace_transaction"}
METHODS = set(STATE) | TRANSACTIONS | {"eth_getLogs"}
TRACES = {"debug_traceTransaction", "trace_transaction"}


def seconds(value, name):
    need(type(value) in (float, int) and math.isfinite(value) and value > 0,
         name + " must be positive and finite")
    return float(value)


def hex_data(value):
    need(isinstance(value, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", value), "invalid hex data")
    return value.lower()


def prepare(plan):
    need(set(plan) <= {"schema_version", "target", "pins", "queries", "log_ranges"}, "unknown plan field")
    need(plan["schema_version"] == 1, "unsupported plan schema")
    target = {"chain_id": integer(plan["target"]["chain_id"], "chain ID", 1),
              "address": address(plan["target"]["address"])}
    pins, queries, ids = {}, [], set()
    for pin in plan["pins"]:
        name = label(pin["id"])
        need(name not in pins, "duplicate pin ID")
        pins[name] = integer(pin["number"], "block number", 0)
    for scan in plan.get("log_ranges", []):
        name = label(scan["id"])
        start = integer(scan["from_block"], "range start")
        end = integer(scan["to_block"], "range end")
        need(start <= end and end - start < 10000, "range must contain 1-10000 blocks")
        for number in range(start, end + 1):
            pid = label(f"{name}-{number}")
            need(pid not in pins, "range pin ID conflict")
            pins[pid] = number
            queries.append({"id": pid, "pin_id": pid, "method": "eth_getLogs",
                            "params": [{"address": scan["address"], "topics": scan.get("topics", [])}]})
    need(bool(pins), "at least one explicit pin is required")
    need(all(len(pid) <= 60 for pid in pins), "pin IDs must leave room for generated evidence IDs (maximum 60 characters)")
    queries += json.loads(json.dumps(plan.get("queries", [])))
    for query in queries:
        required = {"id", "pin_id", "method", "params"}
        need(required <= set(query) <= required | {"priority"}, "query fields must be id, pin_id, method, params and optional priority")
        need(integer(query.get("priority", 50), "query priority") <= 100, "priority must be 0-100; lower runs first")
        qid = label(query["id"])
        need(qid not in ids and not qid.startswith("sys-"), "duplicate or reserved query ID")
        ids.add(qid)
        need(query["pin_id"] in pins, "unknown query pin")
        method, params = query["method"], query["params"]
        need(method in METHODS and isinstance(params, list), "method not in read-only allowlist")
        if method in STATE:
            need(len(params) == STATE[method], "state query omits block; overrides are forbidden")
            if method == "eth_call":
                call = params[0]
                need(isinstance(call, dict) and set(call) <= {"to", "from", "data"}, "unsupported call fields")
                call["to"] = address(call["to"])
                call["data"] = hex_data(call["data"])
                if "from" in call:
                    call["from"] = address(call["from"])
            else:
                params[0] = address(params[0])
                if method == "eth_getStorageAt":
                    need(quantity(params[1]) < 2**256, "storage slot outside uint256")
        elif method == "eth_getLogs":
            need(len(params) == 1 and isinstance(params[0], dict), "invalid log filter")
            f = params[0]
            need(set(f) <= {"address", "topics"} or set(f) <= {"address", "topics", "from_block", "to_block"} and {"from_block", "to_block"} <= set(f),
                 "log bounds are supplied from the pin, or an explicit bounded from_block/to_block range")
            if "from_block" in f:
                start, end = integer(f["from_block"], "range start"), integer(f["to_block"], "range end")
                need(start <= end and end - start < 10000, "log range must span 1-10000 blocks")
            f["address"] = address(f["address"])
            topics = f.get("topics", [])
            need(isinstance(topics, list) and len(topics) <= 4, "invalid topics")
            for topic in topics:
                options = topic if isinstance(topic, list) else [topic]
                need(bool(options), "empty topic alternatives")
                for item in options:
                    if item is not None:
                        need(isinstance(item, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", item), "invalid topic")
        else:
            need(len(params) == 1, "transaction reads accept one hash; custom trace options are disabled")
            params[0] = digest(params[0], "transaction hash", prefix=True)
    # Trace binding requires an explicit receipt query, at the same historical pin.
    receipts = {(q["pin_id"], q["params"][0].lower()) for q in queries
                if q["method"] == "eth_getTransactionReceipt"}
    for q in queries:
        if q["method"] in {"debug_traceTransaction", "trace_transaction"}:
            need((q["pin_id"], q["params"][0].lower()) in receipts, "trace requires a matching receipt query")
    queries.sort(key=lambda q: (q["method"] in {"debug_traceTransaction", "trace_transaction"}, q.get("priority", 50), q["id"]))
    return target, pins, queries


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HttpTransport:
    synthetic = False

    def __init__(self, url, headers, timeout=20, max_bytes=16_000_000):
        self.url, self.headers = url, headers
        self.namespace = sha(canonical({"url": url, "headers": headers}))
        self.timeout, self.max_bytes = seconds(timeout, "request timeout"), max_bytes
        self.deadline = None
        self.local = threading.local()
        self.opener = urllib.request.build_opener(NoRedirect())
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
            while size <= self.max_bytes:
                if time.monotonic() >= read_deadline:
                    raise TimeoutError("RPC response deadline reached")
                chunk = response.read1(min(65536, self.max_bytes + 1 - size))
                if time.monotonic() >= read_deadline:
                    raise TimeoutError("RPC response deadline reached")
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                self.local.response_bytes = size
            raw = b"".join(chunks)
        need(len(raw) <= self.max_bytes, "response size limit")
        # Redact known transport secrets even if an upstream server echoes them.
        self.last_redacted = False
        return self.redact(json.loads(raw.decode("utf-8")))


def is_drpc_host(hostname):
    hostname = (hostname or "").rstrip(".")
    return any(hostname == h or hostname.endswith("." + h) for h in ("drpc.org", "drpc.live"))


def configuration_settings(args):
    """Validate local URL/auth formats only; this does not grant execution permission."""
    url = os.environ.get(args.rpc_url_env, "")
    parts = urllib.parse.urlsplit(url)
    need(parts.scheme == "https" and bool(parts.hostname) and not parts.username and not parts.password
         and not parts.fragment, "RPC URL must be HTTPS without userinfo or fragment")
    need(parts.port is None or 1 <= parts.port <= 65535, "invalid RPC port")
    hostname = parts.hostname.rstrip(".")
    drpc = is_drpc_host(hostname)
    headers = {}
    if drpc or args.provider == "drpc":
        # Accept only credential-free documented endpoint shapes.
        need(hostname in ("lb.drpc.org", "lb.drpc.live"), "unsupported dRPC host")
        query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
        network_path = re.fullmatch(r"/[a-z0-9-]+/?", parts.path)
        network_query = (parts.path in ("", "/") and set(query) == {"network"} and len(query["network"]) == 1
                         and re.fullmatch(r"[a-z0-9-]+", query["network"][0]))
        need((network_path and not parts.query) or network_query, "use a credential-free dRPC network URL")
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


def configured_transport(args):
    return HttpTransport(*transport_settings(args), timeout=getattr(args, "request_timeout", 20))


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
            # A private env still exporting the pre-rename name yields no endpoint under the current variable; name that
            # so the fix (rename to the current variable) is clear instead of a bare "unconfigured".
            reason = "rpc_url_env_renamed" if os.environ.get("CRYPTO_RPC_URL", "").strip() else "rpc_endpoint_unconfigured"
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


class Collector:
    def __init__(self, root, cache, transport, endpoint_label, max_requests=200, max_logs=10000,
                 workers=4, timeout=120, session=None):
        self.root, self.cache, self.transport = Path(root), cache, transport
        need(transport.synthetic or session is not None, "live collector requires an investigation session")
        self.endpoint_label = label(endpoint_label)
        self.max_requests = integer(max_requests, "max requests", 1)
        self.max_logs = integer(max_logs, "max logs", 1)
        self.workers = integer(workers, "workers", 1)
        need(self.workers <= 4, "workers must be between 1 and 4")
        self.timeout = seconds(timeout, "collection timeout")
        self.deadline = None
        self.query_deadline = None
        self.reserve = 0
        self.limit_reached = None
        self.stats = {"network_attempts": 0, "cache_hits": 0}
        self.evidence, self.gaps, self.query_evidence = [], [], {}
        self.request_keys = set()
        self.run_records = {}
        self.session, self.owner = session, str(uuid.uuid4())
        self.final_rechecking = False
        self.telemetry = {"request_seconds": 0.0, "response_bytes": 0, "failures": {}, "peak_in_flight": 0}

    def request_key(self, method, params, pin_hash):
        # Transport identity is independent of the report target. Exact queried
        # addresses/callers remain in params; reuse is confined to one investigation.
        return sha(canonical({"schema": 2, "provider": self.transport.namespace,
                             "investigation_id": self.session.id if self.session else self.cache.investigation_id,
                             "synthetic": self.transport.synthetic, "chain_id": self.target["chain_id"],
                             "block_hash": pin_hash, "method": method, "params": params}))

    def start_request(self, key, method, params, cached):
        """Only the main thread touches the budget and SQLite connection."""
        self.request_keys.add(key)
        attempt_id = self.run_records.get(key) if cached else None
        record = self.cache.attempt(attempt_id) if attempt_id is not None else None
        if record is not None:
            hit = record["status"] == "ok"
            self.stats["cache_hits"] += int(hit)
            return record, hit
        record = self.cache.get(key) if cached else None
        if record is not None:
            try:
                need(not record.get("redacted", False), "redacted cached response")
                need(record["request"]["method"] == method and record["request"]["params"] == params,
                     "cached request mismatch")
                need(validate_response(record["request"], record["response"]), "unavailable cached response")
            except (ValueError, KeyError, TypeError):
                # Quarantine invalid legacy data as an attempt, then obtain a fresh read.
                quarantined = dict(record, status="cache_quarantined", captured_at_utc=stamp())
                self.cache.record(key, quarantined, reusable=False)
                self.cache.evict([key])
                record = None
        if record is not None:
            self.stats["cache_hits"] += 1
            return record, True
        req = {"jsonrpc": "2.0", "id": key[:24], "method": method, "params": params}
        record = {"request": req, "captured_at_utc": stamp()}
        limit = self.acquire_attempt(method, reserved=self.final_rechecking)
        if limit is not None:
            record.update(status="deadline_exhausted" if limit == "collection_deadline" else "budget_exhausted",
                          transport_error={"category": limit})
        return record, False

    def scheduling_deadline(self):
        return self.query_deadline if self.query_deadline is not None and not self.final_rechecking else self.deadline

    def acquire_attempt(self, method, *, reserved=False):
        """Charge every scheduled transport attempt on the coordinator thread."""
        deadline = self.scheduling_deadline()
        if deadline is not None and time.monotonic() >= deadline:
            self.limit_reached = "collection_deadline"
        elif self.stats["network_attempts"] >= self.max_requests - self.reserve:
            self.limit_reached = "request_budget"
        elif self.session is not None and not self.session.acquire(method, owner=self.owner, reserved=reserved):
            self.limit_reached = "investigation_limit"
        else:
            self.stats["network_attempts"] += 1
            return None
        return self.limit_reached

    TRANSIENT_FAILURES = ("throttled", "timeout", "dns_resolution", "transport_error", "server_error", "node_lag")
    NODE_LAG = ("unsupported block number", "block not found", "header not found", "unknown block", "missing trie node", "block is not available")
    transient_retries = 1

    def retryable(self, record):
        return (record.get("status") in ("transport_failure", "unavailable")
                and record.get("failure_category") in self.TRANSIENT_FAILURES
                and record.get("retries", 0) < self.transient_retries)

    def start_retry(self, record):
        """Authorize retries after worker backoff, without replacing the observed failure if denied."""
        if not self.retryable(record):
            return None
        deadline = self.scheduling_deadline()
        if deadline is not None and time.monotonic() + 1.0 >= deadline:
            return None
        # A failed recheck already consumed its own lease; its retry must not spend
        # another pin's reserved request. Spare unreserved capacity may be used.
        if self.acquire_attempt(record["request"]["method"]) is not None:
            return None
        return {key: record[key] for key in ("request", "captured_at_utc", "duration_seconds", "response_bytes")} | {
            "retries": record.get("retries", 0) + 1}

    def fetch(self, record):
        """Network-only worker: no evidence, cache or budget mutations.

        Back off transient failures here so independent requests still overlap;
        only the coordinator can authorize and charge the one bounded retry.
        """
        if "status" in record:
            return record
        started = time.monotonic()
        try:
            self.fetch_once(record)
            deadline = self.scheduling_deadline()
            if self.retryable(record):
                pause = 0.75 if deadline is None else min(0.75, max(0, deadline - time.monotonic() - 1.0))
                if pause:
                    time.sleep(pause)
        finally:
            record.setdefault("retries", 0)
            record["duration_seconds"] = round(record.get("duration_seconds", 0) + time.monotonic() - started, 6)
            local = getattr(self.transport, "local", None)
            record["response_bytes"] = record.get("response_bytes", 0) + getattr(
                local, "response_bytes", len(canonical(record["response"])) if "response" in record else 0)
            record["byte_measurement"] = "transport_body" if isinstance(self.transport, HttpTransport) else "serialized_fixture_response"
            record.setdefault("http_status", getattr(local, "http_status", None))
        return record

    def fetch_once(self, record):
        req = record["request"]
        try:
            resp = self.transport(req)
            record["response"] = resp  # Preserve malformed replies too; never cache them as success.
            try:
                available = validate_response(req, resp, redacted=getattr(self.transport, "last_redacted", False))
            except (ValueError, KeyError, TypeError):
                record.update(status="malformed_data", validation_error="RPC wire validation failed")
                return record
            redacted = getattr(self.transport, "last_redacted", False)
            status = "redacted" if redacted else "ok" if available else "unavailable"
            if "error" in resp and not redacted:
                error = resp["error"] if isinstance(resp["error"], dict) else {}
                code = error.get("code")
                message = str(error.get("message", "")).lower()
                record["rpc_error_code"] = code
                if code == 3 or "revert" in message:
                    # A revert at the pin is the chain's definitive answer (function absent or guarded),
                    # not an operational failure: recorded as reverted, never retried, never lost coverage.
                    status = "reverted"
                    record["failure_category"] = "execution_reverted"
                elif any(marker in message for marker in self.NODE_LAG):
                    # A load-balanced public endpoint whose backend has not imported the pinned block yet.
                    record["failure_category"] = "node_lag"
                else:
                    record["failure_category"] = "method_unavailable" if code == -32601 else "rpc_error"
            elif not available:
                record["failure_category"] = "redacted" if redacted else "null_result"
            record.update(response=resp, status=status, redacted=redacted)
        except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as exc:
            # Exception strings, HTTP bodies and URLs may contain API keys.
            record.update(status="transport_failure", transport_error={"category": type(exc).__name__})
            if isinstance(exc, urllib.error.HTTPError):
                record["http_status"] = exc.code
                record["failure_category"] = {401: "authentication", 403: "access_denied", 404: "not_found", 429: "throttled"}.get(
                    exc.code, "server_error" if 500 <= exc.code < 600 else "http_error")
            elif isinstance(getattr(exc, "reason", exc), socket.gaierror):
                record["failure_category"] = "dns_resolution"
            elif isinstance(exc, TimeoutError):
                record["failure_category"] = "timeout"
            else:
                record["failure_category"] = "transport_error"
        return record

    def store_record(self, key, record, cached):
        # Repeated failed queries reuse their attempt within this run only. Future
        # runs may retry failures, and chain/header rechecks always remain fresh.
        if not cached or key not in self.run_records:
            attempt_id = self.cache.record(key, record, reusable=record["status"] == "ok" and cached)
            self.telemetry["request_seconds"] += record.get("duration_seconds", 0)
            self.telemetry["response_bytes"] += record.get("response_bytes", 0)
            if record["status"] != "ok":
                failures = self.telemetry["failures"]
                failures[record["status"]] = failures.get(record["status"], 0) + 1
            if cached:
                self.run_records[key] = attempt_id

    def request(self, eid, method, params, pin_id=None, pin_hash=None, scoped_address=None, cached=True):
        key = self.request_key(method, params, pin_hash)
        record, hit = self.start_request(key, method, params, cached)
        if not hit:
            if "status" not in record:
                record = self.fetch(record)
                retry = self.start_retry(record)
                if retry is not None:
                    record = self.fetch(retry)
            self.store_record(key, record, cached)
        return self.save_response(eid, method, params, pin_id, scoped_address, record, hit)

    def request_many(self, requests, validate_result=None):
        """Rolling bounded execution with coordinator-owned validation and disk spooling.

        Only in-flight responses occupy the scheduler buffer. Complete each started
        acquisition even if validation stops further scheduling; sort evidence by the
        original request order rather than pairing completion order with request order.
        """
        groups = {}
        order = {request[0]: index for index, request in enumerate(requests)}
        for request in requests:
            eid, method, params, pid, pin_hash, scoped = request
            key = self.request_key(method, params, pin_hash)
            groups.setdefault(key, []).append(request)
        queued = iter(groups.items())
        pending, exhausted, failure = {}, False, None
        first_row = len(self.evidence)
        first_gap = len(self.gaps)

        def finish(key, record, hit, members):
            nonlocal failure
            if not hit:
                self.store_record(key, record, True)
            for index, request in enumerate(members):
                eid, method, params, pid, _, scoped = request
                reused = hit or (index > 0 and record["status"] == "ok")
                self.stats["cache_hits"] += int(index > 0 and record["status"] == "ok")
                result = self.save_response(eid, method, params, pid, scoped, record, reused)
                if validate_result is not None and failure is None:
                    try:
                        validate_result(request, result)
                    except (ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
                        failure = exc

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            while pending or not exhausted:
                while not exhausted and failure is None and len(pending) < self.workers:
                    try:
                        key, members = next(queued)
                    except StopIteration:
                        exhausted = True
                        break
                    _, method, params, _, _, _ = members[0]
                    try:
                        record, hit = self.start_request(key, method, params, True)
                    except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                        failure = exc
                        break  # Drain and preserve every already-started acquisition below.
                    if hit or "status" in record:
                        finish(key, record, hit, members)
                    else:
                        pending[executor.submit(self.fetch, record)] = (key, members)
                        self.telemetry["peak_in_flight"] = max(self.telemetry["peak_in_flight"], len(pending))
                if failure is not None:
                    exhausted = True
                if not pending:
                    continue
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in sorted(completed, key=lambda f: order[pending[f][1][0][0]]):
                    key, members = pending.pop(future)
                    record = future.result()
                    retry = None
                    if failure is None:
                        try:
                            retry = self.start_retry(record)
                        except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                            failure = exc
                    if retry is not None:
                        pending[executor.submit(self.fetch, retry)] = (key, members)
                    else:
                        finish(key, record, False, members)
        self.evidence[first_row:] = sorted(self.evidence[first_row:], key=lambda row: order[row["id"]])
        self.gaps[first_gap:] = sorted(self.gaps[first_gap:], key=lambda row: order.get(row.get("evidence_id"), len(order)))
        if failure is not None:
            raise failure

    def save_response(self, eid, method, params, pin_id, scoped_address, record, hit):
        artifact = "evidence/" + label(eid) + ".json"
        obj = {"request": record["request"]}
        if "response" in record:
            obj["response"] = record["response"]
            if "validation_error" in record:
                obj["validation_error"] = record["validation_error"]
        else:
            obj["transport_error"] = record["transport_error"]
        write_new(self.root / artifact, obj)
        row = {"id": eid, "target": self.target, "chain_id": self.target["chain_id"],
               "address": scoped_address or self.target["address"], "pin_id": pin_id,
               "tx_hash": params[0] if method in TRANSACTIONS else None,
               "kind": "rpc" if "response" in obj and "validation_error" not in obj else "document", "artifact": artifact,
               "sha256": sha(canonical(obj)), "query": record["request"],
               "endpoint_label": self.endpoint_label, "captured_at_utc": record["captured_at_utc"],
               "decoding_basis": "raw JSON-RPC; method semantics require review",
               "coverage": "observed response" if record["status"] == "ok" else record["status"],
               "observation_status": record["status"],
               "acquisition": {"operation": method, "tool": "rpc_collect", "access_mode": "synthetic" if self.transport.synthetic else "rpc",
                               "http_status": record.get("http_status"), "rpc_error_code": record.get("rpc_error_code"),
                               "failure_category": record.get("failure_category", record.get("transport_error", {}).get("category", record["status"] if record["status"] != "ok" else None)),
                               "provider_namespace": self.transport.namespace,
                               "authentication": "configured" if getattr(self.transport, "headers", {}) else "none_or_fixture",
                               "duration_seconds": record.get("duration_seconds", 0), "bytes": record.get("response_bytes", 0),
                               "byte_measurement": record.get("byte_measurement", "no_response")},
               "cache_hit": hit, "redacted": record.get("redacted", False)}
        self.evidence.append(row)
        if record["status"] != "ok":
            self.gaps.append({"evidence_id": eid, "reason": record["status"]})
            return None
        return obj["response"]["result"]

    def header(self, eid, pid, number):
        header = self.request(eid, "eth_getBlockByNumber", [hex(number), False], pid, cached=False)
        need(isinstance(header, dict) and quantity(header["number"]) == number, "pinned header unavailable or mismatched")
        digest(header["hash"], "block hash", prefix=True)
        digest(header["parentHash"], "parent hash", prefix=True)
        digest(header["stateRoot"], "state root", prefix=True)
        quantity(header["timestamp"])
        return header

    def collect_queries(self, queries, pins, receipt_bindings):
        requests = []
        for q in queries:
            pid, method = q["pin_id"], q["method"]
            pin = pins[pid]
            params = json.loads(json.dumps(q["params"]))
            scoped = self.target["address"]
            if method in STATE:
                params.append(hex(pin["number"]))
                scoped = address(params[0]["to"] if method == "eth_call" else params[0])
            elif method == "eth_getLogs":
                if "from_block" in params[0]:
                    start, end = params[0].pop("from_block"), params[0].pop("to_block")
                    need(end <= pin["number"], "log range cannot extend past its pin")
                    params[0]["fromBlock"], params[0]["toBlock"] = hex(start), hex(end)
                else:
                    params[0]["blockHash"] = pin["hash"]
                scoped = address(params[0]["address"])
            elif method in {"debug_traceTransaction", "trace_transaction"}:
                if (pid, params[0].lower()) not in receipt_bindings:
                    self.gaps.append({"query_id": q["id"], "reason": "trace skipped: receipt is unbound or unavailable"})
                    continue
            requests.append((q["id"], method, params, pid, pin["hash"], scoped))
        def validate_result(request, result):
            eid, method, params, pid, _, scoped = request
            pin = pins[pid]
            self.query_evidence[eid] = eid
            if result is None:
                return
            if method in {"eth_getTransactionReceipt", "eth_getTransactionByHash"}:
                field = "transactionHash" if method.endswith("Receipt") else "hash"
                need(result[field].lower() == params[0].lower() and result["blockHash"].lower() == pin["hash"]
                     and quantity(result["blockNumber"]) == pin["number"], "transaction does not match its historical pin")
                if method.endswith("Receipt"):
                    receipt_bindings.add((pid, params[0].lower()))
            if method == "eth_getLogs":
                need(isinstance(result, list), "log response is not a list")
                if len(result) >= self.max_logs:
                    self.gaps.append({"evidence_id": eid, "reason": "per-block log limit reached; completeness unknown"})
                ranged = "fromBlock" in params[0]
                for log in result:
                    if ranged:
                        number = quantity(log["blockNumber"])
                        need(quantity(params[0]["fromBlock"]) <= number <= quantity(params[0]["toBlock"])
                             and (number != pin["number"] or log["blockHash"].lower() == pin["hash"])
                             and address(log["address"]) == scoped and log.get("removed") is False,
                             "log outside query range/address or removed")
                    else:
                        need(log["blockHash"].lower() == pin["hash"] and quantity(log["blockNumber"]) == pin["number"]
                             and address(log["address"]) == scoped and log.get("removed") is False,
                             "log outside query pin/address or removed")
                    for i, expected in enumerate(params[0].get("topics", [])):
                        if expected is not None:
                            choices = expected if isinstance(expected, list) else [expected]
                            need(i < len(log["topics"]) and (None in choices or log["topics"][i].lower() in [x.lower() for x in choices]),
                                 "log does not match requested topics")

        self.request_many(requests, validate_result)

    def collect(self, plan):
        self.target, numbers, queries = prepare(plan)
        started = time.monotonic()
        self.deadline = started + min(self.timeout, self.session.remaining_seconds() if self.session else self.timeout)
        if isinstance(self.transport, HttpTransport):
            self.transport.deadline = self.deadline
        self.root.mkdir(parents=True, exist_ok=False)
        write_new(self.root / "plan.json", plan)
        engine = engine_snapshot(self.root)
        pins, status, receipt_bindings = {}, "complete", set()
        try:
            if self.max_requests < 1 + 2 * len(numbers):
                self.limit_reached = "request_budget"
            need(self.max_requests >= 1 + 2 * len(numbers),
                 "request budget cannot cover chain verification and both checks for every pin; narrow the plan")
            if self.session is not None:
                try:
                    self.session.ensure(1 + 2 * len(numbers))
                    self.session.reserve(self.owner, len(numbers))
                except ValueError:
                    self.limit_reached = "investigation_limit"
                    raise
            self.reserve = len(numbers)
            chain = self.request("sys-chain", "eth_chainId", [], cached=False)
            need(chain is not None and quantity(chain) == self.target["chain_id"], "RPC chain does not match requested chain")
            for pid, number in numbers.items():
                header = self.header("sys-pin-" + pid, pid, number)
                pins[pid] = {"id": pid, "number": number, "hash": header["hash"].lower(),
                             "timestamp_utc": datetime.fromtimestamp(quantity(header["timestamp"]), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "header_evidence": "sys-pin-" + pid, "parent_hash": header["parentHash"].lower(),
                             "state_root": header["stateRoot"].lower()}
            # Adjacent captured blocks must belong to one chain view.
            by_number = {}
            for pin in pins.values():
                if pin["number"] in by_number:
                    need(by_number[pin["number"]]["hash"] == pin["hash"], "conflicting duplicate block pins")
                by_number[pin["number"]] = pin
            for n, pin in by_number.items():
                if n - 1 in by_number:
                    need(pin["parent_hash"] == by_number[n - 1]["hash"], "inconsistent adjacent block headers")
            # Reserve final live header checks before spending on optional queries.
            self.reserve = len(pins)
            reserve_seconds = min(max(0, self.deadline - started) / 3, len(pins) * getattr(self.transport, "timeout", 20))
            self.query_deadline = self.deadline - reserve_seconds
            if isinstance(self.transport, HttpTransport):
                self.transport.deadline = self.query_deadline
            self.collect_queries([q for q in queries if q["method"] not in TRACES], pins, receipt_bindings)
            self.collect_queries([q for q in queries if q["method"] in TRACES], pins, receipt_bindings)
            if isinstance(self.transport, HttpTransport):
                self.transport.deadline = self.deadline
            # Always bypass cache: detect reorgs before accepting reused observations.
            self.final_rechecking = True
            for pid, pin in pins.items():
                self.reserve -= 1
                after = self.header("sys-recheck-" + pid, pid, pin["number"])
                need(after["hash"].lower() == pin["hash"] and after["parentHash"].lower() == pin["parent_hash"]
                     and after["stateRoot"].lower() == pin["state_root"]
                     and datetime.fromtimestamp(quantity(after["timestamp"]), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") == pin["timestamp_utc"],
                     "block changed during collection; evidence invalidated")
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError, sqlite3.Error) as exc:
            status = "invalid"
            self.cache.evict(self.request_keys)
            self.gaps.append({"reason": "collection aborted: " + (str(exc) if isinstance(exc, Invalid) else type(exc).__name__)})
        finally:
            if self.session is not None:
                self.session.release(self.owner)
        if status == "complete" and self.gaps:
            status = "partial"
        if time.monotonic() >= self.deadline:
            self.limit_reached = "collection_deadline"
        collection = {"schema_version": 1, "synthetic": self.transport.synthetic, "status": status,
                      "target": self.target, "engine": engine, "plan_sha256": sha(canonical(plan)),
                      "chain_id_evidence": "sys-chain", "pins": list(pins.values()),
                      "evidence": self.evidence, "query_evidence": self.query_evidence,
                      "coverage_gaps": self.gaps, "statistics": self.stats,
                      "telemetry": {**self.telemetry, "elapsed_seconds": round(time.monotonic() - started, 6)},
                      "investigation": self.session.status() if self.session else {"investigation_id": self.cache.investigation_id, "mode": "library_compatibility"},
                      "execution": {"workers": self.workers, "timeout_seconds": self.timeout,
                                    "request_limit": self.max_requests, "limit_reached": self.limit_reached},
                      "limitations": ["Explicit requested reads only; no automatic discovery or provider completeness proof.",
                                      "Numbered state reads use before/after header checks; RPC honesty is not authenticated.",
                                      "Scheduling and response deadlines do not forcibly interrupt OS/DNS stalls; use an outer process deadline when required."]}
        write_new(self.root / "collection.json", collection)
        self.cache.register(self.root / "collection.json", "collection", engine)
        from operations import automatic
        captured = set()
        for row in self.evidence:
            key = (row["query"]["method"], row["observation_status"])
            if row["observation_status"] not in ("ok", "reverted") and key not in captured and len(captured) < 7:
                automatic(self.root, "collector", key[0], key[1], row["artifact"],
                          sha(canonical(collection)), "synthetic" if self.transport.synthetic else "rpc",
                          feedback_root=self.session.path.parent if self.session else None)
                captured.add(key)
        operational_gaps = [g for g in self.gaps if g.get("reason") != "reverted"]
        if status == "invalid" or (operational_gaps and not captured):
            automatic(self.root, "collector", "collection", "incomplete_collection", "collection.json", sha(canonical(collection)),
                      feedback_root=self.session.path.parent if self.session else None)
        return collection


def add_provider_arguments(p):
    p.add_argument("--rpc-url-env", default="ROBINHOOD_DRPC_URL")
    p.add_argument("--endpoint-label", default="research-rpc")
    p.add_argument("--provider", choices=("generic", "drpc"), default="generic")
    p.add_argument("--auth-env")
    p.add_argument("--auth-header", default="Authorization")
    p.add_argument("--allow-network", action="store_true")
    p.add_argument("--cost-policy", choices=("free", "paid"))
    p.add_argument("--allow-paid", action="store_true", help="use only after user authorization")
    p.add_argument("--request-timeout", type=float, default=20, help="bounded per-request response deadline")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path, nargs="?")
    p.add_argument("--out", type=Path, help="new directory; required for collection")
    p.add_argument("--cache", type=Path, help="required for collection")
    p.add_argument("--session", type=Path, help="existing investigation budget; required for live collection")
    p.add_argument("--check-availability", action="store_true", help="offline provider selection; no plan, output or cache required")
    add_provider_arguments(p)
    p.add_argument("--max-requests", type=int, default=200)
    p.add_argument("--max-logs-per-block", type=int, default=10000)
    p.add_argument("--workers", type=int, default=4, help="1-4 concurrent independent query reads; chain/pin checks remain ordered")
    p.add_argument("--timeout", type=float, default=120, help="collection scheduling deadline in seconds; not a hard process watchdog")
    args = p.parse_args()
    if args.check_availability:
        print(json.dumps(provider_availability(args), sort_keys=True))
        return 0
    if args.plan is None or args.out is None or args.cache is None:
        p.error("collection requires plan, --out and --cache; use --check-availability for offline selection")
    cache = session = None
    try:
        plan = read_json(args.plan)
        prepare(plan)
        integer(args.max_requests, "max requests", 1)
        integer(args.max_logs_per_block, "max logs", 1)
        need(1 <= integer(args.workers, "workers", 1) <= 4, "workers must be between 1 and 4")
        seconds(args.timeout, "collection timeout")
        seconds(args.request_timeout, "request timeout")
        route = provider_availability(args)
        if route["status"] != "ready":
            print(json.dumps(route, sort_keys=True))
            return 3  # Distinct handoff: no collection or cache was created.
        need(args.session is not None, "live collection requires --session; initialize one fresh investigation budget")
        from investigation import Investigation
        session = Investigation(args.session)
        transport = configured_transport(args)
        cache = Cache(args.cache)
        result = Collector(args.out, cache, transport, args.endpoint_label,
                           args.max_requests, args.max_logs_per_block, args.workers, args.timeout, session).collect(plan)
        print(json.dumps({"status": result["status"], **result["statistics"],
                          "limit_reached": result["execution"]["limit_reached"],
                          "next_action": "review_evidence" if result["status"] == "complete" or result["execution"]["limit_reached"]
                          else "continue_standard_flow"}, sort_keys=True))
        return 0 if result["status"] == "complete" else 2
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print("Collection failed: " + (str(exc) if isinstance(exc, Invalid) else type(exc).__name__), file=sys.stderr)
        return 2
    finally:
        if cache:
            cache.close()
        if session:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
