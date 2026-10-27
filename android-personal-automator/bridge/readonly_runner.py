#!/usr/bin/env python3
"""Read-only, local diagnostic runner. No remote listener or arbitrary shell."""
import json
import subprocess
import sys

COMMANDS = {
    "identity": ["id"],
    "android": ["getprop", "ro.build.version.release"],
    "adb": ["adb", "devices"],
    "git-branch": ["git", "branch", "--show-current"],
    "git-status": ["git", "status", "--short"],
}
def run(name):
    if name not in COMMANDS:
        raise ValueError("Unknown diagnostic")
    try:
        p = subprocess.run(COMMANDS[name], capture_output=True, text=True,
                           timeout=10, check=False)
        return {"diagnostic": name, "exit_code": p.returncode,
                "stdout": p.stdout[:4096], "stderr": p.stderr[:1024]}
    except subprocess.TimeoutExpired:
        return {"diagnostic": name, "error": "timeout"}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python readonly_runner.py <diagnostic>")
    try:
        print(json.dumps(run(sys.argv[1])))
    except ValueError as exc:
        raise SystemExit(str(exc))
