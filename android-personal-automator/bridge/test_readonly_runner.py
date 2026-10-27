import importlib.util
import pathlib
import unittest
from unittest.mock import patch
import subprocess

path = pathlib.Path(__file__).with_name("readonly_runner.py")
spec = importlib.util.spec_from_file_location("readonly_runner", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def test_reject_unknown(self):
        with self.assertRaises(ValueError):
            runner.run("sh -c id")

    @patch.object(runner.subprocess, "run")
    def test_allowlist_argv_and_bounds(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], 0, "a" * 6000, "b" * 2000)
        result = runner.run("adb")
        mock_run.assert_called_once_with(["adb", "devices"], capture_output=True,
                                         text=True, timeout=10, check=False)
        self.assertEqual(len(result["stdout"]), 4096)
        self.assertEqual(len(result["stderr"]), 1024)

    @patch.object(runner.subprocess, "run", side_effect=subprocess.TimeoutExpired(["adb"], 10))
    def test_timeout(self, _):
        self.assertEqual(runner.run("adb")["error"], "timeout")

    @patch.object(runner.subprocess, "run")
    def test_all_commands_are_fixed_argv(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
        for name in runner.COMMANDS:
            runner.run(name)
        self.assertEqual(mock_run.call_count, len(runner.COMMANDS))
        self.assertTrue(all(isinstance(v, list) for v in runner.COMMANDS.values()))

if __name__ == "__main__":
    unittest.main()
