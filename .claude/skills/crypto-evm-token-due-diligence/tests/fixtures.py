"""Clearly synthetic artifacts for offline helper validation, never live findings."""
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_bundle import DIMENSIONS, METADATA

TARGET = "0x1234567890abcdef1234567890abcdef12345678"
OTHER = "0x2234567890abcdef1234567890abcdef12345678"
CHAIN = 31337
STAMP = "2024-01-01T00:00:00Z"
HASH = "0x" + hashlib.sha256(b"SYNTHETIC HEADER NOT A REAL CHAIN BLOCK").hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bind(root, manifest, report):
    write_json(root / "manifest.json", manifest)
    report["manifest_sha256"] = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    write_json(root / "report.json", report)


def abi_string(value):
    raw = value.encode()
    return "0x" + ((32).to_bytes(32, "big") + len(raw).to_bytes(32, "big") + raw
                   + bytes((-len(raw)) % 32)).hex()


def add_rpc(root, manifest, eid, method, params, response, chain_id=CHAIN, addr=TARGET, pin_id="p-current"):
    ev = copy.deepcopy(manifest["evidence"][0])
    ev.update(id=eid, chain_id=chain_id, address=addr, pin_id=pin_id, artifact="evidence/" + eid + ".json")
    ev["query"] = {"jsonrpc": "2.0", "id": eid, "method": method, "params": params}
    write_json(root / ev["artifact"], {"request": ev["query"], "response": {"jsonrpc": "2.0", "id": eid, **response}})
    ev["sha256"] = hashlib.sha256((root / ev["artifact"]).read_bytes()).hexdigest()
    manifest["evidence"].append(ev)
    return ev


def add_second_chain(root, manifest, report):
    cid, pid = CHAIN + 1, "p-secondary"
    hh = "0x" + hashlib.sha256(b"SYNTHETIC secondary-chain block").hexdigest()
    add_rpc(root, manifest, "e-secondary-chain", "eth_chainId", [], {"result": hex(cid)}, cid, OTHER, pid)
    add_rpc(root, manifest, "e-secondary-header", "eth_getBlockByNumber", [hex(100), False], {"result": {
        "number": hex(100), "hash": hh, "timestamp": hex(1704067200),
        "parentHash": "0x" + hashlib.sha256(b"synthetic-secondary-parent").hexdigest(),
        "stateRoot": "0x" + hashlib.sha256(b"synthetic-secondary-state").hexdigest()}}, cid, OTHER, pid)
    add_rpc(root, manifest, "e-secondary-code", "eth_getCode", [OTHER, hex(100)], {"result": "0x60006000f3"}, cid, OTHER, pid)
    manifest["chains"].append({"chain_id": cid, "label": "Synthetic second chain", "chain_id_evidence": "e-secondary-chain",
                              "current_pin": pid, "pins": [{"id": pid, "number": 100, "hash": hh,
                              "timestamp_utc": STAMP, "header_evidence": "e-secondary-header"}]})
    scope = copy.deepcopy(manifest["scope"][0])
    scope.update(id="secondary", chain_id=cid, address=OTHER, pin_id=pid,
                 roles=["external dependency"], provenance=["e-secondary-code"])
    scope["runtime"]["evidence_id"] = "e-secondary-code"
    scope["proxy"]["evidence_ids"] = ["e-secondary-code"]
    manifest["scope"].append(scope)
    finding = copy.deepcopy(report["findings"][0])
    finding.update(id="F-secondary", chain_id=cid, address=OTHER, pin_id=pid, evidence_ids=["e-secondary-code"])
    report["findings"].append(finding)
    report["ratings"][-2]["finding_ids"] = ["F-secondary"]


