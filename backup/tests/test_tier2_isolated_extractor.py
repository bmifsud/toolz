"""Synthetic-only tests for experimental isolated recovery; never touch live Debian."""
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from backup.extract_andronix2_isolated_experimental import extract, ROOT


def fixture(path, extra=()):
    with tarfile.open(path, "w:gz") as tf:
        for name, kind, target in [
            (".andronix", tarfile.DIRTYPE, ""),
            (".andronix/distros", tarfile.DIRTYPE, ""),
            (".andronix/distros/debian", tarfile.DIRTYPE, ""),
            (ROOT, tarfile.DIRTYPE, ""),
            ("start-debian.sh", tarfile.REGTYPE, ""),
            *extra,
        ]:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.linkname = target
            info.size = 0
            if kind == tarfile.DIRTYPE:
                info.mode = 0o755  # Real Debian directory entries carry searchable permissions.
            tf.addfile(info, io.BytesIO())


class IsolatedExtractorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.archive = self.base / "fixture.tar.gz"
        self.dest = self.base / "new-destination"

    def test_valid(self):
        fixture(self.archive, [(ROOT + "/etc/systemd\\x2dname", tarfile.REGTYPE, "")])
        self.assertEqual(extract(self.archive, self.dest), 6)
        self.assertTrue((self.dest / "start-debian.sh").exists())

    def test_absolute_symlink_preserved(self):
        fixture(self.archive, [(ROOT + "/etc/awk", tarfile.SYMTYPE, "/etc/alternatives/awk")])
        extract(self.archive, self.dest)
        self.assertEqual(os.readlink(self.dest / ROOT / "etc/awk"), "/etc/alternatives/awk")

    def test_reject_existing_destination(self):
        self.dest.mkdir()
        fixture(self.archive)
        with self.assertRaises(ValueError):
            extract(self.archive, self.dest)

    def test_reject_symlinked_destination_parent(self):
        (self.base / "link").symlink_to(self.base, target_is_directory=True)
        fixture(self.archive)
        with self.assertRaises(ValueError):
            extract(self.archive, self.base / "link" / "out")

    def test_reject_adversarial(self):
        for entry in [
            (ROOT + "/../escape", tarfile.REGTYPE, ""),
            ("/tmp/escape", tarfile.REGTYPE, ""),
            (ROOT + "/etc/evil", tarfile.SYMTYPE, "../../../../../../tmp"),
            (ROOT + "/etc/fifo", tarfile.FIFOTYPE, ""),
            ("start-debian.sh", tarfile.REGTYPE, ""),
        ]:
            with self.subTest(entry=entry):
                dest = self.base / "out"
                fixture(self.archive, [entry])
                with self.assertRaises((ValueError, FileExistsError)):
                    extract(self.archive, dest)
                if dest.exists():
                    # Remove only this synthetic fixture destination.
                    import shutil
                    shutil.rmtree(dest)


if __name__ == "__main__":
    unittest.main()
