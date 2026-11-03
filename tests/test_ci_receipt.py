"""Receipts must reject invalid provenance and never promote live acceptance."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("ci_receipt", Path(__file__).resolve().parents[1] / "scripts/ci_receipt.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReceiptTests(unittest.TestCase):
    def test_failed_gate_stays_failed(self):
        data = module.receipt("a" * 40, "failure", "123", "2", "pull_request")
        self.assertEqual(data["offline_gate_outcome"], "failure")
        self.assertEqual(data["tested_commit"], "a" * 40)
        self.assertEqual(data["device_and_live_backup_acceptance"], "unverified")

    def test_invalid_provenance_rejected(self):
        for args in [("main", "success", "1", "1", "push"),
                     ("a" * 40, "passed", "1", "1", "push"),
                     ("a" * 40, "success", "../1", "1", "push")]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                module.receipt(*args)

    def test_bounded_metadata(self):
        for run_id, attempt, event in [("0", "1", "push"),
                                       ("1", "0", "push"),
                                       ("١", "1", "push"),
                                       ("1", "²", "push"),
                                       ("1", "1", "arbitrary-private-text"),
                                       ("1", "1", "pull_request_target")]:
            with self.subTest(event=event, run_id=run_id, attempt=attempt):
                with self.assertRaises(ValueError):
                    module.receipt("a" * 40, "success", run_id, attempt, event)

    def test_all_outcomes_remain_offline_only(self):
        for event in ("pull_request", "push"):
            for outcome in ("success", "failure", "cancelled", "skipped"):
                data = module.receipt("b" * 40, outcome, "1", "1", event)
                self.assertEqual(data["offline_gate_outcome"], outcome)
                self.assertEqual(data["device_and_live_backup_acceptance"], "unverified")
