"""Durable, fail-closed diagnostic task queue. No background worker or shell execution.

A trusted, authenticated dispatcher must invoke claim/complete; persistence alone
does not authorize execution. All state changes use SQLite transactions.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

ALLOWED = frozenset({"git-branch", "ssh-status", "tier1-tests"})
STATES = frozenset({"queued", "running", "succeeded", "failed", "cancelled"})
MAX_OUTPUT = 8192


def _failure_receipt(error_code: str) -> str:
    """Stable, secret-safe receipt for controller-side expiry without worker output."""
    return json.dumps({
        "receipt_version": 2,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "output_suppressed": False,
        "error": error_code,
    })


class TaskQueue:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, diagnostic TEXT NOT NULL,
                state TEXT NOT NULL, created REAL NOT NULL,
                deadline REAL NOT NULL, lease_until REAL,
                result TEXT, attempt INTEGER NOT NULL DEFAULT 0)""")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def submit(self, diagnostic: str, timeout: int = 60) -> str:
        if diagnostic not in ALLOWED:
            raise ValueError("diagnostic not allowlisted")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 300:
            raise ValueError("timeout out of bounds")
        task_id = uuid.uuid4().hex
        now = time.time()
        with self._connect() as db:
            db.execute("INSERT INTO tasks(id,diagnostic,state,created,deadline) VALUES(?,?,?,?,?)",
                       (task_id, diagnostic, "queued", now, now + timeout))
        return task_id

    def claim(self, lease_seconds: int = 30):
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 1 <= lease_seconds <= 300:
            raise ValueError("lease out of bounds")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE tasks SET state='failed', result=? WHERE state IN ('queued','running') AND deadline<=?",
                       (_failure_receipt("deadline_exceeded"), now))
            # Fail closed: expired running leases become failed, never replayed automatically.
            db.execute("UPDATE tasks SET state='failed', result=? WHERE state='running' AND lease_until<=?",
                       (_failure_receipt("lease_expired"), now))
            row = db.execute("SELECT id,diagnostic,deadline FROM tasks WHERE state='queued' ORDER BY created,id LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE tasks SET state='running', attempt=attempt+1, lease_until=? WHERE id=?",
                           (min(now + lease_seconds, row[2]), row[0]))
            db.execute("COMMIT")
        return {"id": row[0], "diagnostic": row[1], "deadline": row[2]} if row else None

    def complete(self, task_id: str, result: dict, *, success: bool) -> bool:
        if not isinstance(result, dict):
            raise ValueError("invalid result")
        if type(success) is not bool:
            raise ValueError("success must be a boolean")
        # A caller-supplied success flag cannot turn a failed or missing
        # exit status into a successful durable receipt. An unsuccessful
        # result may still have exit_code=0 (e.g. termination unverified).
        if success and (type(result.get("exit_code")) is not int or result["exit_code"] != 0):
            raise ValueError("successful receipt requires integer exit_code 0")
        # A zero exit code with an explicit worker error is not a verified success.
        if success and result.get("error") is not None:
            raise ValueError("successful receipt cannot contain a worker error")
        # Receipt schema v2: never persist unstructured worker text. Bounded
        # strings and regex substitutions are not sufficient secret controls.
        # Only allowlisted, fixed error codes and verified numeric status survive.
        raw_exit = result.get("exit_code")
        exit_code = raw_exit if type(raw_exit) is int else None
        known_errors = {
            "worker termination unverified": "worker_termination_unverified",
            "worker_termination_unverified": "worker_termination_unverified",
            "deadline exceeded": "deadline_exceeded",
            "deadline_exceeded": "deadline_exceeded",
            "lease expired; execution outcome unknown": "lease_expired",
            "lease_expired": "lease_expired",
            "output limit exceeded": "output_limit_exceeded",
            "output_limit_exceeded": "output_limit_exceeded",
        }
        raw_error = result.get("error")
        error_code = known_errors.get(raw_error, "worker_error") if type(raw_error) is str else "worker_error"
        receipt_fields = {
            "receipt_version": 2,
            "exit_code": exit_code,
            # Deliberately omit stdout/stderr until each diagnostic has an
            # explicit structured, schema-validated, secret-safe receipt.
            "stdout": "",
            "stderr": "",
            "output_suppressed": bool(result.get("stdout") or result.get("stderr")),
        }
        if not success:
            receipt_fields["error"] = (
                "invalid_exit_code" if raw_exit is not None and exit_code is None
                else error_code if raw_error is not None
                else "command_failed" if exit_code is not None and exit_code != 0
                else "execution_unverified"
            )
        receipt = json.dumps(receipt_fields)
        if len(receipt.encode()) > 2 * MAX_OUTPUT + 512:
            raise ValueError("receipt too large")
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET state=?,result=?,lease_until=NULL WHERE id=? AND state='running' AND deadline>? AND lease_until>?",
                ("succeeded" if success else "failed", receipt, task_id, time.time(), time.time()))
            return cursor.rowcount == 1

    def cancel(self, task_id: str) -> bool:
        # Cancelling a running task prevents result acceptance but does NOT stop its process.
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET state='cancelled',lease_until=NULL WHERE id=? AND state IN ('queued','running')",
                (task_id,))
            return cursor.rowcount == 1

    def get(self, task_id: str):
        with self._connect() as db:
            row = db.execute("SELECT id,diagnostic,state,created,deadline,attempt,result FROM tasks WHERE id=?",
                             (task_id,)).fetchone()
        if row is None:
            return None
        return dict(zip(("id", "diagnostic", "state", "created", "deadline", "attempt", "result"), row))
