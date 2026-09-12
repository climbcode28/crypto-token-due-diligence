"""Synthetic offline regression; no live keys, network, trades or detection benchmark."""
import base64
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import solana_common as common
import solana_collect as collect
import solana_legacy_v1 as bundle  # Original schema-1 compatibility suite.

MINT, GENESIS, AUTH, HASH = (common.b58encode(bytes([n])*32) for n in (1, 2, 3, 4))
TARGET = {"family": "solana", "genesis_hash": GENESIS, "mint": MINT}
PIN_TIME = int(time.time())


def mint_bytes(authority=False, extensions=None):
    raw = struct.pack("<I", int(authority)) + bytes([3 if authority else 0])*32
    raw += struct.pack("<QBB", 2**63+5, 9, 1) + bytes(36)
    if extensions is not None:
        raw += bytes(83) + b"\x01"
        for kind, value in extensions:
            raw += struct.pack("<HH", kind, len(value)) + value
    return raw


def account(raw=None, owner=common.TOKEN_PROGRAM):
    raw = mint_bytes() if raw is None else raw
    return {"owner": owner, "executable": False, "data": [base64.b64encode(raw).decode(), "base64"], "space": len(raw)}


class FakeTransport:
    def __init__(self, url, headers, **kwargs):
        self.mode = url
        self.last_redacted = False

    def __call__(self, req):
        eid = req["id"]
        if eid in ("genesis", "genesis_recheck"):
            value = AUTH if self.mode == "wrong_network" or self.mode == "network_switch" and eid == "genesis_recheck" else GENESIS
        elif eid in ("mint", "mint_recheck"):
            raw = mint_bytes()
            owner = common.TOKEN_PROGRAM
            if self.mode == "changed" and eid == "mint_recheck":
                raw = mint_bytes(authority=True)
            if self.mode == "bad_mint":
                raw = bytes(165)
            if self.mode == "unknown_program":
                owner = AUTH
            if self.mode == "unknown_extension":
                owner, raw = common.TOKEN_2022, mint_bytes(extensions=[(60000, b"hello")])
            value = {"context": {"slot": 100 if eid == "mint" else 102}, "value": account(raw, owner)}
            if self.mode == "backwards" and eid == "mint_recheck":
                value["context"]["slot"] = 99
            if self.mode == "missing_account":
                value["value"] = None
        elif eid == "largest":
            value = {"context": {"slot": 101}, "value": [{"address": AUTH, "amount": "123", "decimals": 9}]}
        else:
            value = {"blockhash": HASH, "previousBlockhash": AUTH, "parentSlot": req["params"][0]-1,
                     "blockTime": PIN_TIME}
            if self.mode == "reorg" and eid == "block_recheck":
                value["blockhash"] = MINT
            if self.mode == "stale":
                value["blockTime"] = 123
            if self.mode == "null_time":
                value["blockTime"] = None
            if self.mode == "future":
                value["blockTime"] += 600
        if self.mode == "error" and eid == "mint_recheck":
            return {"jsonrpc": "2.0", "id": eid, "error": {"code": -32000, "message": "unavailable"}}
        if self.mode == "secret" and eid == "mint_recheck":
            raise OSError("SECRET_TEST_KEY https://secret.invalid")
        if self.mode == "redacted" and eid == "mint_recheck":
            self.last_redacted = True
        return {"jsonrpc": "2.0", "id": "wrong" if self.mode == "bad_id" else eid, "result": value}


def fake_worker(root, config, target, largest, cap):
    collect.worker(root, config, target, largest, cap, FakeTransport)


def stalled_worker(root, config, target, largest, cap):
    collect.write_atomic(Path(root)/"attempts"/"genesis.json", {"request": {"method": "getGenesisHash"}})
    time.sleep(30)


