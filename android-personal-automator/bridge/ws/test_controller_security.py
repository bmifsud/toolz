"""Regression checks for controller credential redaction and validation."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

CONTROLLER = Path(__file__).with_name("controller.py")


class ControllerSecurityTests(unittest.TestCase):
    def run_controller(self, token):
        env = os.environ.copy()
        env["BRIDGE_CONTROLLER_TOKEN"] = token
        env["BRIDGE_WS_URL"] = "wss://localhost:1"
        return subprocess.run(
            [sys.executable, str(CONTROLLER), "ssh-status"],
            env=env, capture_output=True, text=True, timeout=10,
        )

    def test_rejects_newline_without_leaking_token(self):
        secret = "A" * 32 + "\n" + "SECRET_MARKER"
        result = self.run_controller(secret)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid token characters", result.stderr + result.stdout)
        self.assertNotIn("SECRET_MARKER", result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_connection_error_has_no_traceback_or_secret(self):
        secret = "A" * 64
        result = self.run_controller(secret)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("credentials redacted", result.stderr)
        self.assertNotIn(secret, result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
