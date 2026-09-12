"""Small, offline EVM decoders. No cryptographic selector guessing or file writes."""
import re
from rpc_wire import data
from validate_bundle import address, integer, need, sha

VERSION = "1.0.0"
SOURCE_MATCH_VERSION = "1.1.0"
COMMON_METHODS = {
    "name()": "06fdde03", "symbol()": "95d89b41", "decimals()": "313ce567",
    "totalSupply()": "18160ddd", "owner()": "8da5cb5b", "balanceOf(address)": "70a08231",
    "allowance(address,address)": "dd62ed3e", "token0()": "0dfe1681", "token1()": "d21220a7",
    "getReserves()": "0902f1ac", "factory()": "c45a0155", "fee()": "ddca3f43",
}


def calldata(signature, arguments=(), method_identifiers=None, derive=False):
    """Encode only static common types. Selectors come from the common table, captured
    compiler methodIdentifiers, or explicit Keccak derivation of a verified-ABI signature."""
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\(([^()]*)\)", signature)
    need(match is not None, "unsupported function signature")
    selector = (method_identifiers or {}).get(signature, COMMON_METHODS.get(signature))
    if selector is None and derive:
        from keccak import selector as derive_selector
        selector = derive_selector(signature)
    need(isinstance(selector, str) and re.fullmatch(r"[0-9a-fA-F]{8}", selector),
         "selector unavailable; supply captured compiler methodIdentifiers or pass derive=True for a verified-ABI signature")
    types = match[2].split(",") if match[2] else []
    need(len(types) == len(arguments), "ABI argument count mismatch")
    words = []
    for typ, value in zip(types, arguments):
        if typ == "address":
            data(value, 20)  # Zero is a valid ABI argument, but never a target/scope identity.
            words.append("0" * 24 + value[2:].lower())
        elif typ == "bool":
            need(type(value) is bool, "bool argument required")
            words.append(format(int(value), "064x"))
        elif re.fullmatch(r"uint(?:8|16|32|64|128|256)", typ):
            integer(value, "ABI integer")
            need(value < 2 ** int(typ[4:]), "ABI integer overflow")
            words.append(format(value, "064x"))
        elif typ == "bytes32":
            data(value, 32)
            words.append(value[2:].lower())
        else:
            raise ValueError("unsupported ABI argument type; use a verified ABI implementation")
    return "0x" + selector.lower() + "".join(words)


def classify_clone(runtime):
    data(runtime)
    raw = bytes.fromhex(runtime[2:])
    result = {"parser_version": VERSION, "runtime_sha256": sha(raw), "implementation": None,
              "status": "unresolved", "pattern": "unsupported_or_not_a_standard_clone"}
    if not raw:
        result.update(status="no_code", pattern="empty")
    elif len(raw) == 45 and raw[:10].hex() == "363d3d373d3d3d363d73" and raw[30:].hex() == "5af43d82803e903d91602b57fd5bf3":
        result.update(status="recognized", pattern="erc1167_standard", implementation=address("0x" + raw[10:30].hex()))
    return result


def _cbor_metadata(raw):
    """Accept a bounded definite-length Solidity CBOR map plus its two-byte length."""
    need(3 <= len(raw) <= 4096 and int.from_bytes(raw[-2:], "big") == len(raw) - 2, "invalid CBOR metadata trailer")
    blob = raw[:-2]
    def parse(pos, depth=0):
        need(depth <= 8 and pos < len(blob), "unsupported CBOR metadata")
        byte, pos = blob[pos], pos + 1
        major, size = byte >> 5, byte & 31
        if size >= 24:
            need(size in (24, 25, 26, 27), "indefinite CBOR metadata unsupported")
            width = 1 << (size - 24)
            need(pos + width <= len(blob), "truncated CBOR metadata")
            size, pos = int.from_bytes(blob[pos:pos + width], "big"), pos + width
        if major in (0, 1):
            return size, pos
        if major in (2, 3):
            need(pos + size <= len(blob), "truncated CBOR bytes")
            value = blob[pos:pos + size]
            return (value.decode("utf-8") if major == 3 else value), pos + size
        if major == 5:
            need(size <= 16, "oversized CBOR map")
            result = {}
            for _ in range(size):
                key, pos = parse(pos, depth + 1)
                need(isinstance(key, str) and key not in result, "invalid CBOR key")
                result[key], pos = parse(pos, depth + 1)
            return result, pos
        if major == 7 and size in (20, 21):
            return size == 21, pos
        raise ValueError("unsupported CBOR metadata value")
    obj, end = parse(0)
    need(isinstance(obj, dict) and obj and set(obj) <= {"ipfs", "bzzr0", "bzzr1", "solc", "experimental"}
         and end == len(blob), "unsupported Solidity metadata map")


