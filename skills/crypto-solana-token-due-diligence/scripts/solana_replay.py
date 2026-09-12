"""Atomic frozen delivery, non-executing verification and explicit trusted replay."""
import ast,copy,os,subprocess,sys,tempfile
from pathlib import Path
from urllib.parse import quote,unquote
from solana_common import sha
from solana_profile import PROFILE,regular,strict_json,check,validate,validate_report,Evidence
from solana_compose import ComposeError, compose,draft_lock
from solana_facts import encoded,atomic
from solana_render import render,reading

VERSION='1.1.0'
ENGINE_ROOT=Path(__file__).resolve().parents[1]
MAX_FILES=2000
MAX_BYTES=192*1024*1024


def snapshot_engine(destination,engine_root=None):
    source=Path(engine_root or ENGINE_ROOT).resolve();files={}
    for folder in ('scripts','assets'):
        for p in sorted((source/folder).rglob('*')):
            check(not p.is_symlink(),'engine','Symlink engine dependency forbidden.')
            if p.is_dir():continue
            if folder=='scripts' and p.suffix!='.py':continue
            name=p.relative_to(source).as_posix();files[name]=regular(source,name).read_bytes()
    check('scripts/solana_replay.py' in files and 'assets/release.json' in files,'engine','Complete engine and release data required.')
    # Include all installed local modules and their non-code assets. Verify static
    # imports resolve locally or to the Python standard library, never an EVM sibling.
    modules={name[len('scripts/'):].split('/')[0].removesuffix('.py') for name in files if name.startswith('scripts/')}
    for name,data in files.items():
        if not name.endswith('.py'):continue
        for node in ast.walk(ast.parse(data,filename=name)):
            names=([n.name for n in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) and not node.level and node.module else [])
            for imported in names:check(imported.split('.')[0] in modules or imported.split('.')[0] in sys.stdlib_module_names,name,'Unlisted non-standard dependency: '+imported)
    for name,data in files.items():atomic(destination/name,data)
    return strict_json(files['assets/release.json'],'engine release')


def file_inventory(root):
    rows=[];total=0
    for p in sorted(root.rglob('*')):
        check(not p.is_symlink(),'freeze','Symlink in frozen tree.')
        if p.is_dir():continue
        name=p.relative_to(root).as_posix()
        if name=='delivery.json':continue
        data=regular(root,name).read_bytes();total+=len(data)
        check(len(rows)<MAX_FILES and total<=MAX_BYTES,'freeze','Frozen inventory exceeds bounds.')
        rows.append({'path':name,'sha256':sha(data),'bytes':len(data)})
    return rows


def verify(root,allow_synthetic=False):
    """Hash/inventory verification only. Never imports or executes bundled Python."""
    root=Path(root).resolve();receipt=strict_json(regular(root,'delivery.json').read_bytes(),'delivery.json')
    check(receipt['schema_version']==1 and receipt['profile']==PROFILE,'delivery','Unknown frozen contract.')
    check(type(receipt['synthetic']) is bool and (allow_synthetic or not receipt['synthetic']),'delivery.synthetic','Synthetic bundle requires explicit opt-in.')
    check(receipt['delivery_status'] in ('delivered','checkpoint'),'delivery','Invalid frozen status.')
    expected=receipt['inventory'];check(isinstance(expected,list) and len(expected)<=MAX_FILES,'delivery.inventory','Bounded inventory required.')
    names=[r['path'] for r in expected];check(len(names)==len(set(names)),'delivery.inventory','Duplicate paths.')
    total=0
    for row in expected:
        total+=regular(root,row['path']).stat().st_size
        check(total<=MAX_BYTES,'delivery.inventory','Frozen byte bound exceeded.')
        data=regular(root,row['path']).read_bytes()
        check(type(row['bytes']) is int and row['bytes']==len(data) and sha(data)==row['sha256'],row['path'],'Frozen dependency hash/size mismatch.')
    check(file_inventory(root)==expected,'delivery.inventory','Missing, changed or unlisted frozen file.')
    required={'manifest.json','report.json','report.md','reading.json','engine/scripts/solana_replay.py','engine/scripts/solana_profile.py','engine/scripts/solana_render.py','engine/assets/release.json'}
    check(required<=set(names),'delivery.inventory','Required frozen dependency missing.')
    manifest=strict_json(regular(root,'manifest.json').read_bytes(),'manifest');report=strict_json(regular(root,'report.json').read_bytes(),'report')
    for name in ('manifest.json','report.json','report.md'):
        check(receipt['source_hashes'][name]==sha(regular(root,name).read_bytes()),name,'Source hash mismatch.')
    for key in ('profile','target','investigation_id','synthetic'):
        check(manifest[key]==report[key]==receipt[key],'delivery.'+key,'Frozen identity differs.')
    check(report['manifest_sha256']==receipt['source_hashes']['manifest.json'],'report','Manifest binding differs.')
    check(report['delivery_status']==receipt['delivery_status'],'delivery','Frozen status differs.')
    if receipt['delivery_status']=='delivered':check(report['scope']=='broad' and report['research_status']=='completed','delivery','Only completed broad reports deliver.')
    else:check(report['research_status']!='completed','checkpoint','Checkpoint is not completed research.')
    return {'valid':True,'verification':'inventory and hashes only; no frozen code executed','executed_frozen_code':False,
        'delivery_status':receipt['delivery_status'],'synthetic':receipt['synthetic'],'files':len(expected),'receipt':receipt}


