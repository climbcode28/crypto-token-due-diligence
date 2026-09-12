import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fixtures import build, bind, write_json, add_rpc, add_second_chain, CHAIN, OTHER, TARGET
from validate_bundle import Invalid, validate, sha
from render_report import render


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="evm-dd-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.m, self.r = build(self.root)

    def save(self):
        bind(self.root, self.m, self.r)

    def reject(self, pattern):
        self.save()
        with self.assertRaisesRegex(Invalid, pattern):
            validate(self.root, allow_synthetic=True)

    def evidence(self, eid):
        return next(e for e in self.m["evidence"] if e["id"] == eid)

    def change_raw(self, eid, transform):
        ev = self.evidence(eid)
        path = self.root / ev["artifact"]
        obj = json.loads(path.read_text())
        transform(obj)
        write_json(path, obj)
        ev["sha256"] = sha(path.read_bytes())

    def test_valid_bundle_with_all_risks_unknown(self):
        validate(self.root, allow_synthetic=True)

    def test_synthetic_rejected_by_default(self):
        with self.assertRaisesRegex(Invalid, "synthetic bundle"):
            validate(self.root)

    def test_same_symbol_substituted_from_another_chain(self):
        # Symbol and address remain identical; queried chain is different.
        self.m["target"]["observed"]["chain_id"] = 1
        self.reject("requested/observed")

    def test_report_wrong_target(self):
        self.r["target"]["address"] = OTHER
        self.reject("report refers to wrong target")

    def test_fake_block_hash(self):
        self.m["chains"][0]["pins"][0]["hash"] = "0x" + sha(b"fabricated-pin")
        self.reject("fake/inconsistent block hash")

    def test_fake_block_timestamp(self):
        self.m["chains"][0]["pins"][0]["timestamp_utc"] = "2024-01-01T00:00:01Z"
        self.reject("fake/inconsistent block timestamp")

    def test_fake_block_number(self):
        self.change_raw("e-header", lambda obj: obj["response"]["result"].update(number="0x65"))
        self.reject("fake/inconsistent block number")

    def test_unknown_check_presented_as_pass(self):
        self.r["ratings"][0].update(status="pass", severity="none", likelihood="unlikely", confidence="high", coverage="complete")
        self.reject("unknown/skipped/partial check presented as a pass")

    def test_placeholder_pin(self):
        self.m["chains"][0]["pins"][0]["hash"] = "0x" + "0" * 64
        self.reject("placeholder hash")

    def test_malformed_address(self):
        self.m["target"]["requested"]["address"] = "0x1234"
        self.reject("malformed address")

    def test_rpc_chain_id_conflict(self):
        self.change_raw("e-chain", lambda obj: obj["response"].update(result="0x1"))
        self.reject("RPC chain ID conflict")

    def test_queried_target_substitution(self):
        self.evidence("e-code")["target"]["address"] = OTHER
        self.reject("queried target identity conflicts")

    def test_query_address_substitution(self):
        ev = self.evidence("e-code")
        ev["query"]["params"][0] = OTHER
        self.change_raw("e-code", lambda obj: obj.update(request=ev["query"]))
        self.reject("query address differs")

    def test_latest_query_rejected(self):
        ev = self.evidence("e-code")
        ev["query"]["params"][1] = "latest"
        self.change_raw("e-code", lambda obj: obj.update(request=ev["query"]))
        self.reject("invalid RPC quantity")

    def test_missing_evidence_file(self):
        (self.root / "evidence/e-code.json").unlink()
        self.reject("missing evidence artifact")

    def test_changed_evidence_bytes(self):
        with (self.root / "evidence/e-code.json").open("a") as f:
            f.write(" ")
        self.reject("evidence hash mismatch")

    def test_scope_chain_conflict(self):
        self.m["scope"][0]["chain_id"] = 1
        self.reject("inconsistent scope chain")

    def test_scope_runtime_hash_conflict(self):
        self.m["scope"][0]["runtime"]["sha256"] = sha(b"different runtime")
        self.reject("runtime byte hash mismatch")

    def test_metadata_report_conflict(self):
        self.r["metadata"]["symbol"]["value"] = "OTHER"
        self.reject("reported metadata differs")

    def test_metadata_declared_value_conflicts_with_rpc(self):
        self.m["target"]["metadata"]["decimals"]["value"] = 6
        self.r["metadata"]["decimals"]["value"] = 6
        self.reject("decoded value conflicts")

    def test_metadata_failure_is_coverage_not_value(self):
        def fail(obj):
            obj["response"].pop("result")
            obj["response"]["error"] = {"code": -32000, "message": "SYNTHETIC archive unavailable"}
        self.change_raw("e-name", fail)
        self.m["target"]["metadata"]["name"].update(status="unresolved", value=None, reason="Synthetic RPC unavailable")
        self.r["metadata"] = copy.deepcopy(self.m["target"]["metadata"])
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_rpc_error_cannot_resolve_metadata(self):
        def fail(obj):
            obj["response"].pop("result")
            obj["response"]["error"] = {"code": -32000, "message": "SYNTHETIC timeout"}
        self.change_raw("e-symbol", fail)
        self.reject("RPC unavailable/error")

    def test_unresolved_metadata_cannot_keep_value(self):
        self.m["target"]["metadata"]["name"].update(status="unresolved", reason="Unavailable")
        self.reject("unresolved metadata cannot assert a value")

    def test_missing_safety_declaration(self):
        self.m["safety"]["no_broadcast"] = False
        self.reject("safety declaration")

    def test_public_simulation_endpoint_rejected(self):
        self.m["safety"]["simulation"] = {"used": True, "verified_disposable_local_fork": True,
          "synthetic_accounts_only": True, "counterfactual": True, "no_transaction_forwarding": True,
          "endpoint": "https://public-rpc.example.invalid"}
        self.reject("fork endpoint must be local")

    def test_missing_risk_dimension(self):
        self.r["ratings"].pop()
        self.reject("eleven distinct risk dimensions")

    def test_duplicate_rating(self):
        self.r["ratings"].append(copy.deepcopy(self.r["ratings"][0]))
        self.reject("duplicate rating id")

    def test_discovery_claim_without_universe(self):
        self.r["findings"][0]["discovery_claim"] = True
        self.reject("discovery claim lacks search universe")

    def test_missing_finding_evidence(self):
        self.r["findings"][0]["evidence_ids"] = []
        self.reject("missing evidence/references")

    def test_manifest_source_not_rebound_after_edit(self):
        self.m["question"] = "Changed question"
        write_json(self.root / "manifest.json", self.m)
        with self.assertRaisesRegex(Invalid, "does not bind this manifest"):
            validate(self.root, allow_synthetic=True)

    def test_artifact_path_traversal(self):
        self.evidence("e-code")["artifact"] = "../outside.json"
        self.reject("artifact path escapes bundle")

    def test_render_roundtrip_and_wrong_rendered_identity(self):
        rendered = self.root / "report.md"
        rendered.write_text(render(self.m, self.r, sha((self.root / "report.json").read_bytes())))
        validate(self.root, allow_synthetic=True, rendered=rendered)
        rendered.write_text(rendered.read_text().replace(TARGET, OTHER))
        with self.assertRaisesRegex(Invalid, "rendered report differs"):
            validate(self.root, allow_synthetic=True, rendered=rendered)

    def test_renderer_escapes_untrusted_html(self):
        self.r["verdict"] = "Synthetic text <script>alert(1)</script>"
        output = render(self.m, self.r, sha((self.root / "report.json").read_bytes()))
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)

    def test_cli_render_and_validation(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for args in (["render_report.py", str(self.root), "--allow-synthetic", "--profile", "legacy-v1"],
                     ["validate_bundle.py", str(self.root), "--allow-synthetic", "--profile", "legacy-v1", "--rendered", str(self.root / "report.md")]):
            result = subprocess.run([sys.executable, str(scripts / args[0]), *args[1:]], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SYNTHETIC FIXTURE", (self.root / "report.md").read_text())

    def test_cli_malformed_json_fails_without_traceback(self):
        (self.root / "manifest.json").write_text("{")
        script = Path(__file__).resolve().parents[1] / "scripts/validate_bundle.py"
        result = subprocess.run([sys.executable, str(script), str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("INVALID:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def control_support(self, error=False, confidence="high"):
        response = {"error": {"code": -32000, "message": "SYNTHETIC archive unavailable"}} if error else {"result": "0x" + "00" * 32}
        add_rpc(self.root, self.m, "e-control", "eth_call", [{"to": TARGET, "data": "0x8da5cb5b"}, hex(100)], response)
        f = copy.deepcopy(self.r["findings"][0])
        f.update(id="F-control", evidence_ids=["e-control"], evidence_type="proven_fact", confidence=confidence,
                 proposition="SYNTHETIC: bounded control read is resolved under the fixture assumptions.")
        self.r["findings"].append(f)
        self.r["ratings"][0].update(status="pass", severity="none", likelihood="unlikely", confidence="high",
                                     coverage="complete", finding_ids=["F-control"])

    def test_failed_rpc_cannot_support_pass(self):
        self.control_support(error=True)
        self.reject("unknown/skipped/partial check presented as a pass")

    def test_failed_rpc_cannot_support_not_applicable(self):
        self.control_support(error=True)
        self.r["ratings"][0].update(status="not_applicable", coverage="not_applicable")
        self.reject("not-applicable rating requires resolved evidence")

    def test_unknown_finding_confidence_cannot_support_pass(self):
        self.control_support(confidence="unknown")
        self.reject("resolved finding has unknown confidence")

    def test_low_finding_confidence_cannot_support_pass(self):
        self.control_support(confidence="low")
        self.reject("unknown/skipped/partial check presented as a pass")

    def test_generic_rpc_missing_response_version(self):
        self.control_support()
        self.change_raw("e-control", lambda obj: obj["response"].pop("jsonrpc"))
        self.reject("invalid RPC response version")

    def test_rpc_result_and_error_both_rejected(self):
        self.control_support()
        self.change_raw("e-control", lambda obj: obj["response"].update(error={"code": -32000, "message": "SYNTHETIC"}))
        self.reject("RPC requires exactly result or error")

    def test_valid_two_chain_bundle(self):
        add_second_chain(self.root, self.m, self.r)
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_secondary_runtime_attempt_requires_own_scope_pin(self):
        add_second_chain(self.root, self.m, self.r)
        self.m["scope"][1]["runtime"] = {"status": "unavailable", "reason": "SYNTHETIC unavailable", "evidence_ids": ["e-code"]}
        self.reject("runtime attempts lack exact scope/pin")

    def test_secondary_proxy_requires_own_scope_pin(self):
        add_second_chain(self.root, self.m, self.r)
        self.m["scope"][1]["proxy"]["evidence_ids"] = ["e-code"]
        self.reject("proxy evidence lacks exact scope/pin")

    def test_cross_chain_proxy_edge_rejected(self):
        add_second_chain(self.root, self.m, self.r)
        self.m["scope"][0]["proxy"].update(status="resolved", implementation_scope_ids=["secondary"])
        self.reject("proxy edge crosses chains")

    def test_real_broadcast_method_rejected(self):
        ev = self.evidence("e-code")
        ev["query"]["method"] = "eth_sendRawTransaction"
        self.change_raw("e-code", lambda obj: obj.update(request=ev["query"]))
        self.reject("unsupported/read-only RPC method")

    def test_state_override_cannot_resolve_metadata(self):
        ev = self.evidence("e-symbol")
        ev["query"]["params"].append({TARGET: {"code": "0x6000"}})
        self.change_raw("e-symbol", lambda obj: obj.update(request=ev["query"]))
        self.reject("overrides are counterfactual")

    def test_block_override_cannot_support_pass(self):
        self.control_support()
        ev = self.evidence("e-control")
        ev["query"]["params"].extend([{}, {"time": "0x1"}])
        self.change_raw("e-control", lambda obj: obj.update(request=ev["query"]))
        self.reject("overrides are counterfactual")

    def test_empty_call_overrides_are_accepted(self):
        ev = self.evidence("e-symbol")
        ev["query"]["params"].extend([None, {}])
        self.change_raw("e-symbol", lambda obj: obj.update(request=ev["query"]))
        self.save()
        validate(self.root, allow_synthetic=True)

    def trace_support(self, method="debug_traceTransaction", response=None):
        tx_hash = "0x" + sha(b"synthetic traced transaction")
        ev = add_rpc(self.root, self.m, "e-trace", method, [tx_hash],
                     {"result": {"gas": 21000}} if response is None else response)
        ev["tx_hash"] = tx_hash
        return tx_hash

    def test_successful_traces_require_transaction_pin_evidence(self):
        for method in ("debug_traceTransaction", "trace_transaction"):
            with self.subTest(method=method):
                self.m, self.r = build(self.root)
                self.trace_support(method)
                self.reject("trace lacks transaction evidence at its chain/pin")

    def test_trace_with_matching_receipt_is_accepted(self):
        tx_hash = self.trace_support()
        pin = self.m["chains"][0]["pins"][0]
        ev = add_rpc(self.root, self.m, "e-receipt", "eth_getTransactionReceipt", [tx_hash],
                     {"result": {"transactionHash": tx_hash, "blockNumber": hex(pin["number"]),
                                 "blockHash": pin["hash"], "status": "0x1"}})
        ev["tx_hash"] = tx_hash
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_trace_cannot_borrow_another_transactions_receipt(self):
        self.test_trace_with_matching_receipt_is_accepted()
        ev = self.evidence("e-trace")
        ev["tx_hash"] = "0x" + sha(b"another synthetic transaction")
        ev["query"]["params"][0] = ev["tx_hash"]
        self.change_raw("e-trace", lambda obj: obj.update(request=ev["query"]))
        self.reject("trace lacks transaction evidence at its chain/pin")

    def test_trace_receipt_must_match_captured_block(self):
        self.test_trace_with_matching_receipt_is_accepted()
        self.change_raw("e-receipt", lambda obj: obj["response"]["result"].update(blockNumber="0x63"))
        self.reject("transaction requires its own historical pin")

    def test_null_receipt_cannot_bind_successful_trace(self):
        self.test_trace_with_matching_receipt_is_accepted()
        self.change_raw("e-receipt", lambda obj: obj["response"].update(result=None))
        self.reject("trace lacks transaction evidence at its chain/pin")

    def test_failed_trace_remains_valid_coverage_evidence(self):
        self.trace_support(response={"error": {"code": -32000, "message": "Pruned state"}})
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_render_preserves_investigation_context(self):
        self.m["context"]["exit_sizes"] = [{"atomic_input": "987654321012345678901", "asset": TARGET}]
        self.m["context"]["deployment"]["reason"] = "Deployment history inaccessible at this endpoint"
        self.save()
        m, r = validate(self.root, allow_synthetic=True)
        output = render(m, r, sha((self.root / "report.json").read_bytes()))
        self.assertIn("987654321012345678901", output)
        self.assertIn("Deployment history inaccessible at this endpoint", output)

    def test_duplicate_json_key_rejected(self):
        text = (self.root / "manifest.json").read_text()
        (self.root / "manifest.json").write_text(text.replace('"synthetic": true', '"synthetic": true, "synthetic": false'))
        with self.assertRaisesRegex(Invalid, "duplicate JSON key"):
            validate(self.root, allow_synthetic=True)

    def logs_support(self, ranged=False):
        pin = self.m["chains"][0]["pins"][0]
        topic = "0x" + sha(b"synthetic event signature")
        query = {"address": TARGET, "topics": [topic]}
        query.update({"fromBlock": "0x63", "toBlock": "0x64"} if ranged else {"blockHash": pin["hash"]})
        log = {"address": TARGET, "topics": [topic], "data": "0x", "blockNumber": "0x64",
               "blockHash": pin["hash"], "transactionHash": "0x" + sha(b"synthetic logged tx"),
               "transactionIndex": "0x0", "logIndex": "0x0", "removed": False}
        add_rpc(self.root, self.m, "e-logs", "eth_getLogs", [query], {"result": [log]})
        self.control_support()
        self.r["findings"][-1]["evidence_ids"] = ["e-logs"]
        return log

    def test_matching_logs_can_support_resolved_evidence(self):
        self.logs_support()
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_log_response_cannot_substitute_scope_pin_or_topics(self):
        cases = ({"address": OTHER}, {"blockNumber": "0x63"},
                 {"blockHash": "0x" + sha(b"wrong synthetic block")},
                 {"topics": ["0x" + sha(b"wrong synthetic event")]},
                 {"removed": True}, {"data": "0x1"})
        for changes in cases:
            with self.subTest(changes=changes):
                self.m, self.r = build(self.root)
                self.logs_support()
                self.change_raw("e-logs", lambda obj: obj["response"]["result"][0].update(changes))
                self.reject("log")

    def test_duplicate_log_cannot_inflate_resolved_evidence(self):
        self.logs_support()
        self.change_raw("e-logs", lambda obj: obj["response"]["result"].append(copy.deepcopy(obj["response"]["result"][0])))
        self.reject("duplicate log")

    def test_range_logs_must_stay_inside_query_and_match_known_headers(self):
        for changes in ({"blockNumber": "0x62"}, {"blockHash": "0x" + sha(b"wrong synthetic endpoint block")}):
            with self.subTest(changes=changes):
                self.m, self.r = build(self.root)
                self.logs_support(ranged=True)
                self.change_raw("e-logs", lambda obj: obj["response"]["result"][0].update(changes))
                self.reject("log")

    def test_empty_and_unavailable_logs_remain_distinct(self):
        self.logs_support()
        self.change_raw("e-logs", lambda obj: obj["response"].update(result=[]))
        self.save()
        validate(self.root, allow_synthetic=True)
        self.change_raw("e-logs", lambda obj: obj["response"].update(result=None))
        self.reject("unknown/skipped/partial check presented as a pass")

    def test_log_filter_cannot_mix_hash_and_range(self):
        self.logs_support()
        ev = self.evidence("e-logs")
        ev["query"]["params"][0].update(fromBlock="0x63", toBlock="0x64")
        self.change_raw("e-logs", lambda obj: obj.update(request=ev["query"]))
        self.reject("log filter")

    def test_same_chain_height_cannot_have_conflicting_pins(self):
        pin = copy.deepcopy(self.m["chains"][0]["pins"][0])
        pin.update(id="p-fork", hash="0x" + sha(b"synthetic contradictory fork"), header_evidence="e-fork-header")
        self.m["chains"][0]["pins"].append(pin)
        header = json.loads((self.root / self.evidence("e-header")["artifact"]).read_text())["response"]["result"]
        add_rpc(self.root, self.m, "e-fork-header", "eth_getBlockByNumber", ["0x64", False],
                {"result": dict(header, hash=pin["hash"])}, pin_id="p-fork")
        self.reject("conflicting pins")

    def test_boolean_rpc_id_cannot_match_integer_request(self):
        self.control_support()
        ev = self.evidence("e-control")
        ev["query"]["id"] = 1
        self.change_raw("e-control", lambda obj: (obj.update(request=ev["query"]), obj["response"].update(id=True)))
        self.reject("response ID mismatch")

    def test_block_reference_cannot_mix_hash_and_number(self):
        ev = self.evidence("e-code")
        ev["query"]["params"][1] = {"blockHash": self.m["chains"][0]["pins"][0]["hash"],
                                    "blockNumber": "0x63", "requireCanonical": True}
        self.change_raw("e-code", lambda obj: obj.update(request=ev["query"]))
        self.reject("inconsistent query block")

    def test_malformed_state_result_cannot_support_pass(self):
        for method, params, result in (("eth_call", [{"to": TARGET, "data": "0x8da5cb5b"}, "0x64"], "ownerless"),
                                       ("eth_getCode", [TARGET, "0x64"], "0x0"),
                                       ("eth_getStorageAt", [TARGET, "0x0", "0x64"], "0x01"),
                                       ("eth_getBalance", [TARGET, "0x64"], "0x00")):
            with self.subTest(method=method):
                self.m, self.r = build(self.root)
                self.control_support()
                ev = self.evidence("e-control")
                ev["query"].update(method=method, params=params)
                self.change_raw("e-control", lambda obj: (obj.update(request=ev["query"]), obj["response"].update(result=result)))
                self.reject("invalid RPC quantity|malformed.*result")

    def test_receipt_logs_must_match_receipt_transaction_and_pin(self):
        for changes in ({"transactionHash": "0x" + sha(b"another tx")},
                        {"blockNumber": "0x63"}, {"blockHash": "0x" + sha(b"another block")},
                        {"removed": True}):
            with self.subTest(changes=changes):
                self.m, self.r = build(self.root)
                log = self.logs_support()
                log.update(changes)
                tx_hash = "0x" + sha(b"synthetic logged tx")
                pin = self.m["chains"][0]["pins"][0]
                ev = add_rpc(self.root, self.m, "e-receipt", "eth_getTransactionReceipt", [tx_hash],
                             {"result": {"transactionHash": tx_hash, "blockNumber": "0x64", "blockHash": pin["hash"],
                                         "status": "0x1", "logs": [log]}})
                ev["tx_hash"] = tx_hash
                self.reject("log")

    def test_matching_receipt_logs_from_multiple_contracts_are_valid(self):
        log = self.logs_support()
        second = dict(log, address=OTHER, logIndex="0x1")
        ev = add_rpc(self.root, self.m, "e-receipt", "eth_getTransactionReceipt", [log["transactionHash"]],
                     {"result": {"transactionHash": log["transactionHash"], "blockNumber": log["blockNumber"],
                                 "blockHash": log["blockHash"], "status": "0x1", "logs": [log, second]}})
        ev["tx_hash"] = log["transactionHash"]
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_log_topic_or_and_wildcard_filters_are_accepted(self):
        log = self.logs_support()
        ev = self.evidence("e-logs")
        ev["query"]["params"][0]["topics"] = [["0x" + sha(b"another event"), log["topics"][0]], None, []]
        self.change_raw("e-logs", lambda obj: (obj.update(request=ev["query"]),
                                             obj["response"]["result"][0]["topics"].extend(["0x" + "0" * 64] * 2)))
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_redacted_success_cannot_support_pass(self):
        self.control_support()
        self.evidence("e-control")["redacted"] = True
        self.reject("unknown/skipped/partial check presented as a pass")

    def test_redacted_malformed_call_can_remain_unknown(self):
        self.control_support()
        self.evidence("e-control")["redacted"] = True
        self.change_raw("e-control", lambda obj: obj["response"].update(result="[REDACTED]"))
        self.r["findings"][-1].update(evidence_type="unknown", confidence="unknown")
        self.r["ratings"][0].update(status="unknown", severity="unknown", confidence="unknown", coverage="unavailable")
        self.save()
        validate(self.root, allow_synthetic=True)

    def test_redacted_rpc_cannot_resolve_metadata(self):
        self.evidence("e-name")["redacted"] = True
        self.reject("RPC unavailable/error")


if __name__ == "__main__":
    unittest.main()