class MintTests(unittest.TestCase):
    def test_base58_preserves_leading_zeros_and_case(self):
        for raw in (bytes(32), bytes(31)+b"\x01", bytes(range(32))):
            self.assertEqual(common.pubkey(common.b58encode(raw)), common.b58encode(raw))
        for key in ("0x"+"12"*20, "1"*31, "1"*33, "0"*44, "z"*44):
            with self.subTest(key=key), self.assertRaises(ValueError):
                common.pubkey(key)

    def test_integer_supply_and_absent_authority(self):
        row = common.decode_mint(account())
        self.assertEqual(row["supply_atomic"], str(2**63+5))
        self.assertIsNone(row["mint_authority"])
        self.assertFalse(row["unknown_extensions"])

    def test_some_zero_key_is_not_revocation(self):
        raw = b"\x01\0\0\0" + mint_bytes()[4:]
        self.assertEqual(common.decode_mint(account(raw))["mint_authority"], "1"*32)

    def test_extension_controls_survive_revoked_base_authorities(self):
        extensions = [(12, bytes([3])*32), (14, bytes([3])*32+bytes([4])*32),
                      (6, b"\x02"), (26, bytes([3])*32+b"\x01"), (9, b"")]
        row = common.decode_mint(account(mint_bytes(extensions=extensions), common.TOKEN_2022))
        self.assertIsNone(row["mint_authority"])
        self.assertEqual(row["extensions"][0]["authority"], AUTH)
        self.assertEqual(row["extensions"][1]["program"], HASH)
        self.assertEqual(row["extensions"][2]["state"], "frozen")
        self.assertTrue(row["extensions"][3]["paused"])

    def test_transfer_fee_epochs_and_caps_are_not_collapsed(self):
        fee = bytes([3])*32 + bytes(32) + struct.pack("<Q", 500)
        fee += struct.pack("<QQH", 1, 10, 20) + struct.pack("<QQH", 100, 30, 10000)
        row = common.decode_mint(account(mint_bytes(extensions=[(1, fee)]), common.TOKEN_2022))["extensions"][0]
        self.assertEqual(row["newer"]["basis_points"], 10000)
        self.assertEqual(row["older"]["maximum_fee_atomic"], "10")
        self.assertNotIn("active_fee", row)

    def test_unknown_extension_is_preserved(self):
        row = common.decode_mint(account(mint_bytes(extensions=[(60000, b"abc")]), common.TOKEN_2022))
        self.assertEqual(row["unknown_extensions"], [60000])

    def test_malformed_or_wrong_account_never_decodes_as_mint(self):
        base = mint_bytes()
        cases = [base[:45]+b"\0"+base[46:], b"\x02\0\0\0"+base[4:], bytes(165), bytes(355),
                 mint_bytes(extensions=[(12, b"x")]), mint_bytes(extensions=[(12, bytes(32)), (12, bytes(32))]),
                 mint_bytes(extensions=[(7, b"")]), mint_bytes(extensions=[(6, b"\x05")]),
                 mint_bytes(extensions=[])+b"\x12"]
        for raw in cases:
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                common.decode_mint(account(raw, common.TOKEN_2022))
        with self.assertRaises(ValueError):
            common.decode_mint(account(owner=AUTH))
        invalid = account()
        invalid["data"][0] = "%%%"
        with self.assertRaises(ValueError):
            common.decode_mint(invalid)


