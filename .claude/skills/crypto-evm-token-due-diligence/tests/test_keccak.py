"""Keccak-256 vectors and the derived selector/topic/pool-id helpers."""
import hashlib
import unittest

from evm_decode import calldata
from keccak import canonical_signature, keccak256, keccak256_hex, pool_id, selector, topic


class KeccakTests(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(keccak256(b"").hex(), "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470")
        self.assertEqual(keccak256(b"abc").hex(), "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45")
        self.assertEqual(keccak256(b"The quick brown fox jumps over the lazy dog").hex(),
                         "4d741b6f1eb29cb2a9b9911c82f56fa8d73b04959d3d9d222895df6c0b28aa15")
        self.assertNotEqual(keccak256(b"abc").hex(), hashlib.sha3_256(b"abc").hexdigest(), "Keccak padding differs from SHA3")

    def test_multi_block_permutation_matches_sha3_sponge(self):
        import keccak as module
        for length in (0, 1, 135, 136, 137, 271, 272, 273, 1000):
            data = bytes([0x11]) * length
            padded = bytearray(data) + b"\x06"
            while len(padded) % 136:
                padded.append(0)
            padded[-1] |= 0x80
            state = [0] * 25
            for offset in range(0, len(padded), 136):
                block = padded[offset:offset + 136]
                for i in range(17):
                    state[i] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
                state = module._keccak_f(state)
            digest = b"".join(lane.to_bytes(8, "little") for lane in state[:4])[:32]
            self.assertEqual(digest, hashlib.sha3_256(data).digest(), length)

    def test_selectors_and_topics_from_verified_signatures(self):
        for signature, expected in (("transfer(address,uint256)", "a9059cbb"), ("balanceOf(address)", "70a08231"),
                                    ("slot0()", "3850c7bd"), ("positions(uint256)", "99fbab88"),
                                    ("getSlot0(bytes32)", "c815641c"), ("isApprovedForAll(address,address)", "e985e9c5"),
                                    ("quoteExactInputSingle((address,address,uint256,uint24,uint160))", "c6a5026a")):
            self.assertEqual(selector(signature), expected, signature)
        self.assertEqual(topic("Transfer(address,address,uint256)"),
                         "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
        for bad in ("owner( )", "owner(", "(bad)()", "x()y", "a(b))", 12):
            with self.assertRaises(ValueError):
                canonical_signature(bad)

    def test_v4_pool_id_reproduces_discovered_pool(self):
        # Key observed for the PONS/USDG v4 pool in verified evidence: fee 3000, tick spacing 60, no hooks.
        self.assertEqual(pool_id("0x39dbed3a2bd333467115de45665cc57f813c4571", "0x5fc5360d0400a0fd4f2af552add042d716f1d168",
                                 3000, 60, "0x0000000000000000000000000000000000000000"),
                         "0x4be9657ec9002e528f4f17a5c43edc525a07f888f7b180c2afbf75e096c4f38a")
        self.assertNotEqual(pool_id("0x39dbed3a2bd333467115de45665cc57f813c4571", "0x5fc5360d0400a0fd4f2af552add042d716f1d168",
                                    100, 1, "0x0000000000000000000000000000000000000000"),
                            "0x4be9657ec9002e528f4f17a5c43edc525a07f888f7b180c2afbf75e096c4f38a")
        with self.assertRaises(ValueError):
            pool_id("0x1234", "0x" + "0" * 40, 3000, 60, "0x" + "0" * 40)
        with self.assertRaises(ValueError):
            pool_id("0x" + "1" * 40, "0x" + "2" * 40, 2 ** 24, 60, "0x" + "0" * 40)

    def test_calldata_derivation_is_explicit(self):
        with self.assertRaises(ValueError):
            calldata("launchFactory()")
        self.assertEqual(calldata("launchFactory()", derive=True), "0x" + selector("launchFactory()"))
        self.assertEqual(calldata("ownerOf(uint256)", [7], derive=True), "0x6352211e" + format(7, "064x"))
        self.assertEqual(keccak256_hex(b"")[:10], "0xc5d24601")


if __name__ == "__main__":
    unittest.main()
