"""Crash-persistent, fail-closed replay guard for authenticated device request IDs.

A request ID is committed before its allowlisted command starts. Each SQLite
connection binds to an O_NOFOLLOW-verified file descriptor, preventing a path
swap after initialization from redirecting replay records. IDs are never
automatically pruned: without a signed freshness window, pruning could permit
replay after a restart. The bounded store refuses new work when full.
"""
import os
import re
import sqlite3
import stat
import time
from contextlib import closing, contextmanager
from pathlib import Path

VALID_ID = re.compile(r"[A-Za-z0-9_-]{8,64}\Z")
MAX_IDS = 100_000


class ReplayStore:
    def __init__(self, path=None, *, max_ids=MAX_IDS):
        if type(max_ids) is not int or not 1 <= max_ids <= MAX_IDS:
            raise ValueError("invalid replay-store capacity")
        self.path = Path(path) if path is not None else (
            Path.home() / ".local/state/toolz-termux-bridge/replay.sqlite3")
        self.max_ids = max_ids
        parent = self.path.parent
        if parent.is_symlink():
            raise RuntimeError("replay directory must not be a symlink")
        parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        # Open and chmod the directory itself, never a substituted symlink.
        directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fchmod(directory_fd, 0o700)
            fd = os.open(self.path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            try:
                self._check_file(fd)
                os.fchmod(fd, 0o600)
            finally:
                os.close(fd)
        finally:
            os.close(directory_fd)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests "
                       "(id TEXT PRIMARY KEY, created_at INTEGER NOT NULL)")
            db.commit()

    @staticmethod
    def _check_file(fd):
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise OSError("replay database must be a private, owned regular file")

    @contextmanager
    def _connect(self):
        # Anchor both parent and database to verified open descriptors. A
        # renamed directory or symlink swap cannot redirect SQLite to a new
        # pathname between validation and use.
        directory_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            directory_info = os.fstat(directory_fd)
            if (directory_info.st_uid != os.getuid() or
                    directory_info.st_mode & 0o077):
                raise OSError("replay directory permissions are not private")
            fd = os.open(self.path.name, os.O_RDWR | os.O_NOFOLLOW, dir_fd=directory_fd)
            try:
                self._check_file(fd)
                if os.fstat(fd).st_mode & 0o077:
                    raise OSError("replay database permissions are not private")
                with closing(sqlite3.connect(f"/proc/self/fd/{fd}", timeout=2,
                                             isolation_level=None)) as db:
                    yield db
            finally:
                os.close(fd)
        finally:
            os.close(directory_fd)

    def claim(self, request_id):
        """Atomically record a new ID; duplicates and capacity exhaustion deny."""
        if not isinstance(request_id, str) or not VALID_ID.fullmatch(request_id):
            return False
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] >= self.max_ids:
                    db.execute("ROLLBACK")
                    return False
                try:
                    db.execute("INSERT INTO requests(id,created_at) VALUES(?,?)",
                               (request_id, int(time.time())))
                except sqlite3.IntegrityError:
                    db.execute("ROLLBACK")
                    return False
                db.execute("COMMIT")
                return True
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
