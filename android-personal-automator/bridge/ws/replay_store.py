"""Crash-persistent, fail-closed replay guard for authenticated device request IDs.

A request ID is committed before its allowlisted command starts. IDs are never
automatically pruned: without a signed freshness window, pruning could permit
replay after a restart. The bounded store refuses new work when full.
"""
import os
import re
import sqlite3
import time
from contextlib import closing
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
        if parent.is_symlink():
            raise RuntimeError("replay directory must not be a symlink")
        os.chmod(parent, 0o700)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests "
                       "(id TEXT PRIMARY KEY, created_at INTEGER NOT NULL)")
            db.commit()

    def claim(self, request_id):
        """Atomically record a new ID; duplicates and capacity exhaustion deny."""
        if not isinstance(request_id, str) or not VALID_ID.fullmatch(request_id):
            return False
        with closing(sqlite3.connect(self.path, timeout=2, isolation_level=None)) as db:
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