def _metadata_boundary(code, start, allow_literal_tail=True):
    """Conservative delimiter/jump-target check; not general EVM equivalence."""
    pos, delimiter, destinations = 0, None, []
    while pos < len(code):
        opcode = code[pos]
        if pos < start and opcode == 0xfe:
            delimiter = pos
        if opcode == 0x5b:
            destinations.append(pos)
        pos += 1 + (opcode - 0x5f if 0x60 <= opcode <= 0x7f else 0)
    # Solidity can place literal data between INVALID and terminal CBOR. The
    # whole suffix must remain unreachable by fallthrough or a valid jump;
    # checking only metadata would miss a jump into those preceding literals.
    # Only CBOR is replaced below, so literal bytes still compare exactly.
    need(delimiter is not None and (allow_literal_tail or delimiter == start - 1)
         and not any(pos > delimiter for pos in destinations),
         "metadata lacks an INVALID delimiter or contains an executable jump target")


def compare_source(runtime, source, chain_id, contract_address, comparison_version=SOURCE_MATCH_VERSION):
    """Reproduce a Sourcify-published compilation comparison, never a local compile.

    Replacement regions must agree with the supplied standard compiler output.
    Unsupported transformations fail closed instead of masking executable bytes.
    """
    need(comparison_version in ("1.0.0", SOURCE_MATCH_VERSION), "unsupported source comparison version")
    data(runtime)
    need(int(source["chainId"]) == chain_id and address(source["address"]) == address(contract_address), "source identity mismatch")
    compilation = source["compilation"]
    identifier = compilation["fullyQualifiedName"]
    filename, contract = identifier.rsplit(":", 1)
    need(bool(source["sources"]) and bool(source["stdJsonInput"]["sources"]), "source inputs missing")
    need(set(source["sources"]) == set(source["stdJsonInput"]["sources"])
         and all(item["content"] == source["stdJsonInput"]["sources"][name]["content"]
                 for name, item in source["sources"].items()), "published source/compiler input mismatch")
    output = source["stdJsonOutput"]["contracts"][filename][contract]["evm"]["deployedBytecode"]
    bytecode = source["runtimeBytecode"]
    compiled = output["object"]
    compiled = compiled if compiled.startswith("0x") else "0x" + compiled
    data(compiled)
    data(bytecode["recompiledBytecode"])
    need(compiled.lower() == bytecode["recompiledBytecode"].lower(), "compiler output/recompiled bytes mismatch")
    for field in ("immutableReferences", "linkReferences"):
        need(bytecode.get(field, {}) == output.get(field, {}), "runtime/compiler reference mismatch")
    expected = bytearray.fromhex(compiled[2:])
    previous_end, applied = 0, []
    values = bytecode.get("transformationValues", {})
    transformations = bytecode.get("transformations", [])
    for transform in transformations:
        integer(transform["offset"], "transformation offset")
    for transform in sorted(transformations, key=lambda x: x["offset"]):
        need(transform["type"] == "replace", "unsupported runtime transformation")
        reason, tid = transform["reason"], transform.get("id")
        start = integer(transform["offset"], "transformation offset")
        if reason == "immutable":
            replacement = values["immutables"][tid]
            refs = output.get("immutableReferences", {}).get(tid, [])
        elif reason == "library":
            replacement = values["libraries"][tid]
            data(replacement, 20)
            library_file, library_name = tid.rsplit(":", 1)
            refs = output.get("linkReferences", {}).get(library_file, {}).get(library_name, [])
        elif reason == "cborAuxdata":
            replacement = values["cborAuxdata"][tid]
            aux = bytecode["cborAuxdata"][tid]
            data(aux["value"])
            old = bytes.fromhex(aux["value"][2:])
            _cbor_metadata(old)
            need(aux["offset"] == start and start + len(old) == len(expected)
                 and bytes(expected[start:]) == old, "metadata transform outside verified terminal metadata")
            _metadata_boundary(expected, start, comparison_version != "1.0.0")
            _metadata_boundary(expected[:start] + bytes.fromhex(replacement[2:]), start, comparison_version != "1.0.0")
            refs = [{"start": start, "length": len(old)}]
            _cbor_metadata(bytes.fromhex(replacement[2:]))
        else:
            raise ValueError("unsupported runtime transformation reason")
        data(replacement)
        replacement = bytes.fromhex(replacement[2:])
        need(any(r["start"] == start and r["length"] == len(replacement) for r in refs), "replacement outside compiler reference")
        need(bool(replacement) and start + len(replacement) <= len(expected) and start >= previous_end, "overlapping/out-of-bounds transformation")
        previous_end = start + len(replacement)
        expected[start:start + len(replacement)] = replacement
        applied.append(transform)
    data(bytecode["onchainBytecode"])
    fresh = bytes.fromhex(runtime[2:])
    return {"tool": "evm_decode.compare_source", "version": comparison_version,
            "status": "matched" if bytes(expected) == fresh == bytes.fromhex(bytecode["onchainBytecode"][2:]) else "mismatch",
            "compilation_basis": "Sourcify-published compiler input/output; no independent local compilation",
            "compiler_version": compilation["compilerVersion"], "contract_identifier": identifier,
            "runtime_sha256": sha(fresh), "recompiled_sha256": sha(bytes.fromhex(compiled[2:])),
            "transformed_sha256": sha(bytes(expected)), "transformations": applied,
            "limitations": "Provider/source-service honesty and compiler provenance require review; source correspondence is not a security audit."}


