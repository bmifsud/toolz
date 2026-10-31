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
    def test_malformed_outer_payload_rejected(self):
        for payload in (None, [], "receipt", 7, True):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "invalid receipt"):
                verify_receipt(payload, expected_request_id="req_12345678",
                               expected_diagnostic="tier1-tests")

    def test_unicode_correlation_values_rejected(self):
        for field in ("request_id", "diagnostic"):
            for value in ("é", "req_\ud800"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.check({**self.payload, field: value})
        # Matching Unicode IDs were never accepted by the ASCII-only comparison.
        with self.assertRaisesRegex(ValueError, "request ID mismatch"):
            self.check({**self.payload, "request_id": "é"}, request_id="é")

    def test_malformed_expected_correlation_rejected(self):
        for value in (None, [], {}, 7, "é"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(request_id=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(diagnostic=value)

    def test_nonzero_exit_codes_preserved(self):
        for code in (-1, 1, 255):
            with self.subTest(code=code):
                self.assertEqual(self.check({**self.payload, "exit_code": code}).exit_code, code)

    def test_utf8_output_limit_is_combined_byte_count(self):
        receipt = {**self.payload, "stdout": "é" * (module.MAX_OUTPUT // 2), "stderr": ""}
        self.assertEqual(self.check(receipt).stdout, receipt["stdout"])
        with self.assertRaisesRegex(ValueError, "output exceeds receipt limit"):
            self.check({**receipt, "stderr": "x"})

    def test_unencodable_output_rejected(self):
        for field in ("stdout", "stderr"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "invalid output"):
                self.check({**self.payload, field: "\ud800"})

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
