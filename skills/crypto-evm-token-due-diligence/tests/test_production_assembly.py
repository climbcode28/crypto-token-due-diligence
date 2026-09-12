"""Offline forward tests of real note/freeze paths; fixture claims are synthetic only."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from bundle_assemble import deliver, freeze, intake, read_draft, save_draft
from compose import compose
from fixtures import bind
from scaffold import scope_entries
from test_strict_profile import strict
from validate_bundle import DIMENSIONS, Invalid, validate


class ProductionAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        m, r = strict(self.root)
        self.draft = self.root / "draft"
        d = intake(self.draft, r["target"], "SYNTHETIC focused owner check", "Offline fixture only", True)
        shutil.copytree(self.root / "evidence", self.draft / "evidence")
        for ev in m["evidence"]:
            ev["observation_status"] = "ok"
        d.update(evidence=m["evidence"], pins=m["chains"][0]["pins"],
                 chain_id_evidence=m["chains"][0]["chain_id_evidence"])
        save_draft(self.draft, d)

    def apply(self, name, note, final=False):
        path = self.root / (name + ".json")
        path.write_text(json.dumps({"note_schema_version": 1, **note}))
        result = compose(self.draft, path, final=final)
        self.assertEqual(result["errors"], [], result)
        return path

    def observed(self, all_dimensions=False, **overrides):
        row = {"id": "pipeline-controls", "dimensions": list(DIMENSIONS) if all_dimensions else ["token_controls"],
               "claim": "state_observation", "strength": "strongly_supported", "confidence": "high",
               "impact": "neutral", "text": "SYNTHETIC: fixture runtime was captured; no real token assessment.",
               "evidence": ["e-code"]}
        row.update(overrides)
        return row

    def checkpoint(self):
        before = (self.draft / "draft.json").read_bytes()
        out = freeze(self.draft, self.root / "checkpoint", True, checkpoint=True)
        _, report = validate(out, True, out / "report.md")
        self.assertEqual((self.draft / "draft.json").read_bytes(), before)
        self.assertEqual(report["delivery_status"], "internal_checkpoint")
        with self.assertRaisesRegex(Invalid, "not eligible for final delivery"):
            deliver(out, True)
        return out, report

    def completed_note(self, partial=False):
        findings = [self.observed(True, topic="token_and_liquidity", signal="Good")]
        if partial:
            findings.append({"id": "open-surface-checks", "dimensions": list(DIMENSIONS), "claim": "coverage_gap",
                             "text": "SYNTHETIC: surface claims beyond the runtime observation remain unavailable.",
                             "evidence": ["e-code"], "topic": "real_work_vs_marketing", "signal": "Unverified"})
        coverage = {dim: {"status": "checked"} for dim in DIMENSIONS}
        if partial:
            coverage = {dim: {"status": "partial", "gap": "SYNTHETIC: additional surface evidence unavailable.",
                              "attempts": [{"check": "Read fixture runtime", "outcome": "Only runtime captured", "evidence": ["e-code"]}],
                              "boundary": "unavailable", "basis": "SYNTHETIC offline fixture has no additional surface sources."}
                        for dim in DIMENSIONS}
        return {"lane": "coordinator", "findings": findings, "coverage": coverage,
                "decision": {"requirements": [], "verdict": {"kind": "findings_with_limits", "scope": "SYNTHETIC plumbing fixture",
                                                               "findings": ["pipeline-controls"]},
                             "synthesis": {axis: "SYNTHETIC fixture only; the stated evidence does not establish real token quality."
                                           for axis in ("technical_exposure", "credibility_maturity", "token_economics", "research_confidence")},
                             "actions": []},
                "text": {key: "SYNTHETIC fixture only; observations retain their evidence limits."
                         for key in ("verdict", "main_reasons", "strongest_contrary_evidence", "unresolved_questions", "change_evidence")}}

    def test_focused_intake_checkpoint_needs_no_coordinator_judgment(self):
        _, report = self.checkpoint()
        self.assertEqual(report["summary"], [{"finding_id": "gap-token_controls", "topic": "token_and_liquidity", "signal": "Unverified"}])
        self.assertNotIn("decision_review", report)
        self.assertNotIn("decision_review_version", report)
        self.assertTrue(all(c["status"] == "not_checked" and c["closure"]["attempts"] == []
                            and c["closure"]["next_route"]["disposition"] == "pending" for c in report["coverage_records"]))
        self.assertTrue(all(r["status"] == "unknown" for r in report["ratings"]))

    def test_documented_checkpoint_cli_saves_pipeline_before_analyst_note(self):
        self.apply("pipeline", {"lane": "pipeline", "findings": [self.observed()]})
        before = (self.draft / "draft.json").read_bytes()
        cli = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/bundle_assemble.py"),
                              "finalize", str(self.draft), "--out", str(self.root / "checkpoint"),
                              "--checkpoint", "--allow-synthetic"], capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        self.assertEqual(json.loads(cli.stdout)["status"], "internal_checkpoint")
        _, report = validate(self.root / "checkpoint", True, self.root / "checkpoint/report.md")
        self.assertIn("pipeline-controls", {f["id"] for f in report["findings"]})
        self.assertEqual(report["summary"], [{"finding_id": "gap-canonical_lp_principal_custody", "topic": "token_and_liquidity", "signal": "Unverified"}])
        self.assertFalse(any(row["finding_id"] == "pipeline-controls" for row in report["summary"]),
                         "Saving evidence must not assign the pipeline's signal")
        self.assertNotIn("decision_review", report)
        self.assertEqual((self.draft / "draft.json").read_bytes(), before)

    def test_observed_all_surfaces_checkpoint_can_have_no_summary_or_gaps(self):
        self.apply("pipeline", {"lane": "pipeline", "findings": [self.observed(True)],
                                "coverage": {dim: {"status": "checked"} for dim in DIMENSIONS}})
        _, report = self.checkpoint()
        self.assertEqual(report["summary"], [])
        self.assertEqual(len(report["findings"]), 1)
        self.assertTrue(all(r["status"] == "pass" for r in report["ratings"]))

    def test_checkpoint_keeps_severe_concern_and_existing_signal(self):
        severe = self.observed(id="seizure", impact="adverse", severity="critical",
                              text="SYNTHETIC: owner can seize balances.",
                              concern={"basis": "reachable_capability", "mechanism": "SYNTHETIC seize()",
                                       "consequence": "SYNTHETIC holder loss"})
        self.apply("severe", {"lane": "pipeline", "findings": [severe]})
        _, report = self.checkpoint()
        self.assertEqual(report["summary"], [{"finding_id": "seizure", "topic": "token_and_liquidity", "signal": "Potential Risk"}])
        self.assertEqual(report["ratings"][0]["status"], "concern")
        self.assertEqual(report["ratings"][0]["severity"], "critical")
        self.assertNotIn("decision_review", report, "Storage must not invent a mitigation or recommendation")

    def test_complete_and_partial_completed_reports_still_require_judgment(self):
        note = self.completed_note(partial=True)
        self.apply("coordinator", note, final=True)
        out = freeze(self.draft, self.root / "complete", True)
        self.assertEqual(deliver(out, True)["status"], "ready_for_final_delivery")
        _, report = validate(out, True)
        self.assertTrue(all(r["status"] == "unknown" for r in report["ratings"]), "Partial observations cannot become passes")
        self.assertTrue(any(s["signal"] == "Unverified" for s in report["summary"]))
        note["findings"] = note["findings"][:1]
        # Replace the open finding with the same ID as a resolved observation;
        # compose then has affirmative evidence instead of silently dropping it.
        note["findings"].append(self.observed(True, id="open-surface-checks"))
        note["coverage"] = {dim: {"status": "checked"} for dim in DIMENSIONS}
        self.apply("coordinator-complete", note, final=True)
        normal = freeze(self.draft, self.root / "normal", True)
        self.assertEqual(deliver(normal, True)["status"], "ready_for_final_delivery")

    def test_no_empty_summary_or_missing_decision_escape_for_complete_report(self):
        self.apply("coordinator", self.completed_note(), final=True)
        out = freeze(self.draft, self.root / "complete", True)
        m, report = validate(out, True)
        empty = copy.deepcopy(report)
        empty["summary"] = []
        bind(out, m, empty)
        with self.assertRaisesRegex(Invalid, "summary must be a nonempty list"):
            validate(out, True)
        missing = copy.deepcopy(report)
        del missing["decision_review"]
        del missing["decision_review_version"]
        bind(out, m, missing)
        with self.assertRaisesRegex(Invalid, "completed report requires its decision review"):
            validate(out, True)

    def test_older_strict_fixture_without_completion_markers_still_validates(self):
        validate(self.root, True)


class ScaffoldProxyObservationTests(unittest.TestCase):
    def test_missing_failed_and_successful_slot_reads_remain_distinct(self):
        architecture = {"label": "locker", "address": "0x" + "b" * 40, "code_bytes": 40,
                        "eip1967_implementation": None, "evidence": {"implementation_slot": "locker-impl", "code": "locker-code"}}
        for status, raw, expected in [(None, None, "unresolved"), ("unavailable", None, "unresolved"),
                                      ("unavailable", 0, "unresolved"), ("ok", None, "unresolved"),
                                      ("ok", False, "unresolved"), ("ok", 0, "none_found")]:
            with self.subTest(status=status, raw=raw):
                a = {**architecture, "implementation_status": status, "eip1967_implementation_raw": raw}
                entry = scope_entries({"architecture": [a]}, {"scope": []})[0]
                self.assertEqual(entry["proxy"]["status"], expected)
                if expected == "unresolved":
                    self.assertNotIn("slot is zero", entry["proxy"]["basis"])
        a = {**architecture, "implementation_status": "ok", "eip1967_implementation_raw": 7,
             "eip1967_implementation": "0x" + "c" * 40}
        entry = scope_entries({"architecture": [a]}, {"scope": []})[0]
        self.assertEqual(entry["proxy"]["status"], "unresolved")
        self.assertIn("points to", entry["proxy"]["basis"])


if __name__ == "__main__":
    unittest.main()
