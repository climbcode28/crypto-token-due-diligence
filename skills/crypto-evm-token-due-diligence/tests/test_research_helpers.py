import copy
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend_fixtures import CHAIN, TOKEN, ALICE, FakeRpc, header, plan
from fixtures import abi_string
from backend_common import Cache, canonical, sha, write_new
from bootstrap import bootstrap
from bundle_assemble import assemble, intake, import_collection, freeze, read_draft, save_draft, add_artifact, source_match
from test_stopping_review import review_cutoff
from evm_decode import calldata, classify_clone, compare_source
from decision_fixtures import cutoff_decision
from validate_bundle import METADATA, validate

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def source_fixture(runtime="0x60006000f3"):
    sources = {"Token.sol": {"content": "contract Token {} // synthetic compilation fixture"}}
    output = {"object": runtime[2:], "immutableReferences": {}, "linkReferences": {}}
    return {"chainId": str(CHAIN), "address": TOKEN, "sources": sources,
            "compilation": {"fullyQualifiedName": "Token.sol:Token", "compilerVersion": "synthetic"},
            "stdJsonInput": {"sources": copy.deepcopy(sources)},
            "stdJsonOutput": {"contracts": {"Token.sol": {"Token": {"evm": {"deployedBytecode": output}}}}},
            "runtimeBytecode": {"onchainBytecode": runtime, "recompiledBytecode": runtime,
                                "immutableReferences": {}, "linkReferences": {}, "transformations": [], "transformationValues": {}}}


def metadata_source_fixture(prefix, old=None, new=None):
    """Synthetic terminal CBOR replacement; all prefix bytes must stay exact."""
    old = bytes.fromhex(old or "a164736f6c6343000807")
    new = bytes.fromhex(new or "a164736f6c6343000808")
    old += len(old).to_bytes(2, "big")
    new += len(new).to_bytes(2, "big")
    compiled, deployed = "0x" + prefix.hex() + old.hex(), "0x" + prefix.hex() + new.hex()
    source = source_fixture(compiled)
    source["runtimeBytecode"].update(onchainBytecode=deployed,
        cborAuxdata={"1": {"offset": len(prefix), "value": "0x" + old.hex()}},
        transformations=[{"type": "replace", "offset": len(prefix), "reason": "cborAuxdata", "id": "1"}],
        transformationValues={"cborAuxdata": {"1": "0x" + new.hex()}})
    return source, deployed


