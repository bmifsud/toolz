"""Isolated Linux regressions for diagnostic process-group descendants.

These are offline host tests, NOT authenticated emulator or Termux E2E receipts.
"""
import asyncio
import importlib
import json
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHILD_SCRIPT = """
import pathlib, subprocess, sys, time
mode, marker = sys.argv[1:]
child = subprocess.Popen(
    [sys.executable, '-c', 'import time; time.sleep(60)'],
    stdout=None if mode == 'inherit' else subprocess.DEVNULL,
    stderr=None if mode == 'inherit' else subprocess.DEVNULL)
pathlib.Path(marker).write_text(str(child.pid))
if mode == 'overflow':
    sys.stdout.write('x' * 5000)
    sys.stdout.flush()
if mode == 'cancel':
    time.sleep(60)
"""


def child_is_live(pid):
    """Linux /proc state check: unreaped zombies are not running workers."""
    try:
        stat = Path("/proc/%d/stat" % pid).read_text()
    except FileNotFoundError:
        return False
    state = stat.rsplit(")", 1)[1].split()[0]
    return state not in ("Z", "X", "x")


class Socket:
    def __init__(self):
        self.messages = []

    async def send(self, raw):
        self.messages.append(json.loads(raw))


@unittest.skipUnless(Path("/proc/self/stat").is_file(), "Linux /proc required")
class OrphanProcessGroupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_WS_URL": "wss://example.invalid",
            "BRIDGE_DEVICE_TOKEN": "device-" + "a" * 40,
        }):
            import device
            self.device = importlib.reload(device)

    async def exercise(self, mode, cancel=False):
        original_create = asyncio.create_subprocess_exec
        processes = []

        async def tracked(*args, **kwargs):
            process = await original_create(*args, **kwargs)
            processes.append(process)
            return process

        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "child.pid"
            stop = Path(folder) / "STOP"
            socket = Socket()
            command = [sys.executable, "-c", CHILD_SCRIPT, mode, str(marker)]
            try:
                with patch.dict(self.device.COMMANDS, {"git-branch": command}):
                    with patch.object(self.device, "STOP", stop):
                        with patch.object(self.device.asyncio, "create_subprocess_exec",
                                          side_effect=tracked):
                            if cancel:
                                task = asyncio.create_task(
                                    self.device.run_diagnostic(socket, "orphan123", "git-branch"))
                                for _ in range(200):
                                    if marker.exists():
                                        break
                                    await asyncio.sleep(0.01)
                                self.assertTrue(marker.exists(), "child did not start")
                                task.cancel()
                                with self.assertRaises(asyncio.CancelledError):
                                    await asyncio.wait_for(task, timeout=5)
                            else:
                                original_wait_for = asyncio.wait_for

                                async def fast_timeout(awaitable, timeout):
                                    if timeout == 10:
                                        timeout = 0.2
                                    return await original_wait_for(awaitable, timeout=timeout)

                                with patch.object(self.device.asyncio, "wait_for",
                                                  side_effect=fast_timeout):
                                    await self.device.run_diagnostic(
                                        socket, "orphan123", "git-branch")
                self.assertTrue(marker.exists(), "child PID was not recorded")
                child_pid = int(marker.read_text())
                for _ in range(50):
                    if not child_is_live(child_pid):
                        break
                    await asyncio.sleep(0.02)
                self.assertFalse(child_is_live(child_pid),
                                 "orphaned diagnostic child survived cleanup")
                if cancel:
                    self.assertEqual(socket.messages, [])
                else:
                    self.assertEqual(len(socket.messages), 1)
                    receipt = socket.messages[0]["result"]
                    self.assertIn(receipt["exit_code"], (0, 124, 125, 126))
                    if receipt["exit_code"] == 126:
                        self.assertEqual(receipt["error"], "worker termination unverified")
                    if mode == "inherit":
                        self.assertNotEqual(receipt["exit_code"], 0)
                    if mode == "overflow":
                        self.assertNotEqual(receipt["exit_code"], 0)
            finally:
                # Always reap our disposable test group, even after assertions fail.
                for process in processes:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    if process.returncode is None:
                        try:
                            await asyncio.wait_for(process.wait(), timeout=2)
                        except asyncio.TimeoutError:
                            pass
                if marker.exists():
                    child_pid = int(marker.read_text())
                    if child_is_live(child_pid):
                        try:
                            os.kill(child_pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    async def test_exited_leader_with_closed_pipes(self):
        await self.exercise("closed")

    async def test_exited_leader_with_inherited_pipes_timeout(self):
        await self.exercise("inherit")

    async def test_exited_leader_with_output_overflow(self):
        await self.exercise("overflow")

    async def test_cancellation_kills_child_as_well_as_leader(self):
        await self.exercise("cancel", cancel=True)


if __name__ == "__main__":
    unittest.main()
