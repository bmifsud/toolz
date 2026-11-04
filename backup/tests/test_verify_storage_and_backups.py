"""Unit and isolated integration tests for backup/verify_storage_and_backups.py."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

BACKUP_DIR = Path(__file__).resolve().parents[1]
if str(BACKUP_DIR) not in sys.path:
    sys.path.insert(0, str(BACKUP_DIR))

import verify_storage_and_backups as vsb  # noqa: E402


def _make_completed(
    stdout: bytes = b"",
    stderr: bytes = b"",
    returncode: int = 0,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["mock"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_redact_sensitive_text():
    raw = "BACKUP_PASSPHRASE=super-secret-value token: abc12345 normal=ok"
    redacted = vsb.redact_sensitive_text(raw)
    assert "super-secret-value" not in redacted
    assert "abc12345" not in redacted
    assert "BACKUP_PASSPHRASE=[REDACTED]" in redacted
    assert "token=[REDACTED]" in redacted
    assert "normal=ok" in redacted


def test_collect_filesystem_df_parses_output(tmp_path):
    sample_df = (
        b"Filesystem     1B-blocks        Used   Available Use% Mounted on\n"
        b"/dev/block/dm-51 118049734656 83316748288 34598768640  71% /\n"
    )
    entries = vsb.collect_filesystem_df(
        paths=(str(tmp_path),),
        runner=lambda cmd: _make_completed(stdout=sample_df),
    )
    assert len(entries) == 1
    assert entries[0]["filesystem"] == "/dev/block/dm-51"
    assert entries[0]["total_bytes"] == 118049734656
    assert entries[0]["used_bytes"] == 83316748288
    assert entries[0]["avail_bytes"] == 34598768640
    assert entries[0]["use_percent"] == "71%"
    assert entries[0]["mountpoint"] == "/"


def test_collect_directory_usage_handles_existing_and_missing(tmp_path):
    existing = tmp_path / "data"
    existing.mkdir()
    missing = tmp_path / "missing"

    def fake_runner(cmd):
        return _make_completed(stdout=f"4096\t{existing}\n".encode())

    usage = vsb.collect_directory_usage(
        paths=(str(existing), str(missing)),
        runner=fake_runner,
    )
    assert usage == [
        {"path": str(existing), "exists": True, "size_bytes": 4096},
        {"path": str(missing), "exists": False, "size_bytes": 0},
    ]


def test_inspect_gpg_header_with_real_aes256_ciphertext(
    tmp_path, short_gnupg_home
):
    plain = tmp_path / "payload.txt"
    plain.write_text("isolated test payload")
    enc = tmp_path / "payload.txt.gpg"
    env = {"GNUPGHOME": str(short_gnupg_home), "PATH": "/usr/bin:/bin"}
    subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "unit-test-pass",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "-o",
            str(enc),
            str(plain),
        ],
        env=env,
        check=True,
    )

    info = vsb.inspect_gpg_header(enc)
    assert info["valid_openpgp_symmetric"] is True
    assert info["cipher_algo"] == "AES256"
    assert info["version"] == 4
    assert info["s2k_type"] == 3
    assert info["has_mdc"] is True
    assert info["error"] is None


def test_inspect_gpg_header_rejects_invalid_or_missing(tmp_path):
    missing = vsb.inspect_gpg_header(tmp_path / "nope.gpg")
    assert missing["valid_openpgp_symmetric"] is False
    assert missing["error"] == "file_missing"

    short_file = tmp_path / "short.gpg"
    short_file.write_bytes(b"short")
    short_info = vsb.inspect_gpg_header(short_file)
    assert short_info["valid_openpgp_symmetric"] is False
    assert short_info["error"] == "truncated_header"

    not_pgp = tmp_path / "plain.txt"
    not_pgp.write_bytes(b"hello world this is plain textnot pgp")
    not_pgp_info = vsb.inspect_gpg_header(not_pgp)
    assert not_pgp_info["valid_openpgp_symmetric"] is False
    assert not_pgp_info["error"] == "not_openpgp_packet"


def test_verify_archive_against_remote_and_stream_sha256(
    tmp_path, short_gnupg_home
):
    archive = tmp_path / "cline_omniroute_backup_20261104_034208.tar.gz.gpg"
    plain = tmp_path / "sample.tar.gz"
    plain.write_bytes(b"sample-archive-bytes-for-hashing")
    subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "unit-test-pass",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "-o",
            str(archive),
            str(plain),
        ],
        env={"GNUPGHOME": str(short_gnupg_home), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    raw_bytes = archive.read_bytes()
    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    catalog = {
        archive.name: {
            "name": archive.name,
            "size_bytes": len(raw_bytes),
            "is_dir": False,
            "md5": expected_md5,
            "sha256": None,
            "id": "gdrive-obj-1",
            "mod_time": "2026-11-04T02:42:12.347Z",
            "mime_type": "application/pgp-encrypted",
        }
    }

    def fake_runner(cmd):
        if cmd[:2] == ["rclone", "cat"]:
            return _make_completed(stdout=raw_bytes)
        raise AssertionError(f"Unexpected command: {cmd}")

    res = vsb.verify_archive_against_remote(
        archive,
        "gdrive:ClineOmniRouteBackups",
        remote_catalog=catalog,
        stream_readback=True,
        runner=fake_runner,
    )
    assert res["status"] == "PASS"
    assert res["reasons"] == []
    assert res["local_sha256"] == expected_sha256
    assert res["remote_stream_sha256"] == expected_sha256
    assert res["sha256_match"] is True
    assert res["md5_match"] is True
    assert res["size_match"] is True


def test_verify_archive_against_remote_detects_mismatch(
    tmp_path, short_gnupg_home
):
    archive = tmp_path / "cline_omniroute_backup_20261104_034208.tar.gz.gpg"
    plain = tmp_path / "sample.tar.gz"
    plain.write_bytes(b"sample-archive-bytes")
    subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "unit-test-pass",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "-o",
            str(archive),
            str(plain),
        ],
        env={"GNUPGHOME": str(short_gnupg_home), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    catalog = {
        archive.name: {
            "name": archive.name,
            "size_bytes": archive.stat().st_size,
            "is_dir": False,
            "md5": "00000000000000000000000000000000",
            "sha256": None,
            "id": "gdrive-obj-1",
            "mod_time": "2026-11-04T02:42:12.347Z",
            "mime_type": "application/pgp-encrypted",
        }
    }
    res = vsb.verify_archive_against_remote(
        archive,
        "gdrive:ClineOmniRouteBackups",
        remote_catalog=catalog,
        stream_readback=True,
        runner=lambda cmd: _make_completed(stdout=b"corrupted-remote-stream"),
    )
    assert res["status"] == "FAIL"
    assert "remote_md5_mismatch" in res["reasons"]
    assert "remote_stream_sha256_mismatch" in res["reasons"]


def test_detect_tier1_retention_blockers(tmp_path):
    t1_dir = tmp_path / "tier1"
    t1_dir.mkdir()
    names = [
        "cline_omniroute_backup_20261028_210001.tar.gz.gpg",
        "cline_omniroute_backup_20261028_220007.tar.gz.gpg",
        "cline_omniroute_backup_20261104_034208.tar.gz.gpg",
    ]
    for name in names:
        (t1_dir / name).write_bytes(b"cipher")

    remote_catalog = {
        "cline_omniroute_backup_20261028_220007.tar.gz.gpg": {"is_dir": False},
        "cline_omniroute_backup_20261104_034208.tar.gz.gpg": {"is_dir": False},
    }
    diag = vsb.detect_tier1_retention_blockers(t1_dir, remote_catalog)
    assert diag["total_matching_archives"] == 3
    assert diag["newest_archive"] == names[-1]
    assert diag["retention_blocked"] is True
    assert diag["missing_on_remote"] == [names[0]]
    assert diag["first_blocking_archive"] == names[0]


def test_cli_main_skip_remote(tmp_path, short_gnupg_home, capsys):
    t1_dir = tmp_path / "t1"
    t2_dir = tmp_path / "t2"
    t1_dir.mkdir()
    t2_dir.mkdir()
    plain = tmp_path / "p.txt"
    plain.write_text("ok")
    t1_arc = t1_dir / "cline_omniroute_backup_20261104_034208.tar.gz.gpg"
    subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "unit-test-pass",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "-o",
            str(t1_arc),
            str(plain),
        ],
        env={"GNUPGHOME": str(short_gnupg_home), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    rc = vsb.main(
        [
            "--tier1-dir",
            str(t1_dir),
            "--tier2-dir",
            str(t2_dir),
            "--skip-remote",
            "--storage-path",
            str(t1_dir),
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tier1"]["local_archive_count"] == 1
    assert (
        out["tier1"]["latest_archive"]["gpg_header"]["valid_openpgp_symmetric"]
        is True
    )
    assert out["tier2"]["local_archive_count"] == 0
