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

    async def test_http_health_get_and_head(self):
        from starlette.testclient import TestClient
        with TestClient(self.relay.app) as client:
            get = client.get("/healthz")
            head = client.head("/healthz")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(get.text, "ok\n")
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b"")

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
