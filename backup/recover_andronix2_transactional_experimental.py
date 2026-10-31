#!/usr/bin/env python3
"""EXPERIMENTAL transactional wrapper for synthetic Tier-2 fixtures only.

A failed attempt leaves a uniquely named .incomplete directory for inspection.
Only successful extraction is renamed to the requested final directory.
No cleanup, live-rootfs restore, GPG or cloud integration is provided.
"""
import argparse
import ctypes
import errno
import os
from pathlib import Path
import secrets
import stat

from backup.extract_andronix2_isolated_experimental import extract


COMPLETION_MARKER = ".tier2-recovery-complete"


def sync_tree(root):
    """Fsync regular files and directories without following symlinks."""
    for current, dirs, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = Path(current) / name
            if path.is_symlink():
                continue
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                if stat.S_ISREG(os.fstat(fd).st_mode):
                    os.fsync(fd)
            finally:
                os.close(fd)
        fd = os.open(current, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def publish_noreplace(staging, final):
    """Linux renameat2(RENAME_NOREPLACE); fail closed if unavailable."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise NotImplementedError("renameat2 is required for safe publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                          ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    parentfd = os.open(staging.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result = renameat2(parentfd, os.fsencode(staging.name),
                           parentfd, os.fsencode(final.name), 1)  # RENAME_NOREPLACE
        if result:
            err = ctypes.get_errno()
            raise OSError(err, os.strerror(err), str(final))
    finally:
        os.close(parentfd)


def recover_synthetic(archive, destination):
    final = Path(destination).absolute()
    if final.exists() or final.is_symlink():
        raise ValueError("final destination already exists")
    if not final.parent.is_dir() or final.parent.is_symlink():
        raise ValueError("destination parent must be a real directory")
    staging = final.parent / (".tier2-" + secrets.token_hex(12) + ".incomplete")
    # Extractor itself creates the staging directory and checks the live rootfs.
    try:
        count = extract(archive, staging)
    except BaseException:
        # Retain incomplete staging for manual review; never advertise success.
        raise
    # Sync extracted data before creating a completion marker.
    sync_tree(staging)
    marker = staging / COMPLETION_MARKER
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write("synthetic-recovery-complete\\n")
        out.flush()
        os.fsync(out.fileno())
    sync_tree(staging)
    publish_noreplace(staging, final)
    parentfd = os.open(final.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parentfd)
    finally:
        os.close(parentfd)
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive")
    p.add_argument("destination")
    args = p.parse_args()
    print("EXPERIMENTAL synthetic recovery:", recover_synthetic(args.archive, args.destination))


if __name__ == "__main__":
    main()
