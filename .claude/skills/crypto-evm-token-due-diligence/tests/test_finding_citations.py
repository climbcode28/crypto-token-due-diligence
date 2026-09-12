"""Offline citation routing must preserve evidence boundaries and frozen inputs."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from render_report import finding_citations, render_summary


class FindingCitationTests(unittest.TestCase):
    def setUp(self):
        self.finding = {"id": "market", "claim_type": "state_observation",
                        "evidence_type": "strongly_supported", "confidence": "high",
                        "impact": "neutral", "proposition": "Observed market activity",
                        "time_basis": "At the pin", "evidence_ids": ["rpc", "market"],
                        "support": [{"evidence_id": "market", "role": "corroboration"}]}
        self.evidence = {
            "rpc": {"id": "rpc", "kind": "rpc", "query": {"url": "https://private.invalid/rpc"}},
            "market": self.document("market", "https://api.dexscreener.com/token-pairs/v1/chain/token"),
            "unrelated": self.document("unrelated", "https://github.com/unrelated/project")}

    def document(self, eid, url, **fields):
        return dict(id=eid, kind="document", observation_status="ok", query={"url": url}, **fields)

    def test_existing_summary_exposes_only_cited_sources_without_network_or_mutation(self):
        manifest = {"chains": [], "evidence": list(self.evidence.values())}
        report = {"findings": [self.finding], "conditions": "Exact target",
                  "summary": [{"finding_id": "market", "topic": "adoption_and_maturity", "signal": "Good"}],
                  "strongest_contrary_evidence": "Bounded", "unresolved_questions": "Known gaps",
                  "change_evidence": "New state"}
        before = copy.deepcopy((manifest, report))
        with patch("socket.create_connection", side_effect=AssertionError("Presentation must stay offline")):
            output = "\n".join(render_summary(manifest, report))
        self.assertIn("[Market snapshot](<https://api.dexscreener.com/", output)
        self.assertIn("[evidence](#finding-1)", output)
        self.assertNotIn("private.invalid", output)
        citations = finding_citations(self.finding, 1, self.evidence)
        self.assertFalse(any(icon in citations for icon in ("🌐", "💻", "📄", "🔎", "![", "<img")))
        self.assertIn("✅ **Good**", output, "assessment markers remain distinct from source branding")
        self.assertNotIn("unrelated/project", output)
        self.assertEqual((manifest, report), before)

    def test_gap_and_rpc_only_findings_keep_frozen_evidence_fallback(self):
        self.finding.update(claim_type="coverage_gap", evidence_type="unknown", confidence="unknown", impact="unknown", adverse_severity="unknown")
        self.assertEqual(finding_citations(self.finding, 7, self.evidence), "[evidence](#finding-7)")
        self.finding.update(claim_type="state_observation", evidence_type="strongly_supported", impact="neutral", evidence_ids=["rpc"])
        self.assertEqual(finding_citations(self.finding, 8, self.evidence), "[evidence](#finding-8)")

    def test_failed_redacted_and_non_supporting_sources_are_not_promoted(self):
        for change in ({"observation_status": "unavailable"}, {"redacted": True}):
            with self.subTest(change=change):
                evidence = copy.deepcopy(self.evidence)
                evidence["market"].update(change)
                self.assertNotIn("Market snapshot", finding_citations(self.finding, 1, evidence))
        for role in ("failed_attempt", "counterevidence", "identity"):
            self.finding["support"][0]["role"] = role
            self.assertNotIn("Market snapshot", finding_citations(self.finding, 1, self.evidence))

    def test_unsafe_urls_are_skipped_and_valid_destinations_are_escaped(self):
        for url in ("javascript:alert(1)", "https://user:pass@example.com", "https://example.com\n![x](evil)", "https://example.com\\@evil.com"):
            self.evidence["market"]["query"]["url"] = url
            self.assertEqual(finding_citations(self.finding, 1, self.evidence), "[evidence](#finding-1)")
        self.evidence["market"]["query"]["url"] = "https://example.com/a)[x](evil)"
        result = finding_citations(self.finding, 1, self.evidence)
        self.assertIn("%29%5Bx%5D%28evil%29", result)
        self.assertNotIn("[x](evil)", result)

    def test_links_are_deduplicated_capped_and_repository_host_is_exact(self):
        url = "https://api.github.com/repos/org/project"
        self.evidence["market"]["query"] = {"url": url, "source_urls": [url, "https://github.com.evil.invalid/source", "https://example.com/third"]}
        result = finding_citations(self.finding, 3, self.evidence)
        self.assertEqual(result.count(url), 1)
        self.assertEqual(result.count("Repository"), 1)
        self.assertIn("[Source](<https://github.com.evil.invalid/source>)", result)
        self.assertNotIn("example.com/third", result)


if __name__ == "__main__":
    unittest.main()
