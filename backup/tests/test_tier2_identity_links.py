"""Identity resolution uses archive metadata, never the host filesystem."""
import io
import pathlib
import subprocess
import sys
import tarfile

import pytest

ROOT = ".andronix/distros/debian/rootfs"
VALIDATOR = pathlib.Path(__file__).resolve().parents[1] / "validate_andronix2_archive.py"


def validate(target="../usr/lib/os-release", extra=None, reverse=False, strict=True):
    entries = [
        ("etc/os-release", tarfile.SYMTYPE, target),
        ("usr/lib/os-release", tarfile.REGTYPE, b"ID=debian\n" + b"#" * 277),
    ] if extra is None else [("etc/os-release", tarfile.SYMTYPE, target), *extra]
    if reverse:
        entries.reverse()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        for name, kind, value in [
            (ROOT, tarfile.DIRTYPE, b""),
            ("start-debian.sh", tarfile.REGTYPE, b""),
            (ROOT + "/etc/passwd", tarfile.REGTYPE, b"root:x:0:0::/:/bin/sh\n"),
            (ROOT + "/etc/debian_version", tarfile.REGTYPE, b"13.0\n"),
            *[(ROOT + "/" + name, kind, value) for name, kind, value in entries],
        ]:
            member = tarfile.TarInfo(name)
            member.type = kind
            if kind == tarfile.SYMTYPE:
                member.linkname = value
                archive.addfile(member)
            else:
                member.size = len(value)
                archive.addfile(member, io.BytesIO(value))
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *(["--require-debian-identity"] if strict else [])],
        input=buf.getvalue(), capture_output=True, timeout=10,
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("target", ["../usr/lib/os-release", "/usr/lib/os-release"])
def test_debian13_identity_layout(reverse, target):
    result = validate(target=target, reverse=reverse)
    assert result.returncode == 0, result.stderr


def test_identity_link_chain_and_directory_link():
    result = validate(extra=[
        ("usr/lib", tarfile.SYMTYPE, "share"),
        ("usr/share/os-release", tarfile.SYMTYPE, "/identity"),
        ("identity", tarfile.REGTYPE, b"ID=debian\n"),
    ])
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("target,extra", [
    ("../usr/lib/os-release", []),
    ("/etc/hosts", []),  # Exists on host, absent from archive.
    ("os-release", []),
    ("../identity", [("identity", tarfile.SYMTYPE, "etc/os-release")]),
    ("../../rootfs/usr/lib/os-release", [("usr/lib/os-release", tarfile.REGTYPE, b"x")]),
    ("/../usr/lib/os-release", [("usr/lib/os-release", tarfile.REGTYPE, b"x")]),
    ("../../../../../start-debian.sh", []),
    ("../usr/lib/os-release", [("usr/lib/os-release", tarfile.REGTYPE, b"")]),
    ("../usr/lib/os-release", [("usr/lib/os-release", tarfile.DIRTYPE, b"")]),
    ("../usr/lib/os-release", [("usr/lib/os-release", tarfile.FIFOTYPE, b"")]),
    ("../usr/lib/os-release", [("usr", tarfile.REGTYPE, b"x"), ("usr/lib/os-release", tarfile.REGTYPE, b"x")]),
    ("../alias/../usr/lib/os-release", [("alias", tarfile.SYMTYPE, "/"), ("usr/lib/os-release", tarfile.REGTYPE, b"x")]),
    ("../missing/../usr/lib/os-release", [("usr/lib/os-release", tarfile.REGTYPE, b"x")]),
    ("../usr/lib/os-release/", [("usr/lib/os-release", tarfile.REGTYPE, b"x")]),
])
def test_reject_unsafe_identity(target, extra, strict):
    result = validate(target, extra, strict=strict)
    assert result.returncode != 0
    assert b"Unsafe archive:" in result.stderr
