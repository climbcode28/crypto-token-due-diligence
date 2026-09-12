"""Small v2 report scenarios with real synthetic wire packets and explicit judgments."""
from datetime import datetime,timezone
from pathlib import Path
import json,copy
from solana_common import sha
from solana_profile import PROFILE,DIMENSIONS,AXES
from solana_accounts import controls
from pool_fixture import mint,key
from solana_fixture import request,response
from solana_presets import settings
from solana_discovery import MAINNET
import solana_derivations as derivations

BASE=datetime(2026,9,11,12,tzinfo=timezone.utc).timestamp()
def utc(t):return datetime.fromtimestamp(t,timezone.utc).isoformat()
def dump(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


class Bundle:
    def __init__(self,root,*,completed=False,all_gaps=False,adverse=False):
        self.root=Path(root);self.root.mkdir(exist_ok=True);self.target={'family':'solana','genesis_hash':MAINNET,'mint':key(2)}
        self.sub={'genesis_hash':MAINNET,'kind':'mint','address':key(2)};self.docsub={**self.sub,'kind':'document'}
        intake={'investigation_id':'fixture','target':self.target,'question':'Assess this token and whether I can sell $1,000.','focus':['exit depth'],'urls':['https://example.com/token'],
            'scope':'broad','received_at':utc(BASE),'target_at':utc(BASE+420),'deadline_at':utc(BASE+600),'user_hard_deadline':False}
        self.m={'schema_version':2,'profile':PROFILE,'investigation_id':'fixture','target':self.target,'synthetic':True,'intake':intake,
            'artifacts':[],'observations':[],'samples':[],'derivations':[],'attempts':[],'lanes':[],'network_checks':None,'header_checks':[]}
        self.r={'schema_version':2,'profile':PROFILE,'investigation_id':'fixture','target':self.target,'synthetic':True,'scope':'broad','question':intake['question'],'focus':intake['focus'],
            'manifest_sha256':'','research_status':'completed' if completed else 'partial','delivery_status':'draft','findings':[],
            'ratings':dict.fromkeys(DIMENSIONS,'unknown'),'coverage':[],'summary_ids':[],'decision':None,'limitations':['Bounded synthetic scenario; no token-safety conclusion.']}
        if not all_gaps:
            self.rpc('genesis','getGenesisHash',[],MAINNET,1)
            value=mint(1000000,key(60) if adverse else None)
            self.rpc('mint','getAccountInfo',[key(2),settings()],{'context':{'slot':100},'value':value},10)
            self.rpc('mint-fresh','getAccountInfo',[key(2),settings(100)],{'context':{'slot':101},'value':value},20)
            for ident,slot,t in [('block100',100,12),('block101',101,22),('reblock100',100,30),('reblock101',101,32)]:
                self.rpc(ident,'getBlock',[slot,{'commitment':'finalized','transactionDetails':'none','rewards':False}],{'blockhash':key(slot),'previousBlockhash':key(slot-1),'parentSlot':slot-1,'blockTime':int(BASE+10)},t)
            self.rpc('regenesis','getGenesisHash',[],MAINNET,40)
            self.m['network_checks']={'initial_evidence_id':'genesis','recheck_evidence_id':'regenesis'}
            for ident,slot in [('mint',100),('mint-fresh',101)]:
                self.obs(ident)['sample_id']='sample-'+ident
                self.m['samples'].append({'id':'sample-'+ident,'observation_id':ident,'addresses':[key(2)],'address_indices':{key(2):0},'encoding':'base64','commitment':'finalized',
                    'context_slot':slot,'captured_at':self.obs(ident)['captured_at'],'block_evidence_id':'block'+str(slot),'block_recheck_evidence_id':'reblock'+str(slot),
                    'critical':ident=='mint','recheck_of':'sample-mint' if ident=='mint-fresh' else None,'status':'pinned'})
            result=controls(self.obj('mint'),self.target)
            self.derived('controls','controls',{'mint':'mint'},['mint'],result)
            f=self.finding('controls-finding','token_controls','state_observation')
            f.update(signal='potential_risk' if adverse else 'good' if completed else None,impact='high' if adverse else 'informational',
                support=[{'evidence_id':'controls','subject':self.sub,'role':'derivation'}],time_basis={'kind':'sampled_state','sample_ids':['sample-mint'],'stability':'required'})
            if adverse:f.update(text='The retained mint authority can issue additional units.',concern={'basis':'The mint records an authority.','mechanism':'That authority can issue supply.','consequence':'Additional supply may dilute holders.'})
            self.r['findings'].append(f);self.r['summary_ids']=['controls-finding']
            if adverse:self.r['ratings']['token_controls']='concern'
            elif completed:self.r['ratings']['token_controls']='no_issue_detected'
        for dim in DIMENSIONS:
            if dim=='token_controls' and not all_gaps:
                self.r['coverage'].append({'dimension':dim,'status':'checked','finding_ids':['controls-finding'],'attempt_ids':[],
                    'decision_impact':'Observed mint controls are relevant to technical exposure.','pending_work':[],
                    'closure':{'reason':'Mint configuration directly sampled.','attempt_ids':[],'next_route':None,'boundary':'resolved','standard_scope_complete':True}})
            elif completed:
                self.gap(dim)
            else:
                self.r['coverage'].append({'dimension':dim,'status':'not_checked','finding_ids':[],'attempt_ids':[],
                    'decision_impact':'Unjudged.','pending_work':['Standard research remains.'],
                    'closure':{'reason':'Pending','attempt_ids':[],'next_route':'standard','boundary':'pending','standard_scope_complete':False}})
        if completed:
            for owner in ('liquidity','project'):
                path='notes/'+owner+'.json';self.artifact(path,{'owner':owner,'investigation_id':'fixture','question':intake['question'],'target':self.target})
                self.m['lanes'].append({'owner':owner,'status':'local_completed','self_check':True,'note_artifact':path,'evidence_ids':[self.m['observations'][-1]['id']]})
            ids=[f['id'] for f in self.r['findings']]
            self.r['decision']={'verdict_kind':'insufficient_evidence' if all_gaps else 'adverse' if adverse else 'conditional','text':'Evidence supports only the stated bounded observations.',
                'requirements':[{'quote':'whether I can sell $1,000','status':'unverified','text':'Exit cost remains unverified.','finding_ids':[f for f in ids if 'sellability' in f]}],
                'axes':{axis:{'text':'Observed facts and remaining limits are considered separately.','finding_ids':ids,'coverage_dimensions':list(DIMENSIONS)} for axis in AXES},
                'finding_ids':ids,'counterevidence_ids':[],'mitigations':([{'finding_id':'controls-finding','status':'unmitigated','text':'Retained mint authority remains material.','evidence_ids':[]}] if adverse else []),'actions':[]}
        self.save()

    def artifact(self,path,value,*,raw=False):
        data=value if raw else dump(value);file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
        self.m['artifacts']=[a for a in self.m['artifacts'] if a['path']!=path]+[{'path':path,'sha256':sha(data),'bytes':len(data)}]
        return data

    def obs(self,eid):return next(e for e in self.m['observations'] if e['id']==eid)
    def obj(self,eid):return json.loads((self.root/self.obs(eid)['artifact']).read_bytes())
    def rpc(self,eid,method,params,result,t):
        req=request(method,params,eid);packet={'request':req,'response':response(req,result),'status':'ok','started_at':BASE+t,'completed_at':BASE+t+0.5}
        raw=self.artifact('evidence/'+eid+'.json',packet)
        self.m['observations'].append({'id':eid,'kind':'rpc','status':'ok','subject':copy.deepcopy(self.sub),'artifact':'evidence/'+eid+'.json','sha256':sha(raw),
            'captured_at':utc(BASE+t+0.5),'synthetic':True,'source':{'namespace':'public-synthetic'},'request_id':eid,'sample_id':None})
        return packet

    def replace(self,eid,obj):
        e=self.obs(eid);raw=self.artifact(e['artifact'],obj);e['sha256']=sha(raw)

    def derived(self,eid,operation,parameters,inputs,result,sub=None):
        sub=sub or self.sub;raw=self.artifact('evidence/'+eid+'.json',result)
        self.m['observations'].append({'id':eid,'kind':'derived','status':'ok','subject':copy.deepcopy(sub),'artifact':'evidence/'+eid+'.json','sha256':sha(raw),
            'captured_at':utc(BASE+42),'synthetic':True,'source':{'operation':operation},'sample_id':None})
        closure=set(inputs)
        for x in inputs:
            for d in self.m['derivations']:
                if d['id']==x:closure.update(d['transitive_inputs'])
        self.m['derivations'].append({'id':eid,'operation':operation,'version':derivations.VERSION,'parameters':parameters,'subject':copy.deepcopy(sub),
            'inputs':[{'id':x,'sha256':self.obs(x)['sha256']} for x in inputs],'transitive_inputs':sorted(closure),'units':'exact atomic units and typed configuration','output':result})

    def finding(self,fid,dim,claim):
        return {'id':fid,'owner':'coordinator','dimension':dim,'claim':claim,'strength':'direct','confidence':'high','impact':'informational','signal':None,
            'subject':copy.deepcopy(self.sub),'participants':[],'text':'Mint configuration was observed at its stated context.','support':[],'counterevidence':[],
            'time_basis':{'kind':'sampled_state','sample_ids':[],'stability':'not_asserted'},'limitations':['Scope remains bounded.'],'concern':None}

    def document(self,eid,*,status='http_403',body=b'Access unavailable'):
        raw=self.artifact('evidence/'+eid+'.txt',body,raw=True)
        record={'id':eid,'url':'https://'+eid+'.example.com/','final_url':'https://'+eid+'.example.com/','status':status,'http_status':200 if status=='ok' else 403,
            'captured_at':BASE+50,'bytes':len(raw),'sha256':sha(raw)}
        self.m['observations'].append({'id':eid,'kind':'document','status':'ok' if status=='ok' else 'permission_denied','subject':copy.deepcopy(self.docsub),
            'artifact':'evidence/'+eid+'.txt','sha256':sha(raw),'captured_at':utc(BASE+50),'synthetic':True,'source':{'capture':record},'sample_id':None})

    def gap(self,dim):
        aids=[];support=[]
        for route in ('primary','alternate'):
            eid=dim+'-'+route;self.document(eid);aid='attempt-'+eid;aids.append(aid)
            self.m['attempts'].append({'id':aid,'evidence_id':eid,'dimension':dim,'owner':'coordinator','status':'permission_denied','route':route,'source':eid+'.example.com'})
            support.append({'evidence_id':eid,'subject':self.docsub,'role':'attempt'})
        fid='gap-'+dim;f=self.finding(fid,dim,'coverage_gap');f.update(signal='unverified',strength='unresolved',confidence='low',text='Both bounded public routes returned access denials.',
            support=support,participants=[copy.deepcopy(self.docsub)],time_basis={'kind':'attempt','sample_ids':[]})
        self.r['findings'].append(f)
        self.r['coverage'].append({'dimension':dim,'status':'unavailable','finding_ids':[fid],'attempt_ids':aids,'decision_impact':'Unverified evidence limits this assessment.','pending_work':[],
            'closure':{'reason':'Retained primary and alternate access denials.','attempt_ids':aids,'next_route':None,'boundary':'evidenced_external_limit','standard_scope_complete':True}})

    def save(self):
        if self.r['research_status']=='partial':
            for row in self.r['coverage']:row['finding_ids']=[f['id'] for f in self.r['findings'] if f['dimension']==row['dimension']]
        raw=dump(self.m);(self.root/'manifest.json').write_bytes(raw);self.r['manifest_sha256']=sha(raw);(self.root/'report.json').write_bytes(dump(self.r))
