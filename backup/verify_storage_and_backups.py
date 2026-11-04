#!/usr/bin/env python3
"""Read-only storage inventory and Tier-1/Tier-2 backup integrity verifier.

This module performs strictly non-destructive, read-only checks:
- Filesystem capacity and directory storage breakdown (`df -B1`, `du -sb`).
- OpenPGP symmetric encryption header inspection (AES-256 + MDC) without
  prompting for or exposing passphrases.
- Local streaming SHA-256 and MD5 computation for Tier-1 and Tier-2 archives.
- Google Drive remote presence, size, MD5 metadata, and optional full streamed
  ciphertext readback SHA-256 verification via `rclone`.
- Detection of unuploaded older local Tier-1 archives that block chronological
  `tier1_retention.sh` cleanup and `run_scheduled_backup.sh` completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Iterable, Sequence

TIER1_ARCHIVE_RE = re.compile(
    r"^cline_omniroute_backup_\d{8}_\d{6}\.tar\.gz\.gpg$"
)
TIER2_ARCHIVE_RE = re.compile(r"^andronix-debian-\d{8}_\d{6}\.tar\.gz\.gpg$")
SENSITIVE_PATTERN = re.compile(
    r"(?i)(passphrase|password|secret|token|api[_-]?key|authorization)\s*[:=]\s*\S+"
)

DEFAULT_STORAGE_PATHS: tuple[str, ...] = (
    "/usr",
    "/var",
    "/tmp",
    "/opt",
    "/root",
    "/etc",
    "/home/b/.codex",
    "/home/b/.gemini",
    "/home/b/.omniroute",
    "/home/b/.cline",
    "/home/b/.agents",
    "/home/b/.cache",
    "/home/b/.npm",
    "/home/b/.local",
    "/home/b/ClineOmniRouteBackups",
    "/home/b/.omniroute/backups",
    "/sdcard/ClineOmniRouteBackups",
    "/sdcard/Andronix/backups",
)

RunnerType = Callable[[Sequence[str]], subprocess.CompletedProcess[bytes]]


def _default_runner(cmd: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, capture_output=True, check=False)


def redact_sensitive_text(text: str) -> str:
    """Redact potential secret assignments from diagnostic strings."""
    return SENSITIVE_PATTERN.sub(r"\1=[REDACTED]", text)


def collect_filesystem_df(
    paths: Sequence[str] = ("/", "/sdcard"),
    runner: RunnerType = _default_runner,
) -> list[dict[str, Any]]:
    """Return byte-accurate `df -B1` statistics for the requested mount paths."""
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        return []
    proc = runner(["df", "-B1", *existing])
    if proc.returncode != 0:
        return []
    lines = proc.stdout.decode("utf-8", errors="replace").strip().splitlines()
    entries: list[dict[str, Any]] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            total_b = int(parts[1])
            used_b = int(parts[2])
            avail_b = int(parts[3])
        except ValueError:
            continue
        entries.append(
            {
                "filesystem": parts[0],
                "total_bytes": total_b,
                "used_bytes": used_b,
                "avail_bytes": avail_b,
                "use_percent": parts[4],
                "mountpoint": parts[5],
            }
        )
    return entries


def collect_directory_usage(
    paths: Sequence[str] = DEFAULT_STORAGE_PATHS,
    runner: RunnerType = _default_runner,
) -> list[dict[str, Any]]:
    """Measure directory byte usage read-only via `du -sb`."""
    results: list[dict[str, Any]] = []
    for raw_path in paths:
        if not os.path.exists(raw_path):
            results.append(
                {"path": raw_path, "exists": False, "size_bytes": 0}
            )
            continue
        cmd = [
            "du",
            "-sb",
            "--one-file-system",
            "--exclude=/sdcard",
            "--exclude=/proc",
            "--exclude=/sys",
            "--exclude=/dev",
            raw_path,
        ]
        if raw_path.startswith("/sdcard"):
            cmd = ["du", "-sb", raw_path]
        proc = runner(cmd)
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        size_bytes = 0
        if out:
            first_token = out.splitlines()[-1].split("\t", 1)[0].strip()
            if first_token.isdigit():
                size_bytes = int(first_token)
        results.append(
            {
                "path": raw_path,
                "exists": True,
                "size_bytes": size_bytes,
            }
        )
    return results


def inspect_gpg_header(
    archive_path: str | Path,
    max_bytes: int = 4096,
) -> dict[str, Any]:
    """Inspect OpenPGP symmetric encryption header bytes without a passphrase.

    Parses RFC 4880 Symmetric-Key Encrypted Session Key Packet (tag 3) and
    Symmetrically Encrypted Integrity Protected Data Packet (tag 18) directly
    from the leading header bytes, avoiding interactive pinentry or gpg-agent
    side effects.
    """
    path = Path(archive_path)
    if not path.is_file():
        return {
            "valid_openpgp_symmetric": False,
            "cipher_algo": None,
            "s2k_type": None,
            "hash_algo": None,
            "has_mdc": False,
            "error": "file_missing",
        }
    with path.open("rb") as fh:
        data = fh.read(max_bytes)
    if len(data) < 16:
        return {
            "valid_openpgp_symmetric": False,
            "cipher_algo": None,
            "s2k_type": None,
            "hash_algo": None,
            "has_mdc": False,
            "error": "truncated_header",
        }

    first = data[0]
    if not (first & 0x80):
        return {
            "valid_openpgp_symmetric": False,
            "cipher_algo": None,
            "s2k_type": None,
            "hash_algo": None,
            "has_mdc": False,
            "error": "not_openpgp_packet",
        }

    if first & 0x40:
        tag = first & 0x3F
        plen = data[1]
        hlen = 2
    else:
        tag = (first >> 2) & 0x0F
        len_type = first & 0x03
        if len_type == 0:
            plen = data[1]
            hlen = 2
        elif len_type == 1:
            plen = (data[1] << 8) | data[2]
            hlen = 3
        else:
            plen = 0
            hlen = 2

    if tag != 3 or len(data) < hlen + plen or plen < 4:
        return {
            "valid_openpgp_symmetric": False,
            "cipher_algo": None,
            "s2k_type": None,
            "hash_algo": None,
            "has_mdc": False,
            "error": f"unexpected_first_packet_tag_{tag}",
        }

    body = data[hlen : hlen + plen]
    version = body[0]
    cipher_id = body[1]
    s2k_type = body[2]
    hash_id = body[3]

    cipher_names = {
        7: "AES128",
        8: "AES192",
        9: "AES256",
    }
    cipher_name = cipher_names.get(cipher_id, f"CIPHER_{cipher_id}")

    next_offset = hlen + plen
    has_mdc = False
    if next_offset < len(data):
        next_ctb = data[next_offset]
        if next_ctb & 0x80:
            next_tag = (
                (next_ctb & 0x3F)
                if (next_ctb & 0x40)
                else ((next_ctb >> 2) & 0x0F)
            )
            if next_tag in (18, 20):
                has_mdc = True

    return {
        "valid_openpgp_symmetric": version == 4 and cipher_id == 9 and has_mdc,
        "version": version,
        "cipher_id": cipher_id,
        "cipher_algo": cipher_name,
        "s2k_type": s2k_type,
        "hash_algo": hash_id,
        "has_mdc": has_mdc,
        "error": None,
    }


def compute_file_hashes(
    archive_path: str | Path,
    algorithms: Iterable[str] = ("sha256", "md5"),
    chunk_size: int = 8 * 1024 * 1024,
) -> dict[str, str]:
    """Compute streaming cryptographic digests for a file in a single pass."""
    path = Path(archive_path)
    hashers = {alg: hashlib.new(alg) for alg in algorithms}
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            for h in hashers.values():
                h.update(chunk)
    return {alg: h.hexdigest() for alg, h in hashers.items()}


def fetch_remote_objects(
    remote_dir: str,
    runner: RunnerType = _default_runner,
) -> dict[str, dict[str, Any]]:
    """Query `rclone lsjson --hash` for a remote directory."""
    proc = runner(
        ["rclone", "lsjson", "--hash", "--max-depth", "1", remote_dir]
    )
    if proc.returncode != 0:
        err = redact_sensitive_text(
            proc.stderr.decode("utf-8", errors="replace").strip()
        )
        raise RuntimeError(f"rclone lsjson failed for {remote_dir}: {err}")
    raw = json.loads(proc.stdout.decode("utf-8", errors="replace") or "[]")
    catalog: dict[str, dict[str, Any]] = {}
    for item in raw:
        name = item.get("Name") or item.get("Path")
        if not name:
            continue
        hashes = item.get("Hashes") or {}
        catalog[name] = {
            "name": name,
            "size_bytes": int(item.get("Size", -1)),
            "is_dir": bool(item.get("IsDir", False)),
            "md5": hashes.get("md5"),
            "sha256": hashes.get("sha256"),
            "id": item.get("ID"),
            "mod_time": item.get("ModTime"),
            "mime_type": item.get("MimeType"),
        }
    return catalog


def verify_remote_stream_sha256(
    remote_object: str,
    runner: RunnerType = _default_runner,
) -> str:
    """Stream a remote file via `rclone cat` and return its SHA-256 hex digest."""
    proc = runner(["rclone", "cat", remote_object])
    if proc.returncode != 0:
        err = redact_sensitive_text(
            proc.stderr.decode("utf-8", errors="replace").strip()
        )
        raise RuntimeError(f"rclone cat failed for {remote_object}: {err}")
    return hashlib.sha256(proc.stdout).hexdigest()


def verify_archive_against_remote(
    archive_path: str | Path,
    remote_dir: str,
    remote_catalog: dict[str, dict[str, Any]] | None = None,
    stream_readback: bool = False,
    runner: RunnerType = _default_runner,
) -> dict[str, Any]:
    """Verify a local encrypted archive against its Google Drive counterpart."""
    path = Path(archive_path)
    if not path.is_file():
        return {
            "path": str(path),
            "name": path.name,
            "exists": False,
            "status": "FAIL",
            "reasons": ["local_archive_missing"],
        }

    st = path.stat()
    gpg_info = inspect_gpg_header(path)
    digests = compute_file_hashes(path, algorithms=("sha256", "md5"))
    reasons: list[str] = []

    if not gpg_info.get("valid_openpgp_symmetric"):
        reasons.append("invalid_gpg_aes256_header")

    if remote_catalog is None:
        remote_catalog = fetch_remote_objects(remote_dir, runner=runner)

    remote_entry = remote_catalog.get(path.name)
    remote_present = remote_entry is not None and not remote_entry.get("is_dir")
    size_match = False
    md5_match = False
    remote_stream_sha256: str | None = None
    sha256_match: bool | None = None

    if not remote_present:
        reasons.append("missing_on_remote")
    else:
        assert remote_entry is not None
        size_match = st.st_size == remote_entry.get("size_bytes")
        if not size_match:
            reasons.append("remote_size_mismatch")
        remote_md5 = remote_entry.get("md5")
        if remote_md5:
            md5_match = digests["md5"] == remote_md5
            if not md5_match:
                reasons.append("remote_md5_mismatch")
        if stream_readback:
            remote_target = f"{remote_dir.rstrip('/')}/{path.name}"
            remote_stream_sha256 = verify_remote_stream_sha256(
                remote_target, runner=runner
            )
            sha256_match = digests["sha256"] == remote_stream_sha256
            if not sha256_match:
                reasons.append("remote_stream_sha256_mismatch")

    return {
        "path": str(path),
        "name": path.name,
        "exists": True,
        "size_bytes": st.st_size,
        "mtime": int(st.st_mtime),
        "mode": oct(st.st_mode & 0o777),
        "gpg_header": gpg_info,
        "local_sha256": digests["sha256"],
        "local_md5": digests["md5"],
        "remote_present": remote_present,
        "remote_size_bytes": (
            remote_entry.get("size_bytes") if remote_entry else None
        ),
        "remote_md5": remote_entry.get("md5") if remote_entry else None,
        "remote_id": remote_entry.get("id") if remote_entry else None,
        "size_match": size_match,
        "md5_match": md5_match,
        "remote_stream_sha256": remote_stream_sha256,
        "sha256_match": sha256_match,
        "status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }


def detect_tier1_retention_blockers(
    local_dir: str | Path,
    remote_catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Identify older local Tier-1 archives missing from remote storage.

    `tier1_retention.sh` iterates chronologically over older archives and
    exits 1 immediately if an older archive is missing from Google Drive,
    which prevents retention cleanup of subsequent verified archives and causes
    `run_scheduled_backup.sh` to exit non-zero before writing `SUCCESS tier1`.
    """
    base = Path(local_dir)
    if not base.is_dir():
        return {
            "local_dir": str(base),
            "total_matching_archives": 0,
            "newest_archive": None,
            "missing_on_remote": [],
            "retention_blocked": False,
        }

    archives = sorted(
        p.name
        for p in base.iterdir()
        if p.is_file() and TIER1_ARCHIVE_RE.match(p.name)
    )
    if len(archives) <= 1:
        return {
            "local_dir": str(base),
            "total_matching_archives": len(archives),
            "newest_archive": archives[-1] if archives else None,
            "missing_on_remote": [],
            "retention_blocked": False,
        }

    older = archives[:-1]
    missing = [name for name in older if name not in remote_catalog]
    return {
        "local_dir": str(base),
        "total_matching_archives": len(archives),
        "newest_archive": archives[-1],
        "missing_on_remote": missing,
        "first_blocking_archive": missing[0] if missing else None,
        "retention_blocked": bool(missing),
    }


