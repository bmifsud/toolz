#!/usr/bin/env python3
"""EXPERIMENTAL isolated Tier-2 tar.gz extractor. Synthetic fixtures only.

Never target the live rootfs. Not yet approved for production or cloud restore.
"""
import argparse
import os
from pathlib import Path
import stat
import tarfile

ROOT = ".andronix/distros/debian/rootfs"
PREFIXES = {".andronix", ".andronix/distros", ".andronix/distros/debian"}
MAX_MEMBERS = 1000000
MAX_TOTAL = 64 * 1024**3
MAX_FILE = 16 * 1024**3


def reject(msg):
    raise ValueError("Unsafe archive: " + msg)


def extract(source, destination):
    dest = Path(destination).absolute()
    if dest.exists() or dest.is_symlink():
        reject("destination must not exist")
    # Explicitly prohibit the live Termux Debian tree and its ancestors.
    live = (Path.home() / ".andronix/distros/debian/rootfs").absolute()
    if dest == live or dest in live.parents or live in dest.parents:
        reject("destination overlaps live rootfs")
    for ancestor in (dest, *dest.parents):
        if ancestor.is_symlink():
            reject("symlinked destination ancestor")
    if not dest.parent.is_dir():
        reject("destination parent missing")
    dest.mkdir(mode=0o700)
    rootfd = os.open(dest, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    pending_links = []
    directories = []
    seen = set()
    total = 0
    try:
        with tarfile.open(source, "r|gz") as archive:
            for member in archive:
                name = member.name.rstrip("/")
                parts = name.split("/")
                if (member.name.startswith("/") or member.name.startswith("./")
                        or not name or any(p in ("", ".", "..") for p in parts)
                        or len(name) > 4096):
                    reject("invalid path")
                if name in seen:
                    reject("duplicate member")
                seen.add(name)
                if len(seen) > MAX_MEMBERS:
                    reject("member count exceeded")
                if not (name == "start-debian.sh" or name in PREFIXES
                        or name == ROOT or name.startswith(ROOT + "/")):
                    reject("unexpected path")
                if name in PREFIXES | {ROOT} and not member.isdir():
                    reject("required directory replaced")
                if name == "start-debian.sh" and not member.isfile():
                    reject("launcher not a regular file")
                if not (member.isdir() or member.isfile() or member.issym()):
                    reject("unsupported member type")
                if member.size < 0 or member.size > MAX_FILE:
                    reject("invalid file size")
                if member.isfile():
                    total += member.size
                    if total > MAX_TOTAL:
                        reject("expanded size exceeded")
                if member.issym():
                    target = member.linkname
                    if not target or "\x00" in target or len(target) > 4096:
                        reject("invalid symlink")
                    if not target.startswith("/"):
                        resolved = parts[:-1].copy()
                        for part in target.split("/"):
                            if part in ("", "."):
                                continue
                            if part == "..":
                                if not resolved:
                                    reject("escaping symlink")
                                resolved.pop()
                            else:
                                resolved.append(part)
                        joined = "/".join(resolved)
                        if not (name.startswith(ROOT + "/") and
                                (joined == ROOT or joined.startswith(ROOT + "/"))):
                            reject("symlink escapes rootfs")
                    pending_links.append((parts, target))
                    continue
                parent = os.dup(rootfd)
                try:
                    for part in parts[:-1]:
                        try:
                            os.mkdir(part, 0o700, dir_fd=parent)
                        except FileExistsError:
                            pass
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                        os.close(parent)
                        parent = child
                    if member.isdir():
                        try:
                            os.mkdir(parts[-1], 0o700, dir_fd=parent)
                        except FileExistsError:
                            existing = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
                            if not stat.S_ISDIR(existing.st_mode):
                                reject("directory collision")
                        directories.append((parts, member.mode & 0o777))
                    else:
                        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=parent)
                        try:
                            with os.fdopen(fd, "wb") as out:
                                stream = archive.extractfile(member)
                                remaining = member.size
                                while remaining:
                                    chunk = stream.read(min(1024 * 1024, remaining))
                                    if not chunk:
                                        reject("truncated file")
                                    out.write(chunk)
                                    remaining -= len(chunk)
                            os.chmod(parts[-1], member.mode & 0o777, dir_fd=parent,
                                     follow_symlinks=False)
                        except BaseException:
                            raise
                finally:
                    os.close(parent)
        if ROOT not in seen or "start-debian.sh" not in seen:
            reject("missing required rootfs or launcher")
        for parts, target in pending_links:
            parent = os.dup(rootfd)
            try:
                for part in parts[:-1]:
                    try:
                        os.mkdir(part, 0o700, dir_fd=parent)
                    except FileExistsError:
                        pass
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent)
                    parent = child
                os.symlink(target, parts[-1], dir_fd=parent)
            finally:
                os.close(parent)
        # Parent directories created implicitly remain 0700 unless explicit
        # archive directory metadata exists. Restore searchable permissions
        # for synthetic implicit parents only; never loosen explicit metadata.
        explicit_dirs = {tuple(parts) for parts, _mode in directories}
        implicit_dirs = set()
        for name in seen:
            parts = name.split("/")
            for i in range(1, len(parts)):
                prefix = tuple(parts[:i])
                if prefix not in explicit_dirs:
                    implicit_dirs.add(prefix)
        for parts in sorted(implicit_dirs, key=len, reverse=True):
            parent = os.dup(rootfd)
            try:
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent)
                    parent = child
                os.chmod(parts[-1], 0o755, dir_fd=parent, follow_symlinks=False)
            finally:
                os.close(parent)
        for parts, mode in sorted(directories, key=lambda item: -len(item[0])):
            parent = os.dup(rootfd)
            try:
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent)
                    parent = child
                os.chmod(parts[-1], mode, dir_fd=parent, follow_symlinks=False)
            finally:
                os.close(parent)
    finally:
        os.close(rootfd)
    return len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="Synthetic tar.gz fixture only")
    parser.add_argument("destination", help="New empty isolated destination")
    args = parser.parse_args()
    count = extract(args.archive, args.destination)
    print(f"EXPERIMENTAL isolated extraction completed: {count} members")


if __name__ == "__main__":
    main()