def build(root):
    root = Path(root)
    target = {"chain_id": CHAIN, "address": TARGET}
    evidence = []

    def rpc(eid, method, params, result):
        query = {"jsonrpc": "2.0", "id": eid, "method": method, "params": params}
        record = {"request": query, "response": {"jsonrpc": "2.0", "id": eid, "result": result}}
        path = root / "evidence" / (eid + ".json")
        write_json(path, record)
        evidence.append({"id": eid, "target": copy.deepcopy(target), **target, "pin_id": "p-current",
                         "tx_hash": None, "kind": "rpc", "artifact": "evidence/" + path.name,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "query": query,
                         "endpoint_label": "synthetic-offline-fixture", "captured_at_utc": STAMP,
                         "decoding_basis": "Synthetic canonical ABI/RPC fixture; no actual network query",
                         "coverage": "Offline fixture only; no live-token coverage"})

    rpc("e-chain", "eth_chainId", [], hex(CHAIN))
    rpc("e-header", "eth_getBlockByNumber", [hex(100), False], {
        "number": hex(100), "hash": HASH, "timestamp": hex(1704067200),
        "parentHash": "0x" + hashlib.sha256(b"synthetic-parent").hexdigest(),
        "stateRoot": "0x" + hashlib.sha256(b"synthetic-state").hexdigest()})
    code = "0x60006000f3"
    rpc("e-code", "eth_getCode", [TARGET, hex(100)], code)
    values = {"name": "Synthetic Fixture Token", "symbol": "SYNTH", "decimals": 18,
              "total_supply": "1000000000000000000000"}
    metadata = {}
    for field, selector in METADATA.items():
        result = abi_string(values[field]) if field in ("name", "symbol") else "0x" + int(values[field]).to_bytes(32, "big").hex()
        eid = "e-" + field
        rpc(eid, "eth_call", [{"to": TARGET, "data": selector}, hex(100)], result)
        metadata[field] = {"status": "resolved", "value": values[field], "evidence_ids": [eid], "reason": None}
    safety = {"no_real_keys": True, "no_real_signing": True, "no_broadcast": True, "simulation": {"used": False}}
    manifest = {
        "schema_version": 1, "synthetic": True, "mode": "broad",
        "question": "SYNTHETIC: verify offline bundle consistency, not token quality",
        "materiality": "No live materiality. Never suppress authority discovery.",
        "limitations": ["All artifacts are generated synthetic data. No live diligence occurred."],
        "target": {"requested": copy.deepcopy(target), "observed": copy.deepcopy(target), "metadata": metadata},
        "context": {"deployment": {"status": "unresolved", "reason": "Synthetic fixture has no deployment"},
                    "candidate_pools": [], "known_limitations": ["No actual chain or contracts"]},
        "chains": [{"chain_id": CHAIN, "label": "Synthetic fixture chain", "chain_id_evidence": "e-chain",
                    "current_pin": "p-current", "pins": [{"id": "p-current", "number": 100, "hash": HASH,
                    "timestamp_utc": STAMP, "header_evidence": "e-header"}]}],
        "scope": [{"id": "target", **target, "roles": ["target token"], "material": True,
                   "pin_id": "p-current", "provenance": ["e-code"],
                   "runtime": {"status": "captured", "evidence_id": "e-code",
                               "sha256": hashlib.sha256(bytes.fromhex(code[2:])).hexdigest(), "keccak256": None},
                   "proxy": {"status": "unresolved", "basis": "Synthetic runtime is not a real control review",
                             "evidence_ids": ["e-code"], "implementation_scope_ids": [], "authority_scope_ids": []}}],
        "evidence": evidence, "discoveries": [], "safety": safety}
    findings = [{"id": "F-coverage", **target, "pin_id": "p-current",
                 "proposition": "SYNTHETIC: live risk checks are unknown because no live investigation occurred.",
                 "evidence_ids": ["e-code"], "decoding_basis": "No inference of token behavior from fixture bytes",
                 "evidence_type": "unknown", "confidence": "unknown", "alternatives": "Actual deployed behavior could differ",
                 "coverage": "No live state, sources, pools or authority checks", "time_basis": "Synthetic block 100 only",
                 "stale_when": "Replaced with actual captured target evidence", "discovery_claim": False, "discovery_ids": []}]
    report = {"schema_version": 1, "synthetic": True, "manifest_sha256": "", "target": copy.deepcopy(target),
              "metadata": copy.deepcopy(metadata), "safety": copy.deepcopy(safety),
              "verdict": "SYNTHETIC: no token verdict can be drawn; all risk dimensions remain unknown.",
              "conditions": "Offline helper validation only", "main_reasons": "No live evidence was collected",
              "strongest_contrary_evidence": "None supplied in this synthetic fixture",
              "unresolved_questions": "All economic and control questions remain unresolved",
              "change_evidence": "Actual chain-bound evidence and reconciled investigation are required",
              "findings": findings,
              "ratings": [{"id": d, "status": "unknown", "severity": "unknown", "likelihood": "unknown",
                           "confidence": "unknown", "coverage": "unavailable", "time_basis": "Synthetic block 100",
                           "finding_ids": ["F-coverage"], "rationale": "No live investigation; not a pass"} for d in DIMENSIONS]}
    bind(root, manifest, report)
    return manifest, report


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        p.error("output must be absent or empty; fixture generator never overwrites a bundle")
    build(args.output)
    print("Created SYNTHETIC offline fixture at", args.output.resolve())
