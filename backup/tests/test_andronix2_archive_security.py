"""Adversarial tests for the read-only Andronix archive validator."""
import io
import pathlib
import subprocess
import tarfile

VALIDATOR = pathlib.Path(__file__).resolve().parents[1] / "validate_andronix2_archive.py"
ROOT = ".andronix/distros/debian/rootfs"

def check(entries):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        for name, kind, target in entries:
            info = tarfile.TarInfo(name)
            info.type = {"dir": tarfile.DIRTYPE, "file": tarfile.REGTYPE, "sym": tarfile.SYMTYPE, "hard": tarfile.LNKTYPE}[kind]
            if kind in ("sym", "hard"):
                info.linkname = target
            tar.addfile(info)
    return subprocess.run(["python3", str(VALIDATOR)], input=out.getvalue(), capture_output=True)

BASE = [(ROOT, "dir", ""), ("start-debian.sh", "file", "")]

def test_valid_fixture():
    assert check(BASE + [(ROOT + "/etc", "dir", ""), (ROOT + "/etc/config", "file", "")]).returncode == 0

def test_reject_traversal():
    assert check(BASE + [(ROOT + "/../../outside", "file", "")]).returncode != 0

def test_reject_absolute_symlink():
    assert check(BASE + [(ROOT + "/etc/link", "sym", "/tmp/outside")]).returncode != 0

def test_reject_symlink_parent():
    assert check(BASE + [(ROOT + "/etc/link", "sym", "../etc"), (ROOT + "/etc/link/file", "file", "")]).returncode != 0

def test_reject_hardlinks():
    assert check(BASE + [(ROOT + "/etc/link", "hard", "start-debian.sh")]).returncode != 0

def test_reject_duplicate_members():
    assert check(BASE + [(ROOT, "dir", "")]).returncode != 0

def test_reject_missing_launcher():
    assert check([(ROOT, "dir", "")]).returncode != 0

def test_reject_corruption():
    assert subprocess.run(["python3", str(VALIDATOR)], input=b"not gzip", capture_output=True).returncode != 0
