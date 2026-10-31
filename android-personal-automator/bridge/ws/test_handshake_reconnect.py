"""Offline regression for a rejected WebSocket handshake.

This verifies the listener's retry loop, not real emulator/device connectivity.
"""
import asyncio
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from websockets.exceptions import InvalidHandshake

sys.path.insert(0, str(Path(__file__).resolve().parent))


class HandshakeReconnectTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_WS_URL": "wss://example.invalid",
            "BRIDGE_DEVICE_TOKEN": "device-" + "a" * 40,
        }):
            import device
            self.device = importlib.reload(device)

    async def test_handshake_rejection_retries_until_stop(self):
        stop = Mock()
        # Initial loop check, post-failure check, next loop check.
        stop.exists.side_effect = [False, False, True]
        with patch.object(self.device, "STOP", stop), \
             patch.object(self.device, "ReplayStore"), \
             patch.object(self.device, "connect", side_effect=InvalidHandshake("rejected")) as connect, \
             patch.object(self.device.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            await self.device.main()
        connect.assert_called_once()
        sleep.assert_awaited_once_with(5)

    async def test_unexpected_programming_error_not_silenced(self):
        stop = Mock()
        stop.exists.return_value = False
        with patch.object(self.device, "STOP", stop), \
             patch.object(self.device, "ReplayStore"), \
             patch.object(self.device, "connect", side_effect=RuntimeError("bug")):
            with self.assertRaisesRegex(RuntimeError, "bug"):
                await self.device.main()


if __name__ == "__main__":
    unittest.main()
