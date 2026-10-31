import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location("routing_receipts", Path(__file__).resolve().parents[1] / "routing_receipts.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
verify_receipt = module.verify_receipt

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.payload = dict(request_id="req_12345678", diagnostic="tier1-tests",
                            exit_code=0, stdout="12 passed", stderr="")
    def check(self, payload=None, **kwargs):
        return verify_receipt(payload if payload is not None else self.payload,
                              expected_request_id=kwargs.get("request_id", "req_12345678"),
                              expected_diagnostic=kwargs.get("diagnostic", "tier1-tests"))
    def test_valid(self):
        self.assertEqual(self.check().exit_code, 0)
        self.assertEqual(len(self.check().output_sha256), 64)
    def test_request_mismatch(self):
        with self.assertRaises(ValueError):
            self.check(request_id="req_different")
    def test_diagnostic_mismatch(self):
        with self.assertRaises(ValueError):
            self.check(diagnostic="git-branch")
    def test_unknown_diagnostic(self):
        with self.assertRaises(ValueError):
            self.check(diagnostic="shell")
    def test_invalid_code(self):
        with self.assertRaises(ValueError):
            self.check({**self.payload, "exit_code": True})
    def test_oversized_output(self):
        with self.assertRaises(ValueError):
            self.check({**self.payload, "stdout": "x" * 16385})
    def test_invalid_output(self):
        with self.assertRaises(ValueError):
            self.check({**self.payload, "stderr": None})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            self.check("invalid")
    def test_invalid_code_boundaries(self):
        for code in ("0", 256, -2, None):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.check({**self.payload, "exit_code": code})
    def test_missing_request_id(self):
        with self.assertRaises(ValueError):
            self.check({k: v for k, v in self.payload.items() if k != "request_id"})
    def test_utf8_byte_limit(self):
        with self.assertRaises(ValueError):
            self.check({**self.payload, "stdout": "é" * 8193})
    def test_digest_changes_with_output(self):
        first = self.check().output_sha256
        second = self.check({**self.payload, "stdout": "13 passed"}).output_sha256
        self.assertNotEqual(first, second)

if __name__ == "__main__":
    unittest.main()
