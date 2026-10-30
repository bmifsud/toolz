"""Host-side subprocess output budget regressions; not emulator/device E2E."""
import asyncio
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


class RecordingSocket:
    def __init__(self):
        self.messages = []

    async def send(self, data):
        self.messages.append(json.loads(data))


class BoundedOutputTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_WS_URL": "wss://example.invalid",
            "BRIDGE_DEVICE_TOKEN": "d" * 40,
        }):
            import device
            self.device = importlib.reload(device)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        # Keep subprocess tests independent of a real user's checkout.
        checkout = Path(self.directory.name) / "toolz-tier1-test"
        checkout.mkdir()
        (checkout / ".git").mkdir()
        home_patch = patch.object(self.device.Path, "home",
                                  return_value=Path(self.directory.name))
        home_patch.start()
        self.addCleanup(home_patch.stop)
        self.stop_patch = patch.object(
            self.device, "STOP", Path(self.directory.name) / "STOP")
        self.stop_patch.start()
        self.addCleanup(self.stop_patch.stop)

    async def _run(self, code):
        socket = RecordingSocket()
        with patch.dict(self.device.COMMANDS, {
            "git-branch": [sys.executable, "-c", code],
        }):
            await asyncio.wait_for(
                self.device.run_diagnostic(socket, "request123", "git-branch"),
                timeout=8)
        self.assertEqual(len(socket.messages), 1)
        self.assertEqual(socket.messages[0]["id"], "request123")
        return socket.messages[0]["result"]

    async def test_small_stdout_and_stderr_preserved(self):
        result = await self._run(
            "import sys;sys.stdout.write('ok');sys.stderr.write('warning')")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "ok")
        self.assertEqual(result["stderr"], "warning")

    async def test_large_stdout_rejected_before_buffering_all(self):
        result = await self._run(
            "import sys;sys.stdout.write('x'*1048576);sys.stdout.flush()")
        self.assertEqual(result["exit_code"], 125)
        self.assertEqual(result["error"], "output limit exceeded")
        self.assertNotIn("stdout", result)

    async def test_overflow_worker_exits_before_receipt(self):
        pidfile = Path(self.directory.name) / "worker.pid"
        code = (
            "import os,sys,time;"
            "open(" + repr(str(pidfile)) + ",'w').write(str(os.getpid()));"
            "sys.stdout.write('x'*1048576);sys.stdout.flush();"
            "time.sleep(30)"
        )
        result = await self._run(code)
        self.assertEqual(result["error"], "output limit exceeded")
        pid = int(pidfile.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    async def test_large_stderr_rejected_before_buffering_all(self):
        result = await self._run(
            "import sys;sys.stderr.write('e'*1048576);sys.stderr.flush()")
        self.assertEqual(result["exit_code"], 125)
        self.assertEqual(result["error"], "output limit exceeded")
        self.assertNotIn("stderr", result)

    async def test_cancel_does_not_emit_success_receipt(self):
        socket = RecordingSocket()
        with patch.dict(self.device.COMMANDS, {
            "git-branch": [sys.executable, "-c",
                           "import time;time.sleep(30)"],
        }):
            task = asyncio.create_task(
                self.device.run_diagnostic(socket, "request123", "git-branch"))
            await asyncio.sleep(0.25)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)
        self.assertEqual(socket.messages, [])

    async def test_non_allowlisted_diagnostic_never_spawns(self):
        socket = RecordingSocket()
        with patch.object(self.device.asyncio, "create_subprocess_exec") as spawn:
            with self.assertRaises(ValueError):
                await self.device.run_diagnostic(socket, "request123", "git-sync-pr")
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
