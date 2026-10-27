import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).with_name("github_issue_worker.py")
spec = importlib.util.spec_from_file_location("worker", path)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
NOW = dt.datetime(2026, 10, 27, 14, 0, tzinfo=dt.timezone.utc)
def comment(author="bmifsud", diagnostic="git-branch", expires="2026-10-27T14:05:00Z"):
    return {"id": 101, "user": {"login": author}, "created_at": "2026-10-27T13:59:00Z",
            "body": worker.REQUEST + json.dumps({"id": "test-0001", "diagnostic": diagnostic, "expires_at": expires})}
class WorkerTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(worker.validate(comment(), NOW)["diagnostic"], "git-branch")
    def test_untrusted_author(self):
        self.assertIsNone(worker.validate(comment(author="attacker"), NOW))
    def test_disallowed_command(self):
        self.assertIsNone(worker.validate(comment(diagnostic="adb"), NOW))
    def test_expired(self):
        self.assertIsNone(worker.validate(comment(expires="2026-10-27T13:59:59Z"), NOW))
    def test_far_future(self):
        self.assertIsNone(worker.validate(comment(expires="2026-10-27T14:30:00Z"), NOW))
    def test_invalid_json(self):
        c = comment()
        c["body"] = worker.REQUEST + "{"
        self.assertIsNone(worker.validate(c, NOW))
    def test_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(worker, "gh", side_effect=[json.dumps([comment()]), "ok", json.dumps([comment()])]) as gh, patch.object(worker, "run", return_value={"exit_code": 0}) as run:
                worker.poll_once(Path(folder), NOW)
                worker.poll_once(Path(folder), NOW)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(gh.call_count, 3)
    def test_duplicate_request_id_different_comment(self):
        second = comment()
        second["id"] = 102
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(worker, "gh", side_effect=[
                json.dumps([comment(), second]), "ok"
            ]) as gh, patch.object(worker, "run", return_value={"exit_code": 0}) as run:
                worker.poll_once(Path(folder), NOW)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(gh.call_count, 2)

    def test_receipt_contains_timing_and_command(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def fake_gh(*args):
                calls.append(args)
                return json.dumps([comment()]) if len(calls) == 1 else 'ok'
            with patch.object(worker, 'gh', side_effect=fake_gh), patch.object(worker, 'run', return_value={'exit_code': 0, 'stdout': 'main\\n', 'stderr': ''}):
                worker.poll_once(Path(folder), NOW)
            posted = json.loads(calls[1][-1].split(worker.RESULT, 1)[1])
            self.assertEqual(posted['receipt']['command'], 'git branch --show-current')
            self.assertGreaterEqual(posted['receipt']['duration_ms'], 0)
            self.assertIn('started_at', posted['receipt'])
            self.assertIn('finished_at', posted['receipt'])
            self.assertEqual(posted['result']['exit_code'], 0)

    def test_replay_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(worker, "gh", side_effect=[
                json.dumps([comment()]), "ok", json.dumps([comment()])
            ]), patch.object(worker, "run", return_value={"exit_code": 0}) as run:
                worker.poll_once(Path(folder), NOW)
                worker.poll_once(Path(folder), NOW)
                self.assertEqual(run.call_count, 1)

if __name__ == "__main__":
    unittest.main()
