"""Offline cancellation-protocol contract tests; NOT Android emulator E2E proof."""
import asyncio
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))


class Socket:
    def __init__(self, role, token, frames=()):
        self.request = SimpleNamespace(
            path="/" + role,
            headers={"Authorization": "Bearer " + token})
        self.frames = iter(frames)
        self.sent = []

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.frames)
        except StopIteration:
            raise StopAsyncIteration


class CancelProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.device_token = "device-" + "a" * 40
        self.controller_token = "controller-" + "b" * 40
        with patch.dict(os.environ, {
            "BRIDGE_DEVICE_TOKEN": self.device_token,
            "BRIDGE_CONTROLLER_TOKEN": self.controller_token,
            "BRIDGE_WS_URL": "wss://example.invalid",
        }):
            import relay
            import device
            self.relay = importlib.reload(relay)
            self.listener = importlib.reload(device)

    async def test_explicit_cancel_forwards_only_owned_request(self):
        request_id = "request123"
        controller = Socket("controller", self.controller_token, [
            json.dumps({"id": request_id, "diagnostic": "git-branch"}),
            json.dumps({"type": "cancel", "id": request_id}),
        ])
        device = Socket("device", self.device_token)
        self.relay.device = device
        await self.relay.handler(controller)
        self.assertEqual([m["type"] for m in device.sent], ["request", "cancel"])
        self.assertEqual(device.sent[1]["id"], request_id)
        self.assertEqual(controller.sent[-1]["message"], "cancellation attempted; worker termination unverified")
        # No worker-termination receipt has been received by this controller.
        self.assertFalse(any(m.get("type") == "cancel_ack" for m in device.sent))
        self.assertNotIn(request_id, self.relay.pending)

    async def test_failed_cancel_delivery_never_claims_worker_stopped(self):
        request_id = "requestfail01"
        controller = Socket("controller", self.controller_token, [
            json.dumps({"type": "cancel", "id": request_id})
        ])

        class DisconnectedDevice:
            async def send(self, raw):
                raise OSError("device unavailable")

        timer = asyncio.create_task(asyncio.sleep(60))
        self.relay.pending[request_id] = (controller, timer)
        self.relay.device = DisconnectedDevice()
        try:
            await self.relay.handler(controller)
            self.assertEqual(controller.sent[-1]["message"],
                             "cancellation attempted; worker termination unverified")
            self.assertNotIn(request_id, self.relay.pending)
        finally:
            timer.cancel()
            self.relay.device = None

    async def test_other_controller_cannot_cancel_request(self):
        owner = Socket("controller", self.controller_token)
        intruder = Socket("controller", self.controller_token, [
            json.dumps({"type": "cancel", "id": "request456"})
        ])
        device = Socket("device", self.device_token)
        timer = asyncio.create_task(asyncio.sleep(60))
        self.relay.pending["request456"] = (owner, timer)
        self.relay.device = device
        try:
            await self.relay.handler(intruder)
            self.assertEqual(intruder.sent[0]["message"], "unknown request")
            self.assertEqual(device.sent, [])
            self.assertIs(self.relay.pending["request456"][0], owner)
        finally:
            timer.cancel()
            self.relay.pending.clear()

    async def test_controller_disconnect_propagates_cancel(self):
        controller = Socket("controller", self.controller_token, [
            json.dumps({"id": "request789", "diagnostic": "ssh-status"})
        ])
        device = Socket("device", self.device_token)
        self.relay.device = device
        await self.relay.handler(controller)
        self.assertEqual([m["type"] for m in device.sent], ["request", "cancel"])
        self.assertEqual(self.relay.pending, {})

    async def test_timeout_propagates_cancel(self):
        controller = Socket("controller", self.controller_token)
        device = Socket("device", self.device_token)
        self.relay.device = device
        with patch.object(self.relay, "REQUEST_TIMEOUT", 0.01):
            timer = asyncio.create_task(self.relay.expire_request("request999", controller))
            self.relay.pending["request999"] = (controller, timer)
            await asyncio.wait_for(timer, timeout=1)
        self.assertEqual(device.sent[0], {"type": "cancel", "id": "request999"})
        self.assertEqual(controller.sent[0]["message"], "request timeout")
        self.assertEqual(self.relay.pending, {})

    async def test_listener_cancel_frame_cancels_matching_worker(self):
        cancelled = asyncio.Event()
        started = asyncio.Event()
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "STOP"

            async def worker(*args):
                started.set()
                try:
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    cancelled.set()
                    raise

            class DeviceSocket:
                def __init__(self):
                    self.reads = 0
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False
                async def recv(self):
                    self.reads += 1
                    if self.reads == 1:
                        return json.dumps({"type": "request", "id": "requestabc",
                                           "diagnostic": "git-branch"})
                    if self.reads == 2:
                        await asyncio.wait_for(started.wait(), timeout=1)
                        return json.dumps({"type": "cancel", "id": "requestabc"})
                    await asyncio.wait_for(cancelled.wait(), timeout=1)
                    marker.touch()
                    return "{}"

            with patch.object(self.listener, "STOP", marker):
                with patch.object(self.listener, "connect", return_value=DeviceSocket()):
                    with patch.object(self.listener, "run_diagnostic", side_effect=worker):
                        await asyncio.wait_for(self.listener.main(), timeout=4)
        self.assertTrue(cancelled.is_set())


if __name__ == "__main__":
    unittest.main()
