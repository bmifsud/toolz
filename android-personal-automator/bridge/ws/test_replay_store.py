"""Host-side replay persistence regressions; NOT emulator/device end-to-end."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from replay_store import ReplayStore


class ReplayStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "private" / "replay.sqlite3"
        self.store = ReplayStore(self.path, max_ids=3)

    def test_duplicate_rejected_before_and_after_restart(self):
        self.assertTrue(self.store.claim("req_12345678"))
        self.assertFalse(self.store.claim("req_12345678"))
        restarted = ReplayStore(self.path, max_ids=3)
        self.assertFalse(restarted.claim("req_12345678"))
        self.assertTrue(restarted.claim("req_87654321"))

    def test_capacity_fails_closed_without_pruning_old_ids(self):
        for i in range(3):
            self.assertTrue(self.store.claim(f"request_{i:08d}"))
        self.assertFalse(self.store.claim("request_99999999"))
        self.assertFalse(ReplayStore(self.path, max_ids=3).claim("request_99999999"))
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM requests").fetchone()[0], 3)

    def test_reject_malformed_and_non_ascii_ids(self):
        for value in (None, 1, "", "short", "a" * 65, "a" * 7 + "!", "é" * 8,
                      "request id", "../request_123", "req/12345678"):
            with self.subTest(value=value):
                self.assertFalse(self.store.claim(value))
        self.assertTrue(self.store.claim("Valid_ID-123"))

    def test_database_corruption_fails_closed(self):
        self.path.write_bytes(b"not a SQLite database")
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.claim("req_12345678")

    def test_permissions_private(self):
        if os.name != "posix":
            self.skipTest("POSIX permissions required")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)

    def test_symlink_database_rejected(self):
        other = Path(self.tmp.name) / "other.sqlite3"
        other.write_bytes(b"")
        link = Path(self.tmp.name) / "link.sqlite3"
        link.symlink_to(other)
        with self.assertRaises(OSError):
            ReplayStore(link)

    def test_symlink_swap_after_initialization_fails_closed(self):
        # An attacker with same-UID filesystem access must not redirect writes
        # to another SQLite database after ReplayStore construction.
        other = Path(self.tmp.name) / "other.sqlite3"
        with sqlite3.connect(other) as db:
            db.execute("CREATE TABLE requests (id TEXT PRIMARY KEY, created_at INTEGER NOT NULL)")
        self.path.rename(self.path.with_suffix(".saved"))
        self.path.symlink_to(other)
        with self.assertRaises(OSError):
            self.store.claim("req_12345678")
        with sqlite3.connect(other) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM requests").fetchone()[0], 0)

    def test_nonregular_file_swap_fails_closed(self):
        self.path.unlink()
        self.path.mkdir()
        with self.assertRaises(OSError):
            self.store.claim("req_12345678")

    def test_relaxed_permissions_after_initialization_fail_closed(self):
        self.path.chmod(0o644)
        with self.assertRaises(OSError):
            self.store.claim("req_12345678")

    def test_invalid_capacity_rejected(self):
        for value in (0, -1, True, 100_001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ReplayStore(self.path, max_ids=value)


if __name__ == "__main__":
    unittest.main()
