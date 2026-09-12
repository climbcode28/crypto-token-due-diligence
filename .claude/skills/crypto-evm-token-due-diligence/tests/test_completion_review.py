"""Completion means finished scoped work, not a favorable token verdict."""
import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bundle_assemble import deliver, freeze, intake, save_draft
from decision_fixtures import cutoff_decision
from report_profile import validate_completion_review
from test_stopping_review import review_cutoff
from test_strict_profile import strict
from validate_bundle import Invalid, validate


class CompletionReviewTests(unittest.TestCase):
    def review(self, status='checked', disposition=None):
        row = {'dimension': 'token_controls', 'status': status,
               'evidence_ids': ['synthetic-attempt', 'synthetic-boundary']}
        if disposition:
            row['closure'] = {'attempts': [{'evidence_ids': ['synthetic-attempt']}],
                              'next_route': {'disposition': disposition, 'evidence_ids': ['synthetic-boundary']}}
        return {'completion_review_version': 1, 'completion_status': 'complete',
                'closure_review_version': 1, 'coverage_records': [row]}

    def test_soft_time_or_request_cutoff_cannot_complete_unfinished_work(self):
        for status in ('partial', 'unavailable'):
            for disposition in ('budget_exhausted', 'pending', 'out_of_scope'):
                with self.subTest(status=status, disposition=disposition):
                    with self.assertRaisesRegex(Invalid, 'unfinished work'):
                        validate_completion_review(self.review(status, disposition))

    def test_unattempted_surface_cannot_complete_even_with_fabricated_boundary(self):
        with self.assertRaisesRegex(Invalid, 'not investigated'):
            validate_completion_review(self.review('not_checked', 'unavailable'))

    def test_completed_work_can_retain_evidenced_external_uncertainty(self):
        for status, disposition in [('checked', None), ('not_applicable', None),
                                    ('partial', 'exhausted'), ('unavailable', 'unavailable'),
                                    ('partial', 'not_yet_observable')]:
            with self.subTest(status=status, disposition=disposition):
                validate_completion_review(self.review(status, disposition))

    def test_external_boundary_needs_attempts_and_support(self):
        for field in ('attempts', 'evidence_ids'):
            r = self.review('partial', 'unavailable')
            closure = r['coverage_records'][0]['closure']
            (closure if field == 'attempts' else closure['next_route'])[field] = []
            with self.assertRaisesRegex(Invalid, 'evidenced attempts'):
                validate_completion_review(r)

    def test_unavailable_boundary_cannot_borrow_another_surfaces_evidence(self):
        for disposition in ('exhausted', 'unavailable', 'not_yet_observable'):
            r = self.review('partial', disposition)
            r['coverage_records'][0]['closure']['next_route']['evidence_ids'] = ['unrelated-surface']
            with self.assertRaisesRegex(Invalid, 'belong to this surface'):
                validate_completion_review(r)

    def test_markers_are_strict_but_older_reports_still_read(self):
        validate_completion_review({'coverage_records': []})
        for key, value in [('completion_review_version', True), ('completion_status', 'partial'),
                           ('closure_review_version', None)]:
            r = self.review(); r[key] = value
            with self.assertRaises(Invalid):
                validate_completion_review(r)
        r = self.review(); del r['completion_review_version']
        with self.assertRaisesRegex(Invalid, 'version marker'):
            validate_completion_review(r)

    def test_default_freeze_rejects_cutoff_but_checkpoint_preserves_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            m, r = strict(root)
            draft = root / 'draft'
            d = intake(draft, r['target'], 'Synthetic interrupted diligence', 'All authority material', True)
            shutil.copytree(root / 'evidence', draft / 'evidence')
            coverage = review_cutoff(copy.deepcopy(r['coverage_records']))
            d.update(evidence=m['evidence'], pins=m['chains'][0]['pins'],
                     chain_id_evidence=m['chains'][0]['chain_id_evidence'], scope=m['scope'],
                     discoveries=m['discoveries'], findings=r['findings'], ratings=r['ratings'],
                     coverage_records=coverage, summary=r['summary'], decision_review=cutoff_decision(coverage))
            save_draft(draft, d)
            original = (draft / 'draft.json').read_bytes()
            with self.assertRaisesRegex(Invalid, 'not investigated'):
                freeze(draft, root / 'final', True)
            self.assertFalse((root / 'final').exists())
            freeze(draft, root / 'checkpoint', True, checkpoint=True)
            _, frozen = validate(root / 'checkpoint', True, root / 'checkpoint/report.md')
            self.assertEqual(frozen['completion_status'], 'checkpoint')
            self.assertIn('Research checkpoint — required work remains unfinished.',
                          (root / 'checkpoint/report.md').read_text())
            self.assertNotIn('Review completed within', (root / 'checkpoint/report.md').read_text())
            self.assertEqual(original, (draft / 'draft.json').read_bytes())
            with self.assertRaisesRegex(Invalid, 'not eligible for final delivery'):
                deliver(root / 'checkpoint', True)
            saved = {str(p.relative_to(root / 'checkpoint')): p.read_bytes()
                     for p in (root / 'checkpoint').rglob('*') if p.is_file()}
            cli = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/bundle_assemble.py'),
                                  'deliver', str(root / 'checkpoint'), '--allow-synthetic'], capture_output=True, text=True)
            self.assertEqual(cli.returncode, 2)
            self.assertIn('not eligible for final delivery', cli.stderr)
            self.assertEqual(saved, {str(p.relative_to(root / 'checkpoint')): p.read_bytes()
                                    for p in (root / 'checkpoint').rglob('*') if p.is_file()})
            empty_lane = root / 'empty-lane.json'
            empty_lane.write_text('{}')
            mutation = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/bundle_assemble.py'),
                                       'handoff', str(root / 'checkpoint'), str(empty_lane)], capture_output=True, text=True)
            self.assertEqual(mutation.returncode, 2)
            self.assertEqual(saved, {str(p.relative_to(root / 'checkpoint')): p.read_bytes()
                                    for p in (root / 'checkpoint').rglob('*') if p.is_file()})

            # A synthetic resolved-state fixture exercises final rendering. These
            # declarations test structure, not real completeness on eleven surfaces.
            f = d['findings'][0]
            f.update(claim_type='state_observation', impact='neutral', adverse_severity='none',
                     evidence_type='proven_fact', confidence='high')
            f['support'][0]['role'] = 'direct'
            for c in d['coverage_records']:
                c.update(status='checked', evidence_ids=['e-code'])
                del c['closure']
            for rating in d['ratings']:
                rating.update(status='pass', coverage='complete', severity='none',
                              confidence='high', likelihood='observed')
            d['summary'][0]['signal'] = 'Good'
            d['decision_review']['verdict']['kind'] = 'findings_with_limits'
            d['decision_review']['actions'] = []
            d['report_text'] = {'verdict': 'SYNTHETIC resolved-state fixture; no real token assessment.'}
            save_draft(draft, d)
            freeze(draft, root / 'final', True)
            _, completed = validate(root / 'final', True, root / 'final/report.md')
            self.assertEqual(completed['completion_status'], 'complete')
            self.assertIn('Review completed within the documented evidence limits.',
                          (root / 'final/report.md').read_text())
            self.assertNotIn('Complete the named next checks', (root / 'final/report.md').read_text())
            self.assertNotIn('Decision-useful next steps', (root / 'final/report.md').read_text())
            self.assertEqual(completed['decision_review_version'], 2)
            self.assertEqual(deliver(root / 'final', True)['status'], 'ready_for_final_delivery')

    def test_delivery_markers_cannot_turn_a_checkpoint_into_a_final(self):
        r = self.review()
        r.update(completion_review_version=2, completion_status='checkpoint', delivery_status='final_report')
        with self.assertRaisesRegex(Invalid, 'contradicts research completion'):
            validate_completion_review(r)
        r.update(completion_status='complete', delivery_status='internal_checkpoint')
        with self.assertRaises(Invalid):
            validate_completion_review(r)
        r.update(completion_review_version=1, delivery_status='final_report')
        with self.assertRaisesRegex(Invalid, 'version 2'):
            validate_completion_review(r)


if __name__ == '__main__':
    unittest.main()
