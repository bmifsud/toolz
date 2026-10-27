import importlib.util
import pathlib
import unittest
from unittest.mock import patch

PATH = pathlib.Path(__file__).with_name("orchestration_adapter.py")
spec = importlib.util.spec_from_file_location("orchestration_adapter", PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

class AdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_receipt_redacts_output(self):
        r = adapter.receipt("orch-123", "git-branch", {"type":"result", "result":{"exit_code":0,"stdout":"private data","stderr":"secret"}})
        self.assertEqual(r["exit_code"], 0)
        self.assertFalse(r["verified_origin"])
        self.assertNotIn("private data", str(r))
        self.assertNotIn("secret", str(r))
        self.assertEqual(len(r["result_sha256"]), 64)

    async def test_rejects_unallowlisted_without_network(self):
        with self.assertRaises(ValueError):
            await adapter.run("shell", token="x"*40)

    async def test_rejects_missing_token_without_network(self):
        with self.assertRaises(ValueError):
            await adapter.run("git-branch", token="")

    async def test_rejects_plaintext_transport(self):
        with self.assertRaises(ValueError):
            await adapter.run("git-branch", token="x"*40, url="ws://localhost:8765")

if __name__ == "__main__":
    unittest.main()
