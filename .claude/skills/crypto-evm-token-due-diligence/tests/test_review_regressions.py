"""Regressions from the independent review of the pipeline and compose layer (2026-09-10)."""
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backend_common import write_new
from broad_collect import Pipeline, looks_like_address
from bundle_assemble import intake, read_draft, save_draft
from compose import compose, redact_url
from facts import decimal_string, decode_result
from keccak import canonical_signature, pool_id
from test_strict_profile import strict
from web_capture import capture, register


class LaneCaptureSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        m, r = strict(self.root)
        self.run = self.root / "run"
        self.draft = self.run / "draft"
        d = intake(self.draft, r["target"], "Synthetic compose", "Declared synthetic scope", True)
        shutil.copytree(self.root / "evidence", self.draft / "evidence")
        for ev in m["evidence"]:
            ev["observation_status"] = "ok"
        d.update(evidence=m["evidence"], pins=m["chains"][0]["pins"], chain_id_evidence=m["chains"][0]["chain_id_evidence"])
        save_draft(self.draft, d)
        (self.run / "lanes" / "liquidity").mkdir(parents=True)
        (self.run / "secret.env").write_text("DRPC_API_KEY=SUPERSECRET\n")

    def capture_meta(self, alias, **extra):
        meta = {"id": alias, "url": "https://example.invalid/" + alias, "final_url": "https://example.invalid/" + alias, "http_status": 200,
                "captured_at_utc": "2026-01-01T00:00:00Z", "failure_category": None, "host": "example.invalid", "raw": alias + ".raw"}
        meta.update(extra)
        (self.run / "lanes" / "liquidity" / (alias + ".raw")).write_bytes(b"page bytes")
        (self.run / "lanes" / "liquidity" / (alias + ".json")).write_text(json.dumps(meta))

    def note(self, findings):
        path = self.run / "note.json"
        path.write_text(json.dumps({"note_schema_version": 1, "lane": "liquidity", "findings": findings}))
        return path

    def test_traversal_raw_is_refused_and_secret_never_copied(self):
        self.capture_meta("page", raw="../../secret.env")
        result = compose(self.draft, self.note([{"id": "x", "dimension": "current_concentration", "claim": "inference", "strength": "inference",
                                                  "confidence": "low", "impact": "neutral", "text": "SYNTHETIC", "evidence": ["e-code", "page"]}]), lane="liquidity", final=False)
        self.assertEqual(result["status"], "errors")
        self.assertTrue(any("plain <id>.raw" in e for e in result["errors"]), result)
        self.assertFalse(any("SUPERSECRET" in p.read_bytes().decode("utf-8", "replace") for p in (self.draft / "evidence").glob("*")))

    def test_document_cannot_be_explicit_direct_evidence(self):
        self.capture_meta("page")
        result = compose(self.draft, self.note([{"id": "x", "dimension": "current_concentration", "claim": "state_observation", "strength": "proven_fact",
                                                  "confidence": "high", "impact": "neutral", "text": "SYNTHETIC", "evidence": ["page#direct"]}]), lane="liquidity", final=False)
        self.assertTrue(any("cannot be direct evidence" in e for e in result["errors"]), result)

    def test_lane_note_errors_leave_draft_and_evidence_untouched(self):
        self.capture_meta("page")
        before = {str(p): p.read_bytes() for p in self.draft.rglob("*") if p.is_file()}
        result = compose(self.draft, self.note([{"id": "x", "dimension": "current_concentration", "claim": "inference", "strength": "inference",
                                                  "confidence": "low", "impact": "neutral", "text": "SYNTHETIC", "evidence": ["e-code", "page", "missing-alias"]}]), lane="liquidity", final=False)
        self.assertEqual(result["status"], "errors")
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.draft.rglob("*") if p.is_file()})
        result = compose(self.draft, self.note([{"id": "x", "dimension": "current_concentration", "claim": "inference", "strength": "inference",
                                                  "confidence": "low", "impact": "neutral", "text": "SYNTHETIC", "evidence": ["e-code", "page"]}]), lane="liquidity", final=False)
        self.assertEqual(result["errors"], [], result)
        self.assertTrue((self.draft / "evidence" / "doc-liquidity-page.raw").is_file())
        row = next(e for e in read_draft(self.draft)["evidence"] if e["id"] == "doc-liquidity-page")
        self.assertEqual(row["kind"], "document")

    def test_credential_urls_are_redacted_in_evidence(self):
        self.assertEqual(redact_url("https://api.invalid/x?apikey=SECRET&page=2"), "https://api.invalid/x?page=2")
        self.assertEqual(redact_url("https://user:pw@api.invalid/x"), "https://api.invalid/x")


class ComposeContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        m, r = strict(self.root)
        self.draft = self.root / "draft"
        d = intake(self.draft, r["target"], "Synthetic compose", "Declared synthetic scope", True)
        shutil.copytree(self.root / "evidence", self.draft / "evidence")
        for ev in m["evidence"]:
            ev["observation_status"] = "ok"
        d.update(evidence=m["evidence"], pins=m["chains"][0]["pins"], chain_id_evidence=m["chains"][0]["chain_id_evidence"])
        save_draft(self.draft, d)

    def note(self, **body):
        path = self.root / "note.json"
        path.write_text(json.dumps({"note_schema_version": 1, "lane": "coordinator", **body}))
        return path

    def test_incomplete_coverage_needs_a_finding_and_default_status_is_partial(self):
        result = compose(self.draft, self.note(findings=[], coverage={"token_controls": {"status": "partial", "gap": "g", "priority": "material", "decision_impact": "d",
                                                                                          "attempts": [{"check": "c", "outcome": "o", "evidence": ["e-code"]}], "boundary": "exhausted", "basis": "b"}}), final=False)
        self.assertTrue(any("still needs at least one finding" in e for e in result["errors"]), result)
        result = compose(self.draft, self.note(findings=[{"id": "f", "dimension": "token_controls", "claim": "state_observation", "strength": "strongly_supported",
                                                          "confidence": "high", "impact": "neutral", "text": "SYNTHETIC", "evidence": ["e-code"]}]), final=False)
        self.assertEqual(result["errors"], [], result)
        self.assertEqual(next(c for c in read_draft(self.draft)["coverage_records"] if c["dimension"] == "token_controls")["status"], "partial")
        self.assertTrue(any("defaulted to partial" in w for w in result["warnings"]))

    def test_bad_needs_partial_or_complete_coverage_and_medium_confidence(self):
        finding = {"id": "bad", "dimension": "token_controls", "topic": "token_and_liquidity", "signal": "Bad", "claim": "state_observation", "strength": "strongly_supported",
                   "confidence": "high", "impact": "adverse", "severity": "high", "text": "SYNTHETIC seizure", "evidence": ["e-code"],
                   "concern": {"basis": "reachable_capability", "mechanism": "m", "consequence": "c"}}
        coverage = {"token_controls": {"status": "unavailable", "gap": "g", "priority": "material", "decision_impact": "d",
                                       "attempts": [{"check": "c", "outcome": "o", "evidence": ["e-code"]}], "boundary": "unavailable", "basis": "b"}}
        result = compose(self.draft, self.note(findings=[finding], coverage=coverage), final=False)
        self.assertTrue(any("Bad finding needs partial or complete coverage" in e for e in result["errors"]), result)
        gap = {"id": "gap", "dimension": "token_controls", "claim": "coverage_gap", "text": "SYNTHETIC gap", "evidence": ["e-code"]}
        coverage["token_controls"]["status"] = "partial"
        result = compose(self.draft, self.note(findings=[finding, gap], coverage=coverage), final=False)
        self.assertEqual(result["errors"], [], result)
        rating = next(r for r in read_draft(self.draft)["ratings"] if r["id"] == "token_controls")
        self.assertEqual((rating["status"], rating["confidence"], rating["severity"]), ("concern", "high", "high"))

    def test_every_finding_needs_evidence_at_its_subject_and_pin(self):
        other = "0x2234567890abcdef1234567890abcdef12345678"
        result = compose(self.draft, self.note(findings=[{"id": "x", "dimension": "side_pool_removal_risk", "claim": "inference", "strength": "inference",
                                                          "confidence": "low", "impact": "neutral", "subject": other, "text": "SYNTHETIC", "evidence": ["e-code"]}]), final=False)
        self.assertTrue(any("no pinned evidence row" in e or "exact scope/pin" in e for e in result["errors"]), result)

    def test_actions_mirror_validator_rules(self):
        finding = {"id": "good", "dimension": "token_controls", "topic": "token_and_liquidity", "signal": "Good", "claim": "state_observation", "strength": "strongly_supported",
                   "confidence": "high", "impact": "benefit", "text": "SYNTHETIC", "evidence": ["e-code"]}
        decision = {"verdict": {"kind": "findings_with_limits", "scope": "s"}, "synthesis": {"technical_exposure": "a", "credibility_maturity": "b", "token_economics": "c", "research_confidence": "d"},
                    "actions": [{"id": "u", "kind": "use_within_scope", "action": "use", "reason": "r", "findings": ["good", "typo"], "changes_view_if": "x"}]}
        text = {"verdict": "v", "main_reasons": "m", "strongest_contrary_evidence": "s", "unresolved_questions": "u", "change_evidence": "c"}
        result = compose(self.draft, self.note(findings=[finding], coverage={"token_controls": {"status": "partial", "gap": "g", "priority": "material", "decision_impact": "d",
                                                                                                 "attempts": [{"check": "c", "outcome": "o", "evidence": ["e-code"]}], "boundary": "exhausted", "basis": "b"}},
                                                decision=decision, text=text), final=False)
        joined = " | ".join(result["errors"])
        self.assertIn("unknown finding ids typo", joined)
        self.assertIn("completed coverage for every named dimension", joined)

    def test_all_gap_packet_needs_summary_rows(self):
        gap = {"id": "gap", "dimension": "token_controls", "claim": "coverage_gap", "text": "SYNTHETIC gap", "evidence": ["e-code"]}
        decision = {"verdict": {"kind": "insufficient_evidence", "scope": "s", "findings": ["gap"]},
                    "synthesis": {"technical_exposure": "a", "credibility_maturity": "b", "token_economics": "c", "research_confidence": "d"}, "actions": []}
        text = {"verdict": "v", "main_reasons": "m", "strongest_contrary_evidence": "s", "unresolved_questions": "u", "change_evidence": "c"}
        coverage = {"token_controls": {"status": "unavailable", "gap": "g", "priority": "material", "decision_impact": "d",
                                       "attempts": [{"check": "c", "outcome": "o", "evidence": ["e-code"]}], "boundary": "unavailable", "basis": "b"}}
        result = compose(self.draft, self.note(findings=[gap], coverage=coverage, decision=decision, text=text), final=True)
        self.assertTrue(any("summary: no finding carries a topic" in e for e in result["errors"]), result)
        self.assertTrue(any("surface untouched" in e for e in result["errors"]), "final notes report every untouched surface up front")
        gap.update(topic="token_and_liquidity", signal="Unverified")
        result = compose(self.draft, self.note(findings=[gap], coverage=coverage, decision=decision, text=text), final=False)
        self.assertEqual(result["errors"], [], result)
        records = {c["dimension"]: c for c in read_draft(self.draft)["coverage_records"]}
        self.assertEqual(records["side_pool_removal_risk"]["closure"]["next_route"]["disposition"], "pending", "checkpoint mode reviews untouched surfaces")


