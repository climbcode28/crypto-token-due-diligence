from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from solana_transactions import decode_transaction,verify_sales
from transaction_fixture import fixture,key


class SaleTests(unittest.TestCase):
    def run_case(self,**kwargs):
        target,a,p,b=fixture(**kwargs);execution=decode_transaction(target,p,b)
        return verify_sales(target,[{'pool':a['pool'],'execution':execution}]),a,p,b,execution

    def test_fee_payer_is_not_seller_and_receipt_count_is_not_market_activity(self):
        r,a,_,_,_=self.run_case(version=0);sale=r['receipts'][0]
        self.assertEqual(sale['status'],'verified_sale');self.assertEqual(sale['seller'],a['owner'])
        self.assertNotEqual(sale['seller'],a['payer']);self.assertEqual(sale['output_atomic'],'500')
        self.assertEqual(r['verified_receipts'],1);self.assertIsNone(r['indexed_activity_count']);self.assertIsNone(sale['profit'])

    def test_wsol_existing_closure_and_ephemeral_creation_refunds_are_not_proceeds(self):
        for created,refund in ((False,'2039280'),(True,'2039280')):
            r,a,_,_,_=self.run_case(wsol=True,closed=True,created=created,tip=100)
            sale=r['receipts'][0];self.assertEqual(sale['status'],'verified_sale',sale)
            net=sale['native_proceeds'];self.assertIsNotNone(net,sale)
            self.assertEqual(net['net_sale_after_seller_network_fee_lamports'],'500')
            self.assertEqual(net['preexisting_and_funded_account_refund_lamports'],refund)
            self.assertEqual(net['other_native_delta_lamports'],'-100')
            self.assertIsNone(sale['profit'])

    def test_wsol_unknown_native_movement_blocks_only_net_proceeds(self):
        _,a,p,b,_=self.run_case(wsol=True,closed=True)
        p['response']['result']['meta']['postBalances'][a['keys'].index(a['owner'])]+=100
        target,_,_,_=fixture(wsol=True,closed=True);r=verify_sales(target,[{'pool':a['pool'],'execution':decode_transaction(target,p,b)}])
        self.assertEqual(r['receipts'][0]['status'],'verified_sale');self.assertIsNone(r['receipts'][0]['native_proceeds'])

    def test_unrelated_swap_deposit_and_wrong_pool_cannot_become_sale(self):
        for kind in ('pool','flow','mint','balance','owner','nested','multihop'):
            target,a,p,b=fixture();e=decode_transaction(target,p,b)
            if kind=='pool':a['pool']=key(80)
            if kind=='flow':e['effects'][1]['participants']['destination']=key(80)
            if kind=='mint':e['effects'][1]['mint']=key(80)
            if kind=='balance':e['post_token_balances'][a['source']]['amount_atomic']='8000'
            if kind=='owner':e['pre_token_balances'][a['destination']]['owner']=key(80)
            if kind=='nested':e['effects'][0]['locator']['inner_index']=1
            if kind=='multihop':e['effects'].append(copy.deepcopy(e['effects'][0]))
            sale=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
            self.assertEqual(sale['status'],'unverified',kind)

    def test_unrelated_transfer_touching_sale_accounts_and_failure_refused(self):
        target,a,p,b=fixture();e=decode_transaction(target,p,b)
        other=copy.deepcopy(e['effects'][1]);other['id']='other';other['locator']={'outer_index':1,'inner_index':None}
        e['effects'].append(other)
        self.assertEqual(verify_sales(target,[{'pool':a['pool'],'execution':e}])['verified_receipts'],0)
        p['response']['result']['meta']['err']='failed'
        self.assertEqual(verify_sales(target,[{'pool':a['pool'],'execution':decode_transaction(target,p,b)}])['verified_receipts'],0)

    def test_sample_cap_and_duplicate_receipts(self):
        target,a,p,b=fixture();c={'pool':a['pool'],'execution':decode_transaction(target,p,b)}
        for candidates in ([c,c],[c,c,c]):
            with self.assertRaises(ValueError):verify_sales(target,candidates)
        self.assertEqual(verify_sales(target,[])['verified_receipts'],0)

    def test_ephemeral_initialization_after_transfer_is_not_valid_custody(self):
        target,a,p,b=fixture(wsol=True,closed=True,created=True);e=decode_transaction(target,p,b)
        init=next(v for v in e['effects'] if v['kind']=='token_account_initialize')
        e['effects'].remove(init);e['effects'].append(init)
        result=verify_sales(target,[{'pool':a['pool'],'execution':e}])
        self.assertEqual(result['verified_receipts'],0)


if __name__=='__main__':unittest.main()