class CollectorTests(unittest.TestCase):
    def packet(self, mode="normal", largest=False):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        for folder in ("attempts", "evidence"):
            (root/folder).mkdir()
        collect.worker(root, {"url": mode, "headers": {}}, TARGET, largest, 9, FakeTransport)
        return root, collect.summarize(root, TARGET, largest)

    def test_distinct_contexts_remain_samples_and_never_safety_pass(self):
        root, row = self.packet(largest=True)
        self.assertTrue(row["sample_fresh"])
        self.assertEqual([x["slot"] for x in row["samples"]], [100, 102])
        self.assertEqual(row["verdict"], "insufficient_evidence")
        self.assertEqual(row["coverage"]["liquidity_and_custody"], "unknown")
        self.assertEqual(len(list((root/"attempts").glob("*.json"))), 9)
        self.assertTrue(any("top 20" in x for x in row["critical_unknowns"]))

    def test_wrong_network_stops_before_account_reads(self):
        root, row = self.packet("wrong_network")
        self.assertEqual(row["identity"], "network_mismatch")
        self.assertEqual(len(list((root/"attempts").glob("*.json"))), 1)
        self.assertFalse(row["observations"])

    def test_failed_or_changed_evidence_does_not_produce_current_observations(self):
        for mode in ("changed", "reorg", "network_switch", "bad_mint", "unknown_program", "backwards",
                     "missing_account", "stale", "future", "null_time", "error", "bad_id", "redacted", "secret"):
            with self.subTest(mode=mode):
                root, row = self.packet(mode)
                self.assertFalse(row["observations"])
                self.assertIsNone(row["mint"])
                self.assertEqual(row["verdict"], "insufficient_evidence")
                self.assertNotIn("SECRET_TEST_KEY", "".join(p.read_text() for p in root.rglob("*.json")))

    def test_unknown_extension_retains_supported_base_observations_and_gap(self):
        _, row = self.packet("unknown_extension")
        self.assertTrue(row["sample_fresh"])
        self.assertEqual(row["mint"]["unknown_extensions"], [60000])
        self.assertTrue(any("Unsupported extensions" in x for x in row["critical_unknowns"]))

    def test_wrong_mint_query_is_not_accepted_even_if_response_looks_valid(self):
        root, _ = self.packet()
        path = root/"evidence"/"mint.json"
        packet = json.loads(path.read_text())
        packet["request"]["params"][0] = AUTH
        path.write_text(json.dumps(packet))
        self.assertFalse(collect.summarize(root, TARGET)["observations"])

    def test_process_preserves_hashes_and_reproducible_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)/"run"
            row = collect.run_bounded(root, {"url": "normal", "headers": {}}, TARGET, seconds=5, worker_target=fake_worker)
            self.assertTrue(row["sample_fresh"])
            self.assertTrue(row["synthetic"])
            self.assertFalse(row["timed_out"])
            self.assertEqual(bundle.collection(root, allow_synthetic=True), row)
            with self.assertRaises(ValueError):
                bundle.collection(root)
            path = root/"summary.json"
            row["mint"]["mint_authority"] = AUTH
            path.write_text(json.dumps(row))
            with self.assertRaises(ValueError):
                bundle.collection(root, allow_synthetic=True)

    def test_timeout_preserves_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            start = time.monotonic()
            row = collect.run_bounded(Path(td)/"run", {}, TARGET, seconds=0.8, worker_target=stalled_worker)
            self.assertLess(time.monotonic()-start, 3)
            self.assertTrue(row["timed_out"])
            self.assertEqual(row["attempt_upper_bound"], 1)

    def test_invalid_inputs_do_not_create_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            for seconds in (0, 56, True, float("nan"), float("inf")):
                with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                    collect.run_bounded(Path(td)/"run", {}, TARGET, seconds=seconds)
            with self.assertRaises(ValueError):
                collect.run_bounded(Path(td)/"run", {}, {**TARGET, "mint": "0x"+"12"*20})
            self.assertFalse(list(Path(td).iterdir()))

    def test_drpc_approval_and_offline_fallback(self):
        args = collect.parser().parse_args(["--allow-network", "--cost-policy", "free"])
        with patch.dict(os.environ, {"SOLANA_RPC_URL": "https://lb.drpc.live/solana", "DRPC_API_KEY": "SECRET_TEST_KEY"}, clear=True):
            row = collect.provider_availability(args)
        self.assertEqual(row["reason"], "paid_usage_not_authorized")
        result = subprocess.run([sys.executable, str(SCRIPTS/"solana_collect.py"), "--check-availability"],
                                env={"PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["network_requests"], 0)

    def test_configured_unapproved_invocation_creates_no_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run([sys.executable, str(SCRIPTS/"solana_collect.py"),
                                     "--out", str(Path(td)/"run"), "--allow-network", "--cost-policy", "paid"],
                env={"SOLANA_RPC_URL": "https://lb.drpc.live/solana", "DRPC_API_KEY": "SYNTHETIC-SECRET",
                     "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "invocation_required")
            self.assertEqual(json.loads(result.stdout)["network_requests"], 0)
            self.assertNotIn("SYNTHETIC-SECRET", result.stdout + result.stderr)
            self.assertFalse(list(Path(td).iterdir()))


class BundleTests(unittest.TestCase):
    def root(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        bundle.initialize(root, TARGET)
        return root

    def test_partial_initialization_validates_and_cannot_claim_completed(self):
        root = self.root()
        manifest, report = bundle.validate(root)
        self.assertEqual(report["status"], "partial")
        report["status"] = "completed"
        (root/"report.json").write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            bundle.validate(root)

    def test_unknown_cannot_be_promoted_to_pass(self):
        root = self.root()
        report = json.loads((root/"report.json").read_text())
        report["ratings"][0]["status"] = "no_issue_detected"
        (root/"report.json").write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            bundle.validate(root)

    def test_target_and_manifest_hash_are_bound(self):
        root = self.root()
        manifest = json.loads((root/"manifest.json").read_text())
        manifest["target"]["mint"] = AUTH
        (root/"manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            bundle.validate(root)

    def test_artifact_escape_and_modified_bytes_rejected(self):
        root = self.root()
        with self.assertRaises(ValueError):
            bundle.artifact(root, "../outside", "0"*64)
        (root/"evidence.json").write_text("hello")
        with self.assertRaises(ValueError):
            bundle.artifact(root, "evidence.json", "0"*64)

    def test_independent_rpc_state_requires_matching_rechecked_slot(self):
        root = self.root()
        manifest = json.loads((root/"manifest.json").read_text())
        packets = {
            "genesis": ("getGenesisHash", [], GENESIS),
            "mint": ("getAccountInfo", collect.account_params(MINT), {"context": {"slot": 100}, "value": account()}),
            "block": ("getBlock", collect.block_params(100), {"blockhash": HASH, "previousBlockhash": AUTH, "parentSlot": 99, "blockTime": PIN_TIME}),
            "block_recheck": ("getBlock", collect.block_params(100), {"blockhash": HASH, "previousBlockhash": AUTH, "parentSlot": 99, "blockTime": PIN_TIME})}
        for eid, (method, params, result) in packets.items():
            path = root/(eid+".json")
            path.write_text(json.dumps({"request": {"jsonrpc": "2.0", "id": eid, "method": method, "params": params},
                                       "response": {"jsonrpc": "2.0", "id": eid, "result": result}}))
            row = {"id": eid, "artifact": path.name, "sha256": common.sha(path.read_bytes()), "kind": "rpc",
                   "source": "offline synthetic fixture", "subject": TARGET, "time_basis": "finalized slot 100; synthetic"}
            if eid == "mint":
                row["state"] = {"slot": 100, "commitment": "finalized", "block_evidence_id": "block", "block_recheck_evidence_id": "block_recheck"}
            manifest["evidence"].append(row)
        manifest["synthetic"] = True
        manifest["identity_evidence"] = ["genesis", "mint"]

        def save():
            (root/"manifest.json").write_text(json.dumps(manifest))
            report = json.loads((root/"report.json").read_text())
            report["synthetic"] = True
            report["manifest_sha256"] = common.sha((root/"manifest.json").read_bytes())
            (root/"report.json").write_text(json.dumps(report))

        save()
        bundle.validate(root, allow_synthetic=True)
        mint_row = next(x for x in manifest["evidence"] if x["id"] == "mint")
        mint_row["state"]["slot"] = 101
        save()
        with self.assertRaises(ValueError):
            bundle.validate(root, allow_synthetic=True)
        mint_row["state"]["slot"] = 100
        mint_row["state"]["block_recheck_evidence_id"] = "block"
        save()
        with self.assertRaises(ValueError):
            bundle.validate(root, allow_synthetic=True)

    def test_collection_bundle_cli_render_and_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)/"run"
            collect.run_bounded(root, {"url": "normal", "headers": {}}, TARGET, seconds=5, worker_target=fake_worker)
            for action, extra in (("init", ["--from-collection"]), ("render", []), ("validate", ["--rendered", str(root/"report.md")])):
                result = subprocess.run([sys.executable, str(SCRIPTS/"solana_bundle.py"), action, str(root), "--profile", "legacy-v1", "--allow-synthetic", *extra],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "partial")
            self.assertIn("SYNTHETIC", (root/"report.md").read_text())
            with self.assertRaises(ValueError):
                bundle.validate(root)


if __name__ == "__main__":
    unittest.main()
