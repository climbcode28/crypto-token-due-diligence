"""Note-level errors must name the problem; compose never invents evidence or upgrades unknowns."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backend_common import write_new
from bundle_assemble import intake, read_draft, save_draft
from compose import compose
from test_strict_profile import strict


class ComposeTests(unittest.TestCase):
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

    def note(self, **overrides):
        base = {"note_schema_version": 1, "lane": "coordinator", "findings": [
            {"id": "controls", "dimension": "token_controls", "topic": "token_and_liquidity", "signal": "Good", "claim": "state_observation",
             "strength": "strongly_supported", "confidence": "high", "impact": "benefit",
             "text": "SYNTHETIC: runtime and metadata were read at the pin.", "evidence": ["e-code", "e-decimals"]}],
            "coverage": {"token_controls": {"status": "checked"}}}
        base.update(overrides)
        path = self.root / "note.json"
        path.write_text(json.dumps(base))
        return path

    def test_good_note_expands_support_scope_rating_and_summary(self):
        result = compose(self.draft, self.note(), final=False)
        self.assertEqual(result["errors"], [], result)
        d = read_draft(self.draft)
        finding = next(f for f in d["findings"] if f["id"] == "controls")
        self.assertEqual({s["role"] for s in finding["support"]}, {"direct"})
        self.assertEqual(finding["subject_scope_id"], "target")
        self.assertEqual(next(r for r in d["ratings"] if r["id"] == "token_controls")["status"], "pass")
        self.assertEqual(d["summary"], [{"finding_id": "controls", "topic": "token_and_liquidity", "signal": "Good"}])
        self.assertEqual(next(c for c in d["coverage_records"] if c["dimension"] == "token_controls")["status"], "checked")
        self.assertTrue(any(s["id"] == "target" for s in d["scope"]))
        self.assertTrue((self.draft / "notes-applied").is_dir())

    def test_errors_are_collected_and_draft_is_untouched(self):
        before = (self.draft / "draft.json").read_bytes()
        note = self.note(findings=[
            {"id": "bad id!", "dimension": "nowhere", "claim": "state_observation", "strength": "proven_fact", "confidence": "unknown",
             "impact": "adverse", "text": "x", "evidence": ["missing-alias"]},
            {"id": "gap", "dimension": "token_controls", "claim": "coverage_gap", "strength": "proven_fact", "confidence": "high", "impact": "benefit",
             "text": "SYNTHETIC gap mislabeled", "evidence": ["e-code"], "topic": "token_and_liquidity", "signal": "Unverified"}])
        result = compose(self.draft, note, final=False)
        self.assertEqual(result["status"], "errors")
        joined = " | ".join(result["errors"])
        self.assertIn("id must be", joined)
        self.assertIn("coverage gap must have unknown", joined)
        self.assertEqual(before, (self.draft / "draft.json").read_bytes())

    def test_resolved_finding_needs_direct_subject_evidence(self):
        note = self.note(findings=[{"id": "other", "dimension": "token_controls", "claim": "state_observation", "strength": "strongly_supported",
                                    "confidence": "high", "impact": "neutral", "text": "SYNTHETIC: header only", "evidence": ["e-header"]}])
        result = compose(self.draft, note, final=False)
        self.assertTrue(any("needs one successful RPC read of its subject" in e for e in result["errors"]), result)

    def test_adverse_finding_needs_concern_and_severity(self):
        note = self.note(findings=[{"id": "power", "dimension": "token_controls", "claim": "state_observation", "strength": "strongly_supported",
                                    "confidence": "high", "impact": "adverse", "text": "SYNTHETIC adverse without concern", "evidence": ["e-code"]}])
        result = compose(self.draft, note, final=False)
        joined = " | ".join(result["errors"])
        self.assertIn("adverse impact requires severity", joined)
        self.assertIn("need concern", joined)

    def test_final_mode_rejects_pending_boundaries_and_checkpoint_allows_them(self):
        coverage = {"token_controls": {"status": "partial", "gap": "SYNTHETIC unresolved", "priority": "material", "decision_impact": "SYNTHETIC impact",
                                       "attempts": [{"check": "Read code", "outcome": "Only code read", "evidence": ["e-code"]}], "boundary": "pending", "basis": "SYNTHETIC still feasible"}}
        findings = [{"id": "gap", "dimension": "token_controls", "topic": "token_and_liquidity", "signal": "Unverified", "claim": "coverage_gap",
                     "text": "SYNTHETIC: controls not reviewed", "evidence": ["e-code"]}]
        result = compose(self.draft, self.note(findings=findings, coverage=coverage), final=True)
        self.assertTrue(any("completed report needs boundary" in e for e in result["errors"]), result)
        result = compose(self.draft, self.note(findings=findings, coverage=coverage), final=False)
        self.assertEqual(result["errors"], [], result)
        d = read_draft(self.draft)
        row = next(c for c in d["coverage_records"] if c["dimension"] == "token_controls")
        self.assertEqual(row["closure"]["next_route"]["disposition"], "pending")
        self.assertEqual(next(r for r in d["ratings"] if r["id"] == "token_controls")["status"], "unknown")

    def test_checked_coverage_with_gap_findings_is_downgraded_or_explained(self):
        findings = [{"id": "gap", "dimension": "token_controls", "claim": "coverage_gap", "text": "SYNTHETIC gap", "evidence": ["e-code"]}]
        # Lane note: the weaker claim is applied automatically and explained.
        result = compose(self.draft, self.note(findings=findings, coverage={"token_controls": {"status": "checked"}}), final=False)
        self.assertEqual(result["errors"], [], result)
        self.assertTrue(any("downgraded from checked to partial" in w for w in result["warnings"]), result)
        self.assertEqual(next(c for c in read_draft(self.draft)["coverage_records"] if c["dimension"] == "token_controls")["status"], "partial")
        # Final note without a deliverable boundary: one precise instruction instead of a generic refusal.
        result = compose(self.draft, self.note(findings=findings, coverage={"token_controls": {"status": "checked"}}), final=True)
        self.assertTrue(any("so this surface is partial, not checked" in e and "boundary exhausted|unavailable|not_yet_observable" in e for e in result["errors"]), result)
        # Final note with a boundary and basis: downgraded, no error from this rule.
        result = compose(self.draft, self.note(findings=findings, coverage={"token_controls": {"status": "checked", "boundary": "unavailable", "basis": "SYNTHETIC: source does not publish it"}}), final=True)
        self.assertFalse(any("partial, not checked" in e or "cannot keep" in e for e in result["errors"]), result)
        self.assertTrue(any("downgraded from checked to partial" in w for w in result["warnings"]), result)
        self.assertTrue(any("not_applicable" in e or "cannot keep" in e for e in compose(self.draft, self.note(findings=findings, coverage={"token_controls": {"status": "not_applicable"}}), final=False)["errors"]))

    def test_decision_requires_adverse_kind_for_severe_findings_and_mitigation(self):
        findings = [{"id": "seizure", "dimension": "token_controls", "topic": "token_and_liquidity", "signal": "Bad", "claim": "state_observation",
                     "strength": "strongly_supported", "confidence": "high", "impact": "adverse", "severity": "critical",
                     "text": "SYNTHETIC: owner can seize balances.", "evidence": ["e-code"],
                     "concern": {"basis": "reachable_capability", "mechanism": "SYNTHETIC seize()", "consequence": "SYNTHETIC holder loss"}}]
        decision = {"verdict": {"kind": "findings_with_limits", "scope": "SYNTHETIC"},
                    "synthesis": {"technical_exposure": "a", "credibility_maturity": "b", "token_economics": "c", "research_confidence": "d"}, "actions": []}
        text = {"verdict": "v", "main_reasons": "m", "strongest_contrary_evidence": "s", "unresolved_questions": "u", "change_evidence": "c"}
        result = compose(self.draft, self.note(findings=findings, decision=decision, text=text), final=True)
        joined = " | ".join(result["errors"])
        self.assertIn("require kind adverse_findings", joined)
        self.assertIn("need a mitigate action", joined)
        decision["verdict"]["kind"] = "adverse_findings"
        decision["actions"] = [{"id": "m1", "kind": "mitigate", "action": "SYNTHETIC avoid exposure", "reason": "SYNTHETIC seizure power",
                                "findings": ["seizure"], "changes_view_if": "SYNTHETIC power removed"}]
        result = compose(self.draft, self.note(findings=findings, decision=decision, text=text), final=False)
        self.assertEqual(result["errors"], [], result)
        d = read_draft(self.draft)
        self.assertEqual(d["decision_review"]["verdict"]["kind"], "adverse_findings")
        self.assertEqual(d["decision_review"]["actions"][0]["coverage_dimensions"], ["token_controls"])
        self.assertEqual(next(r for r in d["ratings"] if r["id"] == "token_controls")["severity"], "critical")

    def test_not_applicable_surface_cannot_supply_a_summary_row(self):
        findings = [{"id": "no-rewards", "dimension": "reward_accounting_liveness", "topic": "token_economics", "signal": "Good", "claim": "state_observation",
                     "strength": "strongly_supported", "confidence": "medium", "impact": "neutral", "text": "SYNTHETIC: no reward contract", "evidence": ["e-code"]}]
        result = compose(self.draft, self.note(findings=findings, coverage={"reward_accounting_liveness": {"status": "not_applicable", "outcome": "SYNTHETIC none"}}), final=False)
        self.assertTrue(any("cannot be a summary row" in e for e in result["errors"]), result)
        findings[0].pop("topic"); findings[0].pop("signal")
        result = compose(self.draft, self.note(findings=findings, coverage={"reward_accounting_liveness": {"status": "not_applicable", "outcome": "SYNTHETIC none"}}), final=False)
        self.assertEqual(result["errors"], [], result)
        self.assertEqual(next(r for r in read_draft(self.draft)["ratings"] if r["id"] == "reward_accounting_liveness")["status"], "not_applicable")

    def test_cli_reports_errors_with_exit_code(self):
        note = self.note(findings=[{"id": "x", "dimension": "token_controls", "claim": "state_observation", "strength": "proven_fact",
                                    "confidence": "high", "impact": "benefit", "text": "SYNTHETIC", "evidence": ["nope"]}])
        cli = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/bundle_assemble.py"), "compose", str(self.draft), str(note)],
                             capture_output=True, text=True)
        self.assertEqual(cli.returncode, 2)
        self.assertIn("evidence alias not found", cli.stdout)
        facts = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/bundle_assemble.py"), "facts", str(self.draft)],
                               capture_output=True, text=True)
        self.assertEqual(facts.returncode, 0)
        self.assertIn("e-code", facts.stdout)


if __name__ == "__main__":
    unittest.main()
