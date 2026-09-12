"""Run-hygiene regressions from the 2026-09-10 12.7-minute live run.

Every coordinator minute lost in that run traces to one of: a misleading start diagnostic,
lanes spawned with a retyped brief, lane notes repaired by hand, a hand-written coordinator
note, a freeze KeyError, and reverted probe reads recorded as lost coverage. These tests pin
the fixes; everything is synthetic and offline.
"""
import io
import json
import shutil
import socket
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backend_common import Cache, read_json
from backend_fixtures import CHAIN, FakeRpc, TOKEN, plan
import broad_collect
from broad_collect import Pipeline, StartFailure, archive_failed_attempt, prepare_lanes, spawn_lines, spawn_prompt
from bundle_assemble import DIMENSIONS, read_draft
from compose import compose
from investigation import Investigation
from rpc_collect import Collector
from pipeline_note import write_and_compose
from scaffold import scaffold_note
from test_broad_collect import BroadCollectTests, FACTORY, PipelineRpc, REGISTRY, fake_fetch


class CollectorClassificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = Cache(self.root / "cache.sqlite")
        self.addCleanup(self.cache.close)

    def collect(self, rpc, name):
        return Collector(self.root / name, self.cache, rpc, "fixture").collect(plan())

    def test_execution_revert_is_definitive_not_operational(self):
        rpc = FakeRpc()
        rpc.overrides["eth_call"] = lambda req: {"error": {"code": 3, "message": "execution reverted", "data": "0x"}}
        result = self.collect(rpc, "revert")
        rows = {e["id"]: e for e in result["evidence"]}
        self.assertEqual(rows["fee-current"]["observation_status"], "reverted")
        self.assertEqual(rows["fee-current"]["acquisition"]["failure_category"], "execution_reverted")
        self.assertEqual(result["status"], "partial", "a reverted optional read is still a recorded attempt")
        self.assertFalse((self.root / "revert" / "operational-feedback.json").exists(), "reverts are chain answers, not operational failures")
        planned = sum(q["method"] == "eth_call" for q in plan()["queries"])
        self.assertEqual(sum(q["method"] == "eth_call" for q in rpc.calls), planned, "reverts are never retried")

    def test_transient_transport_failure_is_retried_once_and_definitive_failures_are_not(self):
        attempts = {"n": 0}

        def throttle_then_ok(req):
            attempts["n"] += 1
            if attempts["n"] == 1:
                return urllib.error.HTTPError("https://rpc.invalid", 429, "Too Many Requests", {}, None)
            return "0x0"
        rpc = FakeRpc()
        rpc.overrides["eth_getBalance"] = throttle_then_ok
        spec = plan()
        spec["pins"] = [spec["pins"][1]]
        spec["queries"] = [{"id": "bal", "pin_id": "current", "method": "eth_getBalance", "params": [TOKEN]}]
        result = Collector(self.root / "retry", self.cache, rpc, "fixture").collect(spec)
        row = next(e for e in result["evidence"] if e["id"] == "bal")
        self.assertEqual(row["observation_status"], "ok")
        self.assertEqual(attempts["n"], 2)
        self.assertEqual(result["status"], "complete")

        rpc = FakeRpc()
        rpc.overrides["eth_getBalance"] = lambda req: urllib.error.HTTPError("https://rpc.invalid", 403, "Forbidden", {}, None)
        cache = Cache(self.root / "denied-cache.sqlite")  # a fresh cache: the throttled run above stored a reusable success
        self.addCleanup(cache.close)
        result = Collector(self.root / "denied", cache, rpc, "fixture").collect(spec)
        row = next(e for e in result["evidence"] if e["id"] == "bal")
        self.assertEqual(row["acquisition"]["failure_category"], "access_denied")
        self.assertEqual(sum(q["method"] == "eth_getBalance" for q in rpc.calls), 1, "a definitive HTTP refusal is not retried")
        self.assertTrue((self.root / "denied" / "operational-feedback.json").exists())


