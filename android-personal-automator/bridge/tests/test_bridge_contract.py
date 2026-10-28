"""Offline integration contract tests: route -> plan -> executor -> receipt.

Mocks controller subprocess; never asserts a live tablet connection.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj

router = load("request_router")
adapter = load("routing_adapter")
executor = load("bounded_executor")
receipts = load("routing_receipts")

class BridgeContractTests(unittest.TestCase):
    def test_authenticated_roundtrip_contract(self):
        decision = router.route("@Termux: check branch")
        plan = adapter.plan_execution(decision, "git-branch", bridge_authenticated=True)
        self.assertEqual(plan.status, "ready_for_executor")
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "test-token", "BRIDGE_WS_URL": "wss://example.org"}, clear=True):
            with patch.object(executor.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"main\n", b"")):
                result = executor.execute(plan.operation, controller_path="/tmp/controller.py")
        receipt = receipts.verify_receipt({
            "request_id": "req_12345678", "diagnostic": result.diagnostic,
            "exit_code": result.exit_code, "stdout": result.stdout, "stderr": result.stderr
        }, expected_request_id="req_12345678", expected_diagnostic="git-branch")
        self.assertEqual((receipt.exit_code, receipt.stdout), (0, "main\n"))

    def test_disconnected_bridge_cannot_proceed(self):
        decision = router.route("@Termux: check branch")
        plan = adapter.plan_execution(decision, "git-branch", bridge_authenticated=False)
        self.assertNotEqual(plan.status, "ready_for_executor")
        self.assertIsNone(plan.operation)

    def test_mutation_denied_even_when_approved(self):
        decision = router.route("@Termux: delete local backup")
        plan = adapter.plan_execution(decision, "git-branch", bridge_authenticated=True, user_approved=True)
        self.assertEqual(plan.status, "denied")
        self.assertIsNone(plan.operation)

    def test_unlisted_command_denied(self):
        decision = router.route("@Termux: check status")
        plan = adapter.plan_execution(decision, "arbitrary-shell", bridge_authenticated=True)
        self.assertEqual(plan.status, "denied")

    def test_mismatched_receipt_rejected(self):
        with self.assertRaises(ValueError):
            receipts.verify_receipt({
                "request_id": "req_other", "diagnostic": "git-branch",
                "exit_code": 0, "stdout": "main", "stderr": ""
            }, expected_request_id="req_12345678", expected_diagnostic="git-branch")

if __name__ == "__main__":
    unittest.main()
