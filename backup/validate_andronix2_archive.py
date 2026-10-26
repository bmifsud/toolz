#!/usr/bin/env python3
"""Validate a streamed Andronix 2.0 tar.gz before any restore.

Reads gzip tar from stdin. No filesystem writes. Deliberately rejects hard links
and entries nested under symlink members to prevent extraction redirection.
"""
import pathlib
import sys
import tarfile

ROOT = ".andronix/distros/debian/rootfs"
PREFIXES = {".andronix", ".andronix/distros", ".andronix/distros/debian"}
seen = set()
symlinks = set()
found_root = False
found_launcher = False

def reject(message):
    raise SystemExit("Unsafe archive: " + message)

with tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz") as archive:
    for member in archive:
        raw = member.name
        if raw.startswith("/") or raw.startswith("./") or "\\" in raw:
            reject("noncanonical path " + repr(raw))
        name = raw.rstrip("/")
        parts = pathlib.PurePosixPath(name).parts
        if not name or any(p in (".", "..") for p in raw.split("/")):
            reject("invalid path " + repr(raw))
        if name in seen:
            reject("duplicate member " + repr(name))
        seen.add(name)
        if not (name == "start-debian.sh" or name == ROOT or name.startswith(ROOT + "/") or name in PREFIXES):
            reject("unexpected member " + repr(name))
        if name in PREFIXES and not member.isdir():
            reject("non-directory prefix " + repr(name))
        if name == ROOT:
            if not member.isdir():
                reject("rootfs is not a directory")
            found_root = True
        if name == "start-debian.sh":
            if not member.isfile():
                reject("launcher is not a regular file")
            found_launcher = True
        for i in range(1, len(parts)):
            if "/".join(parts[:i]) in symlinks:
                reject("member under symlink " + repr(name))
        if member.issym():
            target = member.linkname
            if not target or target.startswith("/") or "\\" in target:
                reject("absolute or invalid symlink " + repr(name))
            resolved = list(parts[:-1])
            for part in target.split("/"):
                if part in ("", "."):
                    continue
                if part == "..":
                    if not resolved:
                        reject("escaping symlink " + repr(name))
                    resolved.pop()
                else:
                    resolved.append(part)
            # No link may resolve outside the rootfs tree.
            dest = "/".join(resolved)
            if not (name.startswith(ROOT + "/") and (dest == ROOT or dest.startswith(ROOT + "/"))):
                reject("symlink outside rootfs " + repr(name))
            symlinks.add(name)
        elif not (member.isfile() or member.isdir()):
            reject("unsupported entry type " + repr(name))
        if member.size < 0:
            reject("negative size")
if not found_root or not found_launcher:
    reject("required rootfs directory or launcher missing")
print("PASS: validated full archive structure and link safety")