class PipelineInputTests(unittest.TestCase):
    def test_address_heuristic_keeps_control_names_and_drops_amounts(self):
        addr = int("0x263ed295dafae1d9aadd6e56c4b6f9f38ee019dd", 16)
        for name in ("admin", "feeRecipient", "owner", "timelock", "minter", "priceOracle", "launchFactory"):
            self.assertTrue(looks_like_address(addr, name), name)
        for name in ("maxTxAmount", "maxWalletLimit", "totalSupplyCap", "launchBlock", "maxTxBps"):
            self.assertFalse(looks_like_address(addr, name), name)
        self.assertFalse(looks_like_address(2 * 10 ** 25, "treasury"), "small integers are never addresses")

    def test_decimals_are_bounded_everywhere(self):
        self.assertIsNone(decimal_string(1, 2 ** 200))
        self.assertEqual(decimal_string(1, 18), "<0.000001")
        self.assertEqual(decode_result("313ce567", "0x" + format(2 ** 200, "064x"))["int"], 2 ** 200)

    def test_pipeline_rejects_malformed_discovery_identities(self):
        class Dummy:
            synthetic = True
            namespace = "x"
        pipeline = Pipeline(tempfile.mkdtemp(), {"chain_id": 31337, "address": "0x1234567890abcdef1234567890abcdef12345678"}, "q", "m", Dummy(), None, None,
                            registry={"dexscreener": "synthetic", "explorers": []}, synthetic=True)
        pipeline.parse_pairs([{"pairAddress": "0x/../../pwn", "baseToken": {"address": "0x1234567890abcdef1234567890abcdef12345678"}, "quoteToken": {"address": "0x" + "0" * 40}},
                              {"pairAddress": "0x" + "ab" * 20, "baseToken": {"address": "0x1234567890abcdef1234567890abcdef12345678"}, "quoteToken": {"address": "0x" + "cd" * 20}}])
        self.assertEqual([p["pair"] for p in pipeline.pairs], ["0x" + "ab" * 20])
        with self.assertRaises(ValueError):
            pipeline.lookup_block("0x/../../pwn")


