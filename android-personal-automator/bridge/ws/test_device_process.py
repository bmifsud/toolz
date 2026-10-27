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

    async def test_cancellation_terminates_child_process_group(self):
        class Socket:
            async def send(self, message): raise AssertionError("unexpected result")
        original = asyncio.create_subprocess_exec
        processes = []

        async def tracked(*args, **kwargs):
            proc = await original(*args, **kwargs)
            processes.append(proc)
            return proc

        # The diagnostic spawns a child that inherits stdout/stderr pipes.
        # Cancellation must not wait indefinitely for those inherited descriptors.
        code = ("import subprocess,sys,time; "
                "subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                "time.sleep(60)")
        with patch.dict(self.device.COMMANDS, {"git-branch": [sys.executable, "-c", code]}):
            with patch.object(self.device, "STOP", Path("/nonexistent-bridge-stop-test")):
                with patch.object(self.device.asyncio, "create_subprocess_exec", side_effect=tracked):
                    task = asyncio.create_task(self.device.run_diagnostic(Socket(), "process05", "git-branch"))
                    for _ in range(100):
                        if processes:
                            break
                        await asyncio.sleep(0.01)
                    self.assertTrue(processes)
                    await asyncio.sleep(0.1)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(task, timeout=5)
        self.assertIsNotNone(processes[0].returncode)

    async def test_stop_while_idle_exits_without_reconnect(self):
        class FakeSocket:
            def __init__(self, marker): self.marker = marker
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            async def recv(self):
                self.marker.touch()
                await asyncio.sleep(60)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            marker = Path(folder) / "STOP"
            calls = []
            def fake_connect(*args, **kwargs):
                calls.append(args)
                return FakeSocket(marker)
            with patch.object(self.device, "STOP", marker):
                with patch.object(self.device, "connect", side_effect=fake_connect):
                    await asyncio.wait_for(self.device.main(), timeout=4)
            self.assertEqual(len(calls), 1)

    async def test_stop_during_active_request_cancels_worker(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import AsyncMock
        class FakeSocket:
            def __init__(self, marker): self.marker = marker; self.messages = []; self.reads = 0
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            async def recv(self):
                self.reads += 1
                if self.reads == 1:
                    return json.dumps({"type": "request", "id": "active123", "diagnostic": "git-branch"})
                self.marker.touch()
                await asyncio.sleep(60)
            async def send(self, message): self.messages.append(json.loads(message))
        with TemporaryDirectory() as folder:
            marker = Path(folder) / "STOP"
            socket = FakeSocket(marker)
            with patch.object(self.device, "STOP", marker):
                with patch.object(self.device, "connect", return_value=socket):
                    with patch.object(self.device, "run_diagnostic", new_callable=AsyncMock) as worker:
                        async def wait_until_cancelled(*args):
                            await asyncio.sleep(60)
                        worker.side_effect = wait_until_cancelled
                        await asyncio.wait_for(self.device.main(), timeout=4)
                        self.assertEqual(worker.await_count, 1)
            self.assertEqual(socket.messages, [])


if __name__ == "__main__":
    unittest.main()
