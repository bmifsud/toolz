import tempfile
import unittest
from pathlib import Path
from task_controller import TaskQueue


class TaskControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.queue = TaskQueue(Path(self.tmp.name) / "tasks.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_allowlist_and_timeout(self):
        with self.assertRaises(ValueError):
            self.queue.submit("sh -c whoami")
        with self.assertRaises(ValueError):
            self.queue.submit("git-branch", timeout=301)

    def test_durable_receipt(self):
        task_id = self.queue.submit("git-branch")
        claimed = self.queue.claim()
        self.assertEqual(claimed["id"], task_id)
        self.assertTrue(self.queue.complete(task_id, {"exit_code": 0, "stdout": "main", "secret": "ignored"}, success=True))
        fresh = TaskQueue(Path(self.tmp.name) / "tasks.sqlite")
        self.assertEqual(fresh.get(task_id)["state"], "succeeded")
        self.assertNotIn("secret", fresh.get(task_id)["result"])

    def test_cancel_rejects_late_completion(self):
        task_id = self.queue.submit("git-branch")
        self.queue.claim()
        self.assertTrue(self.queue.cancel(task_id))
        self.assertFalse(self.queue.complete(task_id, {"exit_code": 0}, success=True))
        self.assertEqual(self.queue.get(task_id)["state"], "cancelled")

    def test_claim_once(self):
        task_id = self.queue.submit("git-branch")
        self.assertEqual(self.queue.claim()["id"], task_id)
        self.assertIsNone(self.queue.claim())

    def test_expired_task_not_dispatched(self):
        from unittest.mock import patch
        task_id = self.queue.submit("git-branch", timeout=1)
        with patch("task_controller.time.time", return_value=self.queue.get(task_id)["deadline"] + 1):
            self.assertIsNone(self.queue.claim())
        self.assertEqual(self.queue.get(task_id)["state"], "failed")


if __name__ == "__main__":
    unittest.main()
