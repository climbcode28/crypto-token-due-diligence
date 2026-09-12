"""Strict v2 evidence relationships. Validation is not a financial truth oracle."""
from datetime import datetime,timezone
import json,math,re,stat
from pathlib import Path
from solana_common import need,sha,target_identity,pubkey,natural
from solana_session import label,encoded
from solana_transport import unique_object,invalid_constant
from solana_wire import validate_request,validate_response,consistency,STATE
from solana_web_capture import clean_url
import solana_derivations as derivations

PROFILE='solana-evidence-v2'
VERSION='2.0.0'
DIMENSIONS=('token_controls','canonical_lp_principal_custody','side_pool_removal_risk','sellability_exit_depth','current_concentration','historical_launch_integrity',
    'admin_treasury_reward_custody','reward_accounting_liveness','utility_redemption_rights','external_dependencies','development_disclosure')
AXES=('technical_exposure','credibility_maturity','token_economics','research_confidence')
SUBJECTS={'mint','holding','program','controller','pool','position','wallet','document'}
STATUSES={'ok','null','rpc_error','transport_failure','invalid','redacted','unsupported','stale','timeout','permission_denied','budget_denied','method_unavailable','node_lag'}
EXTERNAL_FAILURES={'null','rpc_error','transport_failure','stale','timeout','permission_denied','method_unavailable','node_lag'}


class ProfileError(ValueError):
    def __init__(self,path,message):
        self.errors=[{'path':path,'message':message}]
        super().__init__(path+': '+message)


def check(condition,path,message):
    if not condition:raise ProfileError(path,message)


def text(value,path,*,judged=False):
    check(isinstance(value,str) and bool(value.strip()) and len(value)<=20000,path,'nonempty bounded text required')
    if judged:check(not re.search(r'\bTODO\b|\bTBD\b',value,re.I),path,'unresolved placeholder')
    return value


def sequence(value,path,cap=500):
    check(isinstance(value,list) and len(value)<=cap,path,'bounded list required');return value


def utc(value,path):
    try:
        check(isinstance(value,str),path,'ISO UTC time required');d=datetime.fromisoformat(value.replace('Z','+00:00'))
        check(d.tzinfo is not None and d.utcoffset().total_seconds()==0,path,'UTC timezone required');return d.timestamp()
    except (ValueError,TypeError,OverflowError):raise ProfileError(path,'invalid UTC timestamp') from None


def strict_json(raw,path):
    def finite(value):
        number=float(value);check(math.isfinite(number),path,'non-finite JSON number');return number
    try:return json.loads(raw,object_pairs_hook=unique_object,parse_constant=invalid_constant,parse_float=finite)
    except (ValueError,TypeError,UnicodeError):raise ProfileError(path,'invalid strict UTF-8 JSON') from None


def regular(root,name):
    check(isinstance(name,str) and '\\' not in name and not name.startswith('/') and all(v not in ('','..','.') for v in name.split('/')),name or 'artifact','unsafe relative path')
    candidate=root
    for part in name.split('/'):
        candidate=candidate/part
        check(not candidate.is_symlink(),name,'symlink artifact forbidden')
    check(candidate.is_file() and stat.S_ISREG(candidate.stat().st_mode),name,'regular artifact missing')
    check(candidate.stat().st_size<=64*1024*1024,name,'artifact exceeds byte bound')
    return candidate


def subject(value,target,path):
    check(isinstance(value,dict) and set(value)=={'genesis_hash','kind','address'},path,'exact typed subject required')
    check(value['genesis_hash']==target['genesis_hash'],path+'.genesis_hash','cross-genesis support forbidden')
    pubkey(value['address']);check(value['kind'] in SUBJECTS,path+'.kind','unknown subject kind')
    if value['kind']=='document':check(value['address']==target['mint'],path,'document subject must be exact target mint')
    return value


def index(rows,path):
    result={}
    for i,row in enumerate(sequence(rows,path)):
        at=path+'['+str(i)+']';check(isinstance(row,dict),at,'object required');ident=label(row['id'])
        check(ident not in result,at+'.id','duplicate identifier');result[ident]=row
    return result


def refs(values,known,path,*,nonempty=False):
    sequence(values,path);check(len(values)==len(set(values)),path,'duplicate references')
    check(all(isinstance(v,str) and v in known for v in values),path,'unknown reference')
    if nonempty:check(bool(values),path,'at least one reference required')
    return values


def block_time(packet):
    """Comparable header value: a full header's blockTime or a block-time read."""
    result=packet['response']['result'];return result['blockTime'] if packet['request']['method']=='getBlock' else result


def normalized_status(value):
    status=value.get('status')
    if status in STATUSES:return status
    if status in ('http_401','http_403'):return 'permission_denied'
    if status=='http_404':return 'null'
    if isinstance(status,str) and status.startswith('http_'):return 'transport_failure'
    if status in ('not_sent_deadline','deadline_exceeded','budget_denied'):return 'budget_denied'
    return 'invalid'


