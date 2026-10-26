#!/usr/bin/env python3
"""EXPERIMENTAL transactional wrapper for synthetic Tier-2 fixtures only.

A failed attempt leaves a uniquely named .incomplete directory for inspection.
Only successful extraction is renamed to the requested final directory.
No cleanup, live-rootfs restore, GPG or cloud integration is provided.
"""
import argparse
import os
from pathlib import Path
import secrets

from backup.extract_andronix2_isolated_experimental import extract


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
    # No replacement of existing destination. On POSIX rename is atomic when
    # on the same filesystem; this is not a durable fsync or race-proof publish.
    if final.exists() or final.is_symlink():
        raise FileExistsError("final destination appeared during extraction")
    os.rename(staging, final)
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive")
    p.add_argument("destination")
    args = p.parse_args()
    print("EXPERIMENTAL synthetic recovery:", recover_synthetic(args.archive, args.destination))


if __name__ == "__main__":
    main()
