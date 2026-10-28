#!/usr/bin/env python3
"""Isolated tests for the opt-in Termux listener supervisor."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import unittest

SUPERVISOR = pathlib.Path(__file__).with_name("termux-bridge-supervisor.sh")


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name)
        (self.home / "bin").mkdir()
        self.listener = self.home / "device.py"
        self.listener.write_text("# test listener\n")
        fake_python = self.home / "bin/python"
        fake_python.write_text("#!/bin/sh\necho listener-started\nsleep 0.2\nexit 1\n")
        fake_python.chmod(0o700)
        self.env = dict(os.environ, HOME=str(self.home), PREFIX=str(self.home),
                        BRIDGE_WS_URL="wss://example.invalid",
                        BRIDGE_DEVICE_TOKEN="x" * 40,
                        BRIDGE_DEVICE_SCRIPT=str(self.listener))

    def run_script(self, *args, env=None):
        return subprocess.run(["bash", str(SUPERVISOR), *args],
                              env=env or self.env, capture_output=True, text=True, timeout=8)

    def test_syntax(self):
        result = subprocess.run(["bash", "-n", str(SUPERVISOR)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_usage(self):
        self.assertEqual(self.run_script().returncode, 2)

    def test_missing_credentials(self):
        env = dict(self.env)
        env.pop("BRIDGE_DEVICE_TOKEN")
        result = self.run_script("--start", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("x" * 40, result.stderr)

    def test_missing_listener(self):
        env = dict(self.env, BRIDGE_DEVICE_SCRIPT=str(self.home / "missing.py"))
        self.assertEqual(self.run_script("--start", env=env).returncode, 1)

    def test_restart_and_stop(self):
        proc = subprocess.Popen(["bash", str(SUPERVISOR), "--start"],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            state = self.home / ".local/state/toolz-termux-bridge"
            log = state / "supervisor.log"
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline and (not log.exists() or "listener-started" not in log.read_text()):
                time.sleep(0.05)
            self.assertTrue(log.exists())
            self.assertIn("listener-started", log.read_text())
            self.assertEqual(self.run_script("--start").returncode, 0)  # lock blocks duplicates
            self.assertEqual(self.run_script("--stop").returncode, 0)
            proc.wait(timeout=6)
            self.assertEqual(proc.returncode, 0)
            self.assertNotIn(self.env["BRIDGE_DEVICE_TOKEN"], log.read_text())
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=4)


if __name__ == "__main__":
    unittest.main()