class Evidence:
    def __init__(self,root,manifest,allow_synthetic):
        self.root=root;self.m=manifest;self.target=target_identity(manifest['target']);self.objects={};self.raw={};self.checked={};self.pinned=set();self.usable=set();self.categories={};self.closure={};self.effects={};self.stable=set()
        # Retained evidence that cannot support resolved facts, with the reason; never a hard failure.
        self.degraded={};self.unpinned=set();self.stability_changes={}
        check(manifest['schema_version']==2 and type(manifest['schema_version']) is int and manifest['profile']==PROFILE,'manifest.profile','explicit v2 schema/profile required')
        label(manifest['investigation_id']);check(type(manifest['synthetic']) is bool,'manifest.synthetic','boolean required')
        check(not manifest['synthetic'] or allow_synthetic,'manifest.synthetic','synthetic bundle requires explicit opt-in')
        self.intake=manifest['intake'];self._intake()
        self.inventory={}
        total_bytes=0
        for i,item in enumerate(sequence(manifest['artifacts'],'manifest.artifacts')):
            path=item['path'];check(path not in self.inventory,'manifest.artifacts','duplicate artifact path')
            file=regular(root,path);total_bytes+=file.stat().st_size
            check(total_bytes<=128*1024*1024,'manifest.artifacts','total artifact byte bound exceeded')
            data=file.read_bytes();check(sha(data)==item['sha256'] and len(data)==item['bytes'],'manifest.artifacts['+str(i)+']','artifact digest/size mismatch')
            check(type(item['bytes']) is int,'manifest.artifacts['+str(i)+'].bytes','integer byte count required')
            self.inventory[path]=item;self.raw[path]=data
        self.rows=index(manifest['observations'],'manifest.observations');self.samples=index(manifest['samples'],'manifest.samples')
        self.derivations=index(manifest['derivations'],'manifest.derivations')
        self.attempts=index(manifest['attempts'],'manifest.attempts')
        self._observations();self._samples();self._derive();self._attempts()

    def _intake(self):
        p='manifest.intake';i=self.intake
        check(i['target']==self.target and i['investigation_id']==self.m['investigation_id'],p,'intake identity changed')
        text(i['question'],p+'.question');sequence(i['focus'],p+'.focus');sequence(i['urls'],p+'.urls')
        for url in i['urls']:
            check(isinstance(url,(str,dict)),p+'.urls','original URL entry must remain text/object')
        check(i['scope'] in ('broad','focused'),p+'.scope','invalid scope');check(type(i['user_hard_deadline']) is bool,p,'invalid hard deadline flag')
        received=utc(i['received_at'],p+'.received_at');target=utc(i['target_at'],p+'.target_at');end=utc(i['deadline_at'],p+'.deadline_at')
        check(received<=target<=end and received<end,p,'unordered original absolute timing')

    def _observations(self):
        packets=[];request_ids=set()
        for eid,e in self.rows.items():
            p='manifest.observations.'+eid;subject(e['subject'],self.target,p+'.subject')
            check(type(e['synthetic']) is bool and e['synthetic']==self.m['synthetic'],p+'.synthetic','observation mode mismatch')
            check(e['kind'] in ('rpc','document','derived') and e['status'] in STATUSES,p,'unknown evidence kind/status')
            utc(e['captured_at'],p+'.captured_at');path=e['artifact']
            check(path in self.inventory and self.inventory[path]['sha256']==e['sha256'],p+'.artifact','evidence not hash-bound to inventory')
            raw=self.raw[path];self.categories[eid]='publication' if e['kind']=='document' else 'state'
            if e['kind']=='document':
                record=e['source']['capture'];check(record['id']==eid,p+'.source','capture identifier mismatch')
                check(record['bytes']==len(raw) and record['sha256']==sha(raw),p,'capture bytes changed')
                clean_url(record['url']);clean_url(record['final_url'])
                check(abs(record['captured_at']-utc(e['captured_at'],p))<0.001,p,'document capture time differs')
                if e['status']=='ok':check(record['status']=='ok' and record['http_status']==200,p,'unsuccessful document promoted')
                check(e['status']==normalized_status(record),p+'.status','document status differs from retained capture')
                self.objects[eid]={'record':record,'raw':raw}
                if e['status']=='ok':self.usable.add(eid)
                continue
            value=strict_json(raw,p+'.artifact');self.objects[eid]=value
            if e['kind']=='derived':continue
            req=value['request'];validate_request(req)
            check(req['id']==e['request_id'] and req['id'] not in request_ids,p+'.request_id','RPC identifier mismatch/reuse');request_ids.add(req['id'])
            text(e['source']['namespace'],p+'.source.namespace')
            method=req['method']
            if method in ('getAccountInfo','getMultipleAccounts'):
                requested=req['params'][0] if method=='getMultipleAccounts' else [req['params'][0]]
                check(e['subject']['address'] in requested,p+'.subject','RPC subject not requested')
            elif method in ('getTokenSupply','getTokenLargestAccounts','getSignaturesForAddress','getTokenAccountsByOwner','getProgramAccounts'):
                expected=[req['params'][0]]
                if method=='getProgramAccounts':
                    # A holder scan filters one program by mint prefix; its subject is that mint.
                    filters=req['params'][1].get('filters') if isinstance(req['params'][1],dict) else None
                    if isinstance(filters,list) and len(filters)==2 and isinstance(filters[1].get('memcmp'),dict) and filters[1]['memcmp'].get('offset')==0:expected.append(filters[1]['memcmp'].get('bytes'))
                check(e['subject']['address'] in expected,p+'.subject','RPC subject differs from requested address')
            check(type(value.get('started_at')) in (int,float) and type(value.get('completed_at')) in (int,float),p,'actual request timing required')
            check(math.isfinite(value['started_at']) and math.isfinite(value['completed_at']) and value['started_at']<=value['completed_at'],p,'invalid request timing')
            check(abs(value['completed_at']-utc(e['captured_at'],p))<0.001,p,'RPC capture time differs')
            if value.get('status')=='ok':
                c=validate_response(req,value['response']);self.checked[eid]=c;packets.append(value)
                check(e['status']==c['status'] or e['status'] in ('invalid','stale','unsupported'),p+'.status','RPC observation status contradicts raw response')
            else:
                check(e['status']==normalized_status(value),p+'.status','failed request status altered')
                if isinstance(value.get('response'),dict):
                    try:
                        c=validate_response(req,value['response'])
                        if c['status']=='ok':packets.append({**value,'status':'ok'})
                    except (ValueError,KeyError,TypeError):pass
        consistency(packets,self.target)

    def independent(self,a,b,path):
        check(a in self.rows and b in self.rows and a!=b,path,'two distinct observations required')
        ea,eb=self.rows[a],self.rows[b];va,vb=self.objects[a],self.objects[b]
        check(ea['kind']==eb['kind']=='rpc' and ea['artifact']!=eb['artifact'],path,'independent RPC artifacts required')
        check(ea['status']==eb['status']=='ok',path,'unsuccessful observation cannot serve as recheck')
        check(ea['request_id']!=eb['request_id'] and va['started_at']<=va['completed_at']<vb['started_at']<=vb['completed_at'],path,'recheck must be a later distinct request')
        check(ea['source']['namespace']==eb['source']['namespace'],path,'recheck provider namespace differs')
        check(self.checked.get(a,{}).get('status')==self.checked.get(b,{}).get('status')=='ok',path,'successful rechecks required')
        return va,vb

    def _samples(self):
        network=self.m.get('network_checks');network_ok=False
        if network:
            a,b=network['initial_evidence_id'],network['recheck_evidence_id'];first,last=self.independent(a,b,'manifest.network_checks')
            check(first['request']['method']==last['request']['method']=='getGenesisHash','manifest.network_checks','genesis checks required')
            check(first['response']['result']==last['response']['result']==self.target['genesis_hash'],'manifest.network_checks','genesis identity mismatch')
            network_ok=True;self.usable.update((a,b))
            for eid,c in self.checked.items():
                packet=self.objects[eid]
                if c['status']=='ok' and self.rows[eid]['status']=='ok' and packet['request']['method']=='getSignaturesForAddress':
                    if self.rows[eid]['source']['namespace']==self.rows[a]['source']['namespace'] and first['completed_at']<=packet['started_at'] and last['started_at']>=packet['completed_at']:self.usable.add(eid)
                    else:self.degraded[eid]='history outside verified network interval'  # retained, never usable
        for pair in sequence(self.m.get('header_checks',[]),'manifest.header_checks'):
            x,y=pair['initial_evidence_id'],pair['recheck_evidence_id'];v,w=self.independent(x,y,'manifest.header_checks')
            check(v['request']['method']=='getBlock' and w['request']['method'] in ('getBlock','getBlockTime') and v['request']['params'][0]==w['request']['params'][0],'manifest.header_checks','same-slot header pair required')
            if block_time(v)!=block_time(w):self.degraded[y]='historical header changed';continue
            if network_ok and self.rows[x]['source']['namespace']==self.rows[a]['source']['namespace']:self.usable.update((x,y))
        by_observation={}
        for sid,s in self.samples.items():
            p='manifest.samples.'+sid;eid=s['observation_id'];check(eid in self.rows and eid not in by_observation,p,'unknown/reused sample observation');by_observation[eid]=s
            e=self.rows[eid];packet=self.objects[eid];c=self.checked.get(eid,{})
            check(e['kind']=='rpc' and c.get('status')=='ok' and 'context_slot' in c,p,'sample needs successful contextual RPC')
            check(e.get('sample_id')==sid and s['context_slot']==c['context_slot'],p,'sample/context binding mismatch')
            check(s['addresses']==c.get('addresses',[]) and s['address_indices']==c.get('address_indices',{}),p,'sample address mapping differs from raw response')
            check(s['captured_at']==e['captured_at'] and s['commitment']=='finalized',p,'sample commitment/time mismatch')
            check(s['encoding']==('base64' if packet['request']['method'] in ('getAccountInfo','getMultipleAccounts','getTokenAccountsByOwner','getProgramAccounts') else 'json'),p,'sample encoding mismatch')
            check(s['status'] in ('pinned','partial'),p,'invalid sample status');check(type(s['critical']) is bool,p+'.critical','critical boolean required')
            if s['status']=='partial':continue
            check(e['status']=='ok',p,'unusable observation cannot be pinned')
            check(network_ok,p,'verified network recheck pair required')
            h,r=s['block_evidence_id'],s['block_recheck_evidence_id'];hv,rv=self.independent(h,r,p+'.block_recheck')
            check(hv['request']['method']=='getBlock' and rv['request']['method'] in ('getBlock','getBlockTime') and hv['request']['params'][0]==rv['request']['params'][0]==s['context_slot'],p,'header slot mismatch')
            stamp=hv['response']['result']['blockTime']
            # These are boundary conditions, not identity contradictions: the sample stays retained
            # but unpinned, so a later failed network recheck cannot make the whole import raise.
            reason=('state outside verified provider/network interval' if not (e['source']['namespace']==self.rows[a]['source']['namespace'] and first['completed_at']<=packet['started_at'] and last['started_at']>=packet['completed_at'])
                else 'header changed' if block_time(hv)!=block_time(rv) else 'current sample stale or undated' if not (stamp is not None and -60<=packet['completed_at']-stamp<=300)
                else 'header provider mismatch' if self.rows[h]['source']['namespace']!=e['source']['namespace'] else None)
            if reason:self.unpinned.add(sid);self.degraded[eid]=reason;continue
            self.pinned.add(eid);self.usable.update((eid,h,r))
        for eid,c in self.checked.items():
            if c['status']=='ok' and 'context_slot' in c:check(eid in by_observation,'manifest.samples','contextual observation missing sample')
        for sid,s in self.samples.items():
            p='manifest.samples.'+sid
            if s.get('recheck_of'):
                other=self.samples.get(s['recheck_of']);check(other is not None and other['id']!=sid,p+'.recheck_of','unknown/self recheck')
                v,w=self.independent(other['observation_id'],s['observation_id'],p+'.recheck_of')
                check(s['context_slot']>=other['context_slot'] and set(other['addresses'])<=set(s['addresses']),p,'critical recheck address/context mismatch')
                stable,changes=self.stability(other['addresses'],v,w)
                if stable and sid not in self.unpinned:self.stable.add(other['observation_id'])
                if changes:self.stability_changes[other['observation_id']]=changes
        for sid,s in self.samples.items():
            p='manifest.samples.'+sid
            if s['critical'] and s['status']=='pinned' and sid not in self.unpinned and not s.get('recheck_of'):
                fresh=[r for r in self.samples.values() if r.get('recheck_of')==sid and r['status']=='pinned' and r['id'] not in self.unpinned]
                check(len(fresh)<=1,p,'one later critical account recheck required')
                if not fresh:
                    # The recheck was retained but degraded: the initial critical state is unpinned too.
                    eid=s['observation_id'];self.unpinned.add(sid);self.degraded[eid]='critical recheck unavailable';self.pinned.discard(eid);self.usable.discard(eid);self.stable.discard(eid)

    def stability(self,addresses,v,w):
        """Byte-stable accounts are stable; a mint whose only change is its supply is stable with changed_fields."""
        from solana_programs import observed_account
        from solana_accounts import decode_mint
        changes={}
        for address in addresses:
            a=observed_account(address,v)[0];b=observed_account(address,w)[0]
            if a==b:continue
            if a is None or b is None or {k:x for k,x in a.items() if k!='data'}!={k:x for k,x in b.items() if k!='data'}:return False,changes
            try:da,db=decode_mint(a),decode_mint(b)
            except (ValueError,KeyError,TypeError):return False,changes
            ignored={'supply_atomic','data_sha256'}
            if {k:x for k,x in da.items() if k not in ignored}!={k:x for k,x in db.items() if k not in ignored}:return False,changes
            changes[address]=['supply_atomic']
        return True,changes

    def _derive(self):
        check(set(self.derivations)=={eid for eid,e in self.rows.items() if e['kind']=='derived'},'manifest.derivations','derived observation/operation inventory differs')
        active=set();done=set()
        def visit(eid):
            if eid in done:return
            check(eid not in active,'manifest.derivations.'+eid,'cyclic derived inputs');active.add(eid)
            if eid not in self.derivations:self.closure[eid]=set();done.add(eid);active.remove(eid);return
            d=self.derivations[eid];p='manifest.derivations.'+eid;e=self.rows[eid]
            params=d['parameters'];operation=d['operation']
            try:compatible=derivations.recomputable(operation,d['version'])
            except ValueError:compatible='unsupported operation version'
            check(compatible=='ok',p+'.version',compatible);check(d['subject']==e['subject'],p+'.subject','derivation subject changed')
            expected_address=params.get('address',self.target['mint']) if operation in ('mint','program','source_assurance','history','prior_launches') else params['pool'] if operation=='pool' else params['owner'] if operation=='inventory' else self.target['mint']
            expected_kind='program' if operation in ('program','source_assurance') else 'pool' if operation=='pool' else 'wallet' if operation in ('inventory','prior_launches') else None if operation=='history' else 'mint'
            check(e['subject']['address']==expected_address and (expected_kind is None or e['subject']['kind']==expected_kind),p+'.subject','operation subject differs from bound parameters')
            text(d['units'],p+'.units');inputs=sequence(d['inputs'],p+'.inputs');names=[row['id'] for row in inputs]
            refs(names,self.rows,p+'.inputs',nonempty=True);closure=set(names)
            for row in inputs:
                check(row['sha256']==self.rows[row['id']]['sha256'],p+'.inputs','input digest changed');visit(row['id']);closure.update(self.closure[row['id']])
                check(utc(e['captured_at'],p)>=utc(self.rows[row['id']]['captured_at'],p),p+'.captured_at','derivation predates an input capture')
            check(set(d['transitive_inputs'])==closure and len(d['transitive_inputs'])==len(closure),p+'.transitive_inputs','incomplete transitive closure')
            used=set()
            def resolve(ident):
                check(ident in names,p+'.parameters','undeclared input used');used.add(ident);return self.objects[ident]
            output=derivations.compute(d['operation'],d['parameters'],self.target,resolve)
            check(used==set(names),p+'.inputs','unused/unbound input evidence')
            check(encoded(output)==encoded(self.objects[eid]) and encoded(d['output'])==encoded(output),p+'.output','output does not recompute from bound inputs')
            category='publication' if d['operation'] in derivations.PUBLICATION_OPS else 'execution' if d['operation'] in derivations.EXECUTION_OPS else 'state'
            self.categories[eid]=category;self.closure[eid]=closure
            if all(i in self.usable for i in names) and e['status']=='ok':self.usable.add(eid)
            if d['operation']=='transaction':
                tid=d['parameters']['transaction'];bid=d['parameters']['block'];tx=self.objects[tid]
                check(self.rows[tid]['kind']==self.rows[bid]['kind']=='rpc',p,'execution requires raw RPC')
                if output['block_evidence_id']:
                    check(self.rows[bid]['request_id']==output['block_evidence_id'],p,'historical block source mismatch')
                    check(self.rows[tid]['source']['namespace']==self.rows[bid]['source']['namespace'],p,'transaction/header provider mismatch')
                    network=self.m.get('network_checks')
                    if network and bid in self.usable and self.rows[tid]['status']==e['status']=='ok':
                        initial,final=network['initial_evidence_id'],network['recheck_evidence_id']
                        if self.rows[tid]['source']['namespace']==self.rows[initial]['source']['namespace'] and self.objects[initial]['completed_at']<=tx['started_at'] and self.objects[final]['started_at']>=tx['completed_at']:self.usable.add(tid);self.usable.add(eid)
                        else:self.degraded[tid]='execution outside verified provider/network interval';self.usable.discard(eid)
                for effect in output['effects']:
                    check(effect['id'] not in self.effects,p,'duplicate execution effect identifier');self.effects[effect['id']]=(eid,effect)
            active.remove(eid);done.add(eid)
        for eid in self.rows:visit(eid)

    def _attempts(self):
        for aid,a in self.attempts.items():
            p='manifest.attempts.'+aid;check(a['evidence_id'] in self.rows,p,'attempt evidence missing');e=self.rows[a['evidence_id']]
            check(e['kind'] in ('rpc','document'),p,'attempt must name retained original capture')
            check(a['status']==e['status'],p+'.status','attempt status mismatch')
            check(a['route'] in ('primary','alternate','follow_up'),p+'.route','invalid source route')
            text(a['source'],p+'.source');check(a['owner'] in ('pipeline','coordinator','liquidity','project'),p,'invalid attempt owner')
            from urllib.parse import urlsplit
            actual_source=urlsplit(e['source']['capture']['url']).hostname if e['kind']=='document' else e['source']['namespace']
            check(a['source']==actual_source,p+'.source','attempt source label differs from retained origin')
            check(a['dimension'] in DIMENSIONS,p+'.dimension','unknown attempt dimension')

    def support(self,row,finding,path):
        eid=row['evidence_id'];check(eid in self.rows,path,'unknown support evidence');e=self.rows[eid]
        sub=subject(row['subject'],self.target,path+'.subject');role=row['role']
        check(role in ('state','execution','publication','derivation','attempt','context'),path+'.role','invalid support role')
        allowed=[finding['subject'],*finding['participants']];check(sub in allowed,path+'.subject','support subject not declared by finding')
        if role in ('attempt','context'):
            check(sub==e['subject'],path+'.subject','attempt/context subject mismatch');return False
        check(eid in self.usable,path,'unusable evidence cannot support resolved fact')
        if role=='execution':
            effect_id=row.get('effect_id');check(effect_id in self.effects and self.effects[effect_id][0]==eid,path+'.effect_id','unsupported execution effect')
            effect=self.effects[effect_id][1]
            identities={effect.get('mint'),effect.get('pool'),*effect.get('mints',[]),*effect.get('participants',{}).values()}
            check(sub['address'] in identities,path+'.subject','effect does not involve exact support subject')
        elif role=='publication':check(self.categories[eid]=='publication' and sub==e['subject'],path,'publication support needs matching captured document/derived publication')
        elif role=='derivation':check(e['kind']=='derived' and e['subject']==sub,path,'derivation subject mismatch')
        else:
            check(self.categories[eid]=='state',path,'document/execution cannot be promoted to state')
            if e['kind']=='derived':check(e['subject']==sub,path,'derived state subject differs')
            else:
                check(eid in self.pinned and sub['address'] in self.checked[eid].get('addresses',[]),path,'state subject not in pinned raw account mapping')
                c=self.checked[eid];values=c['result']['value'];values=values if isinstance(values,list) else [values]
                check(values[c['address_indices'][sub['address']]] is not None,path,'null account cannot support present state')
                value=values[c['address_indices'][sub['address']]]
                if sub['kind']=='mint':
                    from solana_accounts import decode_mint
                    decode_mint(value)
                elif sub['kind']=='holding':
                    from solana_accounts import decode_holding
                    decode_holding(value)
                elif sub['kind']=='program':check(value['executable'] is True,path,'program subject must be executable')
                elif sub['kind'] in ('pool','position','controller'):
                    check(False,path,'protocol/controller state needs its tested typed derivation')
        return sub==finding['subject']


