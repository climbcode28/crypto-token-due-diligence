"""Deterministic, offline, evidence-checked facts; no assessment signals."""
import argparse,json,os,tempfile
from pathlib import Path
from solana_common import sha,need
from solana_profile import Evidence,strict_json,regular,PROFILE

VERSION='1.5.0'
CATEGORIES={'mint':'controls','controls':'controls','holders':'holders','program':'programs','controllers':'programs',
 'pool':'pools','local_quote':'quotes','public_quote':'quotes','quote_sizes':'quotes','quote_ladder':'quotes','transaction':'transactions',
 'sales':'transactions','rebuys':'transactions','history':'launch','launch':'launch','metadata':'launch','creator_activity':'creator',
 'inventory':'creator','prior_launches':'creator','source_assurance':'source_assurance',
 'discovery_pools':'maturity','repository_metadata':'maturity','repository_revision':'maturity','repository_tree':'maturity','rugcheck':'corroboration'}
LIMIT_KEYS={'gaps','missing','remaining','limitations','scope','coverage','enumeration','unsupported_lock_paths','selection_scope','newer_unpinned',
 'reserve_quantity_scope','unknown_extensions','extension_errors','additional_withheld_or_confidential_unknown'}
ATTENTION_KEYS={'mint_authority','freeze_authority','controller','delegate','close_authority','upgrade_authority','authority',
 'config_authority','withdraw_authority','permanent_delegate','paused','locked_share','all_principal_locked','exit_executable'}


