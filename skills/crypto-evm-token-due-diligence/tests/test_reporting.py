"""Synthetic reporting cases; labels never authenticate the underlying claims."""
import unittest

import test_bundle
from validate_bundle import Invalid, validate, sha
from render_report import render


class ReportingTests(unittest.TestCase):
    setUp = test_bundle.BundleTests.setUp
    save = test_bundle.BundleTests.save
    reject = test_bundle.BundleTests.reject
    control_support = test_bundle.BundleTests.control_support
    evidence = test_bundle.BundleTests.evidence

    def item(self, signal="Potential Risk", finding_id="F-coverage"):
        return {"finding_id": finding_id, "topic": "token_and_liquidity", "signal": signal}

    def output(self):
        self.save()
        m, r = validate(self.root, allow_synthetic=True)
        return render(m, r, sha((self.root / "report.json").read_bytes()))

    def adverse(self, severity="high"):
        self.control_support()
        self.r["findings"][-1]["proposition"] = "SYNTHETIC: an inspected authority can seize holder balances."
        self.r["ratings"][0].update(status="concern", severity=severity, likelihood="possible", coverage="partial")
        self.r["summary"] = [self.item("Bad", "F-control"), self.item()]

    def test_unknown_is_explicit_coverage_gap_in_summary(self):
        self.r["summary"] = [self.item()]
        output = self.output()
        overview = output.split("## Evidence and technical detail")[0]
        self.assertIn("🟡 **Potential Risk — Unknown**", overview)
        self.assertNotIn("**Good**", overview)
        self.assertNotIn("**Bad**", overview)
        self.assertIn("[evidence](#finding-1)", overview)
        self.assertIn('id="finding-1"', output)

    def test_summary_cannot_upgrade_unknown_to_good_or_bad(self):
        for signal in ("Good", "Bad"):
            with self.subTest(signal=signal):
                self.r["summary"] = [self.item(signal)]
                self.reject("summary signal requires resolved evidence")

    def test_bounded_positive_and_separate_unknown_can_coexist(self):
        self.control_support()
        self.r["summary"] = [self.item("Good", "F-control"), self.item()]
        output = self.output()
        self.assertIn("✅ **Good**", output)
        self.assertIn("Potential Risk — Unknown", output)

    def test_low_confidence_or_inference_cannot_be_bad(self):
        self.adverse()
        for changes in ({"confidence": "low"}, {"evidence_type": "inference"}):
            with self.subTest(changes=changes):
                self.r["findings"][-1].update(evidence_type="proven_fact", confidence="high")
                self.r["findings"][-1].update(changes)
                self.reject("summary signal requires resolved evidence")

    def test_failed_rpc_cannot_support_good_or_bad(self):
        self.control_support(error=True)
        self.r["ratings"][0].update(status="concern", severity="high", likelihood="possible", coverage="partial")
        for signal in ("Good", "Bad"):
            with self.subTest(signal=signal):
                self.r["summary"] = [self.item(signal, "F-control")]
                self.reject("summary signal requires resolved evidence")

    def test_redacted_success_cannot_support_good_or_bad(self):
        self.control_support()
        self.evidence("e-control")["redacted"] = True
        self.r["ratings"][0].update(status="concern", severity="high", likelihood="possible", coverage="partial")
        for signal in ("Good", "Bad"):
            with self.subTest(signal=signal):
                self.r["summary"] = [self.item(signal, "F-control")]
                self.reject("summary signal requires resolved evidence")

    def test_supported_harmful_power_can_be_bad_without_observed_exploit(self):
        self.adverse()
        self.assertIn("🔴 **Bad**", self.output())

    def test_bad_requires_material_concern(self):
        self.adverse(severity="low")
        self.reject("Bad requires a supported material concern")

    def test_critical_finding_cannot_be_omitted_from_summary(self):
        self.adverse(severity="critical")
        self.r["summary"] = [self.item()]
        self.reject("summary omits a high/critical concern")

    def test_low_confidence_critical_concern_stays_visible_as_potential_risk(self):
        self.adverse(severity="critical")
        self.r["findings"][-1].update(evidence_type="inference", confidence="low")
        self.r["summary"][0]["signal"] = "Potential Risk"
        self.assertIn("Potential Risk — Inference", self.output())

    def test_summary_rejects_missing_duplicate_and_unlinked_findings(self):
        for items, pattern in (([], "summary must be a nonempty list"),
                               ([self.item(finding_id="missing")], "summary finding is missing"),
                               ([self.item(), self.item()], "duplicate summary finding")):
            with self.subTest(items=items):
                self.r["summary"] = items
                self.reject(pattern)

    def test_summary_rejects_invented_signal_or_topic(self):
        for field, value, pattern in (("signal", "Safe", "invalid summary signal"),
                                      ("topic", "price_prediction", "invalid summary topic")):
            self.r["summary"] = [dict(self.item(), **{field: value})]
            self.reject(pattern)

    def test_not_applicable_is_never_a_positive_summary_item(self):
        self.control_support()
        self.r["ratings"][0].update(status="not_applicable", coverage="not_applicable")
        self.r["summary"] = [self.item("Good", "F-control")]
        self.reject("summary finding must support an applicable rating")

    def test_summary_cannot_replace_finding_text(self):
        self.r["summary"] = [dict(self.item(), text="Everything is safe")]
        self.reject("summary item requires only")

    def test_summary_escapes_external_markdown(self):
        self.r["summary"] = [self.item()]
        self.r["findings"][0]["proposition"] = "SYNTHETIC: [click](https://example.invalid) | ![image](url)"
        output = self.output().split("## Evidence and technical detail")[0]
        self.assertNotIn("[click](https://example.invalid)", output)
        self.assertNotIn("![image](url)", output)
        self.assertIn("\\|", output)

    def test_summary_render_is_bound_to_source(self):
        self.adverse()
        path = self.root / "report.md"
        path.write_text(self.output(), encoding="utf-8")
        validate(self.root, allow_synthetic=True, rendered=path)
        path.write_text(path.read_text().replace("**Bad**", "**Good**"), encoding="utf-8")
        with self.assertRaisesRegex(Invalid, "rendered report differs"):
            validate(self.root, allow_synthetic=True, rendered=path)

    def test_legacy_report_output_is_byte_identical(self):
        # Captured from the pre-change renderer against this deterministic fixture.
        self.assertEqual(sha(self.output().encode()),
                         "722007471773cf5a613752dd93a079bbf6b8c147f377f464cfa42f10e333883b")

    def test_summary_cannot_reference_unrated_finding(self):
        self.control_support()
        self.r["ratings"][0].update(status="unknown", severity="unknown", confidence="unknown",
                                    finding_ids=["F-coverage"])
        self.r["summary"] = [self.item("Good", "F-control")]
        self.reject("summary finding must support an applicable rating")

    def test_material_concern_without_resolved_rating_cannot_be_bad(self):
        self.adverse()
        self.r["ratings"][0]["confidence"] = "low"
        self.reject("Bad requires a supported material concern")

    def test_summary_preserves_contrary_evidence_before_appendix(self):
        self.adverse()
        self.r["strongest_contrary_evidence"] = "SYNTHETIC: the harmful power was not observed in use."
        self.assertIn(self.r["strongest_contrary_evidence"], self.output().split("## Evidence and technical detail")[0])

    def test_cli_summary_render_and_validation(self):
        self.adverse()
        self.save()
        test_bundle.BundleTests.test_cli_render_and_validation(self)
        self.assertIn("**Bad**", (self.root / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
