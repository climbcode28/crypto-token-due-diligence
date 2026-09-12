import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fixtures import bind
from test_strict_profile import strict
from render_report import render, source_link, artifact_link
from report_replay import freeze_snapshot, verify, replay
from validate_bundle import sha, validate


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.m, self.r = strict(self.root)

    def freeze(self):
        bind(self.root, self.m, self.r)
        validate(self.root, True)
        output = render(self.m, self.r, sha((self.root / "report.json").read_bytes()))
        (self.root / "report.md").write_text(output)
        freeze_snapshot(self.root)
        return output

    def test_frozen_render_survives_installed_version_change(self):
        original = self.freeze()
        with patch("render_report.REPORTING_ENGINE_VERSION", "999.0.0"):
            self.assertNotEqual(render(self.m, self.r, sha((self.root / "report.json").read_bytes())), original)
            self.assertEqual(replay(self.root, True, True)["status"], "reproduced")
        self.assertEqual((self.root / "report.md").read_text(), original)

    def test_default_verification_never_executes_snapshot(self):
        self.freeze()
        with self.assertRaisesRegex(ValueError, "explicitly trust"):
            replay(self.root, allow_synthetic=True)
        with patch("report_replay.subprocess.run", side_effect=AssertionError("must not execute")):
            verify(self.root)

    def test_unlisted_import_shadow_is_not_executed(self):
        self.freeze()
        marker = self.root / "executed"
        (self.root / "reporting-engine/html.py").write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('wrong')\n")
        self.assertEqual(replay(self.root, True, True)["status"], "reproduced")
        self.assertFalse(marker.exists())

    def test_changed_reporting_code_or_report_bytes_rejected(self):
        self.freeze()
        for path in (self.root / "report.md", self.root / "reporting-engine/render_report.py"):
            before = path.read_bytes(); path.write_bytes(before + b"\n")
            with self.assertRaises(ValueError):
                verify(self.root)
            path.write_bytes(before)

    def test_strict_navigation_links_to_evidence_and_local_artifacts(self):
        output = self.freeze()
        self.assertIn("## Coverage by surface", output)
        self.assertIn("[e-code](#evidence-3)", output)
        self.assertIn('<a id="evidence-3"></a>', output)
        self.assertIn("[evidence/e-code.json](<./evidence/e-code.json>)", output)
        self.assertIn("Subject: target", output)

    def test_registered_evidence_is_verified_without_execution(self):
        self.freeze()
        (self.root / "evidence/e-code.json").unlink()
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_document_source_urls_render_through_safe_links(self):
        self.m["evidence"][0]["query"]["source_urls"] = ["https://example.com/source", "javascript:alert(1)"]
        output = render(self.m, self.r, "a" * 64)
        self.assertIn("[source](<https://example.com/source>)", output)
        self.assertNotIn("[source](<javascript:", output)

    def test_urls_and_local_paths_cannot_inject_markdown_or_escape(self):
        for url in ("javascript:alert(1)", "data:text/html,evil", "https://user:pass@example.com", "https://example.com\n![x](evil)", "https://example.com\\@evil.com"):
            self.assertNotIn("](<", source_link(url))
        safe_url = source_link('https://example.com/a)[x](evil)?q=<tag>')
        self.assertIn("%29%5Bx%5D%28evil%29", safe_url)
        self.assertNotIn("<tag>", safe_url)
        for path in ("../outside", "/outside", "a\\..\\outside"):
            self.assertNotIn("](<", artifact_link(path))

    def test_legacy_fixture_replay_preserves_original_renderer(self):
        from fixtures import build
        other = self.root / "legacy"; other.mkdir()
        m, r = build(other)
        output = render(m, r, sha((other / "report.json").read_bytes()))
        (other / "report.md").write_text(output)
        freeze_snapshot(other)
        self.assertEqual(replay(other, True, True)["validation_profile"], "legacy-v1")


if __name__ == "__main__":
    unittest.main()