def findings(evidence,report,judged):
    known=index(report['findings'],'report.findings')
    for fid,f in known.items():
        p='report.findings.'+fid
        check(f['owner'] in ('pipeline','coordinator','liquidity','project'),p+'.owner','unknown finding owner')
        check(f['dimension'] in DIMENSIONS,p+'.dimension','unknown dimension')
        subject(f['subject'],evidence.target,p+'.subject')
        for sub in sequence(f['participants'],p+'.participants',100):subject(sub,evidence.target,p+'.participants')
        check(f['claim'] in ('state_observation','source_analysis','historical_execution','inference','coverage_gap'),p+'.claim','invalid claim class')
        check(f['strength'] in ('direct','corroborated','bounded','unresolved') and f['confidence'] in ('high','medium','low'),p,'invalid strength/confidence')
        check(f['impact'] in ('critical','high','medium','low','informational'),p+'.impact','invalid impact')
        check(f['signal'] in ('good','potential_risk','bad','unverified',None),p+'.signal','invalid signal')
        check(f.get('assertion') in (None,'observation','published_claim','observed_effect','verified_sale','net_proceeds','source_correspondence','executable_capability'),p+'.assertion','unsupported assertion type')
        if judged:check(f['signal'] is not None,p+'.signal','final finding is unjudged')
        text(f['text'],p+'.text',judged=judged);sequence(f['limitations'],p+'.limitations')
        primary=False;roles=set()
        for i,row in enumerate(sequence(f['support'],p+'.support')):
            primary=evidence.support(row,f,p+'.support['+str(i)+']') or primary;roles.add(row['role'])
        for i,row in enumerate(sequence(f['counterevidence'],p+'.counterevidence')):evidence.support(row,f,p+'.counterevidence['+str(i)+']')
        if f['claim']=='coverage_gap':
            check(f['signal'] in (None,'unverified') and f['strength']=='unresolved' and not f.get('concern'),p,'pure unknown cannot become favorable/adverse allegation')
            check(bool(f['support']) and bool(roles & {'attempt','context','publication','derivation'}),p,'coverage gap needs retained attempt/context')
        else:
            check(primary,p+'.support','exact finding subject needs usable substantive support')
            if f['claim']=='state_observation':check(bool(roles & {'state','derivation'}) and all(evidence.categories[r['evidence_id']]=='state' for r in f['support'] if r['role'] in ('state','derivation')),p,'document-as-runtime/state promotion forbidden')
            if f['claim']=='historical_execution':check('execution' in roles,p,'historical claim needs exact supported execution effect')
            if f['claim']=='source_analysis':check(bool(roles & {'publication','derivation'}),p,'source analysis needs captured publication/assurance')
        c=f.get('concern')
        if c is not None:
            check(isinstance(c,dict) and set(c)=={'basis','mechanism','consequence'},p+'.concern','concern must be an object with basis, mechanism and consequence text')
            for k in ('basis','mechanism','consequence'):text(c.get(k),p+'.concern.'+k,judged=judged)
        if f['signal'] in ('bad','potential_risk'):
            check(isinstance(c,dict) and primary and f['claim']!='coverage_gap',p+'.concern','adverse concern needs observed evidence')
        time=f['time_basis'];check(isinstance(time,dict) and time['kind'] in ('sampled_state','historical_execution','publication','mixed','attempt'),p+'.time_basis','explicit time basis required')
        samples=refs(time.get('sample_ids',[]),evidence.samples,p+'.time_basis.sample_ids')
        required_samples=set()
        for row in f['support']:
            if row['role'] not in ('state','derivation'):continue
            for eid in {row['evidence_id'],*evidence.closure.get(row['evidence_id'],set())}:
                sid=evidence.rows[eid].get('sample_id')
                if sid:required_samples.add(sid)
        check(required_samples<=set(samples),p+'.time_basis.sample_ids','state context dependencies omitted from finding')
        if time.get('stability')=='required':
            check(bool(samples) and all(evidence.samples[s]['observation_id'] in evidence.stable for s in samples),p+'.time_basis','stability claim lacks unchanged critical recheck')
        if f.get('assertion') in ('verified_sale','net_proceeds'):
            selected=[evidence.objects[r['evidence_id']] for r in f['support'] if r['role']=='derivation' and evidence.derivations.get(r['evidence_id'],{}).get('operation')=='sales']
            sales=[r for obj in selected for r in obj['receipts'] if r['status']=='verified_sale']
            check(bool(sales),p+'.assertion','sale assertion lacks recomputed sale')
            if f['assertion']=='net_proceeds':check(any(r['native_proceeds'] is not None for r in sales),p+'.assertion','net proceeds unresolved')
        if f.get('assertion')=='executable_capability':
            ops={evidence.derivations[r['evidence_id']]['operation'] for r in f['support'] if r['role']=='derivation'}
            check({'controls','controllers','source_assurance'}<=ops,p+'.assertion','executable claim needs state, controller paths and source correspondence; publication alone insufficient')
            for row in f['support']:
                if row['role']!='derivation':continue
                operation=evidence.derivations[row['evidence_id']]['operation'];value=evidence.objects[row['evidence_id']]
                if operation=='controllers':check(not value.get('gaps') and all(n['status']=='observed' for n in value.get('nodes',[])),p+'.assertion','controller paths unresolved')
                if operation=='source_assurance':check(value['byte_correspondence'] in ('remote_hash_matches_captured_bytes','local_artifact_matches_captured_bytes'),p+'.assertion','source correspondence unresolved')
    return known


