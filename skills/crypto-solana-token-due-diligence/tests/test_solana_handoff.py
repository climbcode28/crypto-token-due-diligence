from pathlib import Path
import sys,tempfile,unittest,time,json,os
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from broad_fixture import RichRpc,Web
from solana_broad_collect import start,public_config,collect,status
from solana_session import Session


class HandoffTests(unittest.TestCase):
    def test_public_recovery_ignores_unused_paid_configuration_without_sends(self):
        for endpoint in ('not a URL', 'https://example.com/solana',
                         'https://lb.drpc.org/solana/test-only',
                         'https://lb.drpc.org/?network=solana&dkey=test-only'):
            for provider in ('auto', 'public'):
                with self.subTest(endpoint=endpoint, provider=provider), patch.dict(os.environ,
                     {'DRPC_API_KEY':'test-only', 'SOLANA_DRPC_URL':endpoint}, clear=True), \
                     patch('socket.socket', side_effect=AssertionError('network')):
                    before=dict(os.environ)
                    config=public_config(allow_network=True, cost_policy='free', provider=provider)
                    self.assertEqual((config['provider'], config['url'], config['headers']),
                                     ('public', 'https://api.mainnet-beta.solana.com', {}))
                    self.assertEqual(config['preflight']['network_requests'], 0)
                    self.assertNotIn('test-only', json.dumps(config))
                    self.assertEqual(dict(os.environ), before)
                    with self.assertRaises(ValueError):
                        public_config(allow_network=True, cost_policy='paid', allow_paid=True, provider='drpc')

    def test_explicit_public_recovery_does_not_reuse_drpc_under_public_export(self):
        with patch.dict(os.environ, {'SOLANA_RPC_URL':'https://lb.drpc.org/solana',
             'DRPC_API_KEY':'test-only'}, clear=True), patch('socket.socket', side_effect=AssertionError('network')):
            config=public_config(allow_network=True, cost_policy='free', provider='public')
            self.assertEqual((config['url'], config['headers']), ('https://api.mainnet-beta.solana.com', {}))

    def test_routed_delay_and_preset_do_not_restart_deadlines(self):
        target=RichRpc.reset();Web.blocked=False
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run';received=time.time()-100;deadline=received+600
            r=start(root,target,question='Original routed request',received_at=received,deadline_at=deadline,scope='focused',synthetic=True,
                factory=RichRpc,config={'url':'https://synthetic.invalid','headers':{}})
            s=Session(root)
            try:self.assertAlmostEqual(s.meta['collection_cutoff'],received+480);self.assertAlmostEqual(s.meta['lane_cutoff'],received+300);self.assertAlmostEqual(s.meta['deadline_unix'],deadline)
            finally:s.close()
            before=status(root);collect(root,{'id':'followup','kind':'creator_history','parameters':{'keys':[target['mint']]}},{'url':'https://synthetic.invalid','headers':{}},factory=RichRpc)
            self.assertEqual(before['target_at'],status(root)['target_at']);self.assertEqual(before['deadline_at'],status(root)['deadline_at'])

    def test_public_preflight_is_zero_network_and_ignores_evm_credentials(self):
        with patch.dict(os.environ,{'DRPC_API_KEY':'test-only','ROBINHOOD_DRPC_URL':'https://lb.drpc.org/robinhood','SOLANA_RPC_URL':'https://api.mainnet-beta.solana.com'}),patch('socket.socket',side_effect=AssertionError('network')):
            c=public_config(allow_network=True,cost_policy='free');self.assertEqual(c['headers'],{});self.assertEqual(c['preflight']['network_requests'],0)
        # A dRPC URL without its key falls back to the public root under auto and is refused under drpc.
        with patch.dict(os.environ,{'SOLANA_DRPC_URL':'https://lb.drpc.org/solana'},clear=False),patch('socket.socket',side_effect=AssertionError('network')):
            os.environ.pop('DRPC_API_KEY',None);os.environ.pop('SOLANA_RPC_URL',None);c=public_config(allow_network=True,cost_policy='free')
            self.assertEqual((c['provider'],c['fallback'],c['url'],c['headers']),('public','drpc_key_missing','https://api.mainnet-beta.solana.com',{}))
            with self.assertRaisesRegex(ValueError,'DRPC_API_KEY'):public_config(allow_network=True,cost_policy='paid',allow_paid=True,provider='drpc')
        # With the key but without paid authorization, auto still falls back; with it, dRPC is used with the key in a header.
        with patch.dict(os.environ,{'SOLANA_DRPC_URL':'https://lb.drpc.org/solana','DRPC_API_KEY':'test-only'}),patch('socket.socket',side_effect=AssertionError('network')):
            os.environ.pop('SOLANA_RPC_URL',None);c=public_config(allow_network=True,cost_policy='free');self.assertEqual((c['provider'],c['fallback']),('public','paid_usage_not_authorized'))
            # The key inside the URL (a path segment or dkey) is refused with the fix named; the preflight names it too.
            for shape in ('https://lb.drpc.org/solana/test-only','https://lb.drpc.org/?network=solana&dkey=test-only'):
                with patch.dict(os.environ,{'SOLANA_DRPC_URL':shape}),self.assertRaisesRegex(ValueError,'belongs only in DRPC_API_KEY'):public_config(allow_network=True,cost_policy='paid',allow_paid=True)
                with patch.dict(os.environ,{'SOLANA_RPC_URL':shape}):
                    from solana_transport import provider_availability
                    from types import SimpleNamespace
                    r=provider_availability(SimpleNamespace(provider='auto',rpc_url_env='SOLANA_RPC_URL',auth_env=None,auth_header='Authorization',allow_network=True,cost_policy='paid',allow_paid=True))
                    self.assertEqual((r['status'],r['reason']),('fallback','rpc_url_carries_credential'));self.assertNotIn('test-only',json.dumps(r))
            c=public_config(allow_network=True,cost_policy='paid',allow_paid=True);self.assertEqual((c['provider'],c['fallback'],c['url'],c['headers']),('drpc',None,'https://lb.drpc.org/solana',{'Drpc-Key':'test-only'}))
            c=public_config(allow_network=True,cost_policy='paid',allow_paid=True,provider='public');self.assertEqual((c['provider'],c['url']),('public','https://api.mainnet-beta.solana.com'))
        with patch.dict(os.environ,{'DRPC_API_KEY':'test-only'}),patch('socket.socket',side_effect=AssertionError('network')):
            os.environ.pop('SOLANA_RPC_URL',None);os.environ.pop('SOLANA_DRPC_URL',None);c=public_config(allow_network=True,cost_policy='paid',allow_paid=True);self.assertEqual((c['provider'],c['url']),('drpc','https://lb.drpc.org/solana'))  # the default dRPC network URL
            c=public_config(allow_network=True,cost_policy='free');self.assertEqual((c['provider'],c['fallback']),('public',None))  # a key alone (the EVM skill's) under free is not a fallback worth diagnosing
            with patch.dict(os.environ,{'SOLANA_DRPC_URL':'https://example.com/solana'}),self.assertRaisesRegex(ValueError,'not a dRPC URL'):public_config(allow_network=True,cost_policy='paid',allow_paid=True)
            with patch.dict(os.environ,{'SOLANA_RPC_URL':'https://lb.drpc.org/solana'}):  # a dRPC URL under the public name still selects dRPC
                c=public_config(allow_network=True,cost_policy='paid',allow_paid=True);self.assertEqual((c['provider'],c['url']),('drpc','https://lb.drpc.org/solana'))
        with self.assertRaises(ValueError):public_config(allow_network=False,cost_policy='free')

    def test_expired_start_does_not_create_new_run_or_grants(self):
        target=RichRpc.reset()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run'
            with self.assertRaises(ValueError):start(root,target,question='late',received_at=time.time()-700,deadline_at=time.time()-100,synthetic=True,factory=RichRpc,config={'url':'https://synthetic.invalid','headers':{}})
            self.assertFalse(root.exists())

if __name__=='__main__':unittest.main()
