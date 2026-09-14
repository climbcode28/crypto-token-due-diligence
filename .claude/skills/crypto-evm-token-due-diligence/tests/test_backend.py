import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend_fixtures import (ALICE, BOB, CAROL, CHAIN, SELECTOR, SUPPLY, TOKEN, TX,
                              FakeRpc, abi, case, header, hh, plan, receipt, transfer)
from backend_common import ENGINE_VERSION, RULE_VERSIONS, Cache, Invalid, canonical, load_collection, read_json, sha, write_new
from detect import analyze, evaluate
from maintain import record_feedback
from rpc_collect import Collector, HttpTransport, configured_transport, prepare

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = Cache(self.root / "cache.sqlite")
        self.rpc = FakeRpc()
        self.counter = 0

    def tearDown(self):
        self.cache.close()
        self.temp.cleanup()

    def collect(self, spec=None, **kwargs):
        self.counter += 1
        root = self.root / str(self.counter)
        value = Collector(root, self.cache, self.rpc, "synthetic-rpc", **kwargs).collect(spec or plan())
        return root, value

    def evaluate(self, root, spec=None):
        c, e, p = load_collection(root, allow_synthetic=True)
        return evaluate(c, e, p, spec or case(root))

    def mutate_artifact(self, root, eid, mutate):
        collection = read_json(root / "collection.json")
        row = next(x for x in collection["evidence"] if x["id"] == eid)
        artifact = root / row["artifact"]
        value = read_json(artifact)
        mutate(value)
        artifact.write_bytes(canonical(value))
        row["sha256"] = sha(artifact.read_bytes())
        collection["plan_sha256"] = sha((root / "plan.json").read_bytes())
        (root / "collection.json").write_bytes(canonical(collection))

    def test_frozen_replay_and_integer_launch_accounting(self):
        root, collection = self.collect()
        self.assertEqual(collection["status"], "complete")
        result = self.evaluate(root)
        launch = result[0]
        self.assertEqual(launch["gross_received_atomic"], str(5 * 10**23))
        self.assertEqual([x["address"] for x in launch["recipients"]], [ALICE, BOB])
        self.assertEqual(launch["recipients"][0]["net_transfer_delta_atomic"], str(10**23))
        self.assertEqual([x["supply_bps_floor"] for x in launch["recipients"]], [2000, 3000])
        self.assertEqual([x["at_or_above_threshold"] for x in launch["recipients"]], [False, True])
        self.assertEqual([x["predicate"] for x in result[1:]], [False, True])
        self.assertFalse(result[1]["semantic_basis_verified_by_engine"])
        cp = self.root / "case.json"
        write_new(cp, case(root))
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            analyze(root, cp, self.root / "a", self.cache, True)
            analyze(root, cp, self.root / "b", self.cache, True)
        self.assertEqual((self.root / "a/findings.json").read_bytes(), (self.root / "b/findings.json").read_bytes())

    def test_cache_hits_still_recheck_chain_and_headers(self):
        self.collect()
        self.rpc.calls.clear()
        _, second = self.collect()
        self.assertEqual(second["statistics"], {"network_attempts": 5, "cache_hits": 6})
        self.assertTrue(all(x["method"] in {"eth_chainId", "eth_getBlockByNumber"} for x in self.rpc.calls))
        self.rpc.namespace = "another-synthetic-provider"
        _, third = self.collect()
        self.assertEqual(third["statistics"]["cache_hits"], 0)

    def test_same_height_new_hash_does_not_reuse_old_cache(self):
        self.collect()
        self.rpc.overrides["eth_getBlockByNumber"] = lambda r: {**header(int(r["params"][0], 16)),
            "hash": hh("fork" + r["params"][0]), "parentHash": hh("fork" + hex(int(r["params"][0], 16) - 1))}
        self.rpc.overrides["eth_getTransactionReceipt"] = lambda r: {**receipt(), "blockHash": hh("fork0x64")}
        _, second = self.collect()
        self.assertEqual(second["statistics"]["cache_hits"], 0)

    def test_chain_mismatch_aborts_before_state_reads(self):
        self.rpc.overrides["eth_chainId"] = lambda r: hex(CHAIN + 1)
        root, value = self.collect()
        self.assertEqual(value["status"], "invalid")
        self.assertEqual(len(self.rpc.calls), 1)
        with self.assertRaises(Invalid):
            load_collection(root, True)

    def test_reorg_during_collection_is_invalid(self):
        counts = {}
        def changed(r):
            n = int(r["params"][0], 16)
            counts[n] = counts.get(n, 0) + 1
            return {**header(n), **({"hash": hh("changed")} if counts[n] > 1 else {})}
        self.rpc.overrides["eth_getBlockByNumber"] = changed
        root, value = self.collect()
        self.assertEqual(value["status"], "invalid")
        with self.assertRaises(Invalid):
            self.evaluate(root)

    def test_null_and_failed_calls_are_retried_not_cached_as_absence(self):
        self.rpc.overrides["eth_call"] = lambda r: {"error": {"code": -32000, "message": "historical state unavailable"}}
        root, first = self.collect()
        self.assertEqual(first["status"], "partial")
        result = self.evaluate(root)
        self.assertIsNone(result[0]["supply_atomic"])
        self.assertEqual(result[1]["status"], "unknown")
        self.rpc.overrides.clear()
        _, second = self.collect()
        self.assertEqual(second["status"], "complete")
        self.assertEqual(second["statistics"]["cache_hits"], 3)

    def test_transport_failures_do_not_fabricate_rpc_or_leak_secret(self):
        self.rpc.overrides["eth_call"] = lambda r: OSError("SECRET api-key in URL")
        root, value = self.collect()
        row = next(x for x in value["evidence"] if x["id"] == "fee-launch")
        artifact = (root / row["artifact"]).read_text()
        self.assertEqual(row["kind"], "document")
        self.assertNotIn("response", artifact)
        self.assertNotIn("SECRET", artifact)
        self.assertEqual(self.evaluate(root)[1]["status"], "unknown")

    def test_impossible_pin_budget_is_rejected_without_network_attempts(self):
        root, value = self.collect(max_requests=4)
        self.assertEqual(value["statistics"]["network_attempts"], 0)
        self.assertEqual(value["status"], "invalid")
        self.assertTrue(any("request budget cannot cover" in x["reason"] for x in value["coverage_gaps"]))
        self.assertEqual(self.rpc.calls, [])

    def test_allowlist_rejects_broadcast_latest_and_overrides(self):
        for query in [
            {"id": "x", "pin_id": "current", "method": "eth_sendRawTransaction", "params": ["0x"]},
            {"id": "x", "pin_id": "current", "method": "eth_call", "params": [{"to": TOKEN, "data": "0x"}, "latest"]},
            {"id": "x", "pin_id": "current", "method": "eth_call", "params": [{"to": TOKEN, "data": "0x"}, {}]},
            {"id": "x", "pin_id": "current", "method": "eth_getLogs", "params": [{"address": TOKEN, "fromBlock": "latest"}]}]:
            with self.subTest(query=query), self.assertRaises(Invalid):
                p = plan(); p["queries"] = [query]; prepare(p)

    def test_ranges_use_each_captured_block_hash_and_mark_limit(self):
        p = plan()
        p["log_ranges"] = [{"id": "scan", "from_block": 100, "to_block": 101, "address": TOKEN}]
        _, value = self.collect(p)
        self.assertEqual(value["status"], "complete")
        log_calls = [r for r in self.rpc.calls if r["method"] == "eth_getLogs"]
        self.assertEqual({x["params"][0]["blockHash"] for x in log_calls}, {hh(100), hh(101)})
        self.assertFalse(any("fromBlock" in x["params"][0] for x in log_calls))

    def test_trace_requires_receipt_and_does_not_run_when_receipt_missing(self):
        p = plan()
        p["queries"].append({"id": "trace", "pin_id": "launch", "method": "debug_traceTransaction", "params": [TX]})
        self.rpc.overrides["eth_getTransactionReceipt"] = lambda r: None
        _, value = self.collect(p)
        self.assertFalse(any(x["method"] == "debug_traceTransaction" for x in self.rpc.calls))
        self.assertEqual(value["status"], "partial")
        p["queries"] = p["queries"][-1:]
        with self.assertRaises(Invalid):
            prepare(p)

    def test_reverted_receipt_cannot_supply_allocations(self):
        self.rpc.overrides["eth_getTransactionReceipt"] = lambda r: {**receipt(), "status": "0x0"}
        root, _ = self.collect()
        result = self.evaluate(root)[0]
        self.assertEqual(result["recipients"], [])
        self.assertEqual(result["status"], "partial")

    def test_duplicate_receipt_query_is_deduplicated(self):
        p = plan()
        q = copy.deepcopy(p["queries"][0]); q["id"] = "duplicate-receipt"; p["queries"].append(q)
        root, _ = self.collect(p)
        c = case(root); c["launch"]["receipt_evidence_ids"].append("duplicate-receipt")
        self.assertEqual(self.evaluate(root, c)[0]["gross_received_atomic"], str(5 * 10**23))

    def test_nft_or_duplicate_or_removed_log_leaves_whole_receipt_unknown(self):
        for problem in ("nft", "duplicate", "removed", "wrong-token-block"):
            r = receipt()
            if problem == "nft": r["logs"][0]["topics"].append(abi(123))
            if problem == "duplicate": r["logs"].append(copy.deepcopy(r["logs"][0]))
            if problem == "removed": r["logs"][0]["removed"] = True
            if problem == "wrong-token-block": r["logs"][0]["blockHash"] = hh(777)
            self.rpc.namespace = problem
            self.rpc.overrides["eth_getTransactionReceipt"] = lambda q, r=r: r
            root, _ = self.collect()
            observed = self.evaluate(root)[0]
            self.assertEqual(observed["recipients"], [], problem)
            self.assertEqual(observed["status"], "partial", problem)

    def test_current_supply_cannot_masquerade_as_launch_supply(self):
        p = plan(); p["queries"][1]["pin_id"] = "current"
        root, _ = self.collect(p)
        result = self.evaluate(root)[0]
        self.assertIsNone(result["supply_atomic"])
        self.assertTrue(all(x["supply_fraction"] is None for x in result["recipients"]))

    def test_fee_nonstandard_bool_and_empty_runtime_are_unknown(self):
        self.rpc.overrides["eth_call"] = lambda r: abi(SUPPLY if r["params"][0]["data"] == "0x18160ddd" else 2)
        root, _ = self.collect()
        self.assertIsNone(self.evaluate(root)[1]["predicate"])
        self.rpc.namespace = "empty-runtime"
        self.rpc.overrides["eth_getCode"] = lambda r: "0x"
        root, _ = self.collect()
        self.assertEqual(self.evaluate(root)[1]["status"], "unknown")

    def test_wrong_fee_account_selector_and_runtime_pin_rejected(self):
        root, _ = self.collect()
        for key, value in (("account", BOB), ("selector", "0x12345678"), ("code_evidence_id", "code-current")):
            c = case(root); c["fee_checks"][0][key] = value
            with self.subTest(key=key), self.assertRaises(Invalid):
                self.evaluate(root, c)

    def test_artifact_tamper_case_mismatch_and_synthetic_gate(self):
        root, _ = self.collect()
        with self.assertRaises(Invalid):
            load_collection(root)
        c = case(root); c["collection_sha256"] = "f" * 64
        cp = self.root / "case.json"; write_new(cp, c)
        with self.assertRaises(Invalid):
            analyze(root, cp, self.root / "a", allow_synthetic=True)
        (root / "evidence/fee-launch.json").write_text("{}")
        with self.assertRaises(Invalid):
            load_collection(root, True)

    def test_cache_corruption_and_future_schema_rejected(self):
        self.collect()
        with self.cache.db:
            self.cache.db.execute("UPDATE responses SET payload=?", (b"{}",))
        _, result = self.collect()
        self.assertEqual(result["status"], "invalid")
        with self.cache.db:
            self.cache.db.execute("PRAGMA user_version=999")
        with self.assertRaises(Invalid):
            Cache(self.root / "cache.sqlite")

    def test_invalid_transaction_response_is_evicted_before_resume(self):
        self.rpc.overrides["eth_getTransactionReceipt"] = lambda r: {**receipt(), "blockHash": hh(999)}
        _, first = self.collect()
        self.assertEqual(first["status"], "partial")
        self.assertEqual(next(e for e in first["evidence"] if e["id"] == "launch-receipt")["observation_status"], "malformed_data")
        self.rpc.overrides.clear()
        root, second = self.collect()
        self.assertEqual(second["status"], "complete")
        self.assertEqual(self.evaluate(root)[0]["status"], "observed")

    def test_mixed_case_query_addresses_are_normalized_without_mutating_plan(self):
        p = plan()
        for q in p["queries"]:
            if q["method"] == "eth_getCode": q["params"][0] = "0x" + TOKEN[2:].upper()
            if q["method"] == "eth_call": q["params"][0]["to"] = "0x" + TOKEN[2:].upper()
        frozen = copy.deepcopy(p)
        root, _ = self.collect(p)
        self.assertEqual(p, frozen)
        self.assertTrue(self.evaluate(root)[2]["predicate"])

    def test_forged_completion_cannot_hide_missing_or_wrong_final_pin_check(self):
        root, _ = self.collect()
        self.mutate_artifact(root, "sys-recheck-launch", lambda obj: obj["response"]["result"].update(hash=hh(999)))
        with self.assertRaises(Invalid):
            load_collection(root, True)

    def test_log_topic_mismatch_invalidates_collection(self):
        p = plan()
        p["queries"] = [{"id": "logs", "pin_id": "launch", "method": "eth_getLogs",
                         "params": [{"address": TOKEN, "topics": [hh("different-event")]}]}]
        self.rpc.overrides["eth_getLogs"] = lambda r: receipt()["logs"]
        _, result = self.collect(p)
        self.assertEqual(result["status"], "invalid")

    def test_log_limit_is_partial_not_clean_empty_success(self):
        p = plan()
        p["queries"] = [{"id": "logs", "pin_id": "launch", "method": "eth_getLogs", "params": [{"address": TOKEN}]}]
        self.rpc.overrides["eth_getLogs"] = lambda r: receipt()["logs"]
        _, result = self.collect(p, max_logs=3)
        self.assertEqual(result["status"], "partial")
        self.assertIn("completeness unknown", result["coverage_gaps"][0]["reason"])

    def test_decoded_upstream_secret_echo_is_redacted(self):
        transport = HttpTransport("https://example.invalid/rpc?api_key=LONG-TEST-SECRET", {"Authorization": "Bearer HEADER-SECRET"})
        raw = '{"error": {"message": "LONG-TEST-SECRET HEADER-\\u0053ECRET"}}'
        result = transport.redact(json.loads(raw))
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertTrue(transport.last_redacted)

    def test_redirects_are_not_followed(self):
        from rpc_collect import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid/"))

    def test_feedback_is_append_only_and_bound_to_evidence(self):
        root, _ = self.collect()
        one = record_feedback(self.cache, root, "coverage_gap", "Synthetic test limitation", ["fee-launch"], True)
        two = record_feedback(self.cache, root, "decoding_failure", "Synthetic follow-up", ["fee-current"], True)
        self.assertGreater(two, one)
        row = self.cache.db.execute("SELECT run_digest FROM feedback WHERE id=?", (one,)).fetchone()
        self.assertEqual(row[0], sha((root / "collection.json").read_bytes()))
        with self.assertRaises(Invalid):
            record_feedback(self.cache, root, "false_positive", "Bad reference", ["absent"], True)

    def test_cli_offline_default_creates_no_collection(self):
        pp = self.root / "plan.json"; write_new(pp, plan())
        result = subprocess.run([sys.executable, str(SCRIPTS / "rpc_collect.py"), str(pp), "--out", str(self.root / "out"),
                                 "--cache", str(self.root / "cli.sqlite")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["status"], "fallback")
        self.assertEqual(json.loads(result.stdout)["next_action"], "continue_standard_flow")
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "out").exists())
        self.assertFalse((self.root / "cli.sqlite").exists())

    def test_drpc_uses_secret_header_and_refuses_a_free_relabel(self):
        args = argparse.Namespace(allow_network=True, cost_policy="free", allow_paid=False, rpc_url_env="TEST_RPC",
                                  provider="generic", auth_env=None, auth_header="Authorization")
        with patch.dict(os.environ, {"TEST_RPC": "https://lb.drpc.org/robinhood-mainnet", "DRPC_API_KEY": "TEST-SECRET"}):
            with self.assertRaises(Invalid): configured_transport(args)  # a free policy cannot relabel the dRPC endpoint
            args.cost_policy = None  # the configured key is the authorization; no paid flags needed
            transport = configured_transport(args)
            self.assertEqual(transport.headers, {"Drpc-Key": "TEST-SECRET"})
            self.assertNotIn("TEST-SECRET", transport.url)
        with patch.dict(os.environ, {"TEST_RPC": "https://lb.drpc.org/?network=ethereum&dkey=TEST-SECRET"}):
            with self.assertRaises(Invalid): configured_transport(args)

    def test_drpc_trailing_dot_cannot_skip_the_free_relabel_gate(self):
        args = argparse.Namespace(allow_network=True, cost_policy="free", allow_paid=False, rpc_url_env="TEST_RPC",
                                  provider="generic", auth_env=None, auth_header="Authorization")
        with patch.dict(os.environ, {"TEST_RPC": "https://lb.drpc.org./ethereum"}):
            with self.assertRaises(Invalid): configured_transport(args)

    def test_storage_balance_transaction_and_bound_traces_execute_pinned(self):
        p = plan()
        for eid, method, params in [("slot", "eth_getStorageAt", [TOKEN, "0x0"]),
                                    ("balance", "eth_getBalance", [TOKEN]),
                                    ("transaction", "eth_getTransactionByHash", [TX]),
                                    ("debug", "debug_traceTransaction", [TX]),
                                    ("trace", "trace_transaction", [TX])]:
            p["queries"].append({"id": eid, "pin_id": "launch", "method": method, "params": params})
        _, result = self.collect(p)
        self.assertEqual(result["status"], "complete")
        reads = {x["method"]: x["params"] for x in self.rpc.calls}
        self.assertEqual(reads["eth_getStorageAt"], [TOKEN, "0x0", "0x64"])
        self.assertEqual(reads["eth_getBalance"], [TOKEN, "0x64"])
        self.assertEqual(reads["debug_traceTransaction"], [TX])

    def test_http_protocol_failure_is_recorded_without_response_or_secret(self):
        import http.client
        self.rpc.overrides["eth_call"] = lambda r: http.client.BadStatusLine("SECRET")
        root, result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertNotIn("SECRET", (root / "evidence/fee-launch.json").read_text())

    def test_missing_final_receipt_cannot_use_earlier_supply(self):
        p = plan()
        p["queries"].append({"id": "later-receipt", "pin_id": "current", "method": "eth_getTransactionReceipt", "params": [hh("later")]})
        self.rpc.overrides["eth_getTransactionReceipt"] = lambda r: receipt() if r["params"] == [TX] else None
        root, _ = self.collect(p)
        c = case(root); c["launch"]["receipt_evidence_ids"].append("later-receipt")
        self.assertIsNone(self.evaluate(root, c)[0]["supply_atomic"])

    def test_release_metadata_matches_engine_contract(self):
        release = read_json(SCRIPTS.parent / "assets/backend-release.json")
        self.assertEqual(release["engine_version"], ENGINE_VERSION)
        self.assertEqual(release["rule_versions"], RULE_VERSIONS)
        self.assertEqual(release["cache_schema_version"], self.cache.db.execute("PRAGMA user_version").fetchone()[0])

    def test_fee_predicate_preserves_explicit_caller_context(self):
        p = plan()
        for q in p["queries"]:
            if q["id"] == "fee-launch": q["params"][0]["from"] = BOB
        root, _ = self.collect(p)
        self.assertEqual(self.evaluate(root)[2]["call_context"]["from"], BOB)

    def test_redacted_legacy_rpc_cannot_resolve_launch_or_fee_observations(self):
        for eid in ("launch-receipt", "launch-supply", "fee-launch", "code-launch"):
            with self.subTest(evidence_id=eid):
                root, collection = self.collect()
                row = next(x for x in collection["evidence"] if x["id"] == eid)
                # Older collectors could retain apparently successful ABI data
                # alongside a redaction marker and ordinary response coverage.
                row["redacted"] = True
                (root / "collection.json").write_bytes(canonical(collection))
                result = self.evaluate(root)
                if eid == "launch-receipt":
                    self.assertEqual(result[0]["status"], "partial")
                    self.assertEqual(result[0]["recipients"], [])
                elif eid == "launch-supply":
                    self.assertIsNone(result[0]["supply_atomic"])
                else:
                    self.assertEqual(result[2]["status"], "unknown")
                    self.assertIsNone(result[2]["predicate"])


if __name__ == "__main__":
    unittest.main()
