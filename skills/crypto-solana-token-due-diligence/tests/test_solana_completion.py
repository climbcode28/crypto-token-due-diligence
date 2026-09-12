from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle
from solana_profile import validate,ProfileError


class CompletionTests(unittest.TestCase):
    def fixture(self,**opts):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);return Bundle(tmp.name,**opts)

    def test_completed_unknowns_pass_and_untouched_pending_or_budget_do_not(self):
        for case in ('untouched','pending','budget','implementation','fallback'):
            b=self.fixture(completed=True);row=b.r['coverage'][1]
            if case=='untouched':row['status']='not_checked'
            if case=='pending':row['pending_work']=['Inspect actual source.']
            if case=='budget':row['closure']['boundary']='budget'
            if case=='implementation':row['closure']['boundary']='implementation_gap'
            if case=='fallback':row['closure']['next_route']='available public alternate'
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_missing_lane_and_uninventoried_note_do_not_complete(self):
        for case in ('missing','failed','note','question'):
            b=self.fixture(completed=True)
            if case=='missing':b.m['lanes'].pop()
            if case=='failed':b.m['lanes'][0]['status']='failed'
            if case=='note':b.m['artifacts']=[x for x in b.m['artifacts'] if x['path']!='notes/liquidity.json']
            if case=='question':b.artifact('notes/liquidity.json',{'owner':'liquidity','question':'Shortened question','investigation_id':'fixture','target':b.target})
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_unjudged_checkpoint_is_valid_but_not_final_delivery(self):
        b=self.fixture();b.r['delivery_status']='checkpoint';b.save();validate(b.root,True)
        b.r['delivery_status']='delivered';b.save()
        with self.assertRaisesRegex(ProfileError,'completed broad'):validate(b.root,True)
        b=self.fixture(completed=True);b.r['scope']=b.m['intake']['scope']='focused';b.r['delivery_status']='frozen';b.save()
        with self.assertRaisesRegex(ProfileError,'completed broad'):validate(b.root,True)

    def test_external_limit_requires_real_alternate_and_failed_capture(self):
        for case in ('source','alternate','no_gap','false_status','primary_ok'):
            b=self.fixture(completed=True);row=b.r['coverage'][1]
            if case=='source':b.m['attempts'][1]['source']=b.m['attempts'][0]['source']
            if case=='primary_ok':  # A successful primary is not an access limitation: every cited closure attempt must have failed.
                a=b.m['attempts'][0];a['status']='ok';e=b.obs(a['evidence_id']);e['status']='ok';e['source']['capture']['status']='ok';e['source']['capture']['http_status']=200
            if case=='alternate':row['closure']['attempt_ids']=row['closure']['attempt_ids'][:1]
            if case=='no_gap':row['finding_ids']=[]
            if case=='false_status':
                e=b.obs(b.m['attempts'][0]['evidence_id']);e['source']['capture']['status']='ok';e['source']['capture']['http_status']=200
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_na_and_checked_need_affirmative_evidence(self):
        for status in ('checked','not_applicable'):
            b=self.fixture(completed=True);b.r['coverage'][1]['status']=status;b.save()
            with self.assertRaisesRegex(ProfileError,'affirmative'):validate(b.root,True)


if __name__=='__main__':unittest.main()