def coverage(evidence,report,known,completed):
    rows=sequence(report['coverage'],'report.coverage',11);ratings=report['ratings']
    check(isinstance(ratings,dict) and set(ratings)==set(DIMENSIONS),'report.ratings','exactly eleven independent ratings required')
    check(len(rows)==11 and {r['dimension'] for r in rows}==set(DIMENSIONS),'report.coverage','exactly eleven coverage rows required')
    for row in rows:
        dim=row['dimension'];p='report.coverage.'+dim;rating=ratings[dim]
        check(rating in ('unknown','concern','no_issue_detected','not_applicable'),p+'.rating','invalid rating')
        check(row['status'] in ('checked','partial','unavailable','not_checked','not_applicable'),p+'.status','invalid coverage')
        refs(row['finding_ids'],known,p+'.finding_ids');refs(row['attempt_ids'],evidence.attempts,p+'.attempt_ids')
        check(all(known[f]['dimension']==dim for f in row['finding_ids']),p,'finding assigned to wrong dimension')
        check(set(row['finding_ids'])=={fid for fid,f in known.items() if f['dimension']==dim},p+'.finding_ids','coverage omitted a finding or unresolved gap')
        check(all(evidence.attempts[a]['dimension']==dim for a in row['attempt_ids']),p,'attempt assigned to wrong dimension')
        text(row['decision_impact'],p+'.decision_impact',judged=completed);sequence(row['pending_work'],p+'.pending_work')
        associated=[known[f] for f in row['finding_ids']]
        affirmative=[f for f in associated if f['claim']!='coverage_gap' and f['strength']!='unresolved']
        gaps=[f for f in associated if f['claim']=='coverage_gap']
        if row['status'] in ('checked','not_applicable'):
            check(bool(affirmative) and not gaps and not row['pending_work'],p,'checked/N/A needs affirmative evidence and no unresolved gap')
        if rating=='no_issue_detected':check(row['status']=='checked' and bool(affirmative) and not any(f['signal'] in ('bad','potential_risk') for f in associated),p,'no-issue rating cannot hide observed concern')
        if rating=='concern':check(any(f['signal'] in ('bad','potential_risk') for f in associated),p,'concern rating lacks adverse evidence')
        if rating=='not_applicable':check(row['status']=='not_applicable',p,'N/A rating requires supported N/A coverage')
        c=row['closure'];check(isinstance(c,dict),p+'.closure','closure object required')
        check(c['boundary'] in ('resolved','evidenced_external_limit','pending','budget','implementation_gap'),p+'.closure.boundary','unknown closure boundary')
        refs(c['attempt_ids'],evidence.attempts,p+'.closure.attempt_ids');check(set(c['attempt_ids'])<=set(row['attempt_ids']),p,'closure attempt outside dimension')
        check(type(c['standard_scope_complete']) is bool,p,'closure flag must be boolean')
        if completed:
            check(row['status'] not in ('not_checked',) and not row['pending_work'] and c['standard_scope_complete'],p,'untouched/pending standard work cannot complete')
            text(c['reason'],p+'.closure.reason',judged=True)
            check(c['boundary'] in ('resolved','evidenced_external_limit'),p,'budget/implementation gap is not completed research')
            check(c['next_route'] is None,p,'feasible unattempted next route prevents completion')
            if c['boundary']=='resolved':check(bool(affirmative) and not gaps and row['status'] in ('checked','not_applicable'),p,'resolved closure needs affirmative completed coverage')
            else:
                attempts=[evidence.attempts[a] for a in c['attempt_ids']]
                check({'primary','alternate'}<={a['route'] for a in attempts} and len({a['source'] for a in attempts})>=2,p,'external boundary needs primary and feasible alternate attempts')
                check(any(a['status'] in EXTERNAL_FAILURES for a in attempts) and bool(gaps),p,'external boundary lacks captured access limitation/gap')
                check(not any(a['status'] in ('budget_denied','invalid','unsupported') for a in attempts),p,'local/unsupported/budget work cannot be relabeled external')
    return {r['dimension']:r for r in rows}


