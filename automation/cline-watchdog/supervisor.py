#!/usr/bin/env python3
"""Persistent, fail-closed task supervision. Trusted adapters only; no shell."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


# Adapter contract: zero means independently VERIFIED completion, not CLI exit.
RESULTS = {0: ("complete", "verified_completion"),
           10: ("retry", "transient_connection_failure"),
           11: ("retry", "incomplete_checkpoint"),
           20: ("blocked", "approval_required"),
           21: ("blocked", "authentication_or_configuration_required"),
           22: ("blocked", "runtime_repair_required")}


def validate(config):
    tasks = config["tasks"]
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    seen = set()
    for task in tasks:
        identity = task["id"]
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("unique nonempty task IDs required")
        seen.add(identity)
        argv = task["adapter"]
        if (not isinstance(argv, list) or not argv or
                not all(isinstance(arg, str) and arg and '\x00' not in arg for arg in argv)
                or not Path(argv[0]).is_absolute()):
            raise ValueError("adapter must be absolute executable argv")
        if not Path(task["cwd"]).is_absolute() or not Path(task["cwd"]).is_dir():
            raise ValueError("existing absolute cwd required")
    timeout = config.get("timeout_seconds", 300)
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError("timeout_seconds must be 1..3600")
    if not Path(config["state_dir"]).is_absolute():
        raise ValueError("absolute state_dir required")


def save(path, data):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        os.chmod(temporary, 0o600)
        json.dump(data, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def tick(config, execute=False, clock=time.time):
    validate(config)
    if not execute:
        return {task["id"]: "observe_only" for task in config["tasks"]}
    root = Path(config["state_dir"])
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_mode & 0o077:
        raise ValueError("state_dir must be private and not a symlink")
    results = {}
    for task in config["tasks"]:
        key = hashlib.sha256(task["id"].encode()).hexdigest()
        path = root / (key + ".json")
        with (root / (key + ".lock")).open("a+") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                results[task["id"]] = "already_running"
                continue
            try:
                state = json.loads(path.read_text()) if path.exists() else {
                    "status": "retry", "attempts": 0, "next_at": 0}
                if (state["status"] not in {"retry", "running", "blocked", "complete"}
                        or type(state["attempts"]) is not int or state["attempts"] < 0
                        or type(state["next_at"]) not in (int, float)
                        or not 0 <= state["next_at"] < float("inf")):
                    raise ValueError("invalid state")
            except (ValueError, KeyError, TypeError, OSError):
                results[task["id"]] = "blocked_corrupt_state_reconcile_required"
                continue
            fingerprint = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()
            if state.get("fingerprint", fingerprint) != fingerprint:
                results[task["id"]] = "blocked_configuration_changed_reconcile_required"
                continue
            if state["status"] == "running":
                state.update(status="blocked", reason="interrupted_attempt_reconcile_ownership")
                save(path, state)
            if state["status"] in {"blocked", "complete"}:
                results[task["id"]] = state
                continue
            if clock() < state["next_at"]:
                results[task["id"]] = "cooldown"
                continue
            state.update(status="running", fingerprint=fingerprint,
                         attempts=state["attempts"] + 1)
            save(path, state)  # Durable BEFORE spawn: ambiguity never causes replay.
            try:
                result = subprocess.run(task["adapter"] + [task["id"]],
                                        cwd=task["cwd"], stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        timeout=config.get("timeout_seconds", 300),
                                        close_fds=True)
                status, reason = RESULTS.get(result.returncode,
                                             ("blocked", "unknown_adapter_failure_inspect_locally"))
            except subprocess.TimeoutExpired:
                status, reason = "blocked", "timeout_reconcile_child_ownership"
            except OSError:
                status, reason = "blocked", "adapter_launch_failed_repair_runtime"
            delay = min(3600, 60 * 2 ** min(state["attempts"] - 1, 6))
            state.update(status=status, reason=reason, next_at=clock() + delay)
            save(path, state)
            results[task["id"]] = state
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(tick(json.loads(Path(args.config).read_text()), args.execute)))
