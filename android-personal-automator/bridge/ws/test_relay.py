"""Offline tests for the push relay; no Render credentials or network required."""
import asyncio
import importlib
import json
import os
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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

    async def test_pre_accept_auth_rejects_without_handshake(self):
        class FakeSocket:
            scope = {"path": "/device", "query_string": b""}
            headers = {}
            def __init__(self):
                self.accepted = False
                self.closed = None
            async def accept(self):
                self.accepted = True
            async def close(self, **kwargs):
                self.closed = kwargs

        socket = FakeSocket()
        await self.relay.websocket_endpoint(socket)
        self.assertFalse(socket.accepted)
        self.assertEqual(socket.closed["code"], 1008)

    async def test_pre_accept_auth_accepts_valid_token(self):
        class FakeSocket:
            scope = {"path": "/controller", "query_string": b""}
            headers = {"Authorization": "Bearer controller-" + "b" * 40}
            def __init__(self):
                self.accepted = False
            async def accept(self):
                self.accepted = True

        socket = FakeSocket()
        with patch.object(self.relay, "handler", new_callable=AsyncMock) as handler:
            await self.relay.websocket_endpoint(socket)
        self.assertTrue(socket.accepted)
        handler.assert_awaited_once()

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

    async def test_device_disconnect_clears_pending_and_notifies_controller(self):
        class FakeSocket:
            request = SimpleNamespace(path="/device", headers={"Authorization": "Bearer device-" + "a" * 40})
            def __init__(self): self.closed = None
            async def close(self, **kwargs): self.closed = kwargs
            def __aiter__(self): return self
            async def __anext__(self): raise StopAsyncIteration
        class Controller:
            def __init__(self): self.messages = []
            async def send(self, message): self.messages.append(json.loads(message))
        controller = Controller()
        timer = asyncio.create_task(asyncio.sleep(60))
        self.relay.pending["request03"] = (controller, timer)
        await self.relay.handler(FakeSocket())
        self.assertNotIn("request03", self.relay.pending)
        self.assertTrue(timer.cancelling())
        self.assertEqual(controller.messages[0]["message"], "device disconnected")

    async def test_controller_disconnect_cancels_its_pending_requests(self):
        class FakeSocket:
            request = SimpleNamespace(path="/controller", headers={"Authorization": "Bearer controller-" + "b" * 40})
            def __aiter__(self): return self
            async def __anext__(self): raise StopAsyncIteration
        ws = FakeSocket()
        timer = asyncio.create_task(asyncio.sleep(60))
        self.relay.pending["request04"] = (ws, timer)
        await self.relay.handler(ws)
        self.assertNotIn("request04", self.relay.pending)
        self.assertTrue(timer.cancelling())

    async def test_controller_oversize_message_closes_connection(self):
        class FakeSocket:
            request = SimpleNamespace(path="/controller", headers={"Authorization": "Bearer controller-" + "b" * 40})
            def __init__(self): self.closed = None
            async def close(self, **kwargs): self.closed = kwargs
            def __aiter__(self): return self
            async def __anext__(self):
                if getattr(self, "read", False): raise StopAsyncIteration
                self.read = True
                return "x" * (self_limit + 1)
        self_limit = self.relay.MAX_MESSAGE
        ws = FakeSocket()
        await self.relay.handler(ws)
        self.assertEqual(ws.closed["code"], 1009)

    async def test_second_device_connection_rejected(self):
        class FakeSocket:
            request = SimpleNamespace(path="/device", headers={"Authorization": "Bearer device-" + "a" * 40})
            def __init__(self): self.closed = None
            async def close(self, **kwargs): self.closed = kwargs
        self.relay.device = object()
        ws = FakeSocket()
        await self.relay.handler(ws)
        self.assertEqual(ws.closed["code"], 1008)

    async def test_controller_rejects_unsupported_diagnostic(self):
        class FakeSocket:
            request = SimpleNamespace(path="/controller", headers={"Authorization": "Bearer controller-" + "b" * 40})
            def __init__(self): self.sent = []
            async def send(self, message): self.sent.append(message)
            def __aiter__(self): return self
            async def __anext__(self):
                if getattr(self, "read", False): raise StopAsyncIteration
                self.read = True
                return json.dumps({"id": "request05", "diagnostic": "shell"})
        ws = FakeSocket()
        await self.relay.handler(ws)
        self.assertEqual(ws.sent, [])
        self.assertEqual(self.relay.pending, {})

    async def test_controller_reports_device_offline(self):
        class FakeSocket:
            request = SimpleNamespace(path="/controller", headers={"Authorization": "Bearer controller-" + "b" * 40})
            def __init__(self): self.sent = []
            async def send(self, message): self.sent.append(json.loads(message))
            def __aiter__(self): return self
            async def __anext__(self):
                if getattr(self, "read", False): raise StopAsyncIteration
                self.read = True
                return json.dumps({"id": "request06", "diagnostic": "git-branch"})
        ws = FakeSocket()
        await self.relay.handler(ws)
        self.assertEqual(ws.sent[0]["message"], "device offline")
        self.assertEqual(self.relay.pending, {})

    async def test_controller_duplicate_pending_request_is_rejected(self):
        class FakeSocket:
            request = SimpleNamespace(path="/controller", headers={"Authorization": "Bearer controller-" + "b" * 40})
            def __init__(self): self.sent = []
            async def send(self, message): self.sent.append(json.loads(message))
            def __aiter__(self): return self
            async def __anext__(self):
                if getattr(self, "read", False): raise StopAsyncIteration
                self.read = True
                return json.dumps({"id": "request07", "diagnostic": "git-branch"})
        class Device:
            async def send(self, message): pass
        ws = FakeSocket()
        other = object()
        timer = asyncio.create_task(asyncio.sleep(60))
        self.relay.pending["request07"] = (other, timer)
        self.relay.device = Device()
        try:
            await self.relay.handler(ws)
            self.assertEqual(ws.sent[0]["message"], "duplicate or busy")
            self.assertIs(self.relay.pending["request07"][0], other)
        finally:
            timer.cancel()
            self.relay.pending.clear()
            self.relay.device = None


    async def test_asgi_rejects_wrong_role_token_before_accept(self):
        class FakeSocket:
            scope = {"path": "/device", "query_string": b""}
            headers = {"Authorization": "Bearer controller-" + "b" * 40}
            def __init__(self):
                self.accepted = False
                self.closed = None
            async def accept(self): self.accepted = True
            async def close(self, **kwargs): self.closed = kwargs
        socket = FakeSocket()
        await self.relay.websocket_endpoint(socket)
        self.assertFalse(socket.accepted)
        self.assertEqual(socket.closed["code"], 1008)

    async def test_asgi_rejects_query_even_with_valid_bearer(self):
        class FakeSocket:
            scope = {"path": "/device", "query_string": b"token=unsafe"}
            headers = {"Authorization": "Bearer device-" + "a" * 40}
            def __init__(self):
                self.accepted = False
                self.closed = None
            async def accept(self): self.accepted = True
            async def close(self, **kwargs): self.closed = kwargs
        socket = FakeSocket()
        await self.relay.websocket_endpoint(socket)
        self.assertFalse(socket.accepted)
        self.assertEqual(socket.closed["code"], 1008)

    async def test_asgi_rejects_invalid_bearer_before_accept(self):
        class FakeSocket:
            scope = {"path": "/controller", "query_string": b""}
            headers = {"Authorization": "Bearer invalid-token"}
            def __init__(self):
                self.accepted = False
                self.closed = None
            async def accept(self): self.accepted = True
            async def close(self, **kwargs): self.closed = kwargs
        socket = FakeSocket()
        await self.relay.websocket_endpoint(socket)
        self.assertFalse(socket.accepted)
        self.assertEqual(socket.closed["code"], 1008)

if __name__ == "__main__":
    unittest.main()