def decision(evidence,report,known,covered,completed):
    d=report['decision']
    if d is None:
        check(not completed,'report.decision','completed report requires analyst decision');return
    p='report.decision';check(d['verdict_kind'] in ('insufficient_evidence','conditional','favorable','adverse'),p+'.verdict_kind','invalid verdict')
    text(d['text'],p+'.text',judged=completed);refs(d['finding_ids'],known,p+'.finding_ids');refs(d['counterevidence_ids'],known,p+'.counterevidence_ids')
    if not any(f['claim']!='coverage_gap' and f['strength']!='unresolved' for f in known.values()):check(d['verdict_kind']=='insufficient_evidence',p,'all-gap evidence requires insufficient-evidence verdict')
    axes=d['axes'];check(isinstance(axes,dict) and set(axes)==set(AXES),p+'.axes','four distinct assessment axes required')
    for name,row in axes.items():
        at=p+'.axes.'+name;text(row['text'],at+'.text',judged=completed);refs(row['finding_ids'],known,at+'.finding_ids');refs(row['coverage_dimensions'],covered,at+'.coverage_dimensions')
        check(bool(row['finding_ids'] or row['coverage_dimensions']),at,'axis must reference evidence/coverage')
    reqs=sequence(d['requirements'],p+'.requirements',30)
    for i,row in enumerate(reqs):
        at=p+'.requirements['+str(i)+']';quote=text(row['quote'],at+'.quote')
        check(quote in report['question'],at+'.quote','requirement must quote original user words')
        check(row['status'] in ('met','not_met','unverified'),at+'.status','invalid requirement judgment')
        text(row['text'],at+'.text',judged=completed);refs(row['finding_ids'],known,at+'.finding_ids')
        if row['status']!='unverified':check(any(known[f]['claim']!='coverage_gap' for f in row['finding_ids']),at,'requirement judgment lacks affirmative evidence')
    if completed:check(bool(reqs),p+'.requirements','explicit original-request requirement review required')
    summary=refs(report['summary_ids'],known,'report.summary_ids');mitigations=sequence(d['mitigations'],p+'.mitigations')
    mids=[]
    for row in mitigations:
        fid=row['finding_id'];check(fid in known and fid not in mids,p+'.mitigations','unknown/duplicate mitigation finding');mids.append(fid)
        check(row['status'] in ('unmitigated','partial','mitigated'),p+'.mitigations','invalid mitigation status');text(row['text'],p+'.mitigations.text',judged=completed)
        refs(row['evidence_ids'],evidence.rows,p+'.mitigations.evidence_ids')
        if row['status']=='mitigated':check(bool(row['evidence_ids']) and all(e in evidence.usable for e in row['evidence_ids']),p+'.mitigations','mitigation needs usable evidence')
    for fid,f in known.items():
        if f['signal'] in ('bad','potential_risk') and f['impact'] in ('high','critical'):
            axis='credibility_maturity' if f['dimension'] in ('historical_launch_integrity','development_disclosure') else 'token_economics' if f['dimension'] in ('utility_redemption_rights','reward_accounting_liveness') else 'technical_exposure'
            check(fid in summary and fid in d['finding_ids'] and fid in axes[axis]['finding_ids'] and fid in mids,p,'high/critical concern omitted from summary, relevant axis or mitigation review')
    for action in sequence(d['actions'],p+'.actions',30):
        check(action['kind'] in ('user_choice','risk_response'),p+'.actions','standard research cannot be assigned as mandatory homework')
        text(action['text'],p+'.actions.text',judged=completed)


