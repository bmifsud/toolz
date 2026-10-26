"""Regression tests for streamed Debian archive validation."""
import io
import pathlib
import subprocess
import sys
import tarfile
import unittest

VALIDATOR = pathlib.Path(__file__).resolve().parents[1] / "validate_andronix2_archive.py"
ROOT = ".andronix/distros/debian/rootfs"


def archive_bytes(extra):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name in [ROOT, *extra]:
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
        launcher = tarfile.TarInfo("start-debian.sh")
        launcher.size = 0
        tar.addfile(launcher)
    return buffer.getvalue()


def run(blob):
    return subprocess.run([sys.executable, str(VALIDATOR)], input=blob, capture_output=True)


class ValidatorTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(run(archive_bytes([])).returncode, 0)

    def test_absolute_debian_symlinks(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for name in (ROOT, ROOT + "/etc", ROOT + "/etc/alternatives"):
                info = tarfile.TarInfo(name)
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            for i in range(1000):
                info = tarfile.TarInfo(ROOT + "/etc/alternatives/link" + str(i))
                info.type = tarfile.SYMTYPE
                info.linkname = "/usr/bin/mawk"
                tar.addfile(info)
            launcher = tarfile.TarInfo("start-debian.sh")
            launcher.size = 0
            tar.addfile(launcher)
        self.assertEqual(run(buffer.getvalue()).returncode, 0)

    def test_reject_parent_traversal(self):
        self.assertNotEqual(run(archive_bytes([ROOT + "/../outside"])).returncode, 0)

    def test_reject_unexpected_file(self):
        self.assertNotEqual(run(archive_bytes(["outside"])).returncode, 0)

    def test_reject_duplicate(self):
        self.assertNotEqual(run(archive_bytes([ROOT])).returncode, 0)

    def test_reject_member_under_symlink(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            root = tarfile.TarInfo(ROOT)
            root.type = tarfile.DIRTYPE
            tar.addfile(root)
            link = tarfile.TarInfo(ROOT + "/escape")
            link.type = tarfile.SYMTYPE
            link.linkname = "/tmp"
            tar.addfile(link)
            child = tarfile.TarInfo(ROOT + "/escape/payload")
            child.size = 0
            tar.addfile(child)
            launcher = tarfile.TarInfo("start-debian.sh")
            launcher.size = 0
            tar.addfile(launcher)
        self.assertNotEqual(run(buffer.getvalue()).returncode, 0)

    def test_reject_hardlink(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            root = tarfile.TarInfo(ROOT)
            root.type = tarfile.DIRTYPE
            tar.addfile(root)
            hardlink = tarfile.TarInfo(ROOT + "/hardlink")
            hardlink.type = tarfile.LNKTYPE
            hardlink.linkname = "start-debian.sh"
            tar.addfile(hardlink)
            launcher = tarfile.TarInfo("start-debian.sh")
            launcher.size = 0
            tar.addfile(launcher)
        self.assertNotEqual(run(buffer.getvalue()).returncode, 0)


if __name__ == "__main__":
    unittest.main()
