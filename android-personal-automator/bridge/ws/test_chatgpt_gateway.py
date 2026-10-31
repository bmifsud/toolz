"""Offline gateway security tests; no live tablet access."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("chatgpt_gateway", Path(__file__).with_name("chatgpt_gateway.py"))
gateway = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gateway
spec.loader.exec_module(gateway)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"BRIDGE_GATEWAY_TOKEN": "test-secret"}, clear=False)
        self.env.start()
        self.client = TestClient(gateway.app)

    def tearDown(self):
        self.env.stop()

    def test_missing_or_bad_token_denied(self):
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            self.assertEqual(self.client.post("/diagnostic", json={"diagnostic": "git-branch"}, headers=headers).status_code, 401)

    def test_unknown_command_denied_without_dispatch(self):
        with patch.object(gateway, "execute", new_callable=AsyncMock) as dispatch:
            response = self.client.post("/diagnostic", json={"diagnostic": "rm -rf /"}, headers={"Authorization": "Bearer test-secret"})
            self.assertEqual(response.status_code, 400)
            dispatch.assert_not_awaited()

    def test_allowlisted_request_returns_bounded_result(self):
        with patch.object(gateway, "execute", new_callable=AsyncMock, return_value={"id": "abc", "result": {"exit_code": 0, "stdout": "main", "stderr": "", "secret": "omit"}, "extra": "omit"}):
            response = self.client.post("/diagnostic", json={"diagnostic": "git-branch"}, headers={"Authorization": "Bearer test-secret"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["stdout"], "main")
            self.assertNotIn("secret", str(response.json()))

    def test_transport_failure_is_generic(self):
        with patch.object(gateway, "execute", new_callable=AsyncMock, side_effect=TimeoutError()):
            response = self.client.post("/diagnostic", json={"diagnostic": "git-branch"}, headers={"Authorization": "Bearer test-secret"})
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("token", response.text)


if __name__ == "__main__":
    unittest.main()
