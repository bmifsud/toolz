"""In-process ASGI WebSocket integration tests; no external relay or device tokens."""
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).resolve().parent))


class WebSocketIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.device_token = "device-" + "a" * 40
        self.controller_token = "controller-" + "b" * 40
        with patch.dict(os.environ, {
            "BRIDGE_DEVICE_TOKEN": self.device_token,
            "BRIDGE_CONTROLLER_TOKEN": self.controller_token,
        }):
            import relay
            self.relay = importlib.reload(relay)

    def test_request_result_round_trip_and_reconnect(self):
        with TestClient(self.relay.app) as client:
            with client.websocket_connect("/device", headers={
                "Authorization": "Bearer " + self.device_token
            }) as device:
                with client.websocket_connect("/controller", headers={
                    "Authorization": "Bearer " + self.controller_token
                }) as controller:
                    controller.send_json({"id": "integration01", "diagnostic": "git-branch"})
                    request = device.receive_json()
                    self.assertEqual(request, {
                        "type": "request", "id": "integration01", "diagnostic": "git-branch"
                    })
                    device.send_json({"type": "result", "id": "integration01", "result": {
                        "exit_code": 0, "stdout": "main"
                    }})
                    result = controller.receive_json()
                    self.assertEqual(result["id"], "integration01")
                    self.assertEqual(result["result"]["stdout"], "main")
            with client.websocket_connect("/device", headers={
                "Authorization": "Bearer " + self.device_token
            }) as device:
                with client.websocket_connect("/controller", headers={
                    "Authorization": "Bearer " + self.controller_token
                }) as controller:
                    controller.send_json({"id": "integration02", "diagnostic": "git-branch"})
                    self.assertEqual(device.receive_json()["id"], "integration02")
                    device.send_json({"type": "result", "id": "integration02", "result": {
                        "exit_code": 0, "stdout": "reconnected"
                    }})
                    self.assertEqual(controller.receive_json()["result"]["stdout"], "reconnected")

    def test_authentication_and_query_string_rejected(self):
        with TestClient(self.relay.app) as client:
            for path, headers in [
                ("/device", {}),
                ("/controller", {"Authorization": "Bearer incorrect"}),
                ("/device?token=secret", {"Authorization": "Bearer " + self.device_token}),
            ]:
                with self.subTest(path=path, headers=headers):
                    with self.assertRaises(WebSocketDisconnect) as failure:
                        with client.websocket_connect(path, headers=headers) as ws:
                            ws.receive_text()
                    self.assertEqual(failure.exception.code, 1008)

    def test_disconnect_notifies_controller_and_allows_new_device(self):
        with TestClient(self.relay.app) as client:
            with client.websocket_connect("/controller", headers={
                "Authorization": "Bearer " + self.controller_token
            }) as controller:
                with client.websocket_connect("/device", headers={
                    "Authorization": "Bearer " + self.device_token
                }) as device:
                    controller.send_json({"id": "integration03", "diagnostic": "git-branch"})
                    self.assertEqual(device.receive_json()["id"], "integration03")
                self.assertEqual(controller.receive_json()["message"], "device disconnected")
                controller.send_json({"id": "integration04", "diagnostic": "git-branch"})
                self.assertEqual(controller.receive_json()["message"], "device offline")
                with client.websocket_connect("/device", headers={
                    "Authorization": "Bearer " + self.device_token
                }) as reconnected:
                    controller.send_json({"id": "integration05", "diagnostic": "git-branch"})
                    self.assertEqual(reconnected.receive_json()["id"], "integration05")
                    reconnected.send_json({"type": "result", "id": "integration05", "result": {
                        "exit_code": 0, "stdout": "recovered"
                    }})
                    self.assertEqual(controller.receive_json()["result"]["stdout"], "recovered")


if __name__ == "__main__":
    unittest.main()
