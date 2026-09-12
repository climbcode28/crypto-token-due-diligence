from pathlib import Path
import sys,tempfile,unittest,time,json,os
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from broad_fixture import RichRpc,Web
from solana_broad_collect import start,public_config,collect,status
from solana_session import Session


class HandoffTests(unittest.TestCase):
    def test_routed_delay_and_preset_do_not_restart_deadlines(self):
        target=RichRpc.reset();Web.blocked=False
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run';received=time.time()-100;deadline=received+600
            r=start(root,target,question='Original routed request',received_at=received,deadline_at=deadline,scope='focused',synthetic=True,
                factory=RichRpc,config={'url':'https://synthetic.invalid','headers':{}})
            s=Session(root)
            try:self.assertAlmostEqual(s.meta['collection_cutoff'],received+480);self.assertAlmostEqual(s.meta['lane_cutoff'],received+240);self.assertAlmostEqual(s.meta['deadline_unix'],deadline)
            finally:s.close()
            before=status(root);collect(root,{'id':'followup','kind':'creator_history','parameters':{'keys':[target['mint']]}},{'url':'https://synthetic.invalid','headers':{}},factory=RichRpc)
            self.assertEqual(before['target_at'],status(root)['target_at']);self.assertEqual(before['deadline_at'],status(root)['deadline_at'])

    def test_public_preflight_is_zero_network_and_ignores_evm_credentials(self):
        with patch.dict(os.environ,{'DRPC_API_KEY':'test-only','CRYPTO_RPC_URL':'https://lb.drpc.org/robinhood','SOLANA_RPC_URL':'https://api.mainnet-beta.solana.com'}),patch('socket.socket',side_effect=AssertionError('network')):
            c=public_config(allow_network=True,cost_policy='free');self.assertEqual(c['headers'],{});self.assertEqual(c['preflight']['network_requests'],0)
        with patch.dict(os.environ,{'SOLANA_RPC_URL':'https://lb.drpc.org/solana'}),self.assertRaisesRegex(ValueError,'deferred'):public_config(allow_network=True,cost_policy='free')
        with self.assertRaises(ValueError):public_config(allow_network=False,cost_policy='free')

    def test_expired_start_does_not_create_new_run_or_grants(self):
        target=RichRpc.reset()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run'
            with self.assertRaises(ValueError):start(root,target,question='late',received_at=time.time()-700,deadline_at=time.time()-100,synthetic=True,factory=RichRpc,config={'url':'https://synthetic.invalid','headers':{}})
            self.assertFalse(root.exists())

if __name__=='__main__':unittest.main()
