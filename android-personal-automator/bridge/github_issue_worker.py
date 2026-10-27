#!/usr/bin/env python3
"""Opt-in, read-only GitHub issue worker. No inbound port, no arbitrary shell."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time
from readonly_runner import run

DISPLAY_COMMANDS = {"git-branch": "git branch --show-current"}

def show(message):
    stamp = dt.datetime.now().astimezone().strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)

REPO = "bmifsud/toolz"
ISSUE = 24
OWNER = "bmifsud"
REQUEST = "TERMUX_DIAG_REQUEST_V2 "
RESULT = "TERMUX_DIAG_RESULT_V2 "
COMMANDS = frozenset({"git-branch"})
STATE_DIR = Path.home() / ".local/state/toolz-termux-bridge"

def gh(*args):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=25)
    if p.returncode:
        raise RuntimeError("GitHub request failed")
    if len(p.stdout) > 256000:
        raise ValueError("GitHub response too large")
    return p.stdout

def validate(comment, now):
    if comment.get("user", {}).get("login") != OWNER:
        return None
    body = comment.get("body", "")
    if not isinstance(body, str) or not body.startswith(REQUEST):
        return None
    try:
        value = json.loads(body[len(REQUEST):])
        if not isinstance(value, dict) or set(value) != {"id", "diagnostic", "expires_at"}:
            return None
        if not isinstance(value["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", value["id"]):
            return None
        if value["diagnostic"] not in COMMANDS:
            return None
        expiry = dt.datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00"))
        if expiry.tzinfo is None or not now < expiry <= now + dt.timedelta(minutes=10):
            return None
        created = dt.datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
        if not now - dt.timedelta(minutes=10) <= created <= now + dt.timedelta(minutes=1):
            return None
        return value
    except (ValueError, KeyError, TypeError, AttributeError):
        return None

def poll_once(state_dir=STATE_DIR, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    comments = json.loads(gh("api", "--paginate", f"repos/{REPO}/issues/{ISSUE}/comments?per_page=100"))
    if not isinstance(comments, list):
        raise ValueError("Invalid GitHub response")
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    state = state_dir / "seen-comment-ids.json"
    seen = set(json.loads(state.read_text())) if state.exists() else set()
    processed_ids = {v[3:] for v in seen if v.startswith("id:")}
    for comment in comments:
        request = validate(comment, now)
        if request is None:
            continue
        comment_id = str(comment["id"])
        if "comment:" + comment_id in seen or request["id"] in processed_ids:
            continue
        # Persist before running; an interrupted publish is not retried automatically.
        seen.update({"comment:" + comment_id, "id:" + request["id"]})
        processed_ids.add(request["id"])
        tmp = state.with_suffix(".tmp")
        tmp.write_text(json.dumps(sorted(seen)))
        tmp.chmod(0o600)
        os.replace(tmp, state)
        show(f"REQUEST RECEIVED id={request['id']} diagnostic={request['diagnostic']}")
        show(f"AUTHORIZED — executing: $ {DISPLAY_COMMANDS[request['diagnostic']]}")
        started_at = dt.datetime.now(dt.timezone.utc)
        started_ns = time.monotonic_ns()
        result = run(request["diagnostic"])
        finished_at = dt.datetime.now(dt.timezone.utc)
        duration_ms = max(0, (time.monotonic_ns() - started_ns) // 1_000_000)
        show(f"COMPLETED exit={result.get('exit_code', 'unknown')} duration={duration_ms}ms")
        for stream in ("stdout", "stderr"):
            output = result.get(stream, "")
            if output:
                show(f"{stream.upper()}:\n{output.rstrip()}")
        payload = {"id": request["id"], "result": result,
                   "receipt": {"started_at": started_at.isoformat(),
                               "finished_at": finished_at.isoformat(),
                               "duration_ms": duration_ms,
                               "command": DISPLAY_COMMANDS[request["diagnostic"]]}}
        gh("api", f"repos/{REPO}/issues/{ISSUE}/comments",
           "--method", "POST", "-f", "body=" + RESULT + json.dumps(payload))
        show(f"RESULT POSTED id={request['id']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=20)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not 10 <= args.interval <= 3600:
        parser.error("interval must be 10-3600 seconds")
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    stop = STATE_DIR / "STOP"
    if stop.exists():
        print("STOP file exists; remove it manually before starting")
        return
    show(f"CONNECTED — polling issue #{ISSUE} every {args.interval}s; stop with Ctrl-C or: touch {stop}")
    try:
        while not stop.exists():
            try:
                poll_once()
            except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                print("Poll failed:", exc, flush=True)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        print("Worker exited")

if __name__ == "__main__":
    main()
