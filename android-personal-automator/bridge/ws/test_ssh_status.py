"""Read-only SSH status diagnostic contract tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from readonly_runner import COMMANDS


class SSHStatusTests(unittest.TestCase):
    def test_ssh_status_is_allowlisted_and_local_only(self):
        command = COMMANDS["ssh-status"]
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], "-c")
        self.assertIn("127.0.0.1", command[2])
        self.assertIn("8022", command[2])
        self.assertNotIn("shell=True", command[2])


if __name__ == "__main__":
    unittest.main()
