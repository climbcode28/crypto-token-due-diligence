import base64
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_accounts import decode_holding, decode_mint, active_transfer_fee, controls
from solana_common import base58_bytes, TOKEN_PROGRAM, TOKEN_2022
from solana_fixture import KEY, OTHER, TARGET, account, request, response
from solana_presets import settings


def tlv(kind, raw):
    return struct.pack("<HH", kind, len(raw))+raw


def holding(quantity=100, *, owner=OTHER, mint=KEY, state=1, program=TOKEN_PROGRAM, extensions=b"", delegate=None, close=None, native=None):
    optional = lambda key: bytes(36) if key is None else b"\1\0\0\0"+base58_bytes(key, 32)
    raw = base58_bytes(mint, 32)+base58_bytes(owner, 32)+quantity.to_bytes(8, "little")+optional(delegate)+bytes([state])
    raw += bytes(12) if native is None else b"\1\0\0\0"+native.to_bytes(8, "little")
    raw += (70 if delegate else 0).to_bytes(8, "little")+optional(close)
    if extensions:
        raw += b"\2"+extensions
    return {**account(raw), "owner": program}


def mint(supply=2**60+17, extensions=b"", program=TOKEN_PROGRAM):
    raw = bytes(36)+supply.to_bytes(8, "little")+b"\11\1"+bytes(36)
    if extensions:
        raw += bytes(83)+b"\1"+extensions
    return {**account(raw), "owner": program}