class ResearchHelperTests(unittest.TestCase):
    def test_comparison_version_preserves_legacy_replay_boundary(self):
        source, deployed = metadata_source_fixture(bytes.fromhex('6000fe112233'))
        self.assertEqual(compare_source(deployed, source, CHAIN, TOKEN)['version'], '1.1.0')
        with self.assertRaisesRegex(ValueError, 'INVALID delimiter'):
            compare_source(deployed, source, CHAIN, TOKEN, '1.0.0')
        adjacent, runtime = metadata_source_fixture(bytes.fromhex('6000fe'))
        self.assertEqual(compare_source(runtime, adjacent, CHAIN, TOKEN, '1.0.0')['version'], '1.0.0')
        with self.assertRaisesRegex(ValueError, 'unsupported source comparison version'):
            compare_source(runtime, adjacent, CHAIN, TOKEN, 'unregistered')

    def test_later_non_runtime_import_does_not_force_new_state_metadata_reads(self):
        from rpc_collect import Collector
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rpc = FakeRpc()
            rpc.overrides['eth_blockNumber'] = lambda q: '0x65'
            cache = Cache(root / 'cache.sqlite')
            try:
                bootstrap(root / 'boot', {'chain_id': CHAIN, 'address': TOKEN}, cache, rpc)
                intake(root / 'draft', {'chain_id': CHAIN, 'address': TOKEN}, 'Synthetic scope', 'Synthetic materiality', True)
                import_collection(root / 'draft', root / 'boot/collection', True)
                before, _ = assemble(root / 'draft', checkpoint=True)
                later = {'schema_version': 1, 'target': {'chain_id': CHAIN, 'address': TOKEN},
                         'pins': [{'id': 'later', 'number': 102}],
                         'queries': [{'id': 'other-state', 'pin_id': 'later', 'method': 'eth_getBalance', 'params': [ALICE]}]}
                Collector(root / 'later', cache, rpc, 'fixture').collect(later)
                draft = import_collection(root / 'draft', root / 'later', True)
                calls = len(rpc.calls)
                after, _ = assemble(root / 'draft', checkpoint=True)
                self.assertEqual(before['chains'][0]['current_pin'], after['chains'][0]['current_pin'])
                self.assertEqual(before['target']['metadata'], after['target']['metadata'])
                self.assertEqual(len(after['chains'][0]['pins']), 2)
                self.assertEqual(len(rpc.calls), calls)
                draft['current_pin'] = next(p['id'] for p in draft['pins'] if p['number'] == 102)
                save_draft(root / 'draft', draft)
                with self.assertRaisesRegex(ValueError, 'target runtime evidence'):
                    assemble(root / 'draft', checkpoint=True)
            finally:
                cache.close()

    def test_clone_parser_exact_and_near_neighbors(self):
        runtime = "0x363d3d373d3d3d363d73" + ALICE[2:] + "5af43d82803e903d91602b57fd5bf3"
        self.assertEqual(classify_clone(runtime)["implementation"], ALICE)
        for code in (runtime[:-2], runtime + "00", "0x00" + runtime[2:], "0x60006000f3"):
            self.assertEqual(classify_clone(code)["status"], "unresolved")
        self.assertEqual(classify_clone("0x")["status"], "no_code")
        with self.assertRaises(ValueError):
            classify_clone("0x1")

    def test_calldata_without_new_cryptography(self):
        self.assertEqual(calldata("owner()"), "0x8da5cb5b")
        self.assertEqual(calldata("balanceOf(address)", ["0x" + "00" * 20]), "0x70a08231" + "00" * 32)
        self.assertEqual(calldata("balanceOf(address)", [ALICE]), "0x70a08231" + "0" * 24 + ALICE[2:])
        self.assertEqual(calldata("custom(uint8)", [255], {"custom(uint8)": "12345678"}), "0x12345678" + format(255, "064x"))
        for signature, args in (("custom(uint8)", [256]), ("unknown()", []), ("balanceOf(address)", ["0x123"])):
            with self.assertRaises(ValueError):
                calldata(signature, args)

    def test_exact_source_comparison_and_mismatch(self):
        source = source_fixture()
        self.assertEqual(compare_source("0x60006000f3", source, CHAIN, TOKEN)["status"], "matched")
        self.assertEqual(compare_source("0x60016000f3", source, CHAIN, TOKEN)["status"], "mismatch")
        with self.assertRaisesRegex(ValueError, "identity"):
            compare_source("0x60006000f3", source, CHAIN, ALICE)

    def test_compiler_bound_immutable_and_arbitrary_mask(self):
        compiled, deployed = "0x7f" + "00" * 32 + "00", "0x7f" + "12" * 32 + "00"
        source = source_fixture(compiled)
        runtime = source["runtimeBytecode"]
        refs = {"1": [{"start": 1, "length": 32}]}
        runtime.update(onchainBytecode=deployed, immutableReferences=refs,
                       transformations=[{"type": "replace", "offset": 1, "reason": "immutable", "id": "1"}],
                       transformationValues={"immutables": {"1": "0x" + "12" * 32}})
        output = source["stdJsonOutput"]["contracts"]["Token.sol"]["Token"]["evm"]["deployedBytecode"]
        output["immutableReferences"] = copy.deepcopy(refs)
        self.assertEqual(compare_source(deployed, source, CHAIN, TOKEN)["status"], "matched")
        runtime["transformations"][0]["offset"] = 0
        with self.assertRaisesRegex(ValueError, "outside compiler reference"):
            compare_source(deployed, source, CHAIN, TOKEN)
        runtime["transformations"][0]["offset"] = 1
        runtime["immutableReferences"]["1"][0]["start"] = 0
        with self.assertRaisesRegex(ValueError, "reference mismatch"):
            compare_source(deployed, source, CHAIN, TOKEN)

    def test_metadata_substitution_cannot_mask_code(self):
        old = bytes.fromhex("a164736f6c6343000807")
        new = bytes.fromhex("a164736f6c6343000808")
        old += len(old).to_bytes(2, "big")
        new += len(new).to_bytes(2, "big")
        compiled, deployed = "0x6000fe" + old.hex(), "0x6000fe" + new.hex()
        source = source_fixture(compiled)
        runtime = source["runtimeBytecode"]
        runtime.update(onchainBytecode=deployed, cborAuxdata={"1": {"offset": 3, "value": "0x" + old.hex()}},
                       transformations=[{"type": "replace", "offset": 3, "reason": "cborAuxdata", "id": "1"}],
                       transformationValues={"cborAuxdata": {"1": "0x" + new.hex()}})
        self.assertEqual(compare_source(deployed, source, CHAIN, TOKEN)["status"], "matched")
        runtime["transformations"][0]["offset"] = 0
        with self.assertRaisesRegex(ValueError, "outside verified terminal"):
            compare_source(deployed, source, CHAIN, TOKEN)

    def test_executable_cbor_cannot_be_masked_as_metadata(self):
        old = "a164697066734b5b60015f5260205ff300000012"
        new = old.replace("6001", "6002")
        source = source_fixture("0x600a56" + old)
        source["runtimeBytecode"].update(onchainBytecode="0x600a56" + new,
            cborAuxdata={"1": {"offset": 3, "value": "0x" + old}},
            transformations=[{"type": "replace", "offset": 3, "reason": "cborAuxdata", "id": "1"}],
            transformationValues={"cborAuxdata": {"1": "0x" + new}})
        with self.assertRaisesRegex(ValueError, "INVALID delimiter|jump target"):
            compare_source("0x600a56" + new, source, CHAIN, TOKEN)

    def test_metadata_after_unreachable_literal_data(self):
        # Representative compiler literal tails: an event topic, or a slot,
        # revert string and event topic. The bytes remain outside the transform.
        topic = bytes.fromhex("ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
        slot = bytes.fromhex("360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc")
        for literals in (topic, slot + b"Address: low-level delegate call failed" + topic,
                         bytes.fromhex("605b")):
            with self.subTest(literals=literals.hex()):
                source, deployed = metadata_source_fixture(bytes.fromhex("6000fe") + literals)
                self.assertEqual(compare_source(deployed, source, CHAIN, TOKEN)["status"], "matched")

    def test_metadata_transform_does_not_mask_literal_data_changes(self):
        source, deployed = metadata_source_fixture(bytes.fromhex("6000fe112233"))
        altered = bytearray.fromhex(deployed[2:])
        altered[4] ^= 1
        altered = "0x" + altered.hex()
        source["runtimeBytecode"]["onchainBytecode"] = altered
        self.assertEqual(compare_source(altered, source, CHAIN, TOKEN)["status"], "mismatch")

    def test_metadata_cannot_be_entered_through_literal_gap(self):
        # JUMP enters the gap at offset 4, then falls through into metadata.
        source, deployed = metadata_source_fixture(bytes.fromhex("600456fe5b"))
        with self.assertRaisesRegex(ValueError, "jump target"):
            compare_source(deployed, source, CHAIN, TOKEN)

    def test_metadata_jump_target_rejected_on_both_sides_of_replacement(self):
        # A well-formed CBOR byte string can also contain a valid JUMPDEST.
        with_jump = "a164697066734b5b60015f5260205ff30000"
        without_jump = with_jump.replace("4b5b", "4b00")
        for old, new in ((with_jump, without_jump), (without_jump, with_jump)):
            with self.subTest(old=old, new=new):
                source, deployed = metadata_source_fixture(bytes.fromhex("6000fe"), old, new)
                with self.assertRaisesRegex(ValueError, "jump target"):
                    compare_source(deployed, source, CHAIN, TOKEN)

    def test_metadata_delimiter_inside_push_operand_is_not_a_barrier(self):
        source, deployed = metadata_source_fixture(bytes.fromhex("60fe00"))
        with self.assertRaisesRegex(ValueError, "INVALID delimiter"):
            compare_source(deployed, source, CHAIN, TOKEN)

    def test_registered_source_comparison_replays_and_binds_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rpc = Path(tmp), FakeRpc()
            rpc.overrides["eth_blockNumber"] = lambda q: "0x65"
            cache = Cache(root / "cache.sqlite")
            try:
                bootstrap(root / "boot", {"chain_id": CHAIN, "address": TOKEN}, cache, rpc)
            finally:
                cache.close()
            intake(root / "draft", {"chain_id": CHAIN, "address": TOKEN}, "Synthetic source test", "All authority", True)
            draft = import_collection(root / "draft", root / "boot/collection", True)
            runtime = next(e for e in draft["evidence"] if e["query"]["method"] == "eth_getCode")
            source = root / "source.json"
            write_new(source, source_fixture())
            descriptor = {**runtime, "id": "source", "kind": "document", "query": {"source_urls": ["https://sourcify.dev/"]}}
            descriptor.pop("collection_provenance")
            add_artifact(root / "draft", source, descriptor)
            source_match(root / "draft", runtime["id"], "source", "comparison")
            draft = read_draft(root / "draft")
            review_cutoff(draft["coverage_records"])
            draft["decision_review"] = cutoff_decision(draft["coverage_records"])
            save_draft(root / "draft", draft)
            out = freeze(root / "draft", root / "report", True, checkpoint=True)
            m, r = validate(out, True)
            self.assertIn("comparison", [e["id"] for e in m["evidence"]])
            source_row = next(e for e in m["evidence"] if e["id"] == "source")
            (out / source_row["artifact"]).unlink()
            with self.assertRaisesRegex(ValueError, "missing evidence"):
                validate(out, True)

    def test_imports_have_no_filesystem_or_network_side_effects(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("file mutation/read on import")), \
             patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network on import")):
            for name in ("bootstrap", "bundle_assemble", "source_lookup", "evm_decode"):
                importlib.reload(importlib.import_module(name))

    def test_bootstrap_invalid_intake_stops_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rpc = Path(tmp), FakeRpc()
            cache = Cache(root / "cache.sqlite")
            try:
                for addr, budget in (("0x123", 20), (TOKEN, 9)):
                    with self.assertRaises(ValueError):
                        bootstrap(root / "out", {"chain_id": CHAIN, "address": addr}, cache, rpc, max_requests=budget)
                self.assertEqual(rpc.calls, [])
                self.assertFalse((root / "out").exists())
            finally:
                cache.close()

    def test_two_target_supported_command_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def run(script, *args):
                result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run("investigation.py", "init", root / "session.sqlite", "--max-requests", 20, "--timeout", 120)
            for index, token in enumerate((TOKEN, ALICE)):
                responses = [{"method": "eth_chainId", "params": [], "response": {"result": hex(CHAIN)}},
                             {"method": "eth_blockNumber", "params": [], "response": {"result": "0x65"}},
                             {"method": "eth_getBlockByNumber", "params": ["0x65", False], "response": {"result": header(101)}},
                             {"method": "eth_getCode", "params": [token, "0x65"], "response": {"result": "0x60006000f3"}}]
                for field, selector in METADATA.items():
                    value = abi_string("SYNTH" + str(index)) if field in ("name", "symbol") else "0x" + format(18 if field == "decimals" else 1000, "064x")
                    responses.append({"method": "eth_call", "params": [{"to": token, "data": selector}, "0x65"], "response": {"result": value}})
                fixture = root / (str(index) + "-fixture.json")
                write_new(fixture, {"schema_version": 1, "synthetic": True, "responses": responses})
                draft, boot, out = root / (str(index) + "-draft"), root / (str(index) + "-boot"), root / (str(index) + "-report")
                run("bundle_assemble.py", "intake", draft, "--chain-id", CHAIN, "--address", token,
                    "--question", "Synthetic intake only", "--materiality", "All authority material", "--synthetic")
                self.assertEqual(len(read_draft(draft)["coverage_records"]), 11)
                run("bootstrap.py", "--chain-id", CHAIN, "--address", token, "--out", boot, "--cache", root / (str(index) + ".sqlite"),
                    "--fixture", fixture, "--allow-synthetic", "--max-requests", 10, "--session", root / "session.sqlite")
                run("bundle_assemble.py", "import", draft, boot / "collection", "--allow-synthetic")
                run("bundle_assemble.py", "import", draft, boot / "collection", "--allow-synthetic")
                self.assertEqual(len(read_draft(draft)["collections"]), 1)
                lane = root / (str(index) + "-closure.json")
                coverage = review_cutoff(read_draft(draft)["coverage_records"])
                write_new(lane, {"coverage_records": coverage, "decision_review": cutoff_decision(coverage)})
                run("bundle_assemble.py", "handoff", draft, lane)
                run("bundle_assemble.py", "freeze", draft, "--out", out, "--allow-synthetic", "--checkpoint")
                run("validate_bundle.py", out, "--allow-synthetic", "--rendered", out / "report.md")
                manifest, report = validate(out, True)
                self.assertEqual(manifest["target"]["observed"]["address"], token)
                self.assertEqual(report["metadata"]["name"]["value"], "SYNTH" + str(index))
                self.assertTrue(all(x["status"] == "unknown" for x in report["ratings"]))
                self.assertEqual(report["summary"][0]["signal"], "Unverified")
                self.assertEqual(report["closure_review_version"], 1)
                self.assertIn("⚪ **Unverified**", (out / "report.md").read_text())
                self.assertEqual(len({x["proposition"] for x in report["findings"]}), 11)
                chain = next(e for e in manifest["evidence"] if e["query"]["method"] == "eth_chainId")
                self.assertIsNone(chain["pin_id"])


if __name__ == "__main__":
    unittest.main()
