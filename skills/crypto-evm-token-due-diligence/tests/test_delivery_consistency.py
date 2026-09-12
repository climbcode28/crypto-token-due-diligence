"""Offline regressions for arithmetic and findings lost during chat compression."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import facts
from pipeline_note import build_pipeline_note
from bundle_assemble import delivery_reading_checklist


class HolderSummaryTests(unittest.TestCase):
    def holders(self):
        # Distinct address balances; no inferred beneficial-owner grouping.
        amounts = [112898312424464466803000251, 81632653061224489738093187,
                   26356208549250987091022872, 18812992302983788424152495,
                   17952202498880588383352259, 14400431660651571498235629,
                   14304899699875665480432131, 12301473609068393772847272,
                   12153251391911140072441330, 10787157073420283199411533]
        return [{"address": "0x" + format(i + 1, "040x"), "raw": raw,
                 "pct_supply": 99,  # Rounded/display values must never feed the aggregate.
                 "code_bytes": 23, "evidence": {"balance": "hold-" + str(i), "runtime": "code-" + str(i)}}
                for i, raw in enumerate(amounts)]

    def test_exact_integer_sum_and_all_code_bearing_cohort(self):
        rows = self.holders()
        result = facts.holder_summary(rows, 10 ** 27)
        self.assertEqual(result["sum_raw"], "321599582271731374462988959")
        self.assertEqual(result["pct_supply"], "32.1600")
        self.assertEqual(result["largest"]["address"], rows[0]["address"])
        self.assertEqual(result["largest"]["pct_supply"], "11.2898")
        self.assertEqual(result["read_count"], 10)
        self.assertEqual(result["account_counts"]["code_bearing"], 10)

    def test_dedup_missing_balances_zero_and_unknown_supply(self):
        rows = self.holders()[:2]
        rows += [copy.deepcopy(rows[0]), {"address": "0x" + "f" * 40, "raw": None},
                 {"address": "0x" + "e" * 40, "raw": 0, "code_bytes": 0}]
        result = facts.holder_summary(rows, 10 ** 27)
        self.assertEqual((result["selected_count"], result["read_count"], result["missing_count"]), (4, 3, 1))
        self.assertEqual(result["sum_raw"], str(rows[0]["raw"] + rows[1]["raw"]))
        self.assertEqual(result["pct_supply"], "19.4531")
        self.assertIsNone(facts.holder_summary(rows, None)["pct_supply"])
        self.assertIsNone(facts.holder_summary(rows, 0)["pct_supply"])
        self.assertIsNone(facts.holder_summary([], 10 ** 27)["pct_supply"])

    def test_runtime_classification_needs_designator_not_just_length(self):
        target = "ab" * 20
        self.assertEqual(facts.account_code_kind("0xef0100" + target), "delegated_account")
        self.assertEqual(facts.account_code_kind("0x" + "60" * 23), "code_bearing")
        self.assertEqual(facts.account_code_kind("0x"), "no_code")
        self.assertEqual(facts.account_code_kind(None), "unknown")

    def test_pipeline_prints_computed_total_and_never_calls_all_code_contracts(self):
        sample = {"target": {"chain_id": 1, "address": "0x" + "f" * 40},
                  "metadata": {"symbol": "TEST", "total_supply": 10 ** 27, "decimals": 18},
                  "top_holders": self.holders(), "source": {"status": "not_found"}}
        evidence = [{"id": alias} for h in sample['top_holders'] for alias in h['evidence'].values()]
        evidence += [{"id": "runtime"}, {"id": "metadata-total_supply"}]
        result = build_pipeline_note(sample, {"scope": [], "evidence": evidence})
        row = next(f for f in result["findings"] if f["id"] == "pipeline-holder-distribution")
        self.assertIn("32.1600%", row["text"])
        self.assertIn("11.2898%", row["text"])
        self.assertNotIn("are contracts", row["text"])
        self.assertNotIn("signal", row, "aggregate concentration does not automatically earn a risk label")


class DeliveryChecklistTests(unittest.TestCase):
    def test_unselected_dimensions_remain_in_existing_delivery_response(self):
        report = {"summary": [{"finding_id": "market", "signal": "Good"}],
                  "findings": [{"id": "market"}, {"id": "holders"}, {"id": "locker"}, {"id": "assurance"}],
                  "coverage_records": [
                      {"dimension": "current_concentration", "status": "partial", "finding_ids": ["holders"], "gap": "Beneficial owners unknown"},
                      {"dimension": "canonical_lp_principal_custody", "status": "partial", "finding_ids": ["locker"], "gap": "Withdrawal authority unresolved"},
                      {"dimension": "development_disclosure", "status": "partial", "finding_ids": ["market", "assurance"], "gap": "No matched token source or audit"}]}
        before = copy.deepcopy(report)
        checklist = delivery_reading_checklist(report)
        self.assertEqual({r["dimension"] for r in checklist}, {r["dimension"] for r in report["coverage_records"]})
        self.assertEqual(checklist[0]["finding_ids"], ["holders"])
        self.assertEqual(checklist[1]["gap"], "Withdrawal authority unresolved")
        self.assertEqual(checklist[2]["gap"], "No matched token source or audit")
        self.assertEqual(report, before, "delivery may not alter a frozen report or its ratings")

    def test_completed_and_not_applicable_surfaces_do_not_gain_gaps(self):
        report = {"coverage_records": [{"dimension": "reward_accounting_liveness", "status": "not_applicable", "finding_ids": ["no-rewards"]}]}
        checklist = delivery_reading_checklist(report)
        self.assertEqual(checklist[0]["status"], "not_applicable")
        self.assertIsNone(checklist[0]["gap"])


if __name__ == "__main__":
    unittest.main()
