"""Frozen compatibility vectors captured before the v2 implementation."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import solana_bundle as bundle
import solana_legacy_v1 as legacy

FIXTURES = Path(__file__).parent / "fixtures" / "legacy_v1"


class LegacyTests(unittest.TestCase):
    def copy(self, name):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "bundle"
        shutil.copytree(FIXTURES / name, root)
        return root

    def test_frozen_bytes_and_rendering(self):
        inventory = json.loads((FIXTURES / "golden-sha256.json").read_text())
        for name, digest in inventory.items():
            self.assertEqual(legacy.sha((FIXTURES / name).read_bytes()), digest, name)
        for name in ("collection", "independent"):
            with self.subTest(name=name):
                root = FIXTURES / name
                result = bundle.validate(root, True, profile="legacy-v1")
                self.assertEqual(bundle.render(*result, profile="legacy-v1").encode(),
                                 (root / "report.md").read_bytes())
                command = [sys.executable, str(SCRIPTS / "solana_bundle.py"), "validate",
                           str(root), "--profile", "legacy-v1", "--allow-synthetic",
                           "--rendered", str(root / "report.md")]
                completed = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_rejection_vectors(self):
        for case in json.loads((FIXTURES / "rejections.json").read_text()):
            with self.subTest(case=case):
                root = self.copy(case["fixture"])
                mutation = case["mutation"]
                if mutation == "alter_evidence":
                    (root / case["path"]).write_text("{}")
                elif mutation == "missing_evidence":
                    (root / case["path"]).unlink()
                else:
                    manifest = json.loads((root / "manifest.json").read_text())
                    report = json.loads((root / "report.json").read_text())
                    if mutation == "copied_recheck":
                        manifest["evidence"][1]["state"]["block_recheck_evidence_id"] = "block"
                    elif mutation == "wrong_subject":
                        manifest["evidence"][1]["subject"]["mint"] = "1" * 32
                    elif mutation == "unknown_completed":
                        report["status"] = "completed"
                    (root / "manifest.json").write_text(json.dumps(manifest))
                    report["manifest_sha256"] = legacy.sha((root / "manifest.json").read_bytes())
                    (root / "report.json").write_text(json.dumps(report))
                with self.assertRaises((ValueError, OSError)):
                    bundle.validate(root, True, profile="legacy-v1")

    def test_reader_is_standalone_and_insulated_from_current_common(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("solana_bundle.py", "solana_legacy_v1.py"):
                shutil.copy2(SCRIPTS / name, root / name)
            # An installed collector/common upgrade must not affect old interpretations.
            (root / "solana_common.py").write_text('raise RuntimeError("current engine")\n')
            (root / "solana_collect.py").write_text('raise RuntimeError("network import")\n')
            for name in ("collection", "independent"):
                result = subprocess.run([sys.executable, "-E", "-B", str(root / "solana_bundle.py"),
                    "validate", str(FIXTURES / name), "--profile", "legacy-v1", "--allow-synthetic",
                    "--rendered", str(FIXTURES / name / "report.md")], cwd=temporary,
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_profile_dispatch_does_not_promote_or_mutate_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "new"
            with self.assertRaisesRegex(ValueError, "Start a new v2 investigation"):
                bundle.initialize(root, profile="solana-evidence-v2")
            self.assertFalse(root.exists())
        with self.assertRaisesRegex(ValueError, "unknown Solana profile"):
            bundle.validate(FIXTURES / "independent", True, profile="auto")

    def test_template_has_all_surfaces_and_unjudged_ownership(self):
        assets = SCRIPTS.parent / "assets"
        plan = json.loads((assets / "work-plan.template.json").read_text())
        self.assertEqual(set(bundle.DIMENSIONS), {x["dimension"] for x in plan["surfaces"]})
        note = json.loads((assets / "note.template.json").read_text())
        self.assertEqual(note["owner"], "coordinator")
        self.assertIsNone(note["decision"])
        self.assertEqual(note["research_status"], "partial")


if __name__ == "__main__":
    unittest.main()
