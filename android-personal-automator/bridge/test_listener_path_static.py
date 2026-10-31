#!/usr/bin/env python3
"""Regression checks for secure bridge listener selection."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
START = (ROOT / "termux-bridge-start-secure.sh").read_text()

class ListenerSelectionTests(unittest.TestCase):
    def test_explicit_override_is_preserved(self):
        self.assertIn('if [[ -z "${BRIDGE_DEVICE_SCRIPT:-}" ]]', START)
        self.assertIn('export BRIDGE_DEVICE_SCRIPT', START)

    def test_installed_and_repository_locations(self):
        self.assertIn('$HOME/toolz-ws-bridge/device.py', START)
        self.assertIn('$(dirname "$0")/ws/device.py', START)

    def test_missing_listener_fails_closed(self):
        self.assertIn('exit 1', START)
        self.assertIn('Bridge listener unreadable', START)

if __name__ == "__main__":
    unittest.main()
