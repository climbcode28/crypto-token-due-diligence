#!/usr/bin/env python3
"""Offline, bounded observations from frozen RPC evidence; never assigns market grades."""
import argparse
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from backend_common import (Cache, Invalid, RULE_VERSIONS, address, canonical, digest,
                            engine_snapshot, integer, label, load_collection, need,
                            quantity, read_json, sha, word, write_new)

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 40


def actor(value):
    return ZERO if value == ZERO else address(value)


def topic_address(value):
    word(value)
    need(value[2:26] == "0" * 24, "noncanonical indexed address")
    return actor("0x" + value[-40:])


class Observations:
    def __init__(self, collection, evidence, pins):
        self.collection, self.evidence, self.pins = collection, evidence, pins
        self.target = collection["target"]["address"]

    def rpc(self, eid, method):
        need(eid in self.evidence, "missing referenced evidence ID")
        row, obj = self.evidence[eid]
        need(row["query"]["method"] == method, "unexpected evidence method")
        need(row["pin_id"] in self.pins, "evidence is missing a captured pin")
        if (row["kind"] != "rpc" or row.get("redacted", False)
                or "error" in obj["response"] or obj["response"].get("result") is None):
            return row, None
        return row, obj["response"]["result"]

    def pinned_call(self, eid):
        row, value = self.rpc(eid, "eth_call")
        params = row["query"]["params"]
        pin = self.pins[row["pin_id"]]
        need(len(params) == 2 and params[1] == hex(pin["number"]), "call is not pinned or has overrides")
        need(address(params[0]["to"]) == address(row["address"]), "call scope mismatch")
        return row, value

    def launch(self, spec):
        need(isinstance(spec["definition"], str) and spec["definition"].strip(), "declare the cohort before measuring")
        ids = spec["receipt_evidence_ids"]
        need(isinstance(ids, list) and bool(ids) and len(ids) == len(set(ids)), "unique launch receipt IDs required")
        sources = {actor(x) for x in spec["source_addresses"]}
        need(bool(sources), "declare allocation source addresses (zero address for mint events)")
        exclusions = {actor(k): v for k, v in spec.get("excluded_recipients", {}).items()}
        need(all(isinstance(v, str) and v.strip() for v in exclusions.values()), "exclusions require reasons")
        threshold = integer(spec.get("flag_at_bps", 1000), "concentration threshold", 1)
        need(threshold <= 10000, "threshold exceeds 100 percent")
        gross, net, recipient_evidence = defaultdict(int), defaultdict(int), defaultdict(set)
        gaps, transactions, receipt_pins, used_ids = [], {}, [], []
        for eid in ids:
            row, receipt = self.rpc(eid, "eth_getTransactionReceipt")
            used_ids.append(eid)
            receipt_pins.append(row["pin_id"])
            if receipt is None:
                gaps.append({"evidence_id": eid, "reason": "receipt unavailable"})
                continue
            pin = self.pins[row["pin_id"]]
            tx = digest(receipt["transactionHash"], "transaction hash", prefix=True)
            need(row["query"]["params"] == [tx] and receipt["blockHash"].lower() == pin["hash"]
                 and quantity(receipt["blockNumber"]) == pin["number"], "receipt identity/pin mismatch")
            if tx in transactions:
                need(transactions[tx] == sha(canonical(receipt)), "conflicting duplicate receipt")
                continue
            transactions[tx] = sha(canonical(receipt))
            if receipt.get("status") != "0x1":
                gaps.append({"evidence_id": eid, "reason": "receipt is reverted or success is unestablished"})
                continue
            seen, decoded = set(), []
            try:
                need(isinstance(receipt["logs"], list), "receipt logs unavailable")
                for log in receipt["logs"]:
                    if address(log["address"]) != self.target:
                        continue
                    topics = log["topics"]
                    if not topics or topics[0].lower() != TRANSFER:
                        continue
                    need(log["transactionHash"].lower() == tx and log["blockHash"].lower() == pin["hash"]
                         and quantity(log["blockNumber"]) == pin["number"] and log.get("removed") is False,
                         "transfer log identity/pin mismatch")
                    index = quantity(log["logIndex"])
                    need(index not in seen, "duplicate transfer log index")
                    seen.add(index)
                    need(len(topics) == 3, "nonstandard Transfer (including NFT encoding) is not ERC-20 evidence")
                    decoded.append((topic_address(topics[1]), topic_address(topics[2]), word(log["data"])))
            except (Invalid, KeyError, TypeError, AttributeError) as exc:
                gaps.append({"evidence_id": eid, "reason": str(exc) if isinstance(exc, Invalid) else "malformed receipt log"})
                continue  # Do not publish a partly decoded receipt as complete allocation.
            for sender, recipient, amount in decoded:
                net[sender] -= amount
                net[recipient] += amount
                recipient_evidence[sender].add(eid)
                recipient_evidence[recipient].add(eid)
                if sender in sources and recipient != ZERO and recipient not in exclusions and amount:
                    gross[recipient] += amount
        supply, supply_pin = None, None
        supply_id = spec.get("supply_evidence_id")
        if supply_id:
            row, raw = self.pinned_call(supply_id)
            used_ids.append(supply_id)
            need(address(row["address"]) == self.target and row["query"]["params"][0]["data"].lower() == "0x18160ddd",
                 "supply evidence must query target totalSupply()")
            supply_pin = row["pin_id"]
            try:
                supply = word(raw)
                need(supply > 0, "zero supply cannot support ratios")
                need(bool(receipt_pins) and self.pins[supply_pin]["number"] == max(self.pins[x]["number"] for x in receipt_pins),
                     "supply pin must match the final declared launch receipt block")
            except Invalid as exc:
                supply = None
                gaps.append({"evidence_id": supply_id, "reason": str(exc)})
        else:
            gaps.append({"reason": "no historical supply evidence; supply ratios unknown"})
        recipients = []
        for recipient in sorted(gross):
            amount = gross[recipient]
            recipients.append({"address": recipient, "gross_received_atomic": str(amount),
                               "net_transfer_delta_atomic": str(net[recipient]),
                               "supply_fraction": {"numerator": str(amount), "denominator": str(supply)} if supply else None,
                               "supply_bps_floor": amount * 10000 // supply if supply else None,
                               "at_or_above_threshold": amount * 10000 >= threshold * supply if supply else None,
                               "evidence_ids": sorted(recipient_evidence[recipient])})
        return {"rule": "launch_recipients", "rule_version": RULE_VERSIONS["launch_recipients"],
                "status": "partial" if gaps else "observed", "definition": spec["definition"],
                "source_addresses": sorted(sources), "excluded_recipients": exclusions,
                "transaction_count": len(transactions), "recipients": recipients,
                "gross_received_atomic": str(sum(gross.values())), "supply_atomic": str(supply) if supply else None,
                "supply_pin_id": supply_pin, "flag_at_bps": threshold,
                "evidence_ids": sorted(set(used_ids)), "coverage_gaps": gaps,
                "limitations": ["Gross direct transfers from declared sources in supplied successful receipts only; not all launch allocations.",
                                "Transfer events need deployed-behavior correspondence; nonstandard balances/rebases are not reconstructed.",
                                "Gross receipts may exceed supply through circulation; shares are not ownership percentages.",
                                "Net transfer delta is not closing inventory, a sale, cash-out, common ownership or profit."]}

    def fee(self, spec):
        label(spec["id"])
        account, contract = address(spec["account"]), address(spec["contract"])
        selector = spec["selector"]
        need(isinstance(selector, str) and re.fullmatch(r"0x[0-9a-fA-F]{8}", selector), "explicit four-byte getter selector required")
        need(isinstance(spec["semantic_basis"], str) and spec["semantic_basis"].strip(), "describe getter semantics and source correspondence limits")
        eid = spec["call_evidence_id"]
        row, raw = self.pinned_call(eid)
        need(address(row["address"]) == contract, "fee getter contract mismatch")
        expected = selector.lower() + "0" * 24 + account[2:]
        need(row["query"]["params"][0]["data"].lower() == expected, "getter calldata does not bind the declared account")
        code_id = spec["code_evidence_id"]
        code_row, code = self.rpc(code_id, "eth_getCode")
        pin = self.pins[row["pin_id"]]
        need(code_row["pin_id"] == row["pin_id"] and address(code_row["address"]) == contract
             and code_row["query"]["params"] == [contract, hex(pin["number"])], "getter runtime evidence must match contract and pin")
        predicate, reason, code_hash = None, None, None
        try:
            need(isinstance(code, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", code), "runtime unavailable or empty")
            code_hash = sha(bytes.fromhex(code[2:]))
            decoded = word(raw)
            need(decoded in (0, 1), "noncanonical ABI bool")
            predicate = bool(decoded)
        except Invalid as exc:
            reason = str(exc)
        return {"id": spec["id"], "rule": "fee_predicate", "rule_version": RULE_VERSIONS["fee_predicate"],
                "status": "observed" if predicate is not None else "unknown", "account": account,
                "contract": contract, "pin_id": row["pin_id"], "pin": pin,
                "call_context": row["query"]["params"][0],
                "predicate": predicate, "runtime_sha256": code_hash, "semantic_basis": spec["semantic_basis"],
                "semantic_basis_verified_by_engine": False, "evidence_ids": [eid, code_id], "unknown_reason": reason,
                "limitations": ["Observes only the configured address-to-bool getter; validate ABI, proxy and transfer-path correspondence separately.",
                                "True is conditional evidence for the documented exemption; false does not exclude other exemptions or fee paths.",
                                "State is end-of-block, not intra-transaction launch state or measured effective fees. Sender/recipient/pair semantics require review."]}


def evaluate(collection, evidence, pins, case):
    need(case["schema_version"] == 1, "unsupported detector case schema")
    need(set(case) <= {"schema_version", "collection_sha256", "launch", "fee_checks"}, "unknown case field")
    obs = Observations(collection, evidence, pins)
    findings = []
    if "launch" in case:
        findings.append(obs.launch(case["launch"]))
    checks = case.get("fee_checks", [])
    need(len({x["id"] for x in checks}) == len(checks), "duplicate fee check ID")
    findings += [obs.fee(x) for x in sorted(checks, key=lambda x: x["id"])]
    need(bool(findings), "case requires at least one detector")
    return findings


def analyze(root, case_path, out, cache=None, allow_synthetic=False):
    root, out = Path(root), Path(out)
    collection, evidence, pins = load_collection(root, allow_synthetic)
    case = read_json(Path(case_path))
    need(case["collection_sha256"] == sha((root / "collection.json").read_bytes()), "case is not bound to this frozen collection")
    findings = evaluate(collection, evidence, pins, case)
    out.mkdir(parents=True, exist_ok=False)
    engine = engine_snapshot(out)
    write_new(out / "case.json", case)
    result = {"schema_version": 1, "synthetic": collection["synthetic"], "target": collection["target"],
              "collection_sha256": case["collection_sha256"], "case_sha256": sha(canonical(case)),
              "engine": engine, "findings": findings,
              "collection_coverage_gaps": collection["coverage_gaps"]}
    write_new(out / "findings.json", result)
    if cache:
        cache.register(out / "findings.json", "findings", engine)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("collection", type=Path)
    p.add_argument("case", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--cache", type=Path)
    p.add_argument("--allow-synthetic", action="store_true")
    args = p.parse_args()
    cache = None
    try:
        cache = Cache(args.cache) if args.cache else None
        result = analyze(args.collection, args.case, args.out, cache, args.allow_synthetic)
        print("Wrote findings for " + str(len(result["findings"])) + " checks; evidence semantics still require review.")
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, sqlite3.Error) as exc:
        print("Detection failed: " + (str(exc) if isinstance(exc, Invalid) else type(exc).__name__), file=sys.stderr)
        return 2
    finally:
        if cache:
            cache.close()


if __name__ == "__main__":
    sys.exit(main())
