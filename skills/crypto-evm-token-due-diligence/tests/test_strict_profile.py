"""Negative audit reproductions and honest partial-report near neighbors."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from fixtures import build, bind, add_rpc, CHAIN, HASH, TARGET, OTHER
from backend_common import canonical, sha
from report_profile import CURRENT_PROFILE
from validate_bundle import Invalid, validate


def strict(root):
    m, r = build(root)
    m["validation_profile"] = r["validation_profile"] = CURRENT_PROFILE
    header = json.loads((root / "evidence/e-header.json").read_text())["response"]["result"]
    add_rpc(root, m, "recheck", "eth_getBlockByNumber", ["0x64", False], {"result": header})
    m["chains"][0]["pins"][0].update(state_profile="numbered_rechecked", recheck_evidence_ids=["recheck"])
    m["evidence"][0].update(pin_id=None, provenance_level="chain")
    m["discoveries"] = [{"id": "intake", "chain_id": CHAIN, "universe": "Exact synthetic target only",
                         "pagination": "No enumeration attempted", "inclusion_rules": "Requested identity",
                         "exclusions": "All surrounding contracts unsearched", "materiality": "Authority always material",
                         "coverage": "Intake only; no broad discovery claim", "block_ranges": [[100, 100]],
                         "evidence_ids": ["e-code"]}]
    f = r["findings"][0]
    f.update(subject_scope_id="target", participant_scope_ids=[], claim_type="coverage_gap",
             impact="unknown", adverse_severity="unknown",
             support=[{"evidence_id": "e-code", "scope_id": "target", "role": "identity"}])
    r["summary"] = [{"finding_id": f["id"], "topic": "token_and_liquidity", "signal": "Potential Risk"}]
    r["coverage_records"] = [{"dimension": x["id"], "status": "not_checked", "surface": x["id"],
                              "outcome": "No investigation of " + x["id"], "gap": "Fresh surface evidence absent",
                              "stop_reason": "Synthetic test", "next_check": "Inspect " + x["id"],
                              "evidence_ids": [], "discovery_ids": ["intake"], "finding_ids": [f["id"]]}
                             for x in r["ratings"]]
    bind(root, m, r)
    return m, r


class StrictProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.m, self.r = strict(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        bind(self.root, self.m, self.r)
        return validate(self.root, True, required_profile=CURRENT_PROFILE)

    def reject(self, message):
        with self.assertRaisesRegex((Invalid, ValueError), message):
            self.check()

    def mutate(self, eid, change):
        e = next(x for x in self.m["evidence"] if x["id"] == eid)
        p = self.root / e["artifact"]
        obj = json.loads(p.read_text())
        change(obj)
        p.write_bytes(canonical(obj))
        e["sha256"] = sha(p.read_bytes())

    def test_explicit_no_attempts_is_valid_unknown(self):
        self.check()

    def test_cannot_strip_profile(self):
        del self.m["validation_profile"]
        self.reject("required report profile")

    def test_extra_chain_observation_cannot_contradict(self):
        add_rpc(self.root, self.m, "chain-again", "eth_chainId", [], {"result": "0x1"})
        self.reject("chain ID conflict")

    def test_extra_recheck_cannot_contradict(self):
        self.mutate("recheck", lambda o: o["response"]["result"].update(hash="0x" + sha(b"other block")))
        self.reject("inconsistent block hash")

    def test_header_roots_cannot_contradict(self):
        self.mutate("recheck", lambda o: o["response"]["result"].update(stateRoot="0x" + sha(b"other root")))
        self.reject("header roots/parent")

    def test_failed_recheck_does_not_verify_state(self):
        self.mutate("recheck", lambda o: o.update(response={"jsonrpc": "2.0", "id": "recheck", "result": None}))
        self.reject("RPC unavailable")

    def test_numbered_reads_need_distinct_recheck(self):
        self.m["chains"][0]["pins"][0]["recheck_evidence_ids"] = ["e-header"]
        self.reject("distinct observation")

    def test_canonical_hash_profile_needs_no_numbered_recheck(self):
        self.m["chains"][0]["pins"][0].update(state_profile="canonical_hash", recheck_evidence_ids=[])
        for e in self.m["evidence"]:
            if e["query"]["method"] in ("eth_call", "eth_getCode"):
                e["query"]["params"][-1] = {"blockHash": HASH, "requireCanonical": True}
                self.mutate(e["id"], lambda o, q=e["query"]: o.update(request=q))
        self.check()

    def test_empty_discovery_ledger_rejected(self):
        self.m["discoveries"] = []
        self.reject("discovery records")

    def test_missing_dimension_coverage_rejected(self):
        self.r["coverage_records"].pop()
        self.reject("one coverage record")

    def test_unknown_cannot_hide_individual_critical_findings(self):
        for i in range(2):
            f = copy.deepcopy(self.r["findings"][0])
            f.update(id="adverse" + str(i), claim_type="state_observation", impact="adverse",
                     adverse_severity="critical", evidence_type="strongly_supported", confidence="medium")
            f["support"][0]["role"] = "direct"
            self.r["findings"].append(f)
            self.r["ratings"][0]["finding_ids"].append(f["id"])
            self.r["coverage_records"][0]["finding_ids"].append(f["id"])
        self.r["ratings"][0].update(status="concern", severity="critical", confidence="medium", coverage="partial")
        self.r["coverage_records"][0].update(status="partial", evidence_ids=["e-code"])
        # A pure gap now fails the broader concern-visibility gate first.
        self.reject("summary omits a high/critical concern")
        self.r["summary"].append({"finding_id": "adverse0", "signal": "Bad", "topic": "token_and_liquidity"})
        self.reject("individual high/critical")
        self.r["summary"].append({"finding_id": "adverse1", "signal": "Bad", "topic": "token_and_liquidity"})
        self.check()

    def test_unrelated_identity_anchor_is_not_direct_support(self):
        f = self.r["findings"][0]
        f.update(claim_type="state_observation", evidence_type="proven_fact", confidence="high")
        self.reject("lacks direct evidence")
        f["support"][0]["role"] = "direct"
        self.check()
        f["subject_scope_id"] = "missing-fee-sink"
        self.reject("subject scope mismatch")

    def add_derived(self):
        e = copy.deepcopy(self.m["evidence"][2])
        e.update(id="derived", kind="derived", artifact="evidence/derived.json",
                 input_evidence_ids=["e-code"], query={"operation": "test"},
                 derivation={"tool": "fixture", "version": "1", "operation": "test", "parameters": {},
                             "source_urls": [], "input_sha256": {"e-code": self.m["evidence"][2]["sha256"]}})
        (self.root / e["artifact"]).write_bytes(canonical({"fixture": "derived statement"}))
        e["sha256"] = sha((self.root / e["artifact"]).read_bytes())
        self.m["evidence"].append(e)
        return e

    def test_derived_inputs_bound_even_if_input_hash_is_updated(self):
        self.add_derived()
        self.check()
        self.mutate("e-code", lambda o: o.update(extra="changed input"))
        self.reject("derivation input digest changed")

    def test_dependency_cycle_rejected(self):
        e = self.add_derived()
        e["input_evidence_ids"] = ["derived"]
        e["derivation"]["input_sha256"] = {"derived": e["sha256"]}
        self.reject("cyclic")

    def test_incidental_unreferenced_file_is_allowed(self):
        (self.root / "scratch.txt").write_text("not evidence")
        self.check()

    def test_inference_type_cannot_be_proven(self):
        self.r["findings"][0].update(claim_type="inference", evidence_type="proven_fact", confidence="high")
        self.reject("inference cannot be")

    def test_recheck_cannot_alias_initial_artifact(self):
        initial = next(e for e in self.m["evidence"] if e["id"] == "e-header")
        recheck = next(e for e in self.m["evidence"] if e["id"] == "recheck")
        recheck.update({k: copy.deepcopy(v) for k, v in initial.items() if k != "id"})
        self.reject("distinct observation")

    def test_coverage_status_must_match_rating(self):
        self.r["ratings"][0]["coverage"] = "partial"
        self.reject("coverage/rating status")

    def test_failed_input_cannot_be_hidden_behind_derived_proof(self):
        e = self.add_derived()
        failed = add_rpc(self.root, self.m, "failure", "eth_call", [{"to": TARGET, "data": "0x12345678"}, "0x64"],
                         {"error": {"code": 3, "message": "reverted"}})
        e["input_evidence_ids"] = ["failure"]
        e["derivation"]["input_sha256"] = {"failure": failed["sha256"]}
        f = self.r["findings"][0]
        f.update(claim_type="state_observation", evidence_type="proven_fact", confidence="high", evidence_ids=["derived"],
                 support=[{"evidence_id": "derived", "role": "direct", "scope_id": "target"}])
        self.reject("direct evidence unavailable")

    def test_revert_is_evidence_of_failure_not_success(self):
        tx = "0x" + sha(b"synthetic transaction")
        e = add_rpc(self.root, self.m, "receipt", "eth_getTransactionReceipt", [tx],
                    {"result": {"transactionHash": tx, "blockNumber": "0x64", "blockHash": HASH,
                                "status": "0x0", "logs": []}})
        e["tx_hash"] = tx
        f = self.r["findings"][0]
        f.update(claim_type="historical_execution", evidence_type="proven_fact", confidence="high",
                 evidence_ids=["receipt"], support=[{"evidence_id": "receipt", "scope_id": "target", "role": "direct"}],
                 execution={"receipt_evidence_id": "receipt", "result": "success", "effects": []})
        self.reject("receipt status")
        f["execution"]["result"] = "reverted"
        self.check()
        self.mutate("receipt", lambda o: o["response"]["result"].update(status="0x1"))
        f["execution"]["result"] = "success"
        self.reject("lacks decoded effects")


if __name__ == "__main__":
    unittest.main()
