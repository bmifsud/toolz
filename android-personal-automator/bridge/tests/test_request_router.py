import json
import unittest
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("request_router", Path(__file__).resolve().parents[1] / "request_router.py")
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
route, audit_event = module.route, module.audit_event

class RouterTests(unittest.TestCase):
    def test_explicit_override(self):
        self.assertEqual(route("@Termux check GitHub branch").destination, "termux")
        self.assertEqual(route("@GitHub check tablet logs").destination, "github")
        self.assertEqual(route("@ChatGPT explain cron").destination, "chatgpt")
    def test_automatic(self):
        self.assertEqual(route("Check my repository workflow").destination, "github")
        self.assertEqual(route("Check cron on my tablet").destination, "termux")
        self.assertEqual(route("Explain encryption").destination, "chatgpt")
    def test_ambiguous(self):
        d = route("Compare GitHub workflow and Termux logs")
        self.assertEqual((d.permission, d.action), ("clarify", "none"))
    def test_mutation_requires_approval(self):
        self.assertEqual(route("@Termux delete backups").permission, "approval_required")
        self.assertEqual(route("@GitHub merge PR").permission, "approval_required")
    def test_tests_are_allowlisted(self):
        d = route("@Termux run pytest")
        self.assertEqual((d.permission, d.action), ("allowlisted_only", "propose_diagnostic"))
    def test_empty_prefix(self):
        self.assertEqual(route("@Termux").permission, "clarify")
        with self.assertRaises(ValueError):
            route(" ")
    def test_redacted_audit(self):
        secret = "secret-token-123"
        record = audit_event("@Termux check " + secret, route("@Termux check"), "req_12345678", datetime(2026, 10, 27, tzinfo=timezone.utc))
        obj = json.loads(record)
        self.assertNotIn(secret, record)
        self.assertEqual(obj["destination"], "termux")
        with self.assertRaises(ValueError):
            audit_event("hello", route("hello"), "../bad")
if __name__ == "__main__":
    unittest.main()
