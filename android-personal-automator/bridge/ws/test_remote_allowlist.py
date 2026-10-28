"""Fail-closed remote diagnostic allowlist regression tests (offline only)."""
import asyncio
import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

class RemoteAllowlistTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.device_token = "device-" + "a" * 40
        self.controller_token = "controller-" + "b" * 40
        with patch.dict(os.environ, {
            "BRIDGE_DEVICE_TOKEN": self.device_token,
            "BRIDGE_CONTROLLER_TOKEN": self.controller_token,
            "BRIDGE_WS_URL": "wss://example.invalid",
        }):
            import relay, device, controller
            self.relay = importlib.reload(relay)
            self.device = importlib.reload(device)
            self.controller = importlib.reload(controller)

    async def test_remote_allowlists_exclude_mutating_git_sync(self):
        expected = {"git-branch", "tier1-tests", "ssh-status"}
        for module in (self.relay, self.device, self.controller):
            self.assertEqual(set(module.ALLOWED_DIAGNOSTICS), expected)
            self.assertNotIn("git-sync-pr", module.ALLOWED_DIAGNOSTICS)

    async def test_direct_device_worker_rejects_mutating_diagnostic(self):
        with patch.object(self.device.asyncio, "create_subprocess_exec") as spawn:
            with self.assertRaises(ValueError):
                await self.device.run_diagnostic(None, "request123", "git-sync-pr")
            spawn.assert_not_called()

    async def test_relay_never_forwards_mutating_diagnostic(self):
        class Controller:
            request = SimpleNamespace(path="/controller", headers={
                "Authorization": "Bearer " + "controller-" + "b" * 40})
            def __init__(self):
                self.frames = iter([json.dumps({"id": "request123", "diagnostic": "git-sync-pr"})])
                self.sent = []
            async def send(self, message):
                self.sent.append(json.loads(message))
            def __aiter__(self):
                return self
            async def __anext__(self):
                try:
                    return next(self.frames)
                except StopIteration:
                    raise StopAsyncIteration
        class Device:
            def __init__(self):
                self.sent = []
            async def send(self, message):
                self.sent.append(message)
        listener = Device()
        self.relay.device = listener
        controller = Controller()
        await self.relay.handler(controller)
        self.assertEqual(listener.sent, [])
        self.assertEqual(controller.sent, [])
        self.assertEqual(self.relay.pending, {})

    async def test_cli_rejects_mutating_diagnostic_before_network(self):
        with patch.object(sys, "argv", ["controller.py", "git-sync-pr"]):
            with patch.object(self.controller, "connect") as connect:
                with patch.object(self.controller, "TOKEN", self.controller_token):
                    with self.assertRaisesRegex(SystemExit, "Unsupported diagnostic"):
                        await self.controller.main()
                connect.assert_not_called()

if __name__ == "__main__":
    unittest.main()
