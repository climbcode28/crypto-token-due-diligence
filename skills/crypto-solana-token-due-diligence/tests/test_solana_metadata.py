from pathlib import Path
import sys,unittest,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from solana_fixture import KEY, account
from metadata_fixture import metadata_account
from solana_metadata import decode_metadata, metadata_address, attribution_leads, PROGRAM
from solana_common import b58encode


def key(n):return b58encode(bytes([n])*32)


class MetadataDecodeTests(unittest.TestCase):
    def test_pda_is_deterministic_and_off_curve(self):
        self.assertEqual(metadata_address(KEY),metadata_address(KEY));self.assertNotEqual(metadata_address(KEY),metadata_address(key(9)))

    def test_valid_account_decodes_fields_and_attribution_leads(self):
        m=metadata_account(KEY,update_authority=key(90),creators=[(key(91),True,60),(key(92),False,40)],name='Stonk',symbol='STONK',uri='https://example.invalid/x.json')
        d=decode_metadata(m['address'],m['account'],KEY)
        self.assertEqual((d['name'],d['symbol'],d['uri'],d['update_authority'],d['seller_fee_basis_points'],d['is_mutable'],d['primary_sale_happened']),('Stonk','STONK','https://example.invalid/x.json',key(90),500,True,False))
        self.assertEqual(d['verified_creators'],[key(91)]);self.assertEqual(d['trailing_bytes'],4);self.assertEqual(d['mint'],KEY)
        self.assertEqual([l['basis'] for l in attribution_leads(d)],['metaplex_update_authority','metaplex_verified_creator'])
        self.assertEqual([l['address'] for l in attribution_leads(d)],[key(90),key(91)])

    def test_wrong_mint_pda_or_owner_is_refused(self):
        m=metadata_account(KEY,update_authority=key(90))
        with self.assertRaisesRegex(ValueError,'PDA'):decode_metadata(m['address'],m['account'],key(9))
        bound=metadata_account(KEY,update_authority=key(90),bound_mint=key(9))
        with self.assertRaisesRegex(ValueError,'mint mismatch'):decode_metadata(bound['address'],bound['account'],KEY)
        with self.assertRaisesRegex(ValueError,'owner'):decode_metadata(m['address'],{**m['account'],'owner':key(1)},KEY)

    def test_truncated_unknown_key_and_bad_shares_are_refused(self):
        m=metadata_account(KEY,update_authority=key(90))
        raw=__import__('base64').b64decode(m['account']['data'][0])[:70]
        with self.assertRaisesRegex(ValueError,'truncated'):decode_metadata(m['address'],{**account(raw),'owner':PROGRAM},KEY)
        other=metadata_account(KEY,update_authority=key(90),key=1)
        with self.assertRaisesRegex(ValueError,'unsupported metadata account key'):decode_metadata(other['address'],other['account'],KEY)
        bad=metadata_account(KEY,update_authority=key(90),creators=[(key(91),True,30)])
        with self.assertRaisesRegex(ValueError,'total 100'):decode_metadata(bad['address'],bad['account'],KEY)

    def test_bounds_tail_and_dedupe(self):
        long=metadata_account(KEY,update_authority=key(90),name='x'*33)
        with self.assertRaisesRegex(ValueError,'exceeds'):decode_metadata(long['address'],long['account'],KEY)
        six=metadata_account(KEY,update_authority=key(90),creators=[(key(91+i),False,100 if i==0 else 0) for i in range(6)])
        with self.assertRaisesRegex(ValueError,'bound'):decode_metadata(six['address'],six['account'],KEY)
        tail=metadata_account(KEY,update_authority=key(90),trailing=bytes([1,7,1,0,1,0,0,0])+bytes(283))
        d=decode_metadata(tail['address'],tail['account'],KEY);self.assertEqual(d['trailing_bytes'],291)
        same=metadata_account(KEY,update_authority=key(91),creators=[(key(91),True,100)])
        self.assertEqual([l['basis'] for l in attribution_leads(decode_metadata(same['address'],same['account'],KEY))],['metaplex_update_authority'])

    def test_platform_update_authority_is_named_and_never_attributed(self):
        platform='TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM'  # pump.fun, read live from two pump.fun tokens on 2026-09-13
        m=metadata_account(KEY,update_authority=platform,creators=[(key(93),True,100)])
        d=decode_metadata(m['address'],m['account'],KEY);self.assertEqual(d['update_authority_platform'],'pump.fun')
        self.assertEqual([(l['address'],l['basis']) for l in attribution_leads(d)],[(key(93),'metaplex_verified_creator')])

    def test_no_creators_and_system_update_authority_yield_no_leads(self):
        m=metadata_account(KEY,update_authority='11111111111111111111111111111111')
        d=decode_metadata(m['address'],m['account'],KEY);self.assertEqual(d['creators'],[]);self.assertEqual(attribution_leads(d),[])


if __name__=='__main__':unittest.main()
