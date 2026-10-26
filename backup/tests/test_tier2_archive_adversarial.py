#!/usr/bin/env python3
"""Adversarial regression tests for Tier-2's read-only stream validator.

Run: python3 -m unittest backup.tests.test_tier2_archive_adversarial -v
No real rootfs, extraction, cloud access or credentials are involved.
"""
import gzip
import io
import pathlib
import subprocess
import sys
import tarfile
import unittest

ROOT = ".andronix/distros/debian/rootfs"
VALIDATOR = pathlib.Path(__file__).resolve().parents[1] / "validate_andronix2_archive.py"


def archive_bytes(extra=()):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, kind, link in [
            (".andronix", tarfile.DIRTYPE, ""),
            (".andronix/distros", tarfile.DIRTYPE, ""),
            (".andronix/distros/debian", tarfile.DIRTYPE, ""),
            (ROOT, tarfile.DIRTYPE, ""),
            ("start-debian.sh", tarfile.REGTYPE, ""),
            *extra,
        ]:
            entry = tarfile.TarInfo(name)
            entry.type = kind
            entry.linkname = link
            entry.size = 0
            tar.addfile(entry, io.BytesIO())
    return buf.getvalue()


class ArchiveValidationTests(unittest.TestCase):
    def run_validator(self, data):
        return subprocess.run(
            [sys.executable, str(VALIDATOR)],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=15, check=False,
        )

    def test_valid_fixture(self):
        self.assertEqual(self.run_validator(archive_bytes()).returncode, 0)

    def test_systemd_backslash_name(self):
        name = ROOT + "/etc/systemd/system/system-systemd\\x2dcryptsetup.slice"
        self.assertEqual(self.run_validator(archive_bytes([(name, tarfile.REGTYPE, "")])).returncode, 0)

    def test_absolute_debian_symlink_is_metadata(self):
        self.assertEqual(self.run_validator(archive_bytes([
            (ROOT + "/usr/bin/awk", tarfile.SYMTYPE, "/etc/alternatives/awk")
        ])).returncode, 0)

    def test_reject_adversarial_entries(self):
        cases = {
            "traversal": (ROOT + "/../outside", tarfile.REGTYPE, ""),
            "absolute": ("/tmp/escape", tarfile.REGTYPE, ""),
            "duplicate": ("start-debian.sh", tarfile.REGTYPE, ""),
            "hardlink": (ROOT + "/etc/hard", tarfile.LNKTYPE, "start-debian.sh"),
            "fifo": (ROOT + "/tmp/pipe", tarfile.FIFOTYPE, ""),
            "device": (ROOT + "/dev/test", tarfile.CHRTYPE, ""),
            "relative_escape": (ROOT + "/etc/bad", tarfile.SYMTYPE, "../../../../../../tmp"),
        }
        for case, entry in cases.items():
            with self.subTest(case=case):
                self.assertNotEqual(self.run_validator(archive_bytes([entry])).returncode, 0)

    def test_reject_symlink_parent(self):
        entries = [
            (ROOT + "/etc/link", tarfile.SYMTYPE, "/tmp"),
            (ROOT + "/etc/link/file", tarfile.REGTYPE, ""),
        ]
        self.assertNotEqual(self.run_validator(archive_bytes(entries)).returncode, 0)

    def test_reject_truncated_stream(self):
        data = archive_bytes([(ROOT + "/etc/issue", tarfile.REGTYPE, "")])
        self.assertNotEqual(self.run_validator(data[:max(10, len(data) // 2)]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