def main():
    import argparse
    import json
    from pathlib import Path
    from validate_bundle import read_json
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    call = sub.add_parser("calldata")
    call.add_argument("signature")
    call.add_argument("--arguments", default="[]", help="JSON array of static ABI arguments")
    call.add_argument("--method-identifiers", type=Path, help="captured compiler signature-to-selector JSON map")
    call.add_argument("--derive", action="store_true", help="derive the selector with Keccak from a verified-ABI signature")
    clone = sub.add_parser("clone")
    clone.add_argument("runtime", help="exact captured 0x-prefixed runtime")
    for name in ("selector", "topic"):
        derived = sub.add_parser(name, help="Keccak-derived function selector or event topic for a verified signature")
        derived.add_argument("signature")
    pool = sub.add_parser("poolid", help="Uniswap v4 PoolId from an exact pool key")
    for flag in ("currency0", "currency1", "hooks"):
        pool.add_argument("--" + flag, required=True)
    pool.add_argument("--fee", type=int, required=True)
    pool.add_argument("--tick-spacing", type=int, required=True)
    args = p.parse_args()
    try:
        if args.action == "clone":
            print(json.dumps(classify_clone(args.runtime), sort_keys=True))
        elif args.action in ("selector", "topic"):
            from keccak import selector as derive_selector, topic as derive_topic
            print(("0x" + derive_selector(args.signature)) if args.action == "selector" else derive_topic(args.signature))
        elif args.action == "poolid":
            from keccak import pool_id
            print(pool_id(args.currency0, args.currency1, args.fee, args.tick_spacing, args.hooks))
        else:
            print(calldata(args.signature, json.loads(args.arguments), read_json(args.method_identifiers) if args.method_identifiers else None, args.derive))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("Decode failed: " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
