"""Offline regression tests for bounded_executor.py."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "bounded_executor.py"
spec = importlib.util.spec_from_file_location("bounded_executor", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class BoundedExecutorTests(unittest.TestCase):
    def test_unverified_controller_denied_by_default(self):
        with patch.object(module.subprocess, 'run') as run:
            with self.assertRaises(RuntimeError):
                module.execute('git-branch', controller_path='/tmp/controller.py')
            run.assert_not_called()

    def test_unknown_diagnostic_rejected_without_subprocess(self):
        with patch.object(module.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                module.execute("arbitrary-command", controller_path="/tmp/controller.py", controller_interface_verified=True)
            run.assert_not_called()

    def test_relative_path_rejected(self):
        with self.assertRaises(ValueError):
            module.execute("git-branch", controller_path="controller.py", controller_interface_verified=True)

    def test_invalid_timeouts_rejected(self):
        for timeout in (0, 121):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                module.execute("git-branch", controller_path="/tmp/controller.py", controller_interface_verified=True, timeout=timeout)

    def test_missing_token_rejected(self):
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "", "BRIDGE_WS_URL": "wss://example.org"}, clear=True):
            with self.assertRaises(RuntimeError):
                module.execute("git-branch", controller_path="/tmp/controller.py", controller_interface_verified=True)

    def test_insecure_relay_rejected(self):
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "dummy", "BRIDGE_WS_URL": "ws://example.org"}, clear=True):
            with self.assertRaises(RuntimeError):
                module.execute("git-branch", controller_path="/tmp/controller.py", controller_interface_verified=True)

    def test_success_and_argument_vector(self):
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "dummy", "BRIDGE_WS_URL": "wss://example.org"}, clear=True):
            with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"main\n", b"")) as run:
                result = module.execute("git-branch", controller_path="/tmp/controller.py", controller_interface_verified=True)
                self.assertEqual((result.exit_code, result.stdout), (0, "main\n"))
                self.assertEqual(run.call_args.args[0][-2:], ["--diagnostic", "git-branch"])
                self.assertFalse(run.call_args.kwargs["shell"])

    def test_nonzero_exit_preserved(self):
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "dummy", "BRIDGE_WS_URL": "wss://example.org"}, clear=True):
            with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 7, b"", b"failed")):
                self.assertEqual(module.execute("tier1-tests", controller_path="/tmp/controller.py", controller_interface_verified=True).exit_code, 7)

    def test_output_size_enforced(self):
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "dummy", "BRIDGE_WS_URL": "wss://example.org"}, clear=True):
            with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"x" * 16385, b"")):
                with self.assertRaises(ValueError):
                    module.execute("git-branch", controller_path="/tmp/controller.py", controller_interface_verified=True)

    def test_timeout_propagates(self):
        with patch.dict(os.environ, {"BRIDGE_CONTROLLER_TOKEN": "dummy", "BRIDGE_WS_URL": "wss://example.org"}, clear=True):
            with patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("controller", 30)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    module.execute("git-branch", controller_path="/tmp/controller.py", controller_interface_verified=True)

if __name__ == "__main__":
    unittest.main()
