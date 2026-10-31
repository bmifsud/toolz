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

if __name__ == "__main__":
    unittest.main()
