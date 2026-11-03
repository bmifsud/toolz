import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from watchdog import check, run

class WatchdogTests(unittest.TestCase):
    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check({"state_dir": d}), "missing_heartbeat")
    def test_healthy_and_stale(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "heartbeat.json"
            p.write_text(json.dumps({"timestamp": 100}))
            c = {"state_dir": d, "stale_seconds": 20}
            self.assertEqual(check(c, now=110), "healthy")
            self.assertEqual(check(c, now=200), "stale")
    def test_dry_run_does_not_launch(self):
        with tempfile.TemporaryDirectory() as d:
            c = {"state_dir": d}
            self.assertEqual(run(c)["status"], "missing_heartbeat")
    def test_missing_command_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            c = {"state_dir": d}
            self.assertEqual(run(c, True)["action"], "no_recovery_command")

if __name__ == "__main__":
    unittest.main()