def validate_report(evidence,report,manifest_digest):
    p='report';m=evidence.m
    check(report['schema_version']==2 and type(report['schema_version']) is int and report['profile']==PROFILE,p+'.profile','explicit v2 report required')
    check(report['manifest_sha256']==manifest_digest,p+'.manifest_sha256','manifest bytes changed')
    for k in ('target','investigation_id','synthetic'):check(report[k]==m[k] and type(report[k]) is type(m[k]),p+'.'+k,'report identity/mode mismatch')
    for k in ('question','focus','scope'):check(report[k]==m['intake'][k],p+'.'+k,'original intake changed')
    check(report['research_status'] in ('partial','blocked','completed') and report['delivery_status'] in ('draft','checkpoint','frozen','delivered'),p,'invalid research/delivery status')
    completed=report['research_status']=='completed'
    if report['delivery_status'] in ('frozen','delivered'):check(completed and report['scope']=='broad',p+'.delivery_status','final broad delivery requires completed broad research')
    if report['delivery_status']=='checkpoint':check(not completed,p+'.delivery_status','checkpoint cannot masquerade as completed report')
    sequence(report['limitations'],p+'.limitations')
    known=findings(evidence,report,completed);covered=coverage(evidence,report,known,completed)
    refs(report['summary_ids'],known,p+'.summary_ids');decision(evidence,report,known,covered,completed)
    lanes=sequence(m['lanes'],'manifest.lanes',2)
    if completed and report['scope']=='broad':
        check(len(lanes)==2 and {r['owner'] for r in lanes}=={'liquidity','project'},'manifest.lanes','both standard lane results required')
        for lane in lanes:
            at='manifest.lanes.'+lane['owner'];check(lane['status'] in ('returned','local_completed') and lane['self_check'] is True,at,'missing/failed/unvalidated lane cannot complete')
            refs(lane['evidence_ids'],evidence.rows,at+'.evidence_ids',nonempty=True)
            note=strict_json(regular(evidence.root,lane['note_artifact']).read_bytes(),at+'.note_artifact')
            check(lane['note_artifact'] in evidence.inventory,at,'lane note not inventoried')
            check(note['owner']==lane['owner'] and note['investigation_id']==m['investigation_id'] and note['question']==report['question'] and note['target']==report['target'],at,'lane intake/ownership mismatch')
    return m,report


