#!/usr/bin/env python3
"""Read-only streamed validation of an Andronix Debian tar.gz archive.

Absolute symlink targets are valid within Debian (e.g. /usr/bin/mawk).
Validation does NOT authorize direct extraction: restore must use a separately
audited isolated extractor that never follows archive-controlled symlinks.
"""
import pathlib
import sys
import tarfile

ROOT = ".andronix/distros/debian/rootfs"
PREFIXES = {".andronix", ".andronix/distros", ".andronix/distros/debian"}


def reject(message):
    raise SystemExit("Unsafe archive: " + message)


def validate(stream):
    seen = set()
    symlinks = set()
    parents = set()
    found_root = found_launcher = False
    required = {ROOT + "/etc/passwd", ROOT + "/etc/os-release"}
    found_required = set()
    with tarfile.open(fileobj=stream, mode="r|gz") as archive:
        for member in archive:
            raw = member.name
            if raw.startswith("/") or raw.startswith("./"):
                reject("noncanonical path " + repr(raw))
            name = raw.rstrip("/")
            if not name or any(part in ("", ".", "..") for part in name.split("/")):
                reject("invalid path " + repr(raw))
            if name in seen:
                reject("duplicate member " + repr(name))
            seen.add(name)
            if name in required:
                if not member.isfile() or member.size == 0:
                    reject("missing or empty Debian identity file " + repr(name))
                found_required.add(name)
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
            parts = pathlib.PurePosixPath(name).parts
            for i in range(1, len(parts)):
                if "/".join(parts[:i]) in symlinks:
                    reject("member under symlink " + repr(name))
            if not member.isdir() and name in parents:
                reject("non-directory ancestor " + repr(name))
            parents.update("/".join(parts[:i]) for i in range(1, len(parts)))
            if member.issym():
                target = member.linkname
                if not target or "\x00" in target:
                    reject("invalid symlink target " + repr(name))
                # Absolute targets are normal in Debian. They are stored as
                # metadata only; never dereference them during validation.
                # Relative targets must not escape the Debian rootfs.
                if not target.startswith("/"):
                    resolved = list(parts[:-1])
                    for part in target.split("/"):
                        if part in ("", "."):
                            continue
                        if part == "..":
                            if len(resolved) <= len(ROOT.split("/")):
                                reject("escaping symlink " + repr(name))
                            resolved.pop()
                        else:
                            resolved.append(part)
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
    if "--require-debian-identity" in sys.argv[1:] and found_required != required:
        reject("missing Debian identity files " + repr(sorted(required - found_required)))
    print("PASS: validated full archive structure (no extraction performed)")


if __name__ == "__main__":
    validate(sys.stdin.buffer)
