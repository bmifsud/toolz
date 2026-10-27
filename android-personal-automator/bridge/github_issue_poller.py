#!/usr/bin/env python3
"""Opt-in one-shot GitHub issue diagnostic poller. No arbitrary shell execution."""
import json
import pathlib
import re
import subprocess
import sys
from readonly_runner import run

REPO = "bmifsud/toolz"
ISSUE = 24
PREFIX = "TERMUX_DIAG_REQUEST_V1 "
STATE = pathlib.Path.home() / ".local/state/toolz-termux-bridge/last-request"

def gh(*args):
    p = subprocess.run(["gh", *args], text=True, capture_output=True, timeout=20)
    if p.returncode:
        raise RuntimeError("GitHub request failed")
    return p.stdout

def once():
    issue = json.loads(gh("api", f"repos/{REPO}/issues/{ISSUE}"))
    if issue.get("user", {}).get("login") != "bmifsud":
        raise ValueError("Untrusted issue author")
    first = issue.get("body", "").splitlines()[0]
    if not first.startswith(PREFIX):
        raise ValueError("No diagnostic request")
    request = json.loads(first[len(PREFIX):])
    if (not isinstance(request, dict) or set(request) != {"id", "diagnostic"}
        or not isinstance(request["id"], str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", request["id"])
        or request["diagnostic"] not in ("git-branch", "git-status")):
        raise ValueError("Request rejected")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    if STATE.exists() and STATE.read_text() == request["id"]:
        print("Already processed")
        return
    result = run(request["diagnostic"])
    # Only public repository metadata, never ADB addresses or secrets.
    comment = "TERMUX_DIAG_RESULT_V1 " + json.dumps({"id": request["id"], "result": result})
    gh("api", f"repos/{REPO}/issues/{ISSUE}/comments",
       "-f", "body=" + comment, "--method", "POST")
    STATE.write_text(request["id"])
    print("Posted result for", request["id"])

if __name__ == "__main__":
    try:
        once()
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("Bridge error:", exc, file=sys.stderr)
        raise SystemExit(1)
