#!/usr/bin/env python3
"""Offline candidate classification; no research, authorization or verified identity."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import sys
import time

VERSION = "1.0.0"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SPECIALISTS = {
    "evm": "crypto-evm-token-due-diligence",
    "solana": "crypto-solana-token-due-diligence",
}
MAX_INPUT_BYTES = 1_000_000


def candidate_family(address):
    if not isinstance(address, str):
        return None
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        return "evm" if int(address, 16) else None
    if not 32 <= len(address) <= 44 or any(c not in ALPHABET for c in address):
        return None
    value = 0
    for char in address:
        value = value * 58 + ALPHABET.index(char)
    size = len(address) - len(address.lstrip("1")) + (value.bit_length() + 7) // 8
    return "solana" if size == 32 and value else None


def number(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{field} must be finite nonnegative Unix seconds")
    return value


def route(packet, *, now=None):
    if not isinstance(packet, dict):
        raise ValueError("intake must be an object")
    if not isinstance(packet.get("request"), str) or not packet["request"].strip():
        raise ValueError("request must contain the full original request")
    current = number(time.time() if now is None else now, "now")
    start = number(packet.get("received_at"), "received_at")
    deadline = number(packet.get("deadline_at", start + 600), "deadline_at")
    target = number(packet.get("target_at", min(start + 420, deadline)), "target_at")
    if start > current or not start < target <= deadline:
        raise ValueError("timing must satisfy received_at <= now and received_at < target_at <= deadline_at")
    hint = packet.get("family_hint")
    if hint not in (None, "evm", "solana", "other"):
        raise ValueError("family_hint must be evm, solana or other when supplied")
    chain_hint = packet.get("chain_hint")
    if chain_hint is not None and (not isinstance(chain_hint, str) or not chain_hint.strip()):
        raise ValueError("chain_hint must be a nonempty string when supplied")
    kind = packet.get("asset_kind", "token")
    if kind not in ("token", "native"):
        raise ValueError("asset_kind must be token or native")
    addresses = packet.get("candidates", [])
    if not isinstance(addresses, list) or any(not isinstance(x, str) or not x for x in addresses):
        raise ValueError("candidates must be a list of nonempty exact address strings")
    addresses = list(addresses)
    if packet.get("address") is not None:
        if not isinstance(packet["address"], str) or not packet["address"]:
            raise ValueError("address must be a nonempty exact address string")
        addresses.append(packet["address"])
    unique = {}
    for address in addresses:
        key = address.lower() if candidate_family(address) == "evm" else address
        unique.setdefault(key, address)
    handoff = deepcopy(packet)
    handoff.update(received_at=start, target_at=target, deadline_at=deadline)
    result = {
        "router_version": VERSION, "status": "clarification_required", "skill": None,
        "family": None, "identity_verified": False, "network_requests": 0,
        "remaining_seconds": max(0, math.floor(deadline - current)),
        "target_remaining_seconds": max(0, math.floor(target - current)),
        "handoff": handoff,
    }
    if result["remaining_seconds"] == 0:
        result.update(status="deadline_reached", reason="No whole second remains before the original deadline; do not start collection")
    elif kind == "native":
        result.update(status="native_asset", reason="Native assets are outside token diligence")
    elif hint == "other":
        result.update(status="unsupported_family", reason="Explicit other-family context overrides address shape")
    elif chain_hint is not None and hint is None:
        result["reason"] = "Classify the explicit chain hint before selecting a family; do not ignore it"
    elif len(unique) != 1:
        result["reason"] = "Supply one exact token target; no candidate was selected" if not unique else "Resolve multiple target candidates"
    else:
        address = next(iter(unique.values()))
        family = candidate_family(address)
        if family is None:
            result["reason"] = "Not a supported token-address candidate; do not assume Solana"
        elif hint is not None and hint != family:
            result["reason"] = "Address format conflicts with the supplied family hint"
        else:
            result.update(status="routed", family=family, address=address, skill=SPECIALISTS[family],
                          reason="Candidate format only; specialist must verify exact network and token identity")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", nargs="?", type=Path, help="JSON intake file; omit to read stdin")
    args = parser.parse_args()
    try:
        if args.intake:
            with args.intake.open("rb") as source:
                raw = source.read(MAX_INPUT_BYTES + 1)
        else:
            raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("intake exceeds 1 MB")
        packet = json.loads(raw, object_pairs_hook=unique_object)
        result = route(packet)
        # Reject non-JSON metadata too; never emit NaN/Infinity into the handoff.
        output = json.dumps(result, ensure_ascii=True, allow_nan=False)
    except (OSError, ValueError, TypeError, RecursionError):
        # Do not echo user text, paths or credential-looking URL contents on errors.
        print(json.dumps({"router_version": VERSION, "status": "invalid_input", "skill": None,
                          "identity_verified": False, "network_requests": 0}))
        return 2
    print(output)
    return 0 if result["status"] == "routed" else 2


if __name__ == "__main__":
    sys.exit(main())