def validate(root,allow_synthetic=False):
    root=Path(root).resolve()
    try:
        check(not (root/'.draft-transaction.json').exists(),'draft','Interrupted composition requires recovery; draft is not deliverable.')
        raw=regular(root,'manifest.json').read_bytes();m=strict_json(raw,'manifest.json')
        r=strict_json(regular(root,'report.json').read_bytes(),'report.json');e=Evidence(root,m,allow_synthetic)
        result=validate_report(e,r,sha(raw))
        if r.get('delivery_status') in ('frozen','delivered'):
            from solana_replay import verify
            verify(root,allow_synthetic)
        return result
    except ProfileError:raise
    except (ValueError,KeyError,TypeError,IndexError,AttributeError,OSError,RecursionError) as exc:
        raise ProfileError('bundle',str(exc) if isinstance(exc,ValueError) else type(exc).__name__+': malformed or missing field/artifact') from None


def initialize(root,target=None,use_collection=False,allow_synthetic=False):
    root=Path(root).resolve()
    check((root/'manifest.json').is_file(),'manifest','Start a new v2 investigation with solana_broad_collect.py start; init requires its existing manifest and never migrates legacy evidence.')
    raw=regular(root,'manifest.json').read_bytes();m=strict_json(raw,'manifest.json');Evidence(root,m,allow_synthetic)
    if target is not None:check(target==m['target'],'target','Existing v2 manifest target differs.')
    check(not use_collection,'collection','Use the maintained broad-start importer for collection data.')
    from solana_scaffold import write
    from solana_compose import compose
    write(root,allow_synthetic=allow_synthetic)
    return compose(root,allow_synthetic=allow_synthetic)
def collection(*args,**kwargs):raise ValueError('v2 collection import requires supported compose workflow')
def render(manifest,report):
    from solana_render import render as readable
    return readable(manifest,report)
