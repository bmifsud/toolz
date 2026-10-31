import importlib.util
import json
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "perplexity_advisory.py"
spec = importlib.util.spec_from_file_location("perplexity_advisory", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, n):
        return json.dumps({"choices":[{"message":{"content":"Finding: test"}}]}).encode()

class PerplexityTests(unittest.TestCase):
    def test_reject_missing_key(self):
        with self.assertRaises(ValueError):
            module.request("review", "diff", "")
    def test_reject_invalid_mode(self):
        with self.assertRaises(ValueError):
            module.request("other", "diff", "test")
    def test_reject_oversized_input(self):
        with self.assertRaises(ValueError):
            module.request("review", "x" * 30001, "test")
    def test_review_payload(self):
        captured = {}
        def opener(req, timeout):
            captured["req"] = req
            captured["timeout"] = timeout
            return FakeResponse()
        self.assertEqual(module.request("review", "diff", "test-key", opener), "Finding: test")
        payload = json.loads(captured["req"].data)
        self.assertEqual(payload["model"], "sonar")
        self.assertEqual(payload["messages"][1]["content"], "diff")
        self.assertEqual(captured["timeout"], 30)
    def test_docs_mode_disallowed(self):
        with self.assertRaises(ValueError):
            module.request("docs", "source", "test", lambda req, timeout: FakeResponse())

if __name__ == "__main__":
    unittest.main()
