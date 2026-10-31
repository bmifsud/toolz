import importlib.util
import json
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "gemini_docs_advisory.py"
spec = importlib.util.spec_from_file_location("gemini_docs_advisory", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FakeResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, n):
        return self.data

class GeminiDocsTests(unittest.TestCase):
    def test_missing_key(self):
        with self.assertRaises(ValueError):
            module.generate("source", "")
    def test_empty_input(self):
        with self.assertRaises(ValueError):
            module.generate("", "key")
    def test_oversize(self):
        with self.assertRaises(ValueError):
            module.generate("x" * 30001, "key")
    def test_request_and_response(self):
        seen = {}
        def opener(req, timeout):
            seen["req"] = req
            seen["timeout"] = timeout
            return FakeResponse(json.dumps({"candidates":[{"content":{"parts":[{"text":"# Docs"}]}}]}).encode())
        self.assertEqual(module.generate("source", "test-key", opener), "# Docs")
        self.assertEqual(seen["timeout"], 30)
        self.assertEqual(json.loads(seen["req"].data)["contents"][0]["parts"][0]["text"], "source")
        self.assertEqual(seen["req"].get_header("X-goog-api-key"), "test-key")
    def test_oversized_response(self):
        with self.assertRaises(ValueError):
            module.generate("source", "key", lambda req, timeout: FakeResponse(b"x" * 16001))
    def test_missing_text(self):
        with self.assertRaises(ValueError):
            module.generate("source", "key", lambda req, timeout: FakeResponse(b'{"candidates":[{"content":{"parts":[]}}]}'))

if __name__ == "__main__":
    unittest.main()
