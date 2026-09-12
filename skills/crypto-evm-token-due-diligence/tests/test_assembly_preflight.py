"""Catch report plumbing faults early without inventing evidence or completion."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from bundle_assemble import intake, preflight, resolve_evidence, save_draft
from test_strict_profile import strict
from validate_bundle import Invalid


class AssemblyPreflightTests(unittest.TestCase):
    def test_alias_resolution_is_exact_and_ambiguous_instances_stay_explicit(self):
        a, b = '0x' + 'a' * 40, '0x' + 'b' * 40
        rows = [{'id': 'import1-main', 'address': a, 'pin_id': 'pin1',
                 'collection_provenance': {'evidence_id': 'nft-positions'}},
                {'id': 'import1-side', 'address': b, 'pin_id': 'pin1',
                 'collection_provenance': {'evidence_id': 'side-nft-positions'}}]
        d = {'evidence': rows}
        self.assertEqual(resolve_evidence(d, 'nft-positions')['id'], 'import1-main')
        self.assertEqual(resolve_evidence(d, 'import1-side')['address'], b)
        rows.append({**rows[0], 'id': 'import2-main', 'pin_id': 'pin2'})
        with self.assertRaisesRegex(Invalid, 'exactly once'):
            resolve_evidence(d, 'nft-positions')
        self.assertEqual(resolve_evidence(d, 'nft-positions', a, 'pin2')['id'], 'import2-main')
        with self.assertRaises(Invalid):
            resolve_evidence(d, 'positions')

    def draft(self, root):
        m, r = strict(root)
        directory = root / 'draft'
        d = intake(directory, r['target'], 'Synthetic preflight', 'Declared synthetic scope', True)
        shutil.copytree(root / 'evidence', directory / 'evidence')
        d.update(evidence=m['evidence'], pins=m['chains'][0]['pins'], scope=m['scope'],
                 findings=r['findings'], coverage_records=r['coverage_records'])
        save_draft(directory, d)
        return directory, d

    def test_multiple_faults_return_together_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, d = self.draft(Path(temp))
            d['scope'][0]['provenance'] = ['missing-provenance']
            d['scope'][0]['runtime'] = {'status': 'unavailable', 'reason': 'Synthetic gap', 'evidence_ids': []}
            d['findings'][0]['evidence_ids'] = ['missing-finding-evidence']
            d['coverage_records'][0].update(status='partial', outcome='')
            save_draft(directory, d)
            before = {str(p): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
            result = preflight(directory)
            self.assertGreaterEqual(len(result['errors']), 4)
            self.assertFalse(result['final_delivery_eligible'])
            self.assertEqual(before, {str(p): p.read_bytes() for p in directory.rglob('*') if p.is_file()})
            cli = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/bundle_assemble.py'),
                                  'check', str(directory)], capture_output=True, text=True)
            self.assertEqual(cli.returncode, 2)
            self.assertEqual(json.loads(cli.stdout), result)
            self.assertEqual(before, {str(p): p.read_bytes() for p in directory.rglob('*') if p.is_file()})

    def test_clean_partial_draft_is_not_claimed_complete_and_hash_tampering_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, d = self.draft(Path(temp))
            result = preflight(directory)
            self.assertEqual(result['errors'], [])
            self.assertFalse(result['final_delivery_eligible'])
            artifact = directory / d['evidence'][0]['artifact']
            artifact.write_bytes(artifact.read_bytes() + b' ')
            self.assertTrue(any('hash mismatch' in e for e in preflight(directory)['errors']))


if __name__ == '__main__':
    unittest.main()
