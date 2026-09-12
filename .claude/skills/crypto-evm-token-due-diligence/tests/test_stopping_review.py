"""A documented cutoff must not masquerade as exhausted or completed research."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from fixtures import bind
from test_strict_profile import strict
from decision_fixtures import cutoff_decision
from validate_bundle import Invalid, sha, validate
from render_report import render


def review_cutoff(coverage):
    """Synthetic-only interruption: do not invent surface requests for a fixture."""
    for c in coverage:
        c['stop_reason'] = 'SYNTHETIC request budget ended before inspecting ' + c['surface']
        c['closure'] = {
            'priority': 'decision_critical' if c['dimension'] == 'token_controls' else 'material',
            'decision_impact': 'SYNTHETIC: unresolved ' + c['surface'] + ' limits the stated conclusion',
            'attempts': [],
            'next_route': {'check': c['next_check'], 'disposition': 'budget_exhausted',
                           'basis': 'SYNTHETIC fixture cutoff; this route was not attempted',
                           'evidence_ids': []}}
    return coverage


class StoppingReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.m, self.r = strict(self.root)
        self.r['closure_review_version'] = 1
        review_cutoff(self.r['coverage_records'])

    def check(self):
        bind(self.root, self.m, self.r)
        return validate(self.root, True)

    def output(self):
        m, r = self.check()
        return render(m, r, sha((self.root / 'report.json').read_bytes()))

    def test_older_strict_report_does_not_claim_retrospective_review(self):
        del self.r['closure_review_version']
        for c in self.r['coverage_records']:
            del c['closure']
        output = self.output()
        self.assertNotIn('## Stopping review', output)

    def test_every_incomplete_surface_needs_review(self):
        del self.r['coverage_records'][-1]['closure']
        with self.assertRaisesRegex(Invalid, 'stopping review missing'):
            self.check()

    def test_review_cannot_lose_its_version_or_use_boolean_version(self):
        del self.r['closure_review_version']
        with self.assertRaisesRegex(Invalid, 'requires its version marker'):
            self.check()
        self.r['closure_review_version'] = True
        with self.assertRaisesRegex(Invalid, 'unsupported stopping review version'):
            self.check()

    def test_completed_surface_cannot_hide_an_unresolved_gap(self):
        c = self.r['coverage_records'][0]
        c.update(status='checked', evidence_ids=['e-code'])
        self.r['ratings'][0]['coverage'] = 'complete'
        del c['closure']
        with self.assertRaisesRegex(Invalid, 'closed coverage cannot retain an unresolved finding'):
            self.check()
        self.r['findings'][0]['claim_type'] = 'state_observation'
        with self.assertRaisesRegex(Invalid, 'closed coverage cannot retain an unresolved finding'):
            self.check()

    def test_resolving_a_surface_removes_its_old_stopping_review(self):
        c = self.r['coverage_records'][0]
        c.update(status='checked', evidence_ids=['e-code'], finding_ids=['resolved-state'])
        self.r['ratings'][0].update(coverage='complete', finding_ids=['resolved-state'])
        f = copy.deepcopy(self.r['findings'][0])
        f.update(id='resolved-state', claim_type='state_observation', evidence_type='proven_fact',
                 confidence='high', impact='neutral', adverse_severity='none')
        f['support'][0]['role'] = 'direct'
        self.r['findings'].append(f)
        with self.assertRaisesRegex(Invalid, 'remove its stale stopping review'):
            self.check()
        del c['closure']
        self.check()

    def test_optional_scope_exclusion_does_not_become_a_pass(self):
        c = self.r['coverage_records'][-1]
        c['closure']['priority'] = 'context'
        c['closure']['next_route']['disposition'] = 'out_of_scope'
        self.check()
        self.assertEqual(c['status'], 'not_checked')
        self.assertEqual(self.r['ratings'][-1]['status'], 'unknown')

    def test_pending_next_route_prevents_freezing(self):
        self.r['coverage_records'][0]['closure']['next_route']['disposition'] = 'pending'
        with self.assertRaisesRegex(Invalid, 'next route remains pending'):
            self.check()

    def test_intake_placeholder_is_not_a_stopping_reason(self):
        self.r['coverage_records'][0]['stop_reason'] = 'Intake only'
        with self.assertRaisesRegex(Invalid, 'intake placeholder'):
            self.check()

    def test_exhaustion_requires_captured_attempts(self):
        route = self.r['coverage_records'][0]['closure']['next_route']
        route.update(disposition='exhausted', evidence_ids=['e-code'])
        with self.assertRaisesRegex(Invalid, 'exhausted route requires'):
            self.check()

    def test_not_checked_cannot_claim_attempts(self):
        c = self.r['coverage_records'][0]
        c['closure']['attempts'] = [{'check': 'SYNTHETIC runtime inspection',
                                   'outcome': 'Runtime alone leaves authority unresolved',
                                   'evidence_ids': ['e-code']}]
        with self.assertRaisesRegex(Invalid, 'not_checked cannot claim surface attempts'):
            self.check()

    def make_attempted(self):
        c = self.r['coverage_records'][0]
        c.update(status='partial', evidence_ids=['e-code'])
        self.r['ratings'][0]['coverage'] = 'partial'
        c['closure']['attempts'] = [{'check': 'SYNTHETIC runtime inspection',
                                   'outcome': 'Runtime alone leaves authority unresolved',
                                   'evidence_ids': ['e-code']}]
        c['closure']['next_route'].update(disposition='exhausted', evidence_ids=['e-code'],
            basis='SYNTHETIC supplied artifact is the only permitted route in this offline exercise')
        return c

    def test_attempted_route_references_captured_coverage(self):
        c = self.make_attempted()
        self.check()
        c['closure']['attempts'][0]['evidence_ids'] = ['nonexistent-attempt']
        with self.assertRaisesRegex(Invalid, 'unknown|reference'):
            self.check()

    def test_exhausted_route_cannot_borrow_an_unattempted_reference(self):
        c = self.make_attempted()
        c['closure']['next_route']['evidence_ids'] = ['e-header']
        with self.assertRaisesRegex(Invalid, 'exhausted route evidence must belong to attempts'):
            self.check()

    def test_attempts_cannot_borrow_other_surface_evidence(self):
        c = self.make_attempted()
        c['closure']['attempts'][0]['evidence_ids'] = ['e-header']
        with self.assertRaisesRegex(Invalid, 'attempt references must belong to surface coverage'):
            self.check()

    def test_stopping_review_is_not_silently_accepted_by_legacy(self):
        from fixtures import build
        self.m, self.r = build(self.root)
        self.r['closure_review_version'] = 1
        with self.assertRaisesRegex(Invalid, 'stopping review requires the strict profile'):
            self.check()

    def test_critical_gap_cannot_be_dismissed_as_scope(self):
        self.r['coverage_records'][0]['closure']['next_route']['disposition'] = 'out_of_scope'
        with self.assertRaisesRegex(Invalid, 'decision-critical gap cannot be out of scope'):
            self.check()

    def test_future_or_unavailable_evidence_needs_a_basis_capture(self):
        route = self.r['coverage_records'][0]['closure']['next_route']
        for disposition in ('unavailable', 'not_yet_observable'):
            with self.subTest(disposition=disposition):
                route['disposition'] = disposition
                with self.assertRaisesRegex(Invalid, 'missing evidence/references'):
                    self.check()

    def test_stopping_details_and_unselected_critical_gap_are_visible_and_escaped(self):
        c = self.r['coverage_records'][-1]
        c['surface'] = 'Delivered work and disclosures'
        c['next_check'] = 'Reconcile the deployed revision with its source'
        c['closure']['priority'] = 'decision_critical'
        c['closure']['decision_impact'] = 'SYNTHETIC: [claim](https://example.invalid) | limit'
        output = self.output()
        reading, details = output.split('## Evidence and technical detail')
        self.assertIn('2 decision-critical coverage gaps', reading)
        self.assertIn('## Stopping review', details)
        self.assertIn(c['surface'], details)
        self.assertIn('No surface verification attempted', details)
        self.assertNotIn('[claim](https://example.invalid)', details)
        self.assertIn(c['next_check'], details)
        path = self.root / 'report.md'
        path.write_text(output)
        validate(self.root, True, path)
        path.write_text(output.replace('2 decision-critical coverage gaps', '0 decision-critical coverage gaps'))
        with self.assertRaisesRegex(Invalid, 'rendered report differs'):
            validate(self.root, True, path)

    def test_final_freeze_requires_review_and_checkpoint_preserves_handoff(self):
        from bundle_assemble import intake, save_draft, freeze, handoff, read_draft
        from backend_common import write_new
        draft = self.root / 'draft'
        d = intake(draft, self.r['target'], 'Synthetic stopping test', 'Authority material', True)
        shutil.copytree(self.root / 'evidence', draft / 'evidence')
        coverage = copy.deepcopy(self.r['coverage_records'])
        for c in coverage:
            del c['closure']
        d.update(evidence=self.m['evidence'], pins=self.m['chains'][0]['pins'],
                 chain_id_evidence=self.m['chains'][0]['chain_id_evidence'],
                 scope=self.m['scope'], discoveries=self.m['discoveries'],
                 findings=self.r['findings'], ratings=self.r['ratings'],
                 coverage_records=coverage, summary=self.r['summary'])
        save_draft(draft, d)
        out = self.root / 'frozen'
        with self.assertRaisesRegex(Invalid, 'stopping review missing'):
            freeze(draft, out, True)
        self.assertFalse(out.exists())
        lane = self.root / 'lane.json'
        write_new(lane, {'coverage_records': self.r['coverage_records'],
                         'decision_review': cutoff_decision(self.r['coverage_records'])})
        handoff(draft, lane)
        before = (draft / 'draft.json').read_bytes()
        freeze(draft, out, True, checkpoint=True)
        _, report = validate(out, True, out / 'report.md')
        self.assertEqual(report['closure_review_version'], 1)
        self.assertEqual(report['coverage_records'], read_draft(draft)['coverage_records'])
        self.assertEqual((draft / 'draft.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