def read(root,allow_synthetic=False):
    """The frozen reading checklist and citations; the full report stays in report_path, never in the payload."""
    root=Path(root).resolve();result=verify(root,allow_synthetic)
    content=strict_json(regular(root,'reading.json').read_bytes(),'reading.json')
    check(content['target']==result['receipt']['target'] and content['delivery_status']==result['delivery_status'],'reading','Reading identity/status differs.')
    from solana_render import safe_text,PUBLICATION_OPS,PUBLICATION_DETAIL_LINES
    for row in content['citations']:
        if row['kind']=='frozen_evidence':
            name=unquote(row['url']);row['path']=str(regular(root,name));target='<'+quote(row['path'],safe='/._- ')+'>'
        else:target=row['url']
        row['answer_link']='['+safe_text(row['label'])+']('+target+')'
    for entry in content['reading_checklist']:
        # Older frozen checklists carry every publication leaf; the presentation caps them the same way.
        if entry.get('kind')=='typed_fact' and entry.get('operation') in PUBLICATION_OPS and isinstance(entry.get('details'),list) and len(entry['details'])>PUBLICATION_DETAIL_LINES+1:
            rest=len(entry['details'])-PUBLICATION_DETAIL_LINES;entry['details']=entry['details'][:PUBLICATION_DETAIL_LINES]+['… '+str(rest)+' further publication detail lines retained in the frozen report and evidence.']
    return {**content,'bundle':str(root),'report_path':str(root/'report.md'),
        'verification':result['verification'],'deliverable':result['delivery_status']=='delivered'}


def copy_draft(root,destination,note_name):
    m=strict_json(regular(root,'manifest.json').read_bytes(),'manifest.json')
    names={'manifest.json','report.json',*[a['path'] for a in m['artifacts']]}
    if note_name is not None:
        names.add(note_name)
        for owner in ('liquidity','project'):
            if (root/'notes'/(owner+'.json')).exists():names.add('notes/'+owner+'.json')
    for name in sorted(names):atomic(destination/name,regular(root,name).read_bytes())


