from pathlib import Path
import sys,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from transaction_fixture import fixture
from solana_transactions import decode_transaction,verify_sales
from solana_launch import creator_activity,reconcile_inventory,history_pages
from pool_fixture import batch,holding,key
from solana_fixture import request,response


class CreatorTests(unittest.TestCase):
    def setup_receipt(self):
        target,a,p,b=fixture();ex=decode_transaction(target,p,b)
        attribution={'mint':target['mint'],'address':a['owner'],'role':'creator','evidence':['creator-role']}
        return target,a,ex,attribution

    def test_attributed_sale_and_transfer_are_separate_from_personal_cashout(self):
        target,a,ex,attribution=self.setup_receipt()
        r=creator_activity(target,[attribution],[ex])['keys'][0]
        self.assertEqual(r['movements'][0]['kind'],'transfer_out');self.assertEqual(r['observed_sale_receipts'],0)
        sales=verify_sales(target,[{'pool':a['pool'],'execution':ex}])
        r=creator_activity(target,[attribution],[ex],sales=sales)['keys'][0]
        self.assertEqual(r['movements'][0]['kind'],'verified_sale_input');self.assertEqual(r['observed_sale_receipts'],1)
        self.assertIsNone(r['personal_cash_out']);self.assertIsNone(r['total_creator_sales']);self.assertIsNone(r['human_identity'])

    def test_missing_attribution_and_duplicate_receipts_rejected(self):
        target,a,ex,attribution=self.setup_receipt()
        with self.assertRaises(ValueError):creator_activity(target,[{**attribution,'evidence':[]}],[ex])
        with self.assertRaises(ValueError):creator_activity(target,[attribution],[ex,ex])
        with self.assertRaises(ValueError):creator_activity(target,[attribution]*3,[ex])

    def test_rebuy_output_and_tampered_sale_never_become_cashout(self):
        from solana_transactions import verify_rebuys
        target,a,ex,attribution=self.setup_receipt()
        sale=verify_sales(target,[{'pool':a['pool'],'execution':ex}]);sale['receipts'][0]['input_atomic']='9999'
        with self.assertRaises(ValueError):creator_activity(target,[attribution],[ex],sales=sale)
        buy_target={**target,'mint':a['output_mint']};ex['target']=buy_target;attribution['mint']=buy_target['mint']
        buys=verify_rebuys(buy_target,[{'pool':a['pool'],'execution':ex}])
        self.assertEqual(buys['verified_receipts'],1)
        r=creator_activity(buy_target,[attribution],[ex],rebuys=buys)['keys'][0]
        self.assertEqual(r['movements'][0]['kind'],'verified_rebuy_output');self.assertEqual(r['observed_sale_receipts'],0)


    def test_failed_history_cannot_be_no_sales_and_fee_operation_has_no_invented_amount(self):
        target,a,ex,attribution=self.setup_receipt();bad=copy.deepcopy(ex);bad['execution_status']='failed'
        r=creator_activity(target,[attribution],[bad])['keys'][0];self.assertIsNone(r['total_creator_sales']);self.assertTrue(r['gaps'])
        ex['effects'].append({'id':'fee','kind':'creator_fee_claim','participants':{'creator':a['owner']},'mint':None,'amount_atomic':None})
        r=creator_activity(target,[attribution],[ex])['keys'][0];self.assertEqual(r['protocol_operations'][0]['kind'],'creator_fee_claim')
        self.assertEqual(r['movements'][0]['amount_atomic'],'1000')

    def inventory(self):
        target,a,ex,_=self.setup_receipt();address=a['source']
        opening=batch({address:holding(target['mint'],a['owner'],10000)},'open',99)
        closing=batch({address:holding(target['mint'],a['owner'],9000)},'close',101)
        req=request('getSignaturesForAddress',[address,{'commitment':'finalized','limit':25}],'history')
        from solana_common import b58encode
        p={'request':req,'status':'ok','response':response(req,[{'signature':ex['signature'],'slot':100,'blockTime':1000,'err':None},
            {'signature':b58encode(bytes([85])*64),'slot':99,'blockTime':999,'err':None}])}
        histories=[history_pages(address,[p],start_slot=99,end_slot=101)]
        return target,a,ex,opening,closing,histories

    def test_conservation_only_with_complete_listed_account_window(self):
        target,a,ex,o,c,h=self.inventory();r=reconcile_inventory(target,a['owner'],o,c,h,[ex])
        self.assertEqual(r['status'],'reconciled',r);self.assertEqual(r['net_flow_atomic'],'-1000');self.assertEqual(r['difference_atomic'],'0')
        for case in ('missing_receipt','history','owner','unrecognized'):
            executions=[copy.deepcopy(ex)];histories=copy.deepcopy(h)
            if case=='missing_receipt':executions=[]
            if case=='history':histories[0]['window_covered']=False
            if case=='owner':executions[0]['pre_token_balances'][a['source']]['owner']=key(99)
            if case=='unrecognized':executions[0]['effect_coverage']='partial'
            r=reconcile_inventory(target,a['owner'],o,c,histories,executions);self.assertEqual(r['status'],'unresolved',case);self.assertTrue(r['gaps'])

    def test_inventory_mismatch_retains_difference_not_false_balance(self):
        target,a,ex,o,c,h=self.inventory();c=batch({a['source']:holding(target['mint'],a['owner'],9500)},'close',101)
        r=reconcile_inventory(target,a['owner'],o,c,h,[ex]);self.assertEqual(r['status'],'mismatch');self.assertEqual(r['difference_atomic'],'500')


if __name__=='__main__':unittest.main()
