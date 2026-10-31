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

    def test_success_requires_verified_zero_exit_code(self):
        task_id = self.queue.submit("git-branch")
        self.queue.claim()
        for result in ({"exit_code": 1}, {"exit_code": None},
                       {"exit_code": False}, {"exit_code": "0"}, {}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                self.queue.complete(task_id, result, success=True)
            self.assertEqual(self.queue.get(task_id)["state"], "running")
        with self.assertRaises(ValueError):
            self.queue.complete(task_id, {"exit_code": 0}, success="false")
        self.assertEqual(self.queue.get(task_id)["state"], "running")
        # Nonzero exits must be persistable as failures.
        self.assertTrue(self.queue.complete(task_id, {"exit_code": 1}, success=False))
        self.assertEqual(self.queue.get(task_id)["state"], "failed")

    def test_unverified_termination_fails_closed_even_with_zero_exit(self):
        task_id = self.queue.submit("git-branch")
        self.queue.claim()
        self.assertTrue(self.queue.complete(task_id, {"exit_code": 0, "stderr": "termination unverified"}, success=False))
        self.assertEqual(self.queue.get(task_id)["state"], "failed")

    def test_explicit_worker_error_cannot_be_recorded_as_success(self):
        task_id = self.queue.submit("git-branch")
        self.queue.claim()
        for error in ("worker termination unverified", "", False):
            with self.subTest(error=error), self.assertRaises(ValueError):
                self.queue.complete(task_id, {"exit_code": 0, "error": error}, success=True)
            self.assertEqual(self.queue.get(task_id)["state"], "running")
        # Explicit failure is retained, including its bounded error reason.
        reason = "worker termination unverified"
        self.assertTrue(self.queue.complete(
            task_id, {"exit_code": 0, "error": reason, "secret": "ignored"}, success=False))
        import json
        receipt = json.loads(self.queue.get(task_id)["result"])
        self.assertEqual(self.queue.get(task_id)["state"], "failed")
        self.assertEqual(receipt["error"], reason)
        self.assertNotIn("secret", receipt)

    def test_error_reason_is_bounded(self):
        import json
        task_id = self.queue.submit("git-branch")
        self.queue.claim()
        self.assertTrue(self.queue.complete(
            task_id, {"exit_code": 126, "error": "x" * 5000}, success=False))
        receipt = json.loads(self.queue.get(task_id)["result"])
        self.assertEqual(receipt["error"], "x" * 256)

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


    def test_expired_running_lease_rejects_completion(self):
        from unittest.mock import patch
        task_id = self.queue.submit("git-branch", timeout=120)
        self.queue.claim(lease_seconds=1)
        with patch("task_controller.time.time", return_value=self.queue.get(task_id)["created"] + 2):
            self.assertFalse(self.queue.complete(task_id, {"exit_code": 0}, success=True))

    def test_crash_recovery_fails_closed(self):
        from unittest.mock import patch
        task_id = self.queue.submit("git-branch", timeout=120)
        self.queue.claim(lease_seconds=1)
        restarted = TaskQueue(Path(self.tmp.name) / "tasks.sqlite")
        with patch("task_controller.time.time", return_value=self.queue.get(task_id)["created"] + 2):
            self.assertIsNone(restarted.claim())
        self.assertEqual(restarted.get(task_id)["state"], "failed")
        self.assertEqual(restarted.get(task_id)["attempt"], 1)

    def test_cancel_queued_task_never_claimed(self):
        task_id = self.queue.submit("git-branch")
        self.assertTrue(self.queue.cancel(task_id))
        self.assertIsNone(self.queue.claim())
        self.assertEqual(self.queue.get(task_id)["state"], "cancelled")

    def test_concurrent_claims_only_one_wins(self):
        from concurrent.futures import ThreadPoolExecutor
        task_id = self.queue.submit("git-branch")
        def claim_from_fresh_connection(_):
            return TaskQueue(Path(self.tmp.name) / "tasks.sqlite").claim()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim_from_fresh_connection, range(8)))
        self.assertEqual([r["id"] for r in results if r], [task_id])

if __name__ == "__main__":
    unittest.main()