class NodeLagTests(unittest.TestCase):
    def test_unsupported_block_number_is_retried_as_node_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = Cache(root / "cache.sqlite")
            try:
                attempts = {"n": 0}

                def lag_then_ok(req):
                    attempts["n"] += 1
                    if attempts["n"] == 1:
                        return {"error": {"code": -32000, "message": "unsupported block number 59938868"}}
                    return "0x0"
                rpc = FakeRpc()
                rpc.overrides["eth_getBalance"] = lag_then_ok
                spec = plan()
                spec["pins"] = [spec["pins"][1]]
                spec["queries"] = [{"id": "bal", "pin_id": "current", "method": "eth_getBalance", "params": [TOKEN]}]
                result = Collector(root / "lag", cache, rpc, "fixture").collect(spec)
                row = next(e for e in result["evidence"] if e["id"] == "bal")
                self.assertEqual(row["observation_status"], "ok")
                self.assertEqual(attempts["n"], 2)
            finally:
                cache.close()

    def test_pin_sits_behind_the_reported_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            session = Investigation.create(root / "session.sqlite", 50, 120, request_ceiling=100, timeout_ceiling=300, limit_basis="analyst_safety")
            cache = Cache(root / "cache.sqlite")
            try:
                pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "q", "m", PipelineRpc(), session, cache, "synthetic", synthetic=True, registry=REGISTRY)
                pinned = pipeline.head()
            finally:
                cache.close()
                session.close()
            self.assertEqual(pinned, 100 - broad_collect.PIN_LAG)
            self.assertEqual(read_json(root / "head" / "head.json")["pin_lag"], broad_collect.PIN_LAG)


class FailingRpc:
    synthetic = True
    namespace = "synthetic-failing"

    def __init__(self, mode):
        self.mode = mode
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        if self.mode == "dns":
            raise urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided"))
        if self.mode == "mismatch" and request["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": request["id"], "result": hex(CHAIN + 1)}
        return {"jsonrpc": "2.0", "id": request["id"], "result": "0x64"}


class StartDiagnosticsTests(unittest.TestCase):
    def head(self, root, rpc):
        session = Investigation.create(root / "session.sqlite", 50, 120, request_ceiling=100, timeout_ceiling=300, limit_basis="analyst_safety")
        cache = Cache(root / "cache.sqlite")
        try:
            pipeline = Pipeline(root, {"chain_id": CHAIN, "address": TOKEN}, "q", "m", rpc, session, cache, "synthetic", synthetic=True, registry=REGISTRY)
            with self.assertRaises(StartFailure) as ctx:
                pipeline.head()
        finally:
            cache.close()
            session.close()
        return ctx.exception.info

    def test_transport_failure_is_not_reported_as_a_chain_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self.head(Path(tmp) / "run", FailingRpc("dns"))
        self.assertEqual(info["stage"], "chain_check")
        self.assertEqual(info["category"], "dns_resolution")
        self.assertIn("not a chain mismatch", info["message"])
        self.assertIn("identical start command", info["next_step"])
        self.assertNotIn("chain does not match", info["message"])

    def test_chain_mismatch_names_both_chains(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self.head(Path(tmp) / "run", FailingRpc("mismatch"))
        self.assertEqual(info["category"], "chain_mismatch")
        self.assertEqual((info["rpc_chain_id"], info["requested_chain_id"]), (CHAIN + 1, CHAIN))
        self.assertIn(str(CHAIN), info["next_step"])

    def test_failed_start_directory_accepts_the_identical_command_once_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            (run / "head").mkdir()
            (run / "head" / "evidence.json").write_text("{}")
            argv = ["broad_collect.py", "start", "--chain-id", str(CHAIN), "--address", TOKEN, "--run", str(run), "--question", "q"]
            err, out = io.StringIO(), io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stderr(err), redirect_stdout(out):
                code = broad_collect.main()
            self.assertEqual(code, 2)
            self.assertIn("run directory must be new", err.getvalue())
            self.assertTrue((run / "head" / "evidence.json").exists(), "an unmarked directory is left untouched")
            (run / "start-failed.json").write_text(json.dumps({"status": "start_failed", "stage": "chain_check"}))
            err, out = io.StringIO(), io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stderr(err), redirect_stdout(out):
                code = broad_collect.main()
            self.assertEqual(code, 3, "past the restart gate the run stops at provider availability (no network flags)")
            self.assertTrue((run / "start-failed.json").exists(), "unready provider leaves the restart available")
            self.assertTrue((run / "head" / "evidence.json").exists())
            self.assertFalse((run / "failed-attempt-1").exists(), "provider checks do not mutate the failed run")

    def test_archive_numbers_successive_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "a.txt").write_text("1")
            archive_failed_attempt(run)
            (run / "b.txt").write_text("2")
            archive_failed_attempt(run)
            self.assertTrue((run / "failed-attempt-1" / "a.txt").exists())
            self.assertTrue((run / "failed-attempt-2" / "b.txt").exists())
            self.assertEqual(sorted(p.name for p in run.iterdir()), ["failed-attempt-1", "failed-attempt-2"])


