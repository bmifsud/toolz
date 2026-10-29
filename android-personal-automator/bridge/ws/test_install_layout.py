"""Offline regression for the documented Termux listener installation layout.

This checks imports only: it never connects to a relay, starts a listener,
runs a diagnostic, or claims Android/emulator end-to-end verification.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


WS = Path(__file__).resolve().parent
BRIDGE = WS.parent
README = WS / "README.md"


class ListenerInstallLayoutTests(unittest.TestCase):
    def test_documented_copy_includes_replay_guard(self):
        instructions = README.read_text(encoding="utf-8")
        self.assertIn("for name in device.py replay_store.py requirements.txt; do", instructions)
        self.assertIn('git fetch --no-tags origin "$REVIEWED_BRIDGE_REF"', instructions)
        self.assertIn('git rev-parse FETCH_HEAD', instructions)
        self.assertIn('"$HOME/toolz-ws-bridge/replay_store.py"', instructions)
        self.assertIn('"$HOME/readonly_runner.py"', instructions)

    def _staged_import(self, omit_guard=False):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            stage = home / "toolz-ws-bridge"
            stage.mkdir()
            for name in ("device.py", "requirements.txt", "replay_store.py"):
                if name != "replay_store.py" or not omit_guard:
                    shutil.copyfile(WS / name, stage / name)
            shutil.copyfile(BRIDGE / "readonly_runner.py", home / "readonly_runner.py")
            env = os.environ.copy()
            env.update({
                "BRIDGE_WS_URL": "wss://example.invalid",
                "BRIDGE_DEVICE_TOKEN": "test-only-" + "a" * 40,
            })
            # Import only; device.main() is deliberately never called.
            return subprocess.run(
                [sys.executable, "-c",
                 "import device; from replay_store import ReplayStore; "
                 "assert device.ReplayStore is ReplayStore"],
                cwd=stage, env=env, capture_output=True, text=True,
                timeout=10, check=False,
            )

    def test_staged_listener_imports_offline(self):
        completed = self._staged_import()
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_missing_replay_guard_fails_closed(self):
        completed = self._staged_import(omit_guard=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("No module named 'replay_store'", completed.stderr)


if __name__ == "__main__":
    unittest.main()
