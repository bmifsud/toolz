"""Negative cases prove the consistency gate detects broken records and links."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("check_adlc", Path(__file__).resolve().parents[1] / "scripts/check_adlc.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class GateTests(unittest.TestCase):
    def test_missing_required_files(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any("missing AGENTS.md" in e for e in gate.check(Path(d))))

    def test_links_and_incomplete_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in gate.REQUIRED:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("")
            (root / "README.md").write_text("[ok](AGENTS.md) [bad](absent.md) [escape](../outside.md) [web](https://example.org)\n```\n[example](fake.md)\n```")
            change = root / "docs/adlc/changes/example"
            change.mkdir(parents=True)
            (change / "intent.md").write_text("intent")
            errors = gate.check(root)
            self.assertEqual(len(errors), 3, errors)
            (root / "README.md").write_text("[ok](AGENTS.md#heading)")
            (change / "evidence.md").write_text("evidence")
            self.assertEqual(gate.check(root), [])


    def test_each_required_support_file_is_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in gate.REQUIRED:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            self.assertEqual(gate.check(root), [])
            for name in gate.REQUIRED:
                with self.subTest(name=name):
                    path = root / name
                    path.unlink()
                    self.assertIn(f"missing {name}", gate.check(root))
                    path.write_text("fixture")

    def test_empty_records_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            change = root / "docs/adlc/changes/empty"
            change.mkdir(parents=True)
            for content in ("", " \n", "<!-- pending -->", "<!-- TODO", "```\nexample\n```"):
                for name in gate.CHANGE_FILES:
                    (change / name).write_text(content)
                errors = gate.check(root)
                for name in gate.CHANGE_FILES:
                    self.assertIn(f"empty: empty {name}", errors)

    def test_encoded_escape_and_symlink_links_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            root.mkdir()
            outside = Path(d) / "outside.md"
            outside.write_text("outside")
            (root / "alias.md").symlink_to(outside)
            (root / "README.md").write_text(
                "[escape](%2e%2e/outside.md) [alias](alias.md)")
            errors = gate.check(root)
            self.assertEqual(sum("invalid local link" in e for e in errors), 2)

    def test_visible_text_before_unclosed_comment_remains_content(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "record.md"
            path.write_text("Verified outcome.<!-- unfinished")
            self.assertTrue(gate._markdown_has_content(path))