class PipelineRunFixture(unittest.TestCase):
    """One synthetic pipeline run shared by the lane, scaffold and compose regressions."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "run"
        cls.root.mkdir()
        (cls.root / "notes").mkdir()
        cls.facts, cls.rpc, cls.status = BroadCollectTests().run_pipeline(cls.root)
        cls.pristine = Path(cls.temp.name) / "pristine"
        shutil.copytree(cls.root, cls.pristine)  # untouched by the notes other tests apply

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()


class LaneHandoffTests(PipelineRunFixture):
    def test_start_side_lane_preparation_writes_briefs_and_charges_budgets(self):
        session = Investigation(self.root / "session.sqlite")
        try:
            before = session.status()["started_attempts"]
            lanes = prepare_lanes(self.root, session)
            after = session.status()["started_attempts"]
        finally:
            session.close()
        self.assertEqual({lane: e["charged"] for lane, e in lanes.items()}, {"liquidity": 20, "project": 20})
        self.assertEqual(after - before, 40)
        for lane in ("liquidity", "project"):
            brief = self.root / "lanes" / lane / "brief.md"
            self.assertTrue(brief.is_file())
            text = brief.read_text()
            self.assertIn("Hard cutoff", text)
            self.assertIn("never later than", text)
            self.assertIn("compose", text, "the brief carries the self-check command")
            self.assertIn(str(brief.resolve()), lanes[lane]["prompt"])
            self.assertLess(len(spawn_prompt(self.root, lane)), 260, "the spawn prompt is a pointer, not the brief")
        self.assertTrue((self.root / "lanes" / "spawn.json").is_file())
        lines = spawn_lines(lanes)
        self.assertTrue(any(line.startswith("NEXT") for line in lines))
        self.assertEqual(sum("lane ->" in line for line in lines), 2)

    def test_reverted_probe_reads_are_marked_not_treated_as_gaps(self):
        factory = next(a for a in self.facts["architecture"] if a["address"] == FACTORY)
        self.assertEqual(factory["reverted"], ["owner"], "owner() reverts on the synthetic factory; that is an answer")
        self.assertEqual(self.facts["controls"]["failed_getters"], [])
        summary = "\n".join(broad_collect.summary_lines(self.facts))
        self.assertIn("owner=reverted (no owner() at the pin)", summary)
        for phase in ("phase2", "phase3"):
            feedback = self.root / phase / "operational-feedback.json"
            if feedback.exists():
                categories = {o["category"] for o in read_json(feedback)["observations"]}
                self.assertNotIn("reverted", categories)
                self.assertNotIn("unavailable", categories, "reverted eth_calls must not surface as unavailable operations")


class PipelineNoteTests(PipelineRunFixture):
    """The pipeline authors the factual findings; the coordinator only assigns judgement."""

    def test_pipeline_note_composes_cleanly_and_carries_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            shutil.copytree(self.pristine, root)
            result = write_and_compose(root)
            self.assertEqual(result["errors"], [], result)
            self.assertGreaterEqual(len(result["findings"]), 9, result["findings"])
            note = read_json(root / "notes" / "pipeline.json")
            ids = {f["id"] for f in note["findings"]}
            for expected in ("pipeline-token-controls", "pipeline-launch-execution", "pipeline-launch-position-custody", "pipeline-pool-depth",
                             "pipeline-verified-sale-1", "pipeline-holder-distribution", "pipeline-admin-authority", "pipeline-maturity-context"):
                self.assertIn(expected, ids)
            self.assertTrue(all("signal" not in f and "topic" not in f for f in note["findings"]), "judgement stays with the coordinator")
            draft = read_draft(root / "draft")
            sale = next(f for f in draft["findings"] if f["id"] == "pipeline-verified-sale-1")
            self.assertEqual(sale["claim_type"], "historical_execution")
            self.assertEqual(sale["execution"]["result"], "success")
            self.assertEqual(len(sale["execution"]["effects"]), 1, "the seller's transfer into the pool is the decoded effect")
            custody = next(f for f in draft["findings"] if f["id"] == "pipeline-launch-position-custody")
            self.assertNotEqual(custody["subject_scope_id"], "target", "custody is about the position owner, not the token")
            # Coordinator judgement through `signals`: a Good row for the observation, refusal of a misplaced Unverified.
            coordinator = root / "notes" / "signals.json"
            coordinator.write_text(json.dumps({"note_schema_version": 1, "lane": "coordinator",
                                               "signals": {"pipeline-pool-depth": {"topic": "token_and_liquidity", "signal": "Good"},
                                                           "pipeline-holder-distribution": {"topic": "token_economics", "signal": "Potential Risk"}}}))
            result = compose(root / "draft", coordinator, final=False)
            self.assertEqual(result["errors"], [], result)
            summary = {s["finding_id"]: s for s in read_draft(root / "draft")["summary"]}
            self.assertEqual(summary["pipeline-pool-depth"]["signal"], "Good")
            self.assertEqual(summary["pipeline-holder-distribution"]["signal"], "Potential Risk")
            bad = root / "notes" / "signals-bad.json"
            bad.write_text(json.dumps({"note_schema_version": 1, "lane": "coordinator",
                                       "signals": {"pipeline-pool-depth": {"topic": "token_and_liquidity", "signal": "Unverified"},
                                                   "missing-finding": {"topic": "token_economics", "signal": "Good"}}}))
            result = compose(root / "draft", bad, final=False, check=True)
            self.assertTrue(any("Unverified is only for coverage gaps" in e for e in result["errors"]), result["errors"])
            self.assertTrue(any("unknown finding id" in e for e in result["errors"]), result["errors"])
            # The scaffold offers a signals skeleton for every pipeline finding.
            scaffolded = scaffold_note(root / "draft", root / "notes" / "coordinator.json")
            self.assertEqual(set(scaffolded["pipeline_findings"]), ids)
            self.assertIn("signals", read_json(root / "notes" / "coordinator.json"))


class UserFocusTests(PipelineRunFixture):
    """The user's extra asks and links reach both lane briefs and the scaffold."""

    def test_focus_and_links_render_in_both_briefs_and_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            shutil.copytree(self.pristine, root)
            intake = {"target": {"chain_id": CHAIN, "address": TOKEN}, "question": "Broad diligence",
                      "focus": "dig into the lore behind this coin and whether it is \"true\" or AI slop {{FACTS}}",
                      "user_urls": ["https://x.com/example/status/123", "https://example.invalid/whitepaper"]}
            (root / "intake.json").write_text(json.dumps(intake))
            for lane in ("liquidity", "project"):
                text = broad_collect.brief(root, lane, 4)
                self.assertIn("## What the user asked", text)
                self.assertIn("dig into the lore behind this coin", text)
                self.assertIn("https://x.com/example/status/123", text)
                self.assertIn("https://example.invalid/whitepaper", text)
                self.assertIn("og:description", text)
                self.assertNotIn("{{", text)
            self.assertIn("Capture every one of these first", broad_collect.brief(root, "project", 4))
            self.assertIn("the project lane covers the rest", broad_collect.brief(root, "liquidity", 4))
            result = scaffold_note(root / "draft", root / "notes" / "coordinator.json")
            self.assertEqual(result["user_urls"], intake["user_urls"])
            self.assertIn("lore", result["user_focus"])
            self.assertIn("user_focus", result["next"])

    def test_standard_scope_without_focus_says_so(self):
        text = broad_collect.brief(self.pristine, "liquidity", 4)
        self.assertIn("No additional asks beyond the standard scope.", text)
        self.assertNotIn("{{", text)

    def test_user_urls_are_validated_and_capped(self):
        self.assertEqual(broad_collect.user_urls([" https://a.invalid/x ", "https://a.invalid/x", "https://b.invalid/y"]),
                         ["https://a.invalid/x", "https://b.invalid/y"])
        with self.assertRaises(Exception):
            broad_collect.user_urls(["https://user:secret@a.invalid/x"])
        with self.assertRaises(Exception):
            broad_collect.user_urls(["https://a.invalid/page?api_key=abc"])
        with self.assertRaises(Exception):
            broad_collect.user_urls([f"https://a.invalid/{n}" for n in range(7)])


