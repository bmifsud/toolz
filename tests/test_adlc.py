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