def finalize(root,out,*,note_name='notes/coordinator.json',allow_synthetic=False,checkpoint=False,engine_root=None):
    root=Path(root).resolve();out=Path(os.path.abspath(out))
    check(not out.exists() and not out.is_symlink(),'output','Finalization requires a new output directory.')
    out=out.parent.resolve()/out.name
    check(root!=out and root not in out.parents,'output','Frozen output must be outside the active draft.')
    check(out.parent.exists() and not any(p.is_symlink() for p in [out.parent,*out.parent.parents]),'output','Existing non-symlink output parent required.')
    # Work only in a private staging tree. Even successful compose cannot replace
    # the caller's previous draft if freezing or replay later fails.
    with tempfile.TemporaryDirectory(prefix='.solana-freeze-',dir=out.parent) as directory:
        stage=Path(directory)/'bundle';stage.mkdir()
        with draft_lock(root):
            check(not (root/'.draft-transaction.json').exists(),'draft','Recover interrupted composition first.')
            copy_draft(root,stage,note_name)
        note_status='composed'
        if checkpoint:
            # A checkpoint carries the analyst's current judgments when the note composes; an
            # invalid note never blocks preserving the last valid draft.
            try:compose(stage,note_name,allow_synthetic=allow_synthetic)
            except ComposeError as exc:note_status='not_composed: '+'; '.join(e['path']+': '+e['message'] for e in exc.errors[:3])
            m,r=validate(stage,allow_synthetic);check(r['research_status']!='completed','checkpoint','Use finalize for completed broad reports.')
        else:
            compose(stage,note_name,allow_synthetic=allow_synthetic)
            m,r=validate(stage,allow_synthetic)
            check(r['research_status']=='completed' and r['scope']=='broad','finalize','Completed broad research required; use checkpoint for incomplete work.')
        r=copy.deepcopy(r);r['delivery_status']='checkpoint' if checkpoint else 'delivered'
        atomic(stage/'report.json',encoded(r));validate_report(Evidence(stage,m,allow_synthetic),r,sha((stage/'manifest.json').read_bytes()))
        # Mutable notes/locks used during composition are not frozen runtime inputs.
        keep={'manifest.json','report.json',*[a['path'] for a in m['artifacts']]}
        for p in list(stage.rglob('*')):
            if p.is_file() and p.relative_to(stage).as_posix() not in keep:p.unlink()
        release=snapshot_engine(stage/'engine',engine_root)
        atomic(stage/'report.md',render(m,r).encode());atomic(stage/'reading.json',encoded(reading(m,r)))
        receipt={'schema_version':1,'profile':PROFILE,'target':m['target'],'investigation_id':m['investigation_id'],'synthetic':m['synthetic'],
            'delivery_status':r['delivery_status'],'reporting_version':VERSION,'engine_release':release,
            'source_hashes':{n:sha((stage/n).read_bytes()) for n in ('manifest.json','report.json','report.md')},'inventory':file_inventory(stage)}
        atomic(stage/'delivery.json',encoded(receipt));verify(stage,allow_synthetic);validate(stage,allow_synthetic)
        replay(stage,trust_frozen_code=True,allow_synthetic=allow_synthetic)
        # Atomic same-filesystem directory rename; refuse concurrent destination reuse.
        check(not out.exists() and not out.is_symlink(),'output','Output appeared during finalization.')
        os.rename(stage,out)
    return {**read(out,allow_synthetic),**({'note_status':note_status} if checkpoint else {})}


def frozen_run(root,allow_synthetic=False):
    """Called by the explicitly trusted copied engine, never by verification."""
    root=Path(root);m,r=validate(root,allow_synthetic)
    check(render(m,r).encode()==regular(root,'report.md').read_bytes(),'report.md','Frozen rendering differs.')
    check(encoded(reading(m,r))==regular(root,'reading.json').read_bytes(),'reading.json','Frozen reading checklist differs.')
    return {'reproduced':True,'report_sha256':sha(regular(root,'report.md').read_bytes()),'network_requests':0}


def replay(root,*,trust_frozen_code=False,allow_synthetic=False):
    check(trust_frozen_code is True,'replay.trust','Replay executes supplied Python: explicitly trust the frozen code. Import isolation is not a hostile-code sandbox.')
    result=verify(root,allow_synthetic);root=Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='solana-trusted-replay-') as directory:
        temp=Path(directory);bundle=temp/'bundle';bundle.mkdir()
        for row in result['receipt']['inventory']:
            raw=regular(root,row['path']).read_bytes();check(sha(raw)==row['sha256'],row['path'],'Source changed before replay copy.');atomic(bundle/row['path'],raw)
        atomic(bundle/'delivery.json',encoded(result['receipt']));verify(bundle,allow_synthetic)
        bootstrap='import sys,json; sys.dont_write_bytecode=True; sys.path.insert(0,sys.argv[1]); from solana_replay import frozen_run; print(json.dumps(frozen_run(sys.argv[2],sys.argv[3]=="yes")))'
        proc=subprocess.run([sys.executable,'-I','-B','-S','-c',bootstrap,str(bundle/'engine/scripts'),str(bundle),'yes' if allow_synthetic else 'no'],
            cwd=temp,env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=60)
        check(proc.returncode==0,'replay','Trusted frozen engine failed: '+proc.stderr.decode(errors='replace')[-3000:])
        output=strict_json(proc.stdout,'replay output');check(output.get('reproduced') is True,'replay','Frozen engine did not reproduce output.')
    return {**output,'trusted_frozen_code_executed':True,'isolation':'clean temporary copy; isolated Python; no inherited paths, site packages or bytecode; not a security sandbox'}
