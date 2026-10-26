"""Synthetic tests of staged publication; no real rootfs or backup touched."""
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import errno

from backup.recover_andronix2_transactional_experimental import recover_synthetic
from backup.tests.test_tier2_isolated_extractor import fixture, ROOT


class TransactionalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.archive = self.base / "archive.tar.gz"
        self.final = self.base / "published"

    def test_success_publishes(self):
        fixture(self.archive)
        self.assertEqual(recover_synthetic(self.archive, self.final), 5)
        self.assertTrue((self.final / "start-debian.sh").exists())
        self.assertFalse(list(self.base.glob("*.incomplete")))

    def test_failure_never_publishes(self):
        fixture(self.archive, [(ROOT + "/../../escape", tarfile.REGTYPE, "")])
        with self.assertRaises(ValueError):
            recover_synthetic(self.archive, self.final)
        self.assertFalse(self.final.exists())
        stages = list(self.base.glob(".tier2-*.incomplete"))
        self.assertEqual(len(stages), 1)

    def test_corruption_never_publishes(self):
        self.archive.write_bytes(b"invalid gzip")
        with self.assertRaises((tarfile.TarError, OSError)):
            recover_synthetic(self.archive, self.final)
        self.assertFalse(self.final.exists())

    def test_competing_destination_is_not_replaced(self):
        fixture(self.archive)
        from backup import recover_andronix2_transactional_experimental as module
        original = module.publish_noreplace

        def competing_publish(staging, final):
            final.mkdir()
            (final / "sentinel").write_text("other process")
            return original(staging, final)

        with mock.patch.object(module, "publish_noreplace", side_effect=competing_publish):
            with self.assertRaises(OSError) as ctx:
                recover_synthetic(self.archive, self.final)
        self.assertEqual(ctx.exception.errno, errno.EEXIST)
        self.assertEqual((self.final / "sentinel").read_text(), "other process")
        self.assertEqual(len(list(self.base.glob(".tier2-*.incomplete"))), 1)

    def test_existing_final_is_preserved(self):
        fixture(self.archive)
        self.final.mkdir()
        sentinel = self.final / "sentinel"
        sentinel.write_text("unchanged")
        with self.assertRaises(ValueError):
            recover_synthetic(self.archive, self.final)
        self.assertEqual(sentinel.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
