"""Regression: remote pytest is denied, while the local test command remains available.

Offline authorization tests only; not emulator or physical-device evidence.
"""
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class RemotePytestDeniedTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_WS_URL": "wss://example.invalid",
            "BRIDGE_DEVICE_TOKEN": "device-" + "a" * 40,
            "BRIDGE_CONTROLLER_TOKEN": "controller-" + "b" * 40,
        }):
            import relay, device, controller, readonly_runner
            self.relay = importlib.reload(relay)
            self.device = importlib.reload(device)
            self.controller = importlib.reload(controller)
            self.local_runner = readonly_runner

    async def test_local_pytest_command_remains_available(self):
        self.assertIn("tier1-tests", self.local_runner.COMMANDS)
        for module in (self.relay, self.device, self.controller):
            self.assertNotIn("tier1-tests", module.ALLOWED_DIAGNOSTICS)

    async def test_device_rejects_pytest_before_spawning(self):
        with patch.object(self.device.asyncio, "create_subprocess_exec") as spawn:
            with self.assertRaisesRegex(ValueError, "not remotely allowlisted"):
                await self.device.run_diagnostic(None, "testrequest123", "tier1-tests")
            spawn.assert_not_called()

    async def test_controller_rejects_pytest_before_connecting(self):
        with patch.object(sys, "argv", ["controller.py", "tier1-tests"]):
            with patch.object(self.controller, "TOKEN", "controller-" + "b" * 40):
                with patch.object(self.controller, "connect") as connect:
                    with self.assertRaisesRegex(SystemExit, "Unsupported diagnostic"):
                        await self.controller.main()
                    connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