def encoded(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()


def atomic(path,data):
    path=Path(path);need(not path.is_symlink(),'refuse symlink output');path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def scan(value,keys,path=''):
    rows=[]
    if isinstance(value,dict):
        for k,v in sorted(value.items()):
            p=path+'.'+k if path else k
            if k in keys and v not in ([],{},''):rows.append({'path':p,'value':v})
            else:rows.extend(scan(v,keys,p))
    elif isinstance(value,list):
        for i,v in enumerate(value):rows.extend(scan(v,keys,path+'['+str(i)+']'))
    return rows


def census_text(c):
    if not isinstance(c,dict):return ''
    if c.get('status') in ('sampled','empty','partial'):
        share=c.get('sampled_weight_share');basis='summed bin shares, a ranking weight, not principal' if str(c.get('ranking','')).startswith('summed_bin_shares') else 'liquidity ranking weight, not principal'
        return ' of '+str(c.get('positions_counted'))+' counted ('+(share['percent_display']+'% of '+basis if share else 'no ranking weight')+')'
    return ' (position census '+str(c.get('status'))+': '+str(c.get('reason'))+')'


def describe(operation,data):
    """Exact calculations are supplied by typed operations, never redone by an analyst."""
    if operation=='controls':
        m=data['mint'];powers='; '.join(p['role']+'='+('absent in sample' if p['controller'] is None else p['controller']) for p in data['powers'])
        note=data.get('newer_unpinned') or {};newer=note.get('authorities_match')
        prefix=('Earlier pinned snapshot; newer retained snapshot remains unpinned'+(' (its controllers are unchanged)' if newer is True else ' (its controllers differ)' if newer is False else ' (its controllers could not be compared)' if note else '')+'. ') if data.get('selection_scope')=='earlier_pinned_snapshot_newer_unpinned' else ''
        return prefix+'Mint supply '+m['supply_atomic']+' atomic units, decimals '+str(m['decimals'])+'. '+powers+'. Extension and controller coverage remains explicit.'
    if operation=='holders':
        share=data['coverage_share'];ratio='undefined (zero supply)' if share is None else share['percent_display']+'%'
        owners='; '.join(r['spending_owner']+': '+r['amount_atomic']+' atomic ('+(r['supply_share']['percent_display']+'%' if r['supply_share'] else 'undefined share')+'), '+str(len(r['accounts']))+' accounts' for r in data['owners'])
        head=('Largest '+str(len(data['accounts']))+' token accounts (exact ranking at the discovery slot)') if (data.get('discovery') or {}).get('method')=='getTokenLargestAccounts' else 'Sampled '+str(len(data['accounts']))+' accounts'
        return (head+': '+data['observed_base_amount_atomic']+'/'+data['supply_atomic']+' atomic units ('+ratio+'). Custody exclusions '+data['custody_excluded_amount_atomic']+'. Spending-owner aggregates: '+owners+'. '+data['scope']+'.')
    if operation=='pool':
        concentrated=data['adapter']['id'] in ('raydium_clmm','orca_whirlpool','meteora_dlmm')
        reserves=('Reserves atomic '+json.dumps(data['reserves_atomic'])) if data.get('reserves_atomic') is not None else ('Reserves not inferred (concentrated pool; position coverage '+str(data.get('position_coverage'))+')' if concentrated else 'Reserves unresolved')
        return (data['adapter']['id']+' pool '+data['pool']+'. '+reserves+
            '; observed vault count '+str(len(data['vaults']))+'; sampled positions '+str(len(data.get('positions',[])))+census_text(data.get('position_census'))+'. Principal, fees, custody, locks and execution are separately scoped below.')
    if operation=='metadata':
        verified=data['verified_creators'];return ('Metaplex metadata: name '+json.dumps(data['name'])+', symbol '+json.dumps(data['symbol'])+', update authority '+data['update_authority']+(' (mutable)' if data['is_mutable'] else ' (immutable)')+'; '+str(len(data['creators']))+' creator entries, verified: '+(', '.join(verified) if verified else 'none')+'. Keys are attribution leads, not identities; the URI is text only.')
    if operation in ('sales','rebuys'):
        return 'Reconciled '+operation+' candidates in the supplied receipt sample. Counts describe this verification sample; indexed market activity and total actor history remain separate.'
    if operation=='public_quote':
        return ('Read-only '+str(data.get('source'))+' quote: '+str(data.get('input_atomic'))+' atomic units of the mint -> '+str(data.get('output_atomic'))+' atomic units of '+str(data.get('output_mint'))
                +' (status '+str(data.get('status'))+', provider price impact '+(str(data['provider_price_impact_raw']) if data.get('provider_price_impact_raw') is not None else (str(data['price_impact_fraction']['numerator'])+'/'+str(data['price_impact_fraction']['denominator'])) if isinstance(data.get('price_impact_fraction'),dict) else 'not reported')+'). A provider claim at one size; no trade was executed.')
    if operation=='quote_ladder':
        rows=data.get('rows') or [];first=next((r for r in rows if r.get('status')=='quoted'),None)
        steps='; '.join(str(r.get('input_atomic'))+' -> '+((str(r.get('output_atomic'))+(' (baseline)' if r is first else ' ('+str(r.get('impact_vs_smallest_percent'))+'% vs smallest)')) if r.get('output_per_input') is not None else ('not captured ('+str(r.get('reason'))+')' if r.get('status')=='not_captured' else 'not quoted ('+str(r.get('status'))+')')) for r in rows)
        return ('Read-only '+str(data.get('source'))+' quotes at '+str(data.get('sizes_quoted'))+' of '+str(data.get('sizes_requested'))+' illustrative sizes selling the mint into '+str(data.get('output_mint'))+': '+steps
                +'. Largest size impact versus the smallest: '+str(data.get('largest_impact_vs_smallest_percent'))+'%. Quoted outputs are provider claims, not execution.')
    if operation in ('local_quote','quote_sizes'):
        return 'Illustrative '+operation.replace('_',' ')+' with exact input/output units and retained fee/context limits. Estimate or source quote; no trade was executed.'
    if operation=='rugcheck':
        nets=data.get('insider_networks') or [];lead=nets[0] if nets else None
        head=('RugCheck report (third-party transfer-graph analysis): '+str(data.get('insider_networks_total'))+' insider networks'
              +((', the largest '+str(lead['size'])+' wallets holding '+(lead['supply_share']['percent_display']+'% of supply' if lead.get('supply_share') else lead['token_amount_atomic']+' atomic'+(' (exceeds reported supply)' if lead.get('exceeds_supply') else ''))) if lead else ''))
        sample=('no largest-holder sample bound; listed holders unverified' if not data.get('sample_size') else str(data.get('top_holders_verified_in_sample'))+' of '+str(len(data.get('top_holders') or []))+' listed top holders verified by token account in the exact largest-holder sample')
        return (head+'; '+sample+'; '
                +str(len(data.get('lockers') or []))+' lockers; '+str(len(data.get('risks') or []))+' listed risks; score '+str(data.get('score'))+'. Networks are the indexer\'s claim, not proven common ownership.')
    if operation in ('discovery_pools','repository_metadata','repository_revision','repository_tree'):
        return 'Captured '+operation.replace('_',' ')+' publication with its original source and capture time. These metrics do not establish organic use, universal rank, authorship, safety or delivered functionality.'
    if operation=='source_assurance':
        return ('Program '+str(data.get('program'))+' assurance levels remain separate: publication '+str(data.get('publication'))+', third-party verification '+str(data.get('third_party_verification'))+
            ', byte correspondence '+str(data.get('byte_correspondence'))+', independent reproduction '+str(data.get('independent_reproduction'))+'.')
    if operation=='transaction':return 'Historical transaction status and supported instruction effects. Fee payer, signer, seller and beneficial owner remain distinct.'
    if operation=='program':
        return ('Program '+str(data.get('address'))+': loader '+str(data.get('loader'))+', upgradeability '+str(data.get('upgradeability'))+', upgrade authority '+
            ('absent' if data.get('upgrade_authority') is None else str(data['upgrade_authority']))+', code capture '+str(data.get('code_capture'))+'.')
    if operation=='controllers':
        nodes=data.get('nodes',[]);observed=sum(1 for n in nodes if n.get('status')=='observed')
        return ('Controller graph from '+', '.join(data.get('roots',[]))+': '+str(observed)+' of '+str(len(nodes))+' reachable accounts observed; status '+str(data.get('status'))+
            '; safe/locked conclusion '+str(data.get('safe_or_locked_conclusion'))+'.')
    return 'Typed '+operation.replace('_',' ')+' facts within the recorded subject, time and evidence scope.'


def build(root,allow_synthetic=False):
    root=Path(root);raw=regular(root,'manifest.json').read_bytes();m=strict_json(raw,'manifest.json');e=Evidence(root,m,allow_synthetic)
    rows=[];aliases={}
    for eid,d in sorted(e.derivations.items()):
        obs=e.rows[eid];data=e.objects[eid];category=CATEGORIES[d['operation']]
        deps=sorted({eid,*e.closure[eid]});samples=sorted({e.rows[x]['sample_id'] for x in deps if e.rows[x].get('sample_id')})
        row={'id':'fact-'+eid,'evidence_id':eid,'operation':d['operation'],'category':category,'subject':obs['subject'],
             'usable':eid in e.usable,'status':data.get('status','observed') if isinstance(data,dict) else 'observed',
             'captured_at':obs['captured_at'],'sample_ids':samples,'dependencies':deps,
             'input_digests':{x:e.rows[x]['sha256'] for x in deps},'data':data,
             'summary':describe(d['operation'],data),'limits':scan(data,LIMIT_KEYS),'attention':scan(data,ATTENTION_KEYS)}
        if not row['usable']:row['limits'].insert(0,{'path':'evidence','value':'Dependency is not usable; computed values cannot support a resolved finding.'})
        rows.append(row)
        for alias in (eid,d['operation'],category+':'+obs['subject']['address']):aliases.setdefault(alias,[]).append(eid)
    missing=[{'id':eid,'status':o['status'],'subject':o['subject'],'sample_id':o.get('sample_id'),'reason':e.degraded.get(eid)} for eid,o in sorted(e.rows.items()) if eid not in e.usable and o['kind']!='derived']
    for eid in e.rows:aliases.setdefault(eid,[eid])
    return {'facts_version':VERSION,'profile':PROFILE,'investigation_id':m['investigation_id'],'target':e.target,
        'manifest_sha256':sha(raw),'question':m['intake']['question'],'focus':m['intake']['focus'],'urls':m['intake']['urls'],
        'facts':rows,'aliases':{k:sorted(set(v)) for k,v in sorted(aliases.items())},'missing_reads':missing,
        'totals':{'typed_facts':len(rows),'usable_facts':sum(r['usable'] for r in rows),'observations':len(e.rows),'unusable_reads':len(missing)},
        'category_index':{c:[r['id'] for r in rows if r['category']==c] for c in sorted(set(CATEGORIES.values()))}}


def compact(facts,categories=None,limit=12*1024):
    need(type(limit) is int and 1024<=limit<=64*1024,'display limit must be 1–64 KiB')
    selected=set(categories or facts['category_index']);need(selected<=set(facts['category_index']),'unknown facts category')
    lines=['Solana facts '+facts['investigation_id'],json.dumps(facts['totals'],sort_keys=True),'All quantities retain typed units. Full facts.json is the detail source.']
    omitted=[]
    for row in facts['facts']:
        # The title is the citeable evidence ID; program/controller/assurance rows name their subject.
        title=row['evidence_id']+' ['+row['category']+'; '+str(row['status'])+'; usable='+str(row['usable'])+(('; '+row['subject']['address']) if row['operation'] in ('program','controllers','source_assurance') else '')+'; digest='+row['input_digests'][row['evidence_id']]+']'
        # Material controls and coverage limits always appear, even beyond the soft display target.
        critical=json.dumps({'attention':row['attention'],'limits':row['limits']},sort_keys=True,ensure_ascii=False)
        if row['category'] not in selected:
            omitted.append(title+' — category not selected; details facts.json#'+row['id']);continue
        required=title+'\n'+row['summary']+'\n'+critical
        lines.append(required)
        detail=json.dumps(row['data'],sort_keys=True,ensure_ascii=False)
        if len(('\n'.join(lines)+'\n'+detail).encode())<=limit:lines.append(detail)
        else:omitted.append(title+' — remaining typed details facts.json#'+row['id'])
    if facts['missing_reads']:lines.append('Unusable reads (not passing checks): '+json.dumps(facts['missing_reads'],sort_keys=True))
    lines.append('Omitted-detail index: '+('\n'.join(omitted) if omitted else 'none'))
    result='\n'.join(lines)+'\n'
    if len(result.encode())>limit:result+='Display exceeds soft target to retain material controls and coverage limits; choose a category for remaining detail.\n'
    return result


def generate(root,allow_synthetic=False):
    facts=build(root,allow_synthetic);atomic(Path(root)/'facts.json',encoded(facts));return facts


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--allow-synthetic',action='store_true');p.add_argument('--category',action='append');p.add_argument('--check',action='store_true');a=p.parse_args()
    facts=build(a.root,a.allow_synthetic) if a.check else generate(a.root,a.allow_synthetic);print(compact(facts,a.category),end='')
if __name__=='__main__':main()
