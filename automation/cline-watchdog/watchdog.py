#!/usr/bin/env python3
"""Conservative Cline watchdog: detect failures, never launch an unapproved task."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

def check(config, now=None):
    now = time.time() if now is None else now
    state = Path(config["state_dir"])
    heartbeat = state / "heartbeat.json"
    if not heartbeat.exists():
        return "missing_heartbeat"
    try:
        data = json.loads(heartbeat.read_text())
        age = now - float(data["timestamp"])
    except (ValueError, KeyError, OSError, TypeError):
        return "invalid_heartbeat"
    if age < -60:
        return "future_heartbeat"
    if age > config.get("stale_seconds", 900):
        return "stale"
    return "healthy"

def run(config, recover=False):
    state = Path(config["state_dir"])
    state.mkdir(parents=True, exist_ok=True)
    with (state / "watchdog.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return "already_running"
        status = check(config)
        event = {"timestamp": time.time(), "status": status}
        if status != "healthy" and recover:
            history = state / "recovery.json"
            previous = json.loads(history.read_text()) if history.exists() else {}
            last = float(previous.get("last_attempt", 0))
            attempts = int(previous.get("attempts", 0))
            cooldown = min(3600, 60 * (2 ** min(attempts, 6)))
            if time.time() - last < cooldown:
                event["action"] = "cooldown"
            else:
                # Explicitly configured argv; no shell or dynamic model-generated commands.
                argv = config.get("recovery_command")
                if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
                    event["action"] = "no_recovery_command"
                else:
                    workdir = Path(config["working_directory"]).resolve()
                    if not workdir.is_dir():
                        event["action"] = "invalid_workdir"
                    else:
                        with (state / "recovery.log").open("a") as log:
                            proc = subprocess.Popen(argv, cwd=workdir, stdin=subprocess.DEVNULL,
                                                    stdout=log, stderr=subprocess.STDOUT,
                                                    start_new_session=True, close_fds=True)
                        event.update(action="launched", pid=proc.pid)
                        history.write_text(json.dumps({"last_attempt": time.time(), "attempts": attempts + 1}))
        with (state / "events.jsonl").open("a") as log:
            log.write(json.dumps(event) + "\n")
        return event

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--recover", action="store_true")
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    print(json.dumps(run(cfg, args.recover)))
