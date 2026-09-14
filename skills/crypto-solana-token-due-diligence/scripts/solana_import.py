"""Rebuild a strict draft from one durable session; never manufacture missing captures."""
import base64,json,time
from pathlib import Path
from urllib.parse import urlsplit
from solana_common import sha,need
from solana_session import Session,utc
from solana_profile import Evidence,PROFILE,DIMENSIONS,normalized_status,validate_report
from solana_facts import encoded,atomic
from solana_compose import empty_coverage,draft_lock,save_pair
from solana_wire import validate_response
from solana_derivations import compute,VERSION
from solana_programs import observed_account

ADAPTERS=('raydium_cpmm','raydium_amm_v4','raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2','pump_curve','pumpswap')


def quote_capture_times(obs,mint):
    """Capture times (epoch seconds) of every public quote capture for the exact mint, any source, size or outcome: a refused
    quote still marks the moment the sizes were quoted."""
    from solana_quotes import quote_request
    from solana_session import epoch
    out=[]
    for eid,o in obs.items():
        if o.get('kind')!='document':continue
        try:source,request=quote_request(o['source']['capture']['url'])
        except (ValueError,KeyError,TypeError):continue
        if request.get('input_mint')==mint:out.append(epoch(o['captured_at']))
    return out


class Importer:
    def __init__(self,session_root):
        self.session=Session(session_root);self.root=self.session.root/'draft';self.root.mkdir(exist_ok=True);s=self.session.meta
        self.m={'schema_version':2,'profile':PROFILE,'target':s['target'],'investigation_id':s['investigation_id'],'synthetic':s['synthetic'],
          'intake':{k:s[k] for k in ('target','investigation_id','question','focus','urls','scope','received_at','target_at','deadline_at','user_hard_deadline')},
          'artifacts':[],'observations':[],'samples':[],'derivations':[],'attempts':[],'lanes':[],'network_checks':None,'header_checks':[]}
        self.objects={};self.obs={};self.checked={};self.errors=[];self.critical={};self.intents={}

    def artifact(self,name,data):
        name='evidence/'+sha(data)+'-'+name;path=self.root/name
        need(not (self.root/'evidence').is_symlink(),'symlink evidence directory')
        if path.exists():need(not path.is_symlink() and path.read_bytes()==data,'immutable imported artifact changed')
        else:atomic(path,data)
        if not any(r['path']==name for r in self.m['artifacts']):self.m['artifacts'].append({'path':name,'sha256':sha(data),'bytes':len(data)})
        return name

    def subject(self,kind='mint',address=None):return {'genesis_hash':self.m['target']['genesis_hash'],'kind':kind,'address':address or self.m['target']['mint']}

    def rpc(self):
        ledger=self.session.observations()
        # Bodies already have immutable observation artifacts. Preserve every attempt,
        # including lost workers, without duplicating potentially large response bodies.
        self.artifact('attempts.json',encoded([{**{k:v for k,v in a.items() if k!='response'},'response_sha256':sha(a['response'].encode()) if a['response'] else None} for a in ledger]))
        for path in sorted((self.session.root/'sample-plans').glob('*.json')):
            plan=json.loads(path.read_text());sample=plan['sample_id']
            for r in plan['reads']:
                if r['critical']:self.critical[sample+'_'+r['name']]=True
        kinds={}
        for path in sorted((self.session.root/'preset-requests').glob('*.json')):
            try:request=json.loads(path.read_text());kinds[path.stem]=request.get('kind')
            except ValueError:continue
        for a in ledger:
            if a['transport_kind']!='rpc' or a['response'] is None:continue
            p=json.loads(a['response']);eid=p['request']['id']
            if a['completed_at'] is None:continue
            p.update(started_at=a['started_at'],completed_at=a['completed_at']);req=p['request'];method=req['method']
            path=self.artifact(eid+'.json',encoded(p));sub=self.subject()
            if method in ('getAccountInfo','getTokenSupply','getTokenLargestAccounts','getSignaturesForAddress','getTokenAccountsByOwner','getProgramAccounts'):
                filters=req['params'][1].get('filters') if method=='getProgramAccounts' and isinstance(req['params'][1],dict) else None
                scan=filters[1]['memcmp']['bytes'] if isinstance(filters,list) and len(filters)==2 and filters[1].get('memcmp',{}).get('offset')==0 else None
                sub=self.subject('mint',scan) if scan else self.subject('wallet' if method in ('getSignaturesForAddress','getTokenAccountsByOwner') else 'program' if method=='getProgramAccounts' else 'mint',req['params'][0])
            elif method=='getMultipleAccounts':sub=self.subject('mint',req['params'][0][0])
            status=normalized_status(p)
            if p['status']=='ok':
                try:c=validate_response(req,p['response']);self.checked[eid]=c;status=c['status']
                except ValueError:status='invalid'
            o={'id':eid,'kind':'rpc','subject':sub,'status':status,'artifact':path,'sha256':sha(encoded(p)),
               'captured_at':utc(a['completed_at']),'synthetic':self.m['synthetic'],'source':{'namespace':a['source'],'owner':'pipeline'},'request_id':eid,'sample_id':None}
            self.obs[eid]=o;self.objects[eid]=p;self.m['observations'].append(o)
            self.m['attempts'].append({'id':'a-'+str(a['id']),'evidence_id':eid,'dimension':self.rpc_dimension(eid,method,kinds),'owner':'pipeline','status':status,'route':'primary','source':a['source']})
        self.pin()

    def rpc_dimension(self,eid,method,kinds):
        """The coverage surface an RPC attempt evidences: by method, else by the sample that planned it."""
        if method in ('getTokenLargestAccounts','getProgramAccounts'):return 'current_concentration'
        if method=='getSignaturesForAddress':return 'historical_launch_integrity'
        if method=='getTransaction':return 'sellability_exit_depth'
        intent=self.session.root/'read-intents'/(eid+'.json');sample=''
        if intent.exists():
            try:sample=json.loads(intent.read_text()).get('sample_id','') or ''
            except ValueError:sample=''
        kind=kinds.get(sample[:-4] if sample.endswith('lead') else sample)
        by_kind={'pool':'canonical_lp_principal_custody','positions':'canonical_lp_principal_custody','programs':'admin_treasury_reward_custody',
            'transactions':'sellability_exit_depth','pool_activity':'sellability_exit_depth','quote':'sellability_exit_depth','holders':'current_concentration','creator_history':'historical_launch_integrity'}
        if kind in by_kind:return by_kind[kind]
        if sample.startswith('pool') or sample.startswith('lpleads'):return 'canonical_lp_principal_custody'
        if sample=='programs':return 'admin_treasury_reward_custody'
        if sample=='receipts':return 'sellability_exit_depth'
        return 'token_controls'

    def pin(self):
        successful=[eid for eid,c in self.checked.items() if c['status']=='ok']
        genesis=[eid for eid in successful if self.objects[eid]['request']['method']=='getGenesisHash']
        genesis.sort(key=lambda eid:self.objects[eid]['started_at'])
        bracket=None
        if len(genesis)>=2 and self.objects[genesis[0]]['completed_at']<self.objects[genesis[-1]]['started_at']:
            self.m['network_checks']={'initial_evidence_id':genesis[0],'recheck_evidence_id':genesis[-1]}
            # The verified interval and provider that the strict profile requires for a pinned sample.
            bracket=(self.objects[genesis[0]]['completed_at'],self.objects[genesis[-1]]['started_at'],self.obs[genesis[0]]['source']['namespace'])
        headers={}
        for eid in successful:
            p=self.objects[eid]
            if p['request']['method'] in ('getBlock','getBlockTime'):headers.setdefault(p['request']['params'][0],[]).append(eid)
        pairs={}
        for slot,ids in headers.items():
            ids.sort(key=lambda eid:self.objects[eid]['started_at'])
            # The initial header is a full getBlock; the later recheck may be a full header or its block time.
            initial=next((i for i in ids if self.objects[i]['request']['method']=='getBlock'),None)
            later=[i for i in ids if initial and self.objects[i]['started_at']>self.objects[initial]['completed_at']]
            if initial and later:
                pairs[slot]=(initial,later[-1]);self.m['header_checks'].append({'initial_evidence_id':initial,'recheck_evidence_id':later[-1]})
        for eid in successful:
            c=self.checked[eid]
            if 'context_slot' not in c:continue
            p=self.objects[eid];slot=c['context_slot'];h,r=pairs.get(slot,(None,None));critical=self.critical.get(eid.rsplit('_',1)[0],False)
            sid='s-'+eid;self.obs[eid]['sample_id']=sid
            stamp=self.objects[h]['response']['result'].get('blockTime') if h else None
            namespace=self.obs[eid]['source']['namespace']
            inside=bool(bracket and bracket[0]<=p['started_at'] and p['completed_at']<=bracket[1] and namespace==bracket[2])
            header_ok=bool(h and stamp is not None and -60<=p['completed_at']-stamp<=300 and self.obs[h]['source']['namespace']==namespace)
            pinned=inside and header_ok  # Outside the verified interval a sample stays partial; the run still imports.
            self.m['samples'].append({'id':sid,'observation_id':eid,'context_slot':slot,'addresses':c.get('addresses',[]),'address_indices':c.get('address_indices',{}),
                'encoding':'base64' if p['request']['method'] in ('getAccountInfo','getMultipleAccounts','getTokenAccountsByOwner','getProgramAccounts') else 'json',
                'commitment':'finalized','captured_at':self.obs[eid]['captured_at'],'block_evidence_id':h,'block_recheck_evidence_id':r,'critical':critical,
                'recheck_of':None,'status':'pinned' if pinned else 'partial'})
        used=set()
        for s in self.m['samples']:
            if not s['critical']:continue
            p=self.objects[s['observation_id']];prefix=p['request']['id'].split('_',1)[0]+'_critical_'
            candidates=[x for x in self.m['samples'] if x['observation_id'].startswith(prefix) and x['id'] not in used and
                self.objects[x['observation_id']]['started_at']>p['completed_at'] and set(s['addresses'])<=set(x['addresses'])]
            if candidates:
                chosen=min(candidates,key=lambda x:self.objects[x['observation_id']]['started_at']);chosen['recheck_of']=s['id'];used.add(chosen['id'])
                if chosen['status']!='pinned':s['status']='partial'
            else:s['status']='partial'

    @staticmethod
    def planned_route(record):
        """The discovery plan fixes these: DEX Screener pools and GeckoTerminal token info are primary; GeckoTerminal
        pool pages and Solana Explorer are the alternates. None for every other capture."""
        parts=urlsplit(record['url']);host=parts.hostname or '';gecko=host=='geckoterminal.com' or host.endswith('.geckoterminal.com')
        if host=='api.dexscreener.com' or (gecko and parts.path.endswith('/info')):return 'primary'
        if gecko and 'trades' in parts.path.split('/'):return 'follow_up'  # a pool's trade feed feeds receipt probes, never discovery
        if host=='api.rugcheck.xyz':return 'follow_up'  # third-party corroboration, never pool discovery
        if gecko or host=='explorer.solana.com':return 'alternate'
        return None

    @staticmethod
    def dimension_of(record):
        if record.get('dimension'):return record['dimension']
        parts=urlsplit(record['url']);host=parts.hostname or ''
        if host in ('api.dexscreener.com','api.geckoterminal.com') and not parts.path.endswith('/info'):return 'canonical_lp_principal_custody'
        if host in ('lite-api.jup.ag','api.jup.ag'):return 'sellability_exit_depth'
        if host=='api.rugcheck.xyz':return 'current_concentration'
        return 'development_disclosure'  # project pages and the token-info publication that names them

    def routes(self,records):
        """Planned discovery routes keep their plan label. For any other capture, per coverage surface and owner, the
        first host that owner registered is primary and a later, different host is alternate, so two failed lane
        captures at distinct hosts within one surface are the failed primary and alternate an external limit needs."""
        table=self.session.db.execute("SELECT count(*) FROM sqlite_master WHERE name='web_sources'").fetchone()[0]
        order={row[0]:n for n,row in enumerate(self.session.db.execute('SELECT id FROM web_sources ORDER BY rowid'))} if table else {}
        first={};routes={}
        for record in sorted(records,key=lambda r:(order.get(r.get('source_id'),len(order)),r['captured_at'],r['id'])):
            planned=self.planned_route(record)
            if planned:routes[record['id']]=planned;continue
            key=(self.dimension_of(record),record['owner']);host=urlsplit(record['url']).hostname or ''
            first.setdefault(key,host);routes[record['id']]='primary' if first[key]==host else 'alternate'
        return routes

    def web(self):
        records=[]
        for path in sorted((self.session.root/'web-captures').glob('*.json')):
            record=json.loads(path.read_text())
            if record.get('captured_at') and record.get('sha256'):records.append(record)
        routes=self.routes(records)
        for record in records:
            raw=(self.session.root/record['raw']).read_bytes() if record.get('raw') else b''
            need(sha(raw)==record['sha256'] and len(raw)==record['bytes'],'web capture changed')
            eid=record['id'];artifact=self.artifact(eid+'.raw',raw);o={'id':eid,'kind':'document','subject':self.subject('document'),
                'status':normalized_status(record),'artifact':artifact,'sha256':sha(raw),'captured_at':utc(record['captured_at']),'synthetic':self.m['synthetic'],
                'source':{'capture':record,'owner':'shared' if record['owner']=='ordinary' else record['owner']},'sample_id':None}
            self.obs[eid]=o;self.objects[eid]={'record':record,'raw':raw};self.m['observations'].append(o)
            self.m['attempts'].append({'id':'capture-'+sha(eid.encode())[:24],'evidence_id':eid,'dimension':self.dimension_of(record),'owner':'pipeline' if record['owner']=='ordinary' else record['owner'],
                'status':o['status'],'route':routes[eid],'source':urlsplit(record['url']).hostname})

    def derive(self,eid,operation,params,sub=None):
        used=set()
        def resolve(ident):used.add(ident);return self.objects[ident]
        try:
            value=compute(operation,params,self.m['target'],resolve);need(bool(used),'derivation needs actual inputs')
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            self.errors.append({'operation':operation,'id':eid,'reason':str(exc) if isinstance(exc,ValueError) else type(exc).__name__});return None
        raw=encoded(value);path=self.artifact(eid+'.json',raw);sub=sub or self.subject();closure=set(used)
        for d in self.m['derivations']:
            if d['id'] in used:closure.update(d['transitive_inputs'])
        captured=max(self.obs[i]['captured_at'] for i in used)
        d={'id':eid,'operation':operation,'version':VERSION,'parameters':params,'subject':sub,'inputs':[{'id':i,'sha256':self.obs[i]['sha256']} for i in sorted(used)],
           'transitive_inputs':sorted(closure),'units':'exact atomic units and typed configuration','output':value}
        o={'id':eid,'kind':'derived','status':'ok','subject':sub,'artifact':path,'sha256':sha(raw),'captured_at':captured,'synthetic':self.m['synthetic'],'source':{'operation':operation},'sample_id':None}
        self.m['derivations'].append(d);self.m['observations'].append(o);self.objects[eid]=value;self.obs[eid]=o;return value

    def newer_unpinned(self,newer,pinned):
        """The note a controls fact carries about a newer unpinned mint read: every controller compared, a decode failure explained."""
        from solana_accounts import newer_unpinned_note
        return {'observation':newer,**newer_unpinned_note(self.objects[newer],self.objects[pinned],self.m['target'])}

    def latest_accounts(self,usable=None):
        """The latest successful read per address; with `usable`, only reads whose sample stayed pinned."""
        result={}
        for eid,c in sorted(self.checked.items(),key=lambda item:self.objects[item[0]]['completed_at']):
            if c['status']=='ok' and (usable is None or eid in usable) and self.objects[eid]['request']['method'] in ('getAccountInfo','getMultipleAccounts'):
                for a in c.get('addresses',[]):result[a]=eid
        return result

    def facts(self):
        target=self.m['target'];raw_evidence=Evidence(self.root,self.m,self.m['synthetic'])
        # Pool and program facts prefer the latest pinned read per address; the newest read decides only whether the
        # mint's controls fact must fall back to an earlier pinned snapshot.
        latest=self.latest_accounts();usable_accounts=self.latest_accounts(raw_evidence.usable);accounts={**latest,**usable_accounts};mint=latest.get(target['mint'])
        prices=[]
        for eid,o in list(self.obs.items()):
            if o['kind']!='document' or o['status']!='ok':continue
            host=urlsplit(o['source']['capture']['url']).hostname
            path=urlsplit(o['source']['capture']['url']).path
            if host in ('api.dexscreener.com','api.geckoterminal.com') and not (host=='api.geckoterminal.com' and ('/pools' not in path or 'trades' in path.split('/'))):
                did='market-'+sha(eid.encode())[:16]
                result=self.derive(did,'discovery_pools',{'capture':eid,'source':'geckoterminal' if host=='api.geckoterminal.com' else 'dexscreener'})
                if result:
                    prices += [(did,p) for p in result['candidates'] if p['price_denominator_mint']==target['mint'] and p['price_usd'] is not None and not p['conflicts']]
        leads=[]
        auto=self.session.root/'automatic-leads.json'
        if auto.exists():leads+=json.loads(auto.read_text())
        for path in sorted((self.session.root/'preset-requests').glob('*.json')):
            request=json.loads(path.read_text())
            if request['kind'] in ('pool','positions','pool_activity'):leads.append(request.get('parameters',{}))
        epochs=[i for i,c in self.checked.items() if i in raw_evidence.usable and c['status']=='ok' and self.objects[i]['request']['method']=='getEpochInfo']
        usable_mint=mint
        if mint:
            optional_epoch={'epoch':epochs[-1]} if epochs else {}
            params={'mint':mint,**optional_epoch,'selection_scope':'latest_retained_account_snapshot'}
            if mint not in raw_evidence.usable:
                prior=[eid for eid,c in self.checked.items() if eid in raw_evidence.usable and target['mint'] in c.get('addresses',[]) and self.objects[eid]['request']['method'] in ('getAccountInfo','getMultipleAccounts')]
                usable_mint=max(prior,key=lambda eid:self.objects[eid]['completed_at']) if prior else None
                if usable_mint:
                    # The latest pinned snapshot carries the controls fact; the newer unpinned read is a stated limit
                    # (with whether its authorities still match), never a coverage gap that blocks the surface.
                    params={'mint':usable_mint,**optional_epoch,'selection_scope':'earlier_pinned_snapshot_newer_unpinned','newer_unpinned':self.newer_unpinned(mint,usable_mint)}
            self.derive('auto-controls','controls',params)
        # Metaplex metadata for the exact mint: a present, decodable account becomes a fact; an absent one stays a stated limit.
        from solana_metadata import metadata_address
        pda=metadata_address(target['mint']);self.metadata_observation=None
        reads=[eid for eid,c in self.checked.items() if c['status']=='ok' and eid in raw_evidence.usable and self.objects[eid]['request']['method']=='getAccountInfo' and self.objects[eid]['request']['params'][0]==pda]
        if reads:
            latest=max(reads,key=lambda eid:self.objects[eid]['completed_at']);value,_=observed_account(pda,self.objects[latest])
            if value and self.derive('auto-metadata','metadata',{'address':pda,'observation':latest}):self.metadata_observation=latest
        if usable_mint:
            # Aggregates take the latest usable snapshot, never a newer unusable one.
            params={'mint':usable_mint}
            if prices:
                from solana_session import epoch
                # The earliest captured price (capture time, then id) is the policy's price at start and at every later refresh,
                # so a market page a lane captures later can never restate the sizes; observation order alone is hash order.
                prices.sort(key=lambda item:(item[1]['captured_at'],item[0]));did,price=prices[0]
                # The size policy is judged as of the first quote capture once quotes were attempted: a mint re-read minutes
                # later (a follow-up preset) must not restate the sizes and orphan the ladder that was quoted at them.
                quoted=quote_capture_times(self.obs,target['mint'])
                now=max(price['captured_at'],min(quoted)) if quoted else max(epoch(self.obs[usable_mint]['captured_at']),price['captured_at'])
                params.update(price_discovery=did,price_pool=price['pool'],now=now)
            self.derive('auto-sizes','quote_sizes',params)
        def discovers(i):
            req=self.objects[i]['request']
            if req['method']=='getTokenLargestAccounts':return req['params'][0]==target['mint']
            if req['method']=='getProgramAccounts':
                filters=req['params'][1].get('filters') or []
                return len(filters)==2 and filters[1].get('memcmp')=={'offset':0,'bytes':target['mint']}
            return False
        largest=[i for i,c in self.checked.items() if c['status']=='ok' and i in raw_evidence.usable and discovers(i)]
        samples=[i for i,c in self.checked.items() if c['status']=='ok' and i in raw_evidence.usable and self.objects[i]['request']['method']=='getMultipleAccounts' and target['mint'] in c.get('addresses',[]) and len(c['addresses'])>1 and '_holdings_' in i]
        derived_pools=[]
        from adapters import pool_adapter
        by_program={pool_adapter(k).PROGRAM:k for k in ADAPTERS}
        for address,eid in accounts.items():
            value,_=observed_account(address,self.objects[eid])
            if not value:continue
            from solana_programs import decode_program
            if value.get('executable'):
                try:
                    initial=decode_program(address,self.objects[eid]);pd=initial.get('programdata_address')
                    self.derive('program-'+sha(address.encode())[:16],'program',{'address':address,'observation':eid,**({'programdata':accounts[pd]} if pd in accounts else {})},self.subject('program',address))
                except ValueError:pass
            kind=by_program.get(value['owner'])
            if kind:
                module=pool_adapter(kind);extra={}
                for lead in leads:
                    if lead.get('pool')==address and lead.get('adapter')==kind:
                        for k in ('lp_accounts','positions','census'):
                            if k in lead:extra[k]=lead[k]
                # The adapter's arithmetic needs one atomic batch, so the pool packet is the latest usable read that
                # also carries every lead position or LP account; a later bare re-read of the pool (a coordinator
                # `pool` preset) must not erase positions the census already sampled. Program control is added from
                # its own reads (program and ProgramData); no mixing fresh vaults into an old pool.
                required={row['position'] for row in extra.get('positions',[]) if isinstance(row,dict) and row.get('position')}|set(extra.get('lp_accounts') or [])
                if required:
                    covering=[i for i,c in self.checked.items() if c['status']=='ok' and i in raw_evidence.usable and self.objects[i]['request']['method'] in ('getAccountInfo','getMultipleAccounts')
                              and address in c.get('addresses',[]) and required<=set(c['addresses'])]
                    if covering:
                        best=max(covering,key=lambda i:self.objects[i]['completed_at']);candidate,_=observed_account(address,self.objects[best])
                        if candidate:eid,value=best,candidate
                c=self.checked[eid];mapping={a:eid for a in c['addresses']}
                if module.PROGRAM in usable_accounts:
                    # Program control only from usable reads: an unusable program packet would make the whole pool fact unusable.
                    mapping[module.PROGRAM]=usable_accounts[module.PROGRAM]
                    try:pd=decode_program(module.PROGRAM,self.objects[usable_accounts[module.PROGRAM]]).get('programdata_address')
                    except ValueError:pd=None
                    if pd in usable_accounts:mapping[pd]=usable_accounts[pd]
                params={'adapter':kind,'pool':address,'observations':mapping,**extra}
                try:
                    state=module.decode_pool(address,value) if kind in ('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2') else module.decode_pool(value)
                except ValueError:continue
                if kind!='pump_curve' and target['mint'] not in state.get('mints',[]):continue
                fid='pool-'+sha(address.encode())[:16];pool=self.derive(fid,'pool',params,self.subject('pool',address))
                if pool:derived_pools.append((address,kind,pool))
                if pool and kind=='raydium_cpmm' and 'auto-sizes' in self.objects:
                    for j,size in enumerate(self.objects['auto-sizes'].get('sizes',[])):
                        self.derive('quote-'+sha(address.encode())[:12]+'-'+str(j),'local_quote',{'adapter':kind,'pool':address,'observations':mapping,'input_atomic':size['input_atomic']})
        if largest and samples:
            # A pool's vault token account ranked among the largest holders is protocol custody, not a holder: exclude it
            # with the pool observation as evidence so concentration is custody-adjusted (a live DLMM vault ranked top 20).
            sampled=set(self.checked[samples[-1]].get('addresses',[]));exclusions={}
            for address,kind,pool in derived_pools:
                for vault in pool.get('vaults',[]):
                    if vault.get('address') in sampled and vault.get('evidence'):
                        exclusions[vault['address']]={'reason':'pool_vault:'+kind+':'+address,'evidence':list(vault['evidence'])}
            params={'discovery':largest[-1],'sample':samples[-1]}
            if exclusions:params['custody_exclusions']=exclusions
            self.derive('auto-holders','holders',params)
        for eid,o in list(self.obs.items()):
            # RugCheck's report is a third-party corroboration document; its holders cross-check against the exact sample.
            if o['kind']=='document' and o['status']=='ok' and urlsplit(o['source']['capture']['url']).hostname=='api.rugcheck.xyz':
                params={'capture':eid}
                if 'auto-holders' in self.objects:params['holders']='auto-holders'
                self.derive('rugcheck-'+sha(eid.encode())[:12],'rugcheck',params)
        for eid,o in list(self.obs.items()):
            if o['kind']!='document' or o['status']!='ok':continue
            host=urlsplit(o['source']['capture']['url']).hostname
            if host=='api.github.com':
                pieces=urlsplit(o['source']['capture']['url']).path.strip('/').split('/')
                if len(pieces)>=3 and pieces[0]=='repos':
                    repo='/'.join(pieces[1:3]);op='repository_metadata' if len(pieces)==3 else 'repository_revision' if len(pieces)==5 and pieces[3:]==['commits','HEAD'] else None
                    if op:self.derive('repo-'+sha(eid.encode())[:16],op,{'capture':eid,'repository':repo})
        # Captured public quotes (a lane's Jupiter lite/keyed capture) become typed quote facts for the exact mint.
        from solana_quotes import quote_request
        quote_ids={};quote_gaps={}  # (source, output mint, size) -> usable quote derivation, or why none exists
        for eid,o in sorted(self.obs.items(),key=lambda item:(item[1]['captured_at'],item[0])):  # capture order, then id: deterministic
            if o['kind']!='document':continue
            try:source,request=quote_request(o['source']['capture']['url'])
            except (ValueError,KeyError,TypeError):continue
            if request['input_mint']!=target['mint']:continue
            key=(source,request['output_mint'],request['input_atomic']);record=o['source']['capture']
            if o['status']!='ok':
                quote_gaps.setdefault(key,'capture '+str(o['status'])+(' (http '+str(record['http_status'])+')' if record.get('http_status') else ''));continue
            qid='quote-'+sha(eid.encode())[:16];before=len(self.errors)
            if self.derive(qid,'public_quote',{'capture':eid,'source':source,'output_mint':request['output_mint'],'input_atomic':request['input_atomic'],'slippage_bps':request['slippage_bps']}):quote_ids.setdefault(key,qid)
            else:quote_gaps.setdefault(key,'quote not usable: '+str(self.errors[before]['reason']) if len(self.errors)>before else 'quote not usable')
        # One ladder per (source, output mint), bound to the quote_sizes policy: only a quote at a policy size joins it (a lane quote
        # at another size stays its own fact and can never displace a policy size), and a policy size without a usable quote is a
        # named row, so sellability carries a measured impact across the three illustrative sizes or says which size is missing.
        if 'auto-sizes' in self.objects:
            policy=[s['input_atomic'] for s in self.objects['auto-sizes'].get('sizes',[]) if isinstance(s,dict) and s.get('input_atomic')]
            groups={}
            for (source,output_mint,size),qid in quote_ids.items():
                if size in policy:groups.setdefault((source,output_mint),{})[size]=qid
            for (source,output_mint),by_size in sorted(groups.items()):
                missing={size:quote_gaps.get((source,output_mint,size),'not captured') for size in policy if size not in by_size}
                self.derive('ladder-'+sha((source+output_mint).encode())[:16],'quote_ladder',{'sizes':'auto-sizes','quotes':[by_size[s] for s in policy if s in by_size],'source':source,'output_mint':output_mint,'missing':missing})
        txs=[]
        for eid,c in list(self.checked.items()):
            if c['status']=='ok' and self.objects[eid]['request']['method']=='getTransaction':
                headers=[i for i,x in self.checked.items() if x['status']=='ok' and self.objects[i]['request']['method']=='getBlock' and self.objects[i]['request']['params'][0]==c['historical_slot']]
                if headers:
                    name='tx-'+sha(eid.encode())[:16]
                    if self.derive(name,'transaction',{'transaction':eid,'block':headers[0]}):txs.append(name)
        # Attributed-key history pages (coordinator creator_history presets) are typed per address; the
        # window ends at the latest current context and starts at genesis, so coverage stays an explicit gap.
        histories={};latest_slot=max([c.get('context_slot',0) for c in self.checked.values() if c.get('context_slot')] or [0])
        pages={}
        for eid,c in sorted(self.checked.items(),key=lambda item:self.objects[item[0]]['started_at']):
            req=self.objects[eid]['request']
            if c['status']=='ok' and req['method']=='getSignaturesForAddress' and 'creator_history' in eid:pages.setdefault(req['params'][0],[]).append(eid)
        for address,ids in pages.items():
            if latest_slot>0 and self.derive('history-'+sha(address.encode())[:12],'history',{'address':address,'pages':ids[:2],'start_slot':0,'end_slot':latest_slot},self.subject('wallet',address)):histories[address]='history-'+sha(address.encode())[:12]
        launch=None;sales=rebuys=None
        if txs:
            launch=self.derive('auto-launch','launch',{'executions':txs[:4]})
            known_pools={lead['pool'] for lead in leads if lead.get('pool')}
            candidates=[];seen_signatures=set()
            for name in txs:
                sig=self.objects[name].get('signature')
                if sig in seen_signatures:continue  # The same receipt read twice is one execution.
                seen_signatures.add(sig)
                swaps=[e for e in self.objects[name].get('effects',[]) if (e['kind']=='swap_instruction' and e['pool'] in known_pools) or (e['kind']=='protocol_trade_instruction' and e.get('curve') in known_pools)]
                if len(swaps)==1:candidates.append({'pool':swaps[0].get('pool') or swaps[0]['curve'],'execution':name})
            if candidates:
                # Both directions are derived from the same receipts; a buy is never a failed sale.
                from solana_transactions import MAX_TRADE_RECEIPTS
                # Every sampled receipt at a known pool counts, start's and the presets', up to the verifier's bound.
                sales=self.derive('auto-sales','sales',{'candidates':candidates[:MAX_TRADE_RECEIPTS]});rebuys=self.derive('auto-rebuys','rebuys',{'candidates':candidates[:MAX_TRADE_RECEIPTS]})
        attributed=[]
        for init in (launch or {}).get('initializations',[]):
            for address in (init['creator_argument'],):
                if address not in {a['address'] for a in attributed} and len(attributed)<2:attributed.append({'mint':target['mint'],'address':address,'role':'creator','evidence':init['evidence']})
        for address,kind,pool in derived_pools:
            # A Pump curve records its creator on chain; that key outranks metadata, whose update authority is the platform's.
            role=pool.get('creator_role') if kind=='pump_curve' else None
            from solana_metadata import attributable
            if role and attributable(role.get('address')) and role.get('evidence') and role['address'] not in {a['address'] for a in attributed} and len(attributed)<2:
                attributed.append({'mint':target['mint'],'address':role['address'],'role':'creator','basis':'pump_curve_recorded_creator','evidence':list(role['evidence'])})
        if self.metadata_observation and 'auto-metadata' in self.objects:
            # Without a launch receipt, the metadata's update authority and verified creators are the attributable keys.
            from solana_metadata import attribution_leads
            for lead in attribution_leads(self.objects['auto-metadata']):
                if lead['address'] not in {a['address'] for a in attributed} and len(attributed)<2:
                    attributed.append({'mint':target['mint'],'address':lead['address'],'role':'creator','basis':lead['basis'],'evidence':[self.metadata_observation]})
        signers={s for name in txs for s in self.objects[name].get('signers',[]) if any(e['kind']=='launch_initialize' for e in self.objects[name].get('effects',[]))}
        for address in sorted({a['address'] for a in attributed}|signers)[:2]:
            # A prior-launch scan needs sampled executions; the wallet is its subject, never the mint.
            if txs:self.derive('prior-'+sha(address.encode())[:12],'prior_launches',{'address':address,'executions':txs[:8]},self.subject('wallet',address))
        if attributed:
            params={'attributions':attributed,'executions':txs[:8],'histories':[histories[a['address']] for a in attributed if a['address'] in histories]}
            if sales:params['sales']='auto-sales'
            if rebuys:params['rebuys']='auto-rebuys'
            self.derive('auto-creator','creator_activity',params)
        roots=[d['id'] for d in self.m['derivations'] if d['operation'] in ('controls','pool','program')]
        if roots:
            # One unusable root or a newer unusable packet must not taint the whole authority graph:
            # build it from usable roots and the latest usable packet per address.
            usable=Evidence(self.root,self.m,self.m['synthetic']).usable
            chosen=[r for r in roots if r in usable] or roots
            usable_accounts={}
            for eid,c in sorted(self.checked.items(),key=lambda item:self.objects[item[0]]['completed_at']):
                if c['status']=='ok' and eid in usable and self.objects[eid]['request']['method'] in ('getAccountInfo','getMultipleAccounts'):
                    for a in c.get('addresses',[]):usable_accounts[a]=eid
            self.derive('auto-controllers','controllers',{'root_derivations':chosen,'observations':usable_accounts or accounts})
        for d in list(self.m['derivations']):
            if d['operation']=='program':self.derive('assurance-'+sha(d['id'].encode())[:16],'source_assurance',{'address':d['subject']['address'],'program':d['id']},d['subject'])

    def write(self):
        self.rpc();self.web();self.facts();e=Evidence(self.root,self.m,self.m['synthetic']);raw=encoded(self.m)
        # A refresh is explicitly unjudged; existing analyst files are retained for compose.
        from solana_facts import build
        from solana_pipeline_note import build_note
        m=self.m
        r={'schema_version':2,'profile':PROFILE,'target':m['target'],'investigation_id':m['investigation_id'],'synthetic':m['synthetic'],
          **{k:m['intake'][k] for k in ('question','focus','scope')},'manifest_sha256':sha(raw),'research_status':'partial','delivery_status':'draft','findings':[],
          'ratings':dict.fromkeys(DIMENSIONS,'unknown'),'coverage':[empty_coverage(dim,attempts=[a['id'] for a in m['attempts'] if a['dimension']==dim]) for dim in DIMENSIONS],
          'summary_ids':[],'decision':None,'limitations':['Standard research and analyst review remain incomplete.']}
        validate_report(e,r,sha(raw))
        with draft_lock(self.root):save_pair(self.root,raw,r)
        from solana_pipeline_note import generate
        note=generate(self.root,m['synthetic']);r['findings']=note['findings']
        for c in r['coverage']:
            c['finding_ids']=[f['id'] for f in r['findings'] if f['dimension']==c['dimension']]
            if c['finding_ids']:c['status']='partial'
        validate_report(e,r,sha(raw))
        with draft_lock(self.root):save_pair(self.root,raw,r)
        attempts=self.session.observations();started={a['request_id'] for a in attempts}
        unsent=[p.stem for p in (self.session.root/'read-intents').glob('*.json') if p.stem not in started]
        atomic(self.session.root/'import-diagnostics.json',encoded({'errors':self.errors,'unfinished_attempts':[a['request_id'] for a in attempts if a['completed_at'] is None],
            'unsent_intents':sorted(unsent),'unsent_meaning':'Named reads without acquired attempts; budget/deadline/eligibility refusals are not source evidence.'}))
        return {'draft':str(self.root),'observations':len(self.obs),'facts':len(m['derivations']),'errors':self.errors,'research_status':'partial'}


def refresh(root):
    importer=Importer(root)
    try:return importer.write()
    finally:importer.session.close()