class FakeResponse:
    def __init__(self, body):
        self.body, self.status, self.headers = body, 200, {"Content-Type": "application/json"}

    def read1(self, n):
        chunk, self.body = self.body[:n], self.body[n:]
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class WebCaptureSafetyTests(unittest.TestCase):
    def test_credential_url_is_refused_without_aborting_the_batch(self):
        class Opener:
            def open(self, request, timeout=None):
                return FakeResponse(b"{}")
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import patch
            with patch("web_capture.urllib.request.build_opener", return_value=Opener()):
                records = capture([{"id": "a", "url": "https://api.invalid/x?apikey=SECRET"}, {"id": "b", "url": "https://api.invalid/y"}], Path(tmp))
            self.assertEqual(records[0]["failure_category"], "refused_credential_url")
            self.assertNotIn("SECRET", json.dumps(records[0]))
            self.assertNotIn("SECRET", (Path(tmp) / "a.json").read_text())
            self.assertEqual(records[1]["http_status"], 200)

    def test_register_refuses_traversal_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            m, r = strict(root)
            draft = root / "draft"
            d = intake(draft, r["target"], "Synthetic", "scope", True)
            shutil.copytree(root / "evidence", draft / "evidence")
            d.update(evidence=m["evidence"], pins=m["chains"][0]["pins"], chain_id_evidence=m["chains"][0]["chain_id_evidence"])
            save_draft(draft, d)
            (root / "captures").mkdir()
            record = {"id": "page", "url": "https://x.invalid/p", "final_url": "https://x.invalid/p", "http_status": 200, "captured_at_utc": "2026-01-01T00:00:00Z",
                      "failure_category": None, "host": "x.invalid", "raw": "../draft/draft.json", "_dir": str(root / "captures")}
            with self.assertRaises(ValueError):
                register(draft, [record])


class KeccakStrictnessTests(unittest.TestCase):
    def test_non_canonical_types_and_unsorted_pool_keys_are_rejected(self):
        for bad in ("transfer(address,uint)", "f(a,)", "f(,)", "g(address,int)"):
            with self.assertRaises(ValueError):
                canonical_signature(bad)
        canonical_signature("quoteExactInputSingle((address,address,uint256,uint24,uint160))")
        canonical_signature("f(uint256[],bytes32[2])")
        with self.assertRaises(ValueError):
            pool_id("0x5fc5360d0400a0fd4f2af552add042d716f1d168", "0x39dbed3a2bd333467115de45665cc57f813c4571", 3000, 60, "0x" + "0" * 40)


if __name__ == "__main__":
    unittest.main()


class ScopeRenameTests(unittest.TestCase):
    def test_note_scope_id_renames_auto_generated_scope_everywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from test_broad_collect import BroadCollectTests, POOL
            case = BroadCollectTests("test_pipeline_collects_decodes_and_imports_without_model_turns")
            run = root / "run"
            run.mkdir()
            case.run_pipeline(run)
            first = {"note_schema_version": 1, "lane": "liquidity", "findings": [
                {"id": "pool-state", "dimension": "canonical_lp_principal_custody", "claim": "state_observation", "strength": "strongly_supported",
                 "confidence": "medium", "impact": "neutral", "subject": POOL, "text": "SYNTHETIC pool state", "evidence": ["pool1-liquidity", "pool1-runtime"]}]}
            write_new(run / "notes" / "liquidity.json", first)
            self.assertEqual(compose(run / "draft", run / "notes" / "liquidity.json", lane="liquidity")["errors"], [])
            auto = next(s["id"] for s in read_draft(run / "draft")["scope"] if s["address"] == POOL)
            self.assertTrue(auto.startswith("addr-"))
            second = {"note_schema_version": 1, "lane": "coordinator", "scope": [{"id": "pool1", "address": POOL, "roles": ["canonical pool"], "material": True}],
                      "findings": [{"id": "pool-fee", "dimension": "canonical_lp_principal_custody", "claim": "state_observation", "strength": "strongly_supported",
                                    "confidence": "medium", "impact": "neutral", "subject": "pool1", "text": "SYNTHETIC fee", "evidence": ["pool1-fee", "pool1-runtime"]}],
                      "coverage": {"canonical_lp_principal_custody": {"status": "checked"}}}
            write_new(run / "notes" / "coordinator.json", second)
            result = compose(run / "draft", run / "notes" / "coordinator.json", final=False)
            self.assertEqual(result["errors"], [], result)
            d = read_draft(run / "draft")
            self.assertEqual([s["id"] for s in d["scope"] if s["address"] == POOL], ["pool1"])
            for f in d["findings"]:
                if f["id"] in ("pool-state", "pool-fee"):
                    self.assertEqual(f["subject_scope_id"], "pool1")
                    self.assertTrue(all(s["scope_id"] != auto for s in f["support"]))
