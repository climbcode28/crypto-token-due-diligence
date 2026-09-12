import json,time,threading,copy,base64,io,urllib.error
from solana_fixture import Rpc,response
from pool_fixture import fixture,key,holding
from solana_discovery import MAINNET
from test_solana_web_capture import Response
from adapters.meteora_common import CLOCK
from meteora_fixture import clock


class RichRpc(Rpc):
    values={};pool=None;target=None;largest={}
    @classmethod
    def reset(cls):
        target,a,v=fixture();cls.target=target;cls.pool=a;cls.values=copy.deepcopy(v);cls.values[CLOCK]=clock(timestamp=int(time.time()))
        cls.values[key(7)]=holding(target['mint'],key(8),10000);cls.largest={target['mint']:[key(7)],a['lp']:[a['holder']]}
        cls.calls=[];cls.active=cls.peak=0;cls.mode='normal';cls.stamp=int(time.time());cls.receipt=None;cls.receipts={};Web.token_info=True;return target
    def __call__(self,req):
        cls=type(self)
        with cls.lock:cls.calls.append(copy.deepcopy(req));cls.active+=1;cls.peak=max(cls.peak,cls.active)
        try:
            if cls.mode=='timeout':raise TimeoutError('fixture timeout')
            m,p=req['method'],req['params']
            if m=='getGenesisHash':value=key(3) if cls.mode=='wrong_network' else MAINNET
            elif m in ('getAccountInfo','getMultipleAccounts'):
                keys=p[0] if m=='getMultipleAccounts' else [p[0]];vals=[copy.deepcopy(cls.values.get(k)) for k in keys]
                value={'context':{'slot':100},'value':vals if m=='getMultipleAccounts' else vals[0]}
            elif m=='getEpochInfo':value={'absoluteSlot':100,'blockHeight':80,'epoch':1,'slotIndex':10,'slotsInEpoch':90}
            elif m=='getTokenLargestAccounts':
                if cls.mode=='largest_refused':raise urllib.error.HTTPError('https://synthetic.invalid',429,'limited',{'Retry-After':'10','x-ratelimit-method-limit':'0'},io.BytesIO(b''))
                from solana_accounts import decode_holding,decode_mint
                decimals=decode_mint(cls.values[p[0]])['decimals']
                value={'context':{'slot':100},'value':[{'address':a,'amount':decode_holding(cls.values[a])['amount_atomic'],'decimals':decimals} for a in cls.largest.get(p[0],[])]}
            elif m=='getProgramAccounts':
                mint_key=p[1]['filters'][1]['memcmp']['bytes'];part=p[1].get('dataSlice');rows=[]
                for a in cls.largest.get(mint_key,[]):
                    acct=copy.deepcopy(cls.values[a]);raw=base64.b64decode(acct['data'][0])
                    if part:acct['data']=[base64.b64encode(raw[part['offset']:part['offset']+part['length']]).decode(),'base64']
                    rows.append({'pubkey':a,'account':acct})
                value={'context':{'slot':100},'value':rows}
            elif m=='getBlock':value={'blockhash':key(20),'previousBlockhash':key(21),'parentSlot':p[0]-1,'blockTime':cls.stamp}
            elif m=='getBlockTime':value=cls.stamp
            elif m=='getSignaturesForAddress':
                # Optional extra receipts (signature -> transaction) precede the swap receipt in the recent page.
                rows=[{'signature':sig,'slot':100,'err':None,'memo':None,'blockTime':cls.stamp} for sig in cls.receipts]
                value=rows+([{'signature':cls.receipt['transaction']['signatures'][0],'slot':100,'err':None,'memo':None,'blockTime':cls.stamp}] if cls.receipt else [])
            elif m=='getTransaction':
                value=cls.receipts.get(p[0],cls.receipt)
                if isinstance(value,BaseException):raise value  # One signature's receipt fails at the transport.
                value=copy.deepcopy(value)
            else:value=None
            result=response(req,value);self.local.response_bytes=len(json.dumps(result).encode());return result
        finally:
            with cls.lock:cls.active-=1


class Web:
    calls=[];blocked=False;token_info=True
    def open(self,request,timeout):
        cls=type(self);cls.calls.append(request.full_url);url=request.full_url
        if cls.blocked:return Response(b'Unavailable',403,{'Content-Type':'text/plain'})
        if 'api.dexscreener.com' in url:
            value=[{'chainId':'solana','pairAddress':RichRpc.pool['pool'],'baseToken':{'address':RichRpc.target['mint']},'quoteToken':{'address':key(3)},'dexId':'raydium',
              'liquidity':{'usd':'1000000'},'priceUsd':'2','volume':{'h24':'500000'},'info':{'websites':[{'url':'https://project.example/token'}]}}]
        elif 'geckoterminal' in url and url.endswith('/info'):
            value={'data':{'id':'solana_'+RichRpc.target['mint'],'type':'token','attributes':{'address':RichRpc.target['mint'],'name':'Coin','symbol':'COIN','websites':['https://project.example/'],'twitter_handle':None,'telegram_handle':None,'discord_url':None}}} if cls.token_info else {'data':{}}
        elif 'geckoterminal' in url:value={'data':[]}
        elif 'lite-api.jup.ag' in url:
            from urllib.parse import urlsplit,parse_qsl
            q=dict(parse_qsl(urlsplit(url).query));out=q['outputMint']
            value={'inputMint':q['inputMint'],'outputMint':out,'inAmount':q['amount'],'outAmount':'500','otherAmountThreshold':'497','slippageBps':int(q['slippageBps']),'swapMode':'ExactIn',
                   'priceImpactPct':'0.0012','contextSlot':100,'swapUsdValue':'1.5','routePlan':[{'swapInfo':{'ammKey':RichRpc.pool['pool'],'label':'Raydium','inputMint':q['inputMint'],'outputMint':out,'inAmount':q['amount'],'outAmount':'500','feeAmount':'3','feeMint':q['inputMint']},'percent':100}]}
        else:value={'mint':RichRpc.target['mint'],'claim':'Dated public project description; runtime remains separately verified.'}
        return Response(json.dumps(value).encode())
