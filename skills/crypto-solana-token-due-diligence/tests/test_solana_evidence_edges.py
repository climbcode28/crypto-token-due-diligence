from pathlib import Path
import sys,tempfile,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_fixture import Bundle,BASE,utc,key
from solana_profile import validate,ProfileError
from solana_transactions import decode_transaction,verify_sales
from transaction_fixture import fixture as transaction_fixture


class EvidenceEdgeTests(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);return Bundle(tmp.name)

    def execution(self,b):
        target,a,p,block=transaction_fixture();p['response']['result']['blockTime']=int(BASE+10)
        p['started_at']=BASE+15;p['completed_at']=BASE+15.5;p['request']['id']='receipt';p['response']['id']='receipt'
        b.rpc('receipt','getTransaction',p['request']['params'],p['response']['result'],15)
        result=decode_transaction(b.target,p,b.obj('block100'))
        b.derived('execution','transaction',{'transaction':'receipt','block':'block100'},['receipt','block100'],result)
        return a,result

    def test_supported_effect_and_sale_recompute(self):
        b=self.fixture();a,ex=self.execution(b)
        f=b.finding('sale-transfer','sellability_exit_depth','historical_execution')
        f.update(support=[{'evidence_id':'execution','subject':b.sub,'role':'execution','effect_id':'receipt-ix-0-inner-0'}],time_basis={'kind':'historical_execution','sample_ids':[]})
        b.r['findings'].append(f);sales=verify_sales(b.target,[{'pool':a['pool'],'execution':ex}])
        b.derived('sale','sales',{'candidates':[{'pool':a['pool'],'execution':'execution'}]},['execution'],sales)
        f=b.finding('sale-verified','sellability_exit_depth','inference');f.update(assertion='verified_sale',support=[{'evidence_id':'sale','subject':b.sub,'role':'derivation'}],time_basis={'kind':'historical_execution','sample_ids':[]})
        b.r['findings'].append(f);b.save();validate(b.root,True)
        b.r['findings'][-1]['assertion']='net_proceeds';b.save()
        with self.assertRaisesRegex(ProfileError,'net proceeds'):validate(b.root,True)

    def test_wrong_or_failed_effect_cannot_support_execution(self):
        for case in ('effect_id','subject','failed','alter_amount'):
            b=self.fixture();a,ex=self.execution(b)
            f=b.finding('execution-claim','sellability_exit_depth','historical_execution')
            f.update(support=[{'evidence_id':'execution','subject':b.sub,'role':'execution','effect_id':'receipt-ix-0-inner-0'}],time_basis={'kind':'historical_execution','sample_ids':[]})
            if case=='effect_id':f['support'][0]['effect_id']='unsupported-effect'
            if case=='subject':f['subject']={**b.sub,'address':key(88)};f['support'][0]['subject']=f['subject']
            if case=='failed':
                packet=b.obj('receipt');packet['response']['result']['meta']['err']={'failed':True};b.replace('receipt',packet)
                d=b.m['derivations'][-1];d['inputs'][0]['sha256']=b.obs('receipt')['sha256'];out=decode_transaction(b.target,packet,b.obj('block100'));b.replace('execution',out);d['output']=out
            if case=='alter_amount':
                out=b.obj('execution');out['effects'][1]['amount_atomic']='2';b.replace('execution',out);b.m['derivations'][-1]['output']=out
            b.r['findings'].append(f);b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_publication_can_stand_alone_but_cannot_prove_runtime(self):
        b=self.fixture();b.document('published',status='ok',body=b'Our documentation describes a reward mechanism.')
        f=b.finding('published-claim','reward_accounting_liveness','source_analysis');f.update(subject=b.docsub,
            support=[{'evidence_id':'published','subject':b.docsub,'role':'publication'}],time_basis={'kind':'publication','sample_ids':[]})
        b.r['findings'].append(f);b.save();validate(b.root,True)
        for case in ('state','execution','capability'):
            altered=copy.deepcopy(f)
            if case=='state':altered['claim']='state_observation';altered['support'][0]['role']='state'
            if case=='execution':altered['claim']='historical_execution'
            if case=='capability':altered['assertion']='executable_capability'
            b.r['findings'][-1]=altered;b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_wrong_account_subject_and_missing_time_context_rejected(self):
        for case in ('subject','time','null'):
            b=self.fixture();f=b.r['findings'][0]
            if case=='subject':f['subject']={**b.sub,'address':key(3)};f['support'][0]['subject']=f['subject']
            if case=='time':f['time_basis']['sample_ids']=[]
            if case=='null':
                f['support']=[{'evidence_id':'mint','subject':b.sub,'role':'state'}]
                p=b.obj('mint');p['response']['result']['value']=None;b.replace('mint',p)
            b.save()
            with self.assertRaises(ProfileError,msg=case):validate(b.root,True)

    def test_legacy_input_cannot_be_relabelled_v2(self):
        from solana_bundle import validate as dispatch
        root=Path(__file__).parent/'fixtures/legacy_v1/independent'
        with self.assertRaises(ProfileError):dispatch(root,True,profile='solana-evidence-v2')
        dispatch(root,True,profile='legacy-v1')


if __name__=='__main__':unittest.main()