def build_verification_report(
    tier1_dir: str | Path = "/home/b/ClineOmniRouteBackups",
    tier2_dir: str | Path = "/sdcard/Andronix/backups",
    tier1_remote: str = "gdrive:ClineOmniRouteBackups",
    tier2_remote: str = "gdrive:ClineOmniRouteBackups/AndronixSnapshots",
    storage_paths: Sequence[str] = DEFAULT_STORAGE_PATHS,
    stream_tier1_latest: bool = True,
    skip_remote: bool = False,
    runner: RunnerType = _default_runner,
) -> dict[str, Any]:
    """Assemble a complete read-only storage and backup verification report."""
    df_stats = collect_filesystem_df(runner=runner)
    dir_usage = collect_directory_usage(paths=storage_paths, runner=runner)

    t1_base = Path(tier1_dir)
    t1_archives = (
        sorted(
            p
            for p in t1_base.iterdir()
            if p.is_file() and TIER1_ARCHIVE_RE.match(p.name)
        )
        if t1_base.is_dir()
        else []
    )
    t2_base = Path(tier2_dir)
    t2_archives = (
        sorted(
            p
            for p in t2_base.iterdir()
            if p.is_file() and TIER2_ARCHIVE_RE.match(p.name)
        )
        if t2_base.is_dir()
        else []
    )

    t1_catalog: dict[str, dict[str, Any]] = {}
    t2_catalog: dict[str, dict[str, Any]] = {}
    if not skip_remote:
        t1_catalog = fetch_remote_objects(tier1_remote, runner=runner)
        t2_catalog = fetch_remote_objects(tier2_remote, runner=runner)

    tier1_latest_report = None
    if t1_archives:
        latest_t1 = t1_archives[-1]
        if skip_remote:
            tier1_latest_report = {
                "path": str(latest_t1),
                "name": latest_t1.name,
                "size_bytes": latest_t1.stat().st_size,
                "gpg_header": inspect_gpg_header(latest_t1),
                **compute_file_hashes(latest_t1),
            }
        else:
            tier1_latest_report = verify_archive_against_remote(
                latest_t1,
                tier1_remote,
                remote_catalog=t1_catalog,
                stream_readback=stream_tier1_latest,
                runner=runner,
            )

    tier2_latest_report = None
    if t2_archives:
        latest_t2 = t2_archives[-1]
        if skip_remote:
            tier2_latest_report = {
                "path": str(latest_t2),
                "name": latest_t2.name,
                "size_bytes": latest_t2.stat().st_size,
                "gpg_header": inspect_gpg_header(latest_t2),
                **compute_file_hashes(latest_t2),
            }
        else:
            tier2_latest_report = verify_archive_against_remote(
                latest_t2,
                tier2_remote,
                remote_catalog=t2_catalog,
                stream_readback=False,
                runner=runner,
            )

    retention_diag = (
        detect_tier1_retention_blockers(t1_base, t1_catalog)
        if not skip_remote
        else None
    )

    return {
        "filesystems": df_stats,
        "directory_usage": dir_usage,
        "tier1": {
            "local_dir": str(t1_base),
            "remote_dir": tier1_remote,
            "local_archive_count": len(t1_archives),
            "latest_archive": tier1_latest_report,
            "retention_diagnostics": retention_diag,
        },
        "tier2": {
            "local_dir": str(t2_base),
            "remote_dir": tier2_remote,
            "local_archive_count": len(t2_archives),
            "latest_archive": tier2_latest_report,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only storage and backup integrity verifier."
    )
    parser.add_argument(
        "--tier1-dir",
        default="/home/b/ClineOmniRouteBackups",
        help="Local Tier-1 archive directory",
    )
    parser.add_argument(
        "--tier2-dir",
        default="/sdcard/Andronix/backups",
        help="Local Tier-2 snapshot directory",
    )
    parser.add_argument(
        "--tier1-remote",
        default="gdrive:ClineOmniRouteBackups",
        help="Remote rclone path for Tier-1 backups",
    )
    parser.add_argument(
        "--tier2-remote",
        default="gdrive:ClineOmniRouteBackups/AndronixSnapshots",
        help="Remote rclone path for Tier-2 snapshots",
    )
    parser.add_argument(
        "--no-stream-tier1",
        action="store_true",
        help="Skip full streamed rclone cat readback on latest Tier-1 archive",
    )
    parser.add_argument(
        "--skip-remote",
        action="store_true",
        help="Perform local-only checks without invoking rclone",
    )
    parser.add_argument(
        "--storage-path",
        action="append",
        dest="storage_paths",
        help="Override storage paths to measure (may be passed multiple times)",
    )
    args = parser.parse_args(argv)

    report = build_verification_report(
        tier1_dir=args.tier1_dir,
        tier2_dir=args.tier2_dir,
        tier1_remote=args.tier1_remote,
        tier2_remote=args.tier2_remote,
        storage_paths=tuple(args.storage_paths or DEFAULT_STORAGE_PATHS),
        stream_tier1_latest=not args.no_stream_tier1,
        skip_remote=args.skip_remote,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
