#!/usr/bin/env python3
"""Measured synthetic scheduler comparison with identical wire demands and bytes."""
import argparse,contextlib,copy,io,json,platform,random,statistics,sys,tempfile,threading,time,urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from broad_fixture import RichRpc,Web
from meteora_fixture import clock
from adapters.meteora_common import CLOCK
from solana_broad_collect import start
from solana_profile import validate,Evidence
from solana_session import Session
from solana_facts import encoded,atomic
from solana_common import sha


class Meter:
    def __init__(self,profile,jitter,scale=1):
        self.profile,self.jitter,self.scale=profile,jitter,scale;self.lock=threading.Lock();self.active={'rpc':0,'http':0};self.peak=dict(self.active);self.trace=[];self.wire_seconds=0
    def begin(self,kind,key):
        with self.lock:self.active[kind]+=1;self.peak[kind]=max(self.peak[kind],self.active[kind])
        base=(.6 if kind=='rpc' else 1.2) if self.profile=='slow' else (.25 if kind=='rpc' else .5)
        delay=max(0,base+self.jitter.get(kind+':'+key,0))*self.scale
        time.sleep(delay);return delay
    def end(self,kind,item,delay):
        with self.lock:self.active[kind]-=1;self.trace.append({'kind':kind,**item});self.wire_seconds+=delay


METER=None
class TimedRpc(RichRpc):
    def __call__(self,req):
        delay=METER.begin('rpc',req['id']);result=None;failure=None
        try:
            if req['id']=='baseline_mint_0' and METER.profile in ('429','timeout'):
                failure=METER.profile
                if failure=='429':raise urllib.error.HTTPError('https://synthetic.invalid',429,'fixture',{},io.BytesIO(b''))
                raise TimeoutError('controlled fixture timeout')
            result=super().__call__(req);return result
        finally:METER.end('rpc',{'request':req,'response':result,'failure':failure},delay)


class TimedWeb(Web):
    def open(self,request,timeout):
        delay=METER.begin('http',request.full_url);result=None
        try:result=super().open(request,timeout);return result
        finally:METER.end('http',{'url':request.full_url,'status':result.status if result else None,'body_sha256':sha(result.getvalue()) if result else None},delay)


def one(mode,profile,jitter,stamp,scale=1):
    global METER
    target=RichRpc.reset();RichRpc.stamp=stamp;RichRpc.values[CLOCK]=clock(timestamp=stamp)
    TimedRpc.stamp=stamp;TimedRpc.values=RichRpc.values;TimedRpc.calls=[];TimedRpc.active=TimedRpc.peak=0
    Web.blocked=False;TimedWeb.blocked=False;Web.calls=[];METER=Meter(profile,jitter,scale)
    with tempfile.TemporaryDirectory(prefix='solana-benchmark-') as directory,contextlib.ExitStack() as stack:
        root=Path(directory)/'run'
        if mode=='sequential':
            for module in ('solana_broad_collect','solana_collect_v2','solana_web_capture'):
                stack.enter_context(patch(module+'.ThreadPoolExecutor',lambda max_workers:ThreadPoolExecutor(max_workers=1)))
        received=time.time();cpu=time.process_time();wall=time.perf_counter()
        result=start(root,target,question='Synthetic scheduler acceptance: verify controls, custody and exit depth.',received_at=received,deadline_at=received+600,
            synthetic=True,config={'url':'https://synthetic.invalid','headers':{}},factory=TimedRpc,opener_factory=TimedWeb)
        helper_seconds=time.perf_counter()-wall;cpu_seconds=time.process_time()-cpu
        m,r=validate(root/'draft',True);e=Evidence(root/'draft',m,True)
        session=Session(root)
        try:status=session.status();attempts=session.observations()
        finally:session.close()
        critical=[s for s in m['samples'] if s['critical']];fresh=[s for s in m['samples'] if s['recheck_of']]
        trace=sorted(METER.trace,key=lambda item:encoded(item))
        semantic=sha(encoded(trace));names=[x['kind']+':'+(x['request']['id'] if x['kind']=='rpc' else x['url']) for x in trace]
        return {'scheduler':mode,'profile':profile,'helper_elapsed_seconds':round(helper_seconds,6),'helper_cpu_seconds':round(cpu_seconds,6),
            'injected_wire_seconds_sum':round(METER.wire_seconds,6),'rpc_attempts':sum(a['transport_kind']=='rpc' for a in attempts),
            'http_attempts':sum(a['transport_kind']=='web' for a in attempts),'attempts_started':status['started_attempts'],
            'attempts_completed':sum(a['completed_at'] is not None for a in attempts),'account_reads':sum(a['accounts'] for a in attempts),
            'response_bytes':status['response_bytes'],'peak_wire_concurrency':METER.peak,'critical_initial_reads':len(critical),
            'critical_rechecks':len(fresh),'critical_usable':sum(s['observation_id'] in e.usable for s in critical),
            'report_valid':True,'research_status':r['research_status'],'diagnostics':result['diagnostics'],
            'logical_wire_sha256':semantic,'manifest_sha256':sha((root/'draft/manifest.json').read_bytes()),'names':names}


