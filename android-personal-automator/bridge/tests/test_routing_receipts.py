import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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

class ReceiptBoundaryTests(unittest.TestCase):
    setUp = ReceiptTests.setUp
    check = ReceiptTests.check

    def test_every_planned_diagnostic_has_receipt_support(self):
        from routing_adapter import HOST_DIAGNOSTICS, DEBIAN_DIAGNOSTICS
        self.assertEqual(module.VALID_DIAGNOSTICS, HOST_DIAGNOSTICS | DEBIAN_DIAGNOSTICS)
        for diagnostic in module.VALID_DIAGNOSTICS:
            with self.subTest(diagnostic=diagnostic):
                payload = {**self.payload, "diagnostic": diagnostic}
                self.assertEqual(self.check(payload, diagnostic=diagnostic).diagnostic, diagnostic)

    def test_invalid_correlation_inputs(self):
        for value in ("é" * 8, "x" * 65, "../bad", None, []):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.check({**self.payload, "request_id": value})
                with self.assertRaises(ValueError):
                    self.check(request_id=value)
                with self.assertRaises(ValueError):
                    self.check({**self.payload, "diagnostic": value})
                with self.assertRaises(ValueError):
                    self.check(diagnostic=value)

    def test_combined_utf8_byte_boundary(self):
        payload = {**self.payload, "stdout": "é" * 8191, "stderr": "ab"}
        self.assertEqual(self.check(payload).stderr, "ab")
        with self.assertRaises(ValueError):
            self.check({**payload, "stderr": "abc"})

    def test_unpaired_surrogate_rejected(self):
        for field in ("stdout", "stderr"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check({**self.payload, field: chr(0xD800)})

if __name__ == "__main__":
    unittest.main()
