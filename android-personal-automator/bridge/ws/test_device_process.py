"""Subprocess cancellation tests for the Termux WebSocket device listener."""
import asyncio
import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


class DeviceProcessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_WS_URL": "wss://example.invalid",
            "BRIDGE_DEVICE_TOKEN": "device-" + "a" * 40,
        }):
            import device
            self.device = importlib.reload(device)

    async def test_successful_allowlisted_diagnostic(self):
        class Socket:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(json.loads(message))
        socket = Socket()
        with patch.dict(self.device.COMMANDS, {"git-branch": [
            sys.executable, "-c", "print('verified')"
        ]}):
            with patch.object(self.device, "STOP", Path("/nonexistent-bridge-stop-test")):
                await self.device.run_diagnostic(socket, "process01", "git-branch")
        self.assertEqual(socket.messages[0]["result"]["stdout"].strip(), "verified")

    async def test_cancellation_reaps_running_subprocess(self):
        class Socket:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(json.loads(message))
        socket = Socket()
        original = self.device.asyncio.create_subprocess_exec
        processes = []

        async def tracked(*args, **kwargs):
            proc = await original(*args, **kwargs)
            processes.append(proc)
            return proc

        with patch.dict(self.device.COMMANDS, {"git-branch": [
            sys.executable, "-c", "import time; time.sleep(60)"
        ]}):
            with patch.object(self.device, "STOP", Path("/nonexistent-bridge-stop-test")):
                with patch.object(self.device.asyncio, "create_subprocess_exec", side_effect=tracked):
                    task = asyncio.create_task(self.device.run_diagnostic(socket, "process02", "git-branch"))
                    for _ in range(100):
                        if processes:
                            break
                        await asyncio.sleep(0.01)
                    self.assertTrue(processes, "diagnostic did not start")
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(task, timeout=5)
        self.assertIsNotNone(processes[0].returncode, "subprocess survived cancellation")
        self.assertEqual(socket.messages, [])

    async def test_stop_marker_suppresses_result(self):
        class Socket:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(json.loads(message))
        socket = Socket()
        with patch.dict(self.device.COMMANDS, {"git-branch": [
            sys.executable, "-c", "print('should-not-send')"
        ]}):
            with patch.object(self.device, "STOP", Path(__file__)):
                await self.device.run_diagnostic(socket, "process03", "git-branch")
        self.assertEqual(socket.messages, [])

    async def test_timeout_reaps_subprocess(self):
        class Socket:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(json.loads(message))
        socket = Socket()
        original_wait_for = asyncio.wait_for
        original_create = asyncio.create_subprocess_exec
        processes = []

        async def tracked(*args, **kwargs):
            process = await original_create(*args, **kwargs)
            processes.append(process)
            return process

        async def fast_timeout(awaitable, timeout):
            return await original_wait_for(awaitable, timeout=0.05)

        with patch.dict(self.device.COMMANDS, {"git-branch": [
            sys.executable, "-c", "import time; time.sleep(60)"
        ]}):
            with patch.object(self.device, "STOP", Path("/nonexistent-bridge-stop-test")):
                with patch.object(self.device.asyncio, "create_subprocess_exec", side_effect=tracked):
                    with patch.object(self.device.asyncio, "wait_for", side_effect=fast_timeout):
                        await self.device.run_diagnostic(socket, "process04", "git-branch")
        self.assertTrue(processes)
        self.assertIsNotNone(processes[0].returncode)
        self.assertEqual(socket.messages[0]["result"]["error"], "timeout")


if __name__ == "__main__":
    unittest.main()
