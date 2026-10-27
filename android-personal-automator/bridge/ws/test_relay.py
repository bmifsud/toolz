"""Offline tests for the push relay; no Render credentials or network required."""
import asyncio
import importlib
import os
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(os.environ, {
            "BRIDGE_DEVICE_TOKEN": "device-" + "a" * 40,
            "BRIDGE_CONTROLLER_TOKEN": "controller-" + "b" * 40,
        }):
            import relay
            self.relay = importlib.reload(relay)

    async def test_head_probe_log_filter_is_narrow(self):
        filt = self.relay.HealthProbeLogFilter()
        expected = ValueError("unsupported HTTP method; expected GET; got HEAD")
        wrapped = RuntimeError("invalid request")
        wrapped.__cause__ = expected
        record = logging.LogRecord("websockets.server", logging.ERROR, __file__, 1, "opening handshake failed", (), (RuntimeError, wrapped, None))
        self.assertFalse(filt.filter(record))
        other = ValueError("different handshake failure")
        record.exc_info = (ValueError, other, None)
        self.assertTrue(filt.filter(record))
        record.msg = "another error"
        self.assertTrue(filt.filter(record))

    async def test_healthz(self):
        result = await self.relay.process_request(None, SimpleNamespace(path="/healthz"))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.body, b"ok\n")

    async def test_non_health_request_proceeds_to_websocket(self):
        result = await self.relay.process_request(None, SimpleNamespace(path="/device"))
        self.assertIsNone(result)

    async def test_unauthorized_device_rejected(self):
        class FakeSocket:
            request = SimpleNamespace(path="/device", headers={})
            def __init__(self): self.closed = None
            async def close(self, **kwargs): self.closed = kwargs
        ws = FakeSocket()
        await self.relay.handler(ws)
        self.assertEqual(ws.closed["code"], 1008)

    async def test_query_token_rejected(self):
        class FakeSocket:
            request = SimpleNamespace(path="/device?token=leak", headers={"Authorization": "Bearer device-" + "a" * 40})
            def __init__(self): self.closed = None
            async def close(self, **kwargs): self.closed = kwargs
        ws = FakeSocket()
        await self.relay.handler(ws)
        self.assertEqual(ws.closed["code"], 1008)

if __name__ == "__main__":
    unittest.main()
