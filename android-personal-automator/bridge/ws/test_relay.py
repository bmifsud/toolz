"""Offline tests for the push relay; no Render credentials or network required."""
import asyncio
import importlib
import json
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

    async def test_pending_request_timeout(self):
        class Controller:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(json.loads(message))
        controller = Controller()
        with patch.object(self.relay, "REQUEST_TIMEOUT", 0.001):
            task = asyncio.create_task(self.relay.expire_request("request01", controller))
            self.relay.pending["request01"] = (controller, task)
            await asyncio.wait_for(task, timeout=1)
        self.assertNotIn("request01", self.relay.pending)
        self.assertEqual(controller.messages[0]["message"], "request timeout")

    async def test_expiry_does_not_remove_reassigned_request(self):
        class Controller:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(message)
        old, new = Controller(), Controller()
        with patch.object(self.relay, "REQUEST_TIMEOUT", 0.001):
            task = asyncio.create_task(self.relay.expire_request("request02", old))
            self.relay.pending["request02"] = (new, None)
            await asyncio.wait_for(task, timeout=1)
        self.assertIn("request02", self.relay.pending)
        self.assertEqual(old.messages, [])
        self.relay.pending.clear()

if __name__ == "__main__":
    unittest.main()