class AccountTests(unittest.TestCase):
    def test_pinned_integer_fixture(self):
        fixture = json.loads((Path(__file__).parent/"fixtures/token-accounts/integer-and-frozen.json").read_text())
        holding_row, mint_row = decode_holding(fixture["holding"]), decode_mint(fixture["mint"])
        expected = fixture["expected"]
        self.assertEqual(holding_row["amount_atomic"], expected["amount_atomic"])
        self.assertEqual(holding_row["state"], expected["state"])
        self.assertEqual(holding_row["extensions"][0]["withheld_atomic"], expected["withheld_atomic"])
        self.assertEqual(mint_row["supply_atomic"], expected["supply_atomic"])
        self.assertEqual(mint_row["freeze_authority"], expected["freeze_authority"])

    def test_complete_holding_base_and_coption_present_zero(self):
        value = decode_holding(holding(2**60+9, delegate="1"*32, close=KEY, native=0), mint=KEY, token_program=TOKEN_PROGRAM)
        self.assertEqual(value["amount_atomic"], str(2**60+9))
        self.assertEqual(value["delegate"], "1"*32)
        self.assertEqual(value["delegated_amount_atomic"], "70")
        self.assertEqual(value["native_reserve_lamports"], "0")
        self.assertEqual(value["close_authority"], KEY)
        self.assertIsNone(decode_holding(holding())["native_reserve_lamports"])

    def test_wrong_program_mint_layout_and_coption_rejected(self):
        invalid = [holding(mint=OTHER), {**holding(), "owner": KEY}, holding(state=3), {**holding(), "executable": True}]
        raw = bytearray(base64.b64decode(holding()["data"][0]));raw[72] = 2
        invalid.append(account(bytes(raw)))
        for value in invalid:
            with self.assertRaises(ValueError):
                decode_holding(value, mint=KEY, token_program=TOKEN_PROGRAM)

    def test_withheld_memo_cpi_hook_and_confidential_quantities(self):
        data = tlv(2, (55).to_bytes(8, "little"))+tlv(8, b"\1")+tlv(11, b"\1")+tlv(15, b"\0")+tlv(17, bytes([9])*64)
        row = decode_holding(holding(program=TOKEN_2022, extensions=data))
        self.assertTrue(row["extensions_valid"])
        extensions = {r["type"]: r for r in row["extensions"]}
        self.assertEqual(extensions[2]["withheld_atomic"], "55")
        self.assertTrue(extensions[8]["require_incoming_memo"])
        self.assertTrue(extensions[11]["lock_cpi"])
        self.assertFalse(extensions[15]["transferring"])
        self.assertIsNone(extensions[17]["withheld_atomic"])

    def test_invalid_extensions_keep_base_facts_but_prevent_complete_coverage(self):
        variants = [tlv(8, b"\2"), tlv(8, b"\0")*2, tlv(1, bytes(108)), b"\2\0\10\0x"]
        for data in variants:
            row = decode_holding(holding(11, program=TOKEN_2022, extensions=data))
            self.assertEqual(row["amount_atomic"], "11")
            self.assertFalse(row["extensions_valid"])
        row = decode_holding(holding(program=TOKEN_2022, extensions=tlv(60000, b"opaque")))
        self.assertEqual(row["unknown_extensions"], [60000])
        self.assertEqual(len(row["extensions"][0]["sha256"]), 64)

    def test_mint_base_survives_bad_tlv_and_frozen_holdings_survive_revocation(self):
        value = decode_mint(mint(extensions=tlv(26, bytes(32)+b"\2"), program=TOKEN_2022))
        self.assertEqual(value["supply_atomic"], str(2**60+17))
        self.assertIsNone(value["freeze_authority"])
        self.assertFalse(value["extensions_valid"])
        self.assertEqual(decode_holding(holding(state=2))["state"], "frozen")

    def test_wrong_base_type_cannot_masquerade_as_partially_decoded_mint(self):
        valid = mint(extensions=tlv(26, bytes(33)), program=TOKEN_2022)
        raw = bytearray(base64.b64decode(valid["data"][0]))
        variants = [bytes(raw[:165]), bytes(raw[:83])]
        raw[165] = 2
        variants.append(bytes(raw))
        for raw in variants:
            with self.assertRaises(ValueError):
                decode_mint({**account(raw), "owner": TOKEN_2022})

    def test_epoch_selects_current_and_scheduled_fees_without_float_math(self):
        data = bytes(64)+(99).to_bytes(8, "little")+struct.pack("<QQH", 2, 100, 50)+struct.pack("<QQH", 8, 1000, 200)
        value = decode_mint(mint(extensions=tlv(1, data), program=TOKEN_2022))
        self.assertEqual(active_transfer_fee(value, None)["status"], "epoch_unresolved")
        req = request("getEpochInfo", [{"commitment": "finalized"}])
        for epoch, expected, scheduled in ((7, 50, True), (8, 200, False)):
            packet = {"request": req, "status": "ok", "response": response(req, {"absoluteSlot": 50, "blockHeight": 49, "epoch": epoch, "slotIndex": 0, "slotsInEpoch": 10})}
            selected = active_transfer_fee(value, packet, mint_context_slot=52)
            self.assertEqual(selected["current"]["basis_points"], expected)
            self.assertEqual(selected["scheduled"] is not None, scheduled)
            self.assertEqual(active_transfer_fee(value, packet, mint_context_slot=61)["status"], "epoch_scope_unresolved")

    def test_display_pointer_and_permissioned_burn_controls(self):
        data = tlv(18, base58_bytes(KEY, 32)+base58_bytes(OTHER, 32))+tlv(25, bytes(32)+struct.pack("<dqd", 2, 1234, 3))+tlv(28, base58_bytes(KEY, 32))
        value = decode_mint(mint(extensions=data, program=TOKEN_2022))
        extensions = {r["type"]: r for r in value["extensions"]}
        self.assertEqual(extensions[18]["address"], OTHER)
        self.assertFalse(extensions[25]["changes_atomic_supply"])
        self.assertEqual(value["supply_atomic"], str(2**60+17))
        self.assertEqual(extensions[28]["authority"], KEY)

    def test_controls_bind_exact_mint_and_never_close_uninvestigated_paths(self):
        req = request("getAccountInfo", [KEY, settings()], "mint-sample")
        packet = {"request": req, "status": "ok", "response": response(req, {"context": {"slot": 10}, "value": mint()})}
        result = controls(packet, TARGET)
        self.assertEqual(result["evidence"], ["mint-sample"])
        self.assertEqual(result["coverage"], "partial")
        self.assertTrue(all(p["controller_status"] == "absent_in_sample" for p in result["powers"]))
        with self.assertRaises(ValueError):
            controls(packet, {**TARGET, "mint": OTHER})


if __name__ == "__main__":
    unittest.main()
