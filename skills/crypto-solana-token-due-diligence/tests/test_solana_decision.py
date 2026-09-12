from pathlib import Path
import sys,tempfile,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from solana_profile import validate,ProfileError


class DecisionTests(unittest.TestCase):
    def fixture(self,**opts):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);return Bundle(tmp.name,completed=True,**opts)

    def test_all_gap_requires_insufficient_evidence_and_cannot_be_adverse(self):
        b=self.fixture(all_gaps=True);validate(b.root,True)
        b.r['decision']['verdict_kind']='favorable';b.save()
        with self.assertRaisesRegex(ProfileError,'insufficient'):validate(b.root,True)
        b.r['decision']['verdict_kind']='insufficient_evidence';b.r['findings'][0]['signal']='bad';b.save()
        with self.assertRaisesRegex(ProfileError,'pure unknown'):validate(b.root,True)

    def test_high_control_concern_survives_summary_axes_and_mitigation(self):
        for field in ('summary','decision','axis','mitigation'):
            b=self.fixture(adverse=True);validate(b.root,True);d=b.r['decision']
            if field=='summary':b.r['summary_ids']=[]
            if field=='decision':d['finding_ids'].remove('controls-finding')
            if field=='axis':d['axes']['technical_exposure']['finding_ids'].remove('controls-finding')
            if field=='mitigation':d['mitigations']=[]
            b.save()
            with self.assertRaisesRegex(ProfileError,'high/critical'):validate(b.root,True)

    def test_exact_requirement_and_four_axes_enforced(self):
        for case in ('quote','axis','met_gap','unjudged'):
            b=self.fixture();d=b.r['decision']
            if case=='quote':d['requirements'][0]['quote']='I hold a million tokens'
            if case=='axis':d['axes'].pop('token_economics')
            if case=='met_gap':d['requirements'][0]['status']='met'
            if case=='unjudged':b.r['findings'][0]['signal']=None
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_positive_activity_cannot_remove_observed_restriction(self):
        b=self.fixture(adverse=True);b.r['ratings']['token_controls']='no_issue_detected';b.save()
        with self.assertRaisesRegex(ProfileError,'concern'):validate(b.root,True)

    def test_actions_optional_and_deferred_standard_work_not_homework(self):
        b=self.fixture();self.assertEqual(b.r['decision']['actions'],[]);validate(b.root,True)
        b.r['decision']['actions']=[{'kind':'finish_standard_research','text':'Run the missing checks yourself.'}];b.save()
        with self.assertRaisesRegex(ProfileError,'homework'):validate(b.root,True)


if __name__=='__main__':unittest.main()
