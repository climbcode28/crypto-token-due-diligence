"""Neutral research gaps must neither allege harm nor conceal supported concerns."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from fixtures import bind
from test_strict_profile import strict
from decision_fixtures import cutoff_decision
from validate_bundle import Invalid, sha, validate
from report_profile import CURRENT_PROFILE
from render_report import render


class AssessmentReportingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.m, self.r = strict(self.root)
        self.r['summary'][0]['signal'] = 'Unverified'

    def output(self):
        bind(self.root, self.m, self.r)
        m, r = validate(self.root, True, required_profile=CURRENT_PROFILE)
        return render(m, r, sha((self.root / 'report.json').read_bytes()))

    def add_finding(self, fid, topic, signal, impact='benefit', inference=False):
        f = copy.deepcopy(self.r['findings'][0])
        f.update(id=fid, proposition='SYNTHETIC: ' + fid,
                 claim_type='inference' if inference else 'state_observation',
                 evidence_type='inference' if inference else 'strongly_supported',
                 confidence='low' if inference else 'medium', impact=impact,
                 adverse_severity='high' if impact == 'adverse' else 'none')
        f['support'][0]['role'] = 'direct'
        self.r['findings'].append(f)
        index = 0 if impact == 'adverse' else -1
        rating, coverage = self.r['ratings'][index], self.r['coverage_records'][index]
        rating['finding_ids'].append(fid)
        coverage['finding_ids'].append(fid)
        if impact == 'adverse':
            rating.update(status='concern', severity='high', likelihood='possible',
                          confidence=f['confidence'], coverage='partial')
            coverage.update(status='partial', evidence_ids=['e-code'])
        self.r['summary'].append({'finding_id': fid, 'topic': topic, 'signal': signal})
        return f

    def test_pure_gap_is_neutral_and_separate(self):
        output = self.output().split('## Evidence and technical detail')[0]
        assessed, gaps = output.split('### Research gaps', 1)
        self.assertNotIn('[evidence](#finding-1)', assessed)
        self.assertNotIn('| Area | Assessment | Finding |', assessed)
        self.assertIn('⚪ **Unverified**', gaps)
        self.assertIn('[evidence](#finding-1)', gaps)
        self.assertNotIn('Potential Risk — Unknown', output)
        self.assertTrue(all(r['status'] == 'unknown' for r in self.r['ratings']))

    def test_older_strict_gap_is_compatible_without_mutating_source(self):
        self.r['summary'][0]['signal'] = 'Potential Risk'
        self.assertIn('⚪ **Unverified**', self.output())
        self.assertEqual(self.r['summary'][0]['signal'], 'Potential Risk')

    def test_adoption_and_economics_do_not_clear_technical_gaps(self):
        self.add_finding('sustained usage', 'adoption_and_maturity', 'Good')
        self.add_finding('observed buybacks', 'token_economics', 'Good')
        output = self.output().split('## Evidence and technical detail')[0]
        assessed, gaps = output.split('### Research gaps', 1)
        self.assertIn('Adoption and maturity', assessed)
        self.assertIn('Token economics', assessed)
        self.assertIn('✅ **Good**', assessed)
        self.assertIn('⚪ **Unverified**', gaps)
        self.assertEqual(self.r['ratings'][0]['status'], 'unknown')

    def test_inferred_adverse_condition_remains_yellow(self):
        self.add_finding('possible seizure', 'token_and_liquidity', 'Potential Risk',
                         impact='adverse', inference=True)
        assessed, gaps = self.output().split('### Research gaps', 1)
        self.assertIn('🟡 **Potential Risk — Inference**', assessed)
        self.assertIn('possible seizure', assessed)
        self.assertNotIn('possible seizure', gaps.split('## Evidence and technical detail')[0])

    def test_unverified_cannot_hide_observed_or_inferred_adverse_findings(self):
        for inference in (False, True):
            with self.subTest(inference=inference):
                original = copy.deepcopy(self.r)
                self.add_finding('seizure', 'token_and_liquidity', 'Unverified',
                                 impact='adverse', inference=inference)
                with self.assertRaisesRegex(Invalid, 'Unverified requires a pure coverage gap'):
                    self.output()
                self.r = original

    def test_popularity_cannot_replace_critical_disclosure(self):
        self.add_finding('large adoption', 'adoption_and_maturity', 'Good')
        self.add_finding('withdrawal authority', 'token_and_liquidity', 'Bad', impact='adverse')
        self.r['summary'].pop()
        with self.assertRaisesRegex(Invalid, 'summary omits'):
            self.output()
        self.r['summary'].append({'finding_id': 'withdrawal authority',
                                  'topic': 'token_and_liquidity', 'signal': 'Bad'})
        assessed = self.output().split('### Research gaps')[0]
        self.assertIn('🔴 **Bad**', assessed)
        self.assertIn('withdrawal authority', assessed)

    def test_unknown_evidence_is_not_enough_for_neutral_if_adverse(self):
        self.r['findings'][0].update(claim_type='state_observation', impact='adverse',
                                      adverse_severity='high')
        with self.assertRaisesRegex(Invalid, 'Unverified requires a pure coverage gap'):
            self.output()

    def test_gap_with_adverse_impact_stays_assessed_in_compatible_input(self):
        # Compatibility must not neutralize an older mixed/poorly classified finding.
        self.r['summary'][0]['signal'] = 'Potential Risk'
        self.r['findings'][0].update(impact='adverse', adverse_severity='high')
        output = self.output().split('## Evidence and technical detail')[0]
        self.assertIn('🟡 **Potential Risk — Unknown**', output)
        self.assertNotIn('### Research gaps', output)

    def test_resolved_positive_cannot_be_reclassified_as_unverified(self):
        self.add_finding('measured use', 'adoption_and_maturity', 'Unverified')
        with self.assertRaisesRegex(Invalid, 'Unverified requires a pure coverage gap'):
            self.output()

    def test_legacy_rejects_new_signal_and_topics_before_rendering(self):
        from fixtures import build
        for topic, signal in [('token_and_liquidity', 'Unverified'),
                              ('adoption_and_maturity', 'Potential Risk'),
                              ('token_economics', 'Potential Risk')]:
            with self.subTest(topic=topic, signal=signal):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    m, r = build(root)
                    r['summary'] = [{'finding_id': r['findings'][0]['id'],
                                     'topic': topic, 'signal': signal}]
                    bind(root, m, r)
                    with self.assertRaisesRegex(Invalid, 'require the strict profile'):
                        validate(root, True)

    def test_gap_text_is_escaped_and_rendering_remains_bound(self):
        self.r['findings'][0]['proposition'] = 'SYNTHETIC: [click](https://example.invalid) | ![x](url)'
        output = self.output()
        self.assertNotIn('[click](https://example.invalid)', output)
        path = self.root / 'report.md'
        path.write_text(output)
        validate(self.root, True, path, required_profile=CURRENT_PROFILE)
        path.write_text(output.replace('⚪ **Unverified**', '✅ **Good**'))
        with self.assertRaisesRegex(Invalid, 'rendered report differs'):
            validate(self.root, True, path, required_profile=CURRENT_PROFILE)

    def test_assembly_normalizes_older_gaps_and_freezes_without_editing_draft(self):
        from test_stopping_review import review_cutoff
        from bundle_assemble import intake, save_draft, freeze, read_draft
        draft = self.root / 'draft'
        d = intake(draft, self.r['target'], 'Synthetic assessment', 'All authority material', True)
        shutil.copytree(self.root / 'evidence', draft / 'evidence')
        d.update(evidence=self.m['evidence'], pins=self.m['chains'][0]['pins'],
                 chain_id_evidence=self.m['chains'][0]['chain_id_evidence'],
                 scope=self.m['scope'], findings=self.r['findings'], ratings=self.r['ratings'],
                 discoveries=self.m['discoveries'], coverage_records=review_cutoff(self.r['coverage_records']),
                 summary=[dict(self.r['summary'][0], signal='Potential Risk')])
        d["decision_review"] = cutoff_decision(d["coverage_records"])
        save_draft(draft, d)
        out = self.root / 'frozen'
        freeze(draft, out, True, checkpoint=True)
        _, report = validate(out, True, out / 'report.md', required_profile=CURRENT_PROFILE)
        self.assertEqual(report['summary'][0]['signal'], 'Unverified')
        self.assertEqual(read_draft(draft)['summary'][0]['signal'], 'Potential Risk')
        self.assertTrue(all(r['status'] == 'unknown' for r in report['ratings']))
        # No silent downgrade of invalid Good/Bad labels into a neutral gap.
        d['summary'][0]['signal'] = 'Bad'
        save_draft(draft, d)
        with self.assertRaisesRegex(Invalid, 'requires resolved evidence'):
            freeze(draft, self.root / 'invalid', True, checkpoint=True)


if __name__ == '__main__':
    unittest.main()