def benchmark(runs=7,scale=1,progress=None):
    assert runs>=1 and 0<=scale<=1
    stamp=int(time.time());warmup=one('scheduled','responsive',{},stamp,0)
    generator=random.Random(0);jitter={key:generator.uniform(-.05,.05) for key in sorted(set(warmup['names'])|{'rpc:baseline_mint_1'})}
    results=[];equal=True
    for profile,count in [('responsive',runs),('slow',1),('429',1),('timeout',1)]:
        for n in range(count):
            pair=[]
            for mode in ('sequential','scheduled'):
                row=one(mode,profile,jitter,stamp,scale);row['repetition']=n+1;row.pop('names');results.append(row);pair.append(row)
                if progress:progress({'profile':profile,'repetition':n+1,'scheduler':mode,'elapsed_seconds':row['helper_elapsed_seconds']})
            keys=('logical_wire_sha256','rpc_attempts','http_attempts','account_reads','response_bytes','critical_initial_reads','critical_rechecks','critical_usable','report_valid')
            assert all(pair[0][k]==pair[1][k] for k in keys),('Unequal evidence demand',pair)
            assert all(r['attempts_started']==r['attempts_completed'] and r['attempts_started']<=120 and r['critical_initial_reads']==r['critical_rechecks']==r['critical_usable'] for r in pair)
    responsive=[r for r in results if r['profile']=='responsive'];seq=statistics.median(r['helper_elapsed_seconds'] for r in responsive if r['scheduler']=='sequential');new=statistics.median(r['helper_elapsed_seconds'] for r in responsive if r['scheduler']=='scheduled')
    return {'schema_version':1,'measurement':'Measured offline synthetic helper wall/CPU time with injected sleep latency; not model or live provider latency.',
        'fixture_epoch':stamp,'runs':runs,'seed':0,'latency_scale':scale,'responsive_rpc_ms':250,'responsive_http_ms':500,'jitter_ms':50,
        'slow_rpc_ms':600,'slow_http_ms':1200,'failure_profile':'First baseline mint attempt returns HTTP 429 or timeout; bounded second attempt succeeds.',
        'comparison':'Same maintained start and logical evidence; reference sets only executor concurrency to one. Complete requests, response values, slots, headers and HTTP body hashes are compared without dropping semantics. Actual capture timestamps remain in each validated manifest hash.',
        'fixture_sources':{p.name:sha(p.read_bytes()) for p in [Path(__file__),Path(__file__).with_name('broad_fixture.py'),Path(__file__).with_name('pool_fixture.py')]},
        'engine_sources':{str(p.relative_to(Path(__file__).resolve().parents[1])):sha(p.read_bytes()) for p in sorted((Path(__file__).resolve().parents[1]/'scripts').rglob('*.py'))},
        'release_sha256':sha((Path(__file__).resolve().parents[1]/'assets/release.json').read_bytes()),
        'host':platform.platform(),'python':sys.version,'results':results,'equivalent_evidence':equal,
        'responsive_sequential_median_seconds':seq,'responsive_scheduled_median_seconds':new,'responsive_speedup':seq/new,
        'scheduled_automatic_facts_within_90_seconds':all(r['helper_elapsed_seconds']<=90 for r in responsive if r['scheduler']=='scheduled'),
        'live_performance_proven':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=int,default=7);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert a.runs==7,'Acceptance requires seven responsive repetitions.'
    result=benchmark(a.runs,progress=lambda r:print(json.dumps(r),flush=True));atomic(a.out,encoded(result));print(json.dumps({k:v for k,v in result.items() if k not in ('results','fixture_sources','engine_sources')}))
if __name__=='__main__':main()