class ScaffoldAndComposeTests(PipelineRunFixture):
    def test_scaffold_prefills_structure_and_compose_rejects_leftover_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            shutil.copytree(self.pristine, root)
            self._scaffold_case(root)

    def _scaffold_case(self, root):
        out = root / "notes" / "coordinator.json"
        result = scaffold_note(root / "draft", out)
        note = read_json(out)
        self.assertEqual(sorted(note["coverage"]), sorted(DIMENSIONS))
        self.assertIn("pool1", result["scope_ids"])
        self.assertIn("launchFactory", result["scope_ids"])
        self.assertGreater(result["todo_markers"], 10)
        self.assertEqual(note["lane"], "coordinator")
        self.assertEqual(note["findings"], [])
        composed = compose(root / "draft", out, final=True)
        self.assertEqual(composed["status"], "errors")
        self.assertTrue(any("unfinished placeholder" in e for e in composed["errors"]), composed["errors"][:5])
        self.assertTrue(any(e.startswith("coverage.token_controls.status") for e in composed["errors"]), composed["errors"][:5])
        with self.assertRaises(Exception):
            scaffold_note(root / "draft", out)  # refuses to overwrite without force
        scaffold_note(root / "draft", out, force=True)

    def test_compose_check_mode_writes_nothing(self):
        draft_before = (self.root / "draft" / "draft.json").read_bytes()
        note = self.root / "notes" / "check.json"
        note.write_text(json.dumps({"note_schema_version": 1, "lane": "coordinator", "findings": [
            {"id": "controls-check", "dimension": "token_controls", "claim": "state_observation", "strength": "strongly_supported",
             "confidence": "high", "impact": "neutral", "text": "SYNTHETIC: runtime read at the pin.", "evidence": ["runtime"]}],
            "coverage": {"token_controls": {"status": "checked"}}}))
        result = compose(self.root / "draft", note, final=False, check=True)
        self.assertEqual(result["errors"], [], result)
        self.assertEqual(result["mode"], "check")
        self.assertEqual((self.root / "draft" / "draft.json").read_bytes(), draft_before)
        self.assertFalse((self.root / "draft" / "notes-applied").exists())

    def test_claim_named_with_a_strength_value_gets_the_mapping_hint(self):
        note = self.root / "notes" / "claim.json"
        note.write_text(json.dumps({"note_schema_version": 1, "lane": "liquidity", "findings": [
            {"id": "creation", "dimension": "historical_launch_integrity", "claim": "proven_fact", "strength": "strongly_supported",
             "confidence": "high", "impact": "neutral", "text": "SYNTHETIC creation.", "evidence": ["runtime"]}]}))
        result = compose(self.root / "draft", note, lane="liquidity", final=False, check=True)
        self.assertTrue(any("is a strength value" in e for e in result["errors"]), result["errors"])

    def test_historical_execution_fills_receipt_result_and_derives_effects(self):
        receipt_alias = self.facts["receipts"][0]["evidence"]
        note = self.root / "notes" / "execution.json"
        note.write_text(json.dumps({"note_schema_version": 1, "lane": "coordinator", "findings": [
            {"id": "launch-flow", "dimension": "historical_launch_integrity", "claim": "historical_execution", "strength": "strongly_supported",
             "confidence": "high", "impact": "neutral", "text": "SYNTHETIC: the creation receipt shows the factory minting and distributing supply.",
             "evidence": [receipt_alias, "runtime", "arch-launchFactory-runtime", "actor-creator"],
             "execution": {"status": "success"}}],
            "coverage": {"historical_launch_integrity": {"status": "checked"}}}))
        result = compose(self.root / "draft", note, final=False, check=True)
        self.assertEqual(result["errors"], [], result)
        self.assertTrue(any("derived" in w and "effects" in w for w in result["warnings"]), result["warnings"])
        applied = compose(self.root / "draft", note, final=False)
        self.assertEqual(applied["errors"], [], applied)
        finding = next(f for f in read_draft(self.root / "draft")["findings"] if f["id"] == "launch-flow")
        execution = finding["execution"]
        self.assertEqual(execution["result"], "success")
        self.assertIn("receipt-", execution["receipt_evidence_id"])
        self.assertEqual(len(execution["effects"]), 1)
        self.assertEqual(execution["effects"][0]["asset_scope_id"], "target")
        self.assertEqual(execution["effects"][0]["units"], "raw_token_units")
        self.assertNotIn("status", execution)

    def test_historical_execution_without_a_receipt_names_the_missing_piece(self):
        note = self.root / "notes" / "noreceipt.json"
        note.write_text(json.dumps({"note_schema_version": 1, "lane": "coordinator", "findings": [
            {"id": "no-receipt", "dimension": "historical_launch_integrity", "claim": "historical_execution", "strength": "strongly_supported",
             "confidence": "high", "impact": "neutral", "text": "SYNTHETIC without receipt.", "evidence": ["runtime"], "execution": {"status": "success"}}]}))
        result = compose(self.root / "draft", note, final=False, check=True)
        self.assertTrue(any("receipt" in e for e in result["errors"]), result["errors"])
        self.assertFalse(any(e.strip("'") == "receipt_evidence_id" for e in result["errors"]), "no bare KeyError text")


if __name__ == "__main__":
    unittest.main()
