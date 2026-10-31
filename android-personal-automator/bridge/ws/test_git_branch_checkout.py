"""Offline regression: bridge git-branch must not depend on listener launch cwd.

These tests do not establish authenticated emulator/device connectivity.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


class Socket:
    def __init__(self):
        self.messages = []

    async def send(self, raw):
        self.messages.append(json.loads(raw))


class GitBranchCheckoutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_WS_URL": "wss://example.invalid",
            "BRIDGE_DEVICE_TOKEN": "device-" + "a" * 40,
        }):
            import device
            self.device = importlib.reload(device)

    async def test_missing_checkout_does_not_spawn_in_inherited_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            socket = Socket()
            with patch.object(self.device.Path, "home", return_value=Path(folder)), \
                 patch.object(self.device, "STOP", Path(folder) / "STOP"), \
                 patch.object(self.device.asyncio, "create_subprocess_exec") as spawn:
                await self.device.run_diagnostic(socket, "request123", "git-branch")
            spawn.assert_not_called()
            self.assertEqual(len(socket.messages), 1)
            self.assertEqual(socket.messages[0]["result"]["exit_code"], 2)
            self.assertEqual(socket.messages[0]["result"]["error"],
                             "diagnostic checkout missing")

    async def test_non_repository_directory_does_not_spawn(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "toolz-tier1-test").mkdir()
            socket = Socket()
            with patch.object(self.device.Path, "home", return_value=Path(folder)), \
                 patch.object(self.device, "STOP", Path(folder) / "STOP"), \
                 patch.object(self.device.asyncio, "create_subprocess_exec") as spawn:
                await self.device.run_diagnostic(socket, "request456", "git-branch")
            spawn.assert_not_called()
            self.assertEqual(socket.messages[0]["result"]["exit_code"], 2)

    async def test_uses_designated_checkout_even_when_listener_cwd_differs(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = Path(folder) / "toolz-tier1-test"
            checkout.mkdir()
            # A .git file is valid for a linked Git worktree.
            (checkout / ".git").write_text("gitdir: /not-needed-by-this-test\\n")
            socket = Socket()
            command = [sys.executable, "-c", "import os; print(os.getcwd())"]
            with patch.object(self.device.Path, "home", return_value=Path(folder)), \
                 patch.object(self.device, "STOP", Path(folder) / "STOP"), \
                 patch.dict(self.device.COMMANDS, {"git-branch": command}):
                await self.device.run_diagnostic(socket, "request789", "git-branch")
            self.assertEqual(len(socket.messages), 1)
            result = socket.messages[0]["result"]
            self.assertEqual(result["exit_code"], 0, result)
            self.assertEqual(Path(result["stdout"].strip()), checkout)


if __name__ == "__main__":
    unittest.main()
