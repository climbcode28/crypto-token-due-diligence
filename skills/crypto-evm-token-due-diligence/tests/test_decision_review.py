"""Decisions must distinguish adverse evidence, missing research and user requirements."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from fixtures import bind
from decision_fixtures import cutoff_decision
from test_strict_profile import strict
from test_stopping_review import review_cutoff
from validate_bundle import Invalid, sha, validate
from render_report import render


class DecisionReviewTests(unittest.TestCase):
    def test_v2_empty_actions_do_not_invent_followup_work(self):
        self.r['decision_review_version'] = 2
        self.review['actions'] = []
        reading = self.output().split('## Evidence and technical detail')[0]
        self.assertIn('### Assessment', reading)
        self.assertNotIn('Decision-useful next steps', reading)
        self.assertIn('Unverified', reading)

    def test_v2_complete_report_rejects_research_homework(self):
        from report_profile import validate_decision_review
        self.r.update(decision_review_version=2, completion_status='complete')
        findings = {f['id']: f for f in self.r['findings']}
        ratings = {r['id']: r for r in self.r['ratings']}
        with self.assertRaisesRegex(Invalid, 'cannot delegate research'):
            validate_decision_review(self.r, findings, ratings)
        self.r['completion_status'] = 'checkpoint'
        validate_decision_review(self.r, findings, ratings)

    def test_v2_empty_actions_cannot_hide_severe_concern(self):
        self.r['decision_review_version'] = 2
        self.add('seizure', adverse=True, severity='critical')
        self.adverse_decision('seizure')
        self.review['actions'] = []
        with self.assertRaisesRegex(Invalid, 'actions omit'):
            self.check()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.m, self.r = strict(self.root)
        self.r['closure_review_version'] = 1
        review_cutoff(self.r['coverage_records'])
        self.r['decision_review_version'] = 1
        self.r['decision_review'] = cutoff_decision(self.r['coverage_records'])
        self.review = self.r['decision_review']

    def check(self):
        bind(self.root, self.m, self.r)
        return validate(self.root, True)

    def output(self):
        m, r = self.check()
        return render(m, r, sha((self.root / 'report.json').read_bytes()))

    def add(self, fid, adverse=False, severity='medium', inference=False):
        f = copy.deepcopy(self.r['findings'][0])
        f.update(id=fid, proposition='SYNTHETIC: ' + fid,
                 claim_type='inference' if inference else 'state_observation',
                 evidence_type='inference' if inference else 'strongly_supported',
                 confidence='low' if inference else 'medium', impact='adverse' if adverse else 'benefit',
                 adverse_severity=severity if adverse else 'none')
        f['support'][0]['role'] = 'direct'
        if adverse:
            f['concern'] = {'basis': 'adverse_inference' if inference else 'reachable_capability',
                            'mechanism': 'SYNTHETIC owner can rewrite holder balances.',
                            'consequence': 'SYNTHETIC holder assets can be seized.', 'requirement_ids': []}
        self.r['findings'].append(f)
        c, rating = self.r['coverage_records'][0], self.r['ratings'][0]
        # Existing fixture shares a list across ratings; use replacement intentionally.
        c['finding_ids'] = list(c['finding_ids']) + [fid]
        rating['finding_ids'] = list(rating['finding_ids']) + [fid]
        if adverse:
            c.update(status='partial', evidence_ids=['e-code'])
            c['closure']['attempts'] = [{'check': 'SYNTHETIC code inspection',
                'outcome': 'Authority found', 'evidence_ids': ['e-code']}]
            rating.update(status='concern', coverage='partial', severity=severity,
                          likelihood='possible', confidence=f['confidence'])
        self.r['summary'].append({'finding_id': fid, 'topic': 'token_and_liquidity',
                                 'signal': 'Potential Risk' if adverse else 'Good'})
        return f

    def adverse_decision(self, fid):
        self.review['verdict'].update(kind='adverse_findings', finding_ids=[fid])
        self.review['synthesis'][0]['finding_ids'].append(fid)
        self.review['actions'] = [{'id': 'mitigate', 'kind': 'mitigate',
            'action': 'Avoid exposure to the demonstrated seizure path.', 'reason': 'Owner capability is established.',
            'finding_ids': [fid], 'coverage_dimensions': ['token_controls'], 'requirement_ids': [],
            'changes_view_if': 'Removal of the authority with matching runtime and state would change this finding.'}]

    def test_only_gaps_are_inconclusive_not_an_adverse_token_verdict(self):
        reading = self.output().split('## Evidence and technical detail')[0]
        self.assertIn('Insufficient evidence for an overall assessment', reading)
        self.assertNotIn('A favorable conclusion still depends', reading)
        self.assertIn('Resolve uncertainty', reading)
        self.assertTrue(all(x['status'] == 'unknown' for x in self.r['ratings']))

    def test_gap_cannot_support_adverse_verdict_or_mitigation(self):
        self.review['verdict']['kind'] = 'adverse_findings'
        with self.assertRaisesRegex(Invalid, 'adverse verdict requires'):
            self.check()
        self.review['verdict']['kind'] = 'insufficient_evidence'
        self.review['actions'][0]['kind'] = 'mitigate'
        with self.assertRaisesRegex(Invalid, 'mitigation requires'):
            self.check()

    def test_gap_cannot_support_favorable_scope(self):
        self.review['verdict']['kind'] = 'findings_with_limits'
        with self.assertRaisesRegex(Invalid, 'affirmative evidence'):
            self.check()

    def test_default_broad_question_has_no_requirement_gate(self):
        self.review['verdict']['kind'] = 'requirement_unverified'
        with self.assertRaisesRegex(Invalid, 'verdict requirements'):
            self.check()
        self.review['verdict']['kind'] = 'insufficient_evidence'
        self.review['actions'][0]['kind'] = 'requirement_gate'
        with self.assertRaisesRegex(Invalid, 'action requirements'):
            self.check()

    def test_explicit_requirement_is_unverified_without_alleging_failure(self):
        self.review['requirements'] = [{'id': 'custody', 'text': 'Liquidity principal must be immutable.',
                                       'user_quote': 'I require an irreversible liquidity lock.'}]
        self.review['verdict'].update(kind='requirement_unverified', requirement_ids=['custody'])
        self.review['actions'][0].update(kind='requirement_gate', requirement_ids=['custody'])
        reading = self.output().split('## Evidence and technical detail')[0]
        self.assertIn('User requirement not established', reading)
        self.assertIn('I require an irreversible liquidity lock.', reading)
        self.assertNotIn('Evidence-backed concerns', reading)

    def test_user_requirement_needs_source_words(self):
        self.review['requirements'] = [{'id': 'exit', 'text': 'An analyst chose a $50000 exit size.', 'user_quote': ''}]
        with self.assertRaisesRegex(Invalid, 'user requirement user_quote'):
            self.check()

    def test_positive_controls_and_unchecked_custody_have_bounded_positive_synthesis(self):
        self.add('bounded-controls')
        self.review['verdict'].update(kind='findings_with_limits', finding_ids=['bounded-controls'])
        self.review['synthesis'][0]['finding_ids'].append('bounded-controls')
        reading = self.output().split('## Evidence and technical detail')[0]
        self.assertIn('Supported findings with stated limits', reading)
        self.assertIn('bounded-controls', reading)
        self.assertIn('### Assessment', reading)
        self.assertIn('### Decision-useful next steps', reading)
        self.assertEqual(self.r['ratings'][1]['status'], 'unknown')

    def test_famous_team_cannot_hide_seizure_or_its_mitigation(self):
        self.add('public-accountability')
        self.add('seizure', adverse=True, severity='critical')
        self.review['verdict'].update(kind='findings_with_limits', finding_ids=['public-accountability'])
        with self.assertRaisesRegex(Invalid, 'verdict omits'):
            self.check()
        self.review['verdict']['finding_ids'].append('seizure')
        with self.assertRaisesRegex(Invalid, 'require an adverse verdict'):
            self.check()
        self.adverse_decision('seizure')
        self.check()
        self.review['actions'] = cutoff_decision(self.r['coverage_records'])['actions']
        with self.assertRaisesRegex(Invalid, 'actions omit'):
            self.check()

    def test_inferred_adverse_finding_stays_inferred_and_visible(self):
        self.add('possible-removal', adverse=True, severity='high', inference=True)
        self.adverse_decision('possible-removal')
        self.review['actions'][0].update(
            action='Treat the hypothesized path as unresolved pending authority verification.',
            reason='The supplied observation supports a low-confidence adverse inference only.',
            changes_view_if='Matching authority and execution evidence could establish or refute the hypothesized path.')
        self.assertIn('Potential Risk — Inference', self.output())

    def test_operator_discretion_needs_a_specific_concern_not_a_default_penalty(self):
        f = self.add('redirect-fees', adverse=True)
        del f['concern']
        self.adverse_decision('redirect-fees')
        with self.assertRaisesRegex(Invalid, 'concern mechanism missing'):
            self.check()
        f['concern'] = {'basis': 'user_requirement', 'mechanism': 'Mutable routing',
                        'consequence': 'Does not satisfy an immutable-routing requirement.', 'requirement_ids': []}
        with self.assertRaisesRegex(Invalid, 'concern requirements'):
            self.check()
        f['concern'].update(basis='claim_mismatch', mechanism='SYNTHETIC promised immutable routing can be redirected.')
        self.check()

    def test_missing_research_cannot_be_relabeled_as_an_adverse_finding(self):
        f = self.add('missing-locker', adverse=True)
        f.update(evidence_type='unknown', confidence='unknown', claim_type='coverage_gap')
        self.r['ratings'][0]['confidence'] = 'unknown'
        self.adverse_decision('missing-locker')
        with self.assertRaisesRegex(Invalid, 'missing evidence cannot'):
            self.check()

    def test_inference_needs_an_observed_lead_and_cannot_be_promoted_by_its_basis(self):
        f = self.add('possible-power', adverse=True, inference=True)
        self.adverse_decision('possible-power')
        f['support'][0]['role'] = 'identity'
        with self.assertRaisesRegex(Invalid, 'observed subject-specific basis'):
            self.check()
        f['support'][0]['role'] = 'direct'
        f['concern']['basis'] = 'reachable_capability'
        with self.assertRaisesRegex(Invalid, 'evidence class and concern basis'):
            self.check()

    def test_actions_are_bounded_unique_and_source_linked(self):
        action = self.review['actions'][0]
        self.review['actions'] = [action, copy.deepcopy(action)]
        with self.assertRaisesRegex(Invalid, 'duplicate decision action'):
            self.check()
        self.review['actions'] = [copy.deepcopy(action) for _ in range(4)]
        with self.assertRaisesRegex(Invalid, 'one to three'):
            self.check()
        self.review['actions'] = [action]
        action['finding_ids'] = ['invented-finding']
        with self.assertRaisesRegex(Invalid, 'reference'):
            self.check()

    def test_completed_positive_review_does_not_require_inventing_more_research(self):
        self.add('resolved-control')
        c, rating = self.r['coverage_records'][0], self.r['ratings'][0]
        c.update(status='checked', finding_ids=['resolved-control'], evidence_ids=['e-code'])
        del c['closure']
        rating.update(status='pass', severity='none', likelihood='observed', confidence='medium',
                      coverage='complete', finding_ids=['resolved-control'])
        self.review = self.r['decision_review'] = cutoff_decision(self.r['coverage_records'])
        self.review['verdict'].update(kind='findings_with_limits', finding_ids=['resolved-control'])
        self.review['actions'][0].update(kind='use_within_scope', finding_ids=['resolved-control'],
                                         coverage_dimensions=['token_controls'])
        self.check()
        self.review['actions'][0]['coverage_dimensions'].append('canonical_lp_principal_custody')
        with self.assertRaisesRegex(Invalid, 'completed declared coverage'):
            self.check()

    def test_marker_and_all_axes_required_without_retroactive_claims(self):
        del self.r['decision_review_version']
        with self.assertRaisesRegex(Invalid, 'version marker'):
            self.check()
        del self.r['decision_review']
        self.check()
        self.r['decision_review_version'] = True
        with self.assertRaisesRegex(Invalid, 'unsupported decision review version'):
            self.check()
        self.r['decision_review_version'] = 1
        self.r['decision_review'] = self.review
        self.review['synthesis'].pop()
        with self.assertRaisesRegex(Invalid, 'four separate'):
            self.check()

    def test_scoped_use_cannot_cherry_pick_a_positive_in_a_concern_dimension(self):
        self.add('positive')
        self.add('medium-harm', adverse=True)
        c, rating = self.r['coverage_records'][0], self.r['ratings'][0]
        c.update(status='checked', finding_ids=['positive', 'medium-harm'])
        del c['closure']
        rating.update(coverage='complete', finding_ids=['positive', 'medium-harm'])
        self.review = self.r['decision_review'] = cutoff_decision(self.r['coverage_records'])
        self.review['verdict'].update(kind='findings_with_limits', finding_ids=['positive'])
        self.review['actions'][0].update(kind='use_within_scope', finding_ids=['positive'],
                                         coverage_dimensions=['token_controls'])
        with self.assertRaisesRegex(Invalid, 'concern in its declared scope'):
            self.check()

    def test_checkpoint_may_precede_explicit_review_and_replays_it(self):
        from bundle_assemble import intake, save_draft, handoff, freeze
        from report_replay import replay
        draft = self.root / 'draft'
        d = intake(draft, self.r['target'], 'Synthetic broad diligence', 'All authority material', True)
        shutil.copytree(self.root / 'evidence', draft / 'evidence')
        d.update(evidence=self.m['evidence'], pins=self.m['chains'][0]['pins'],
                 chain_id_evidence=self.m['chains'][0]['chain_id_evidence'], scope=self.m['scope'],
                 findings=self.r['findings'], ratings=self.r['ratings'], discoveries=self.m['discoveries'],
                 coverage_records=self.r['coverage_records'], summary=self.r['summary'])
        save_draft(draft, d)
        freeze(draft, self.root / 'unjudged', True, checkpoint=True)
        _, unjudged = validate(self.root / 'unjudged', True)
        self.assertNotIn('decision_review', unjudged)
        self.assertEqual(unjudged['delivery_status'], 'internal_checkpoint')
        d['decision_review'] = {}
        save_draft(draft, d)
        with self.assertRaisesRegex(Invalid, 'invalid decision review fields'):
            freeze(draft, self.root / 'malformed', True, checkpoint=True)
        import json
        lane = self.root / 'review.json'
        lane.write_text(json.dumps({'decision_review': self.review}))
        handoff(draft, lane)
        out = self.root / 'frozen'
        freeze(draft, out, True, checkpoint=True)
        self.assertEqual(replay(out, True, True)['status'], 'reproduced')
        _, r = validate(out, True, out / 'report.md')
        self.assertEqual(r['decision_review'], self.review)

    def test_rendered_decision_text_is_escaped_and_bound(self):
        self.review['actions'][0]['action'] = '[instruction](https://example.invalid) | **claim**'
        output = self.output()
        self.assertNotIn('[instruction](https://example.invalid)', output)
        path = self.root / 'report.md'
        path.write_text(output)
        validate(self.root, True, path)
        path.write_text(output.replace('Resolve uncertainty', 'Avoid token'))
        with self.assertRaisesRegex(Invalid, 'rendered report differs'):
            validate(self.root, True, path)


if __name__ == '__main__':
    unittest.main()
