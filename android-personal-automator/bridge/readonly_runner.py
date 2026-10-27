#!/usr/bin/env python3
"""Read-only, local diagnostic runner. No remote listener or arbitrary shell."""
import json
from pathlib import Path
import subprocess
import sys

COMMANDS = {
    "identity": ["id"],
    "android": ["getprop", "ro.build.version.release"],
    "adb": ["adb", "devices"],
    "ssh-status": [sys.executable, "-c", "import socket; s=socket.socket(); s.settimeout(1); rc=s.connect_ex(('127.0.0.1',8022)); s.close(); print('SSH port 8022: listening' if rc == 0 else 'SSH port 8022: not reachable'); raise SystemExit(0 if rc == 0 else 1)"],
    "git-branch": ["git", "branch", "--show-current"],
    "git-status": ["git", "status", "--short"],
    "tier1-tests": ["python", "-m", "pytest", "backup/tests/test_tier1.py", "-q", "-rx"],
}
def run(name):
    if name not in COMMANDS:
        raise ValueError("Unknown diagnostic")
    try:
        cwd = str(Path.home() / "toolz-tier1-test") if name == "tier1-tests" else None
        if cwd is not None and not Path(cwd, "backup/tests/test_tier1.py").is_file():
            return {"diagnostic": name, "error": "test checkout missing", "exit_code": 2}
        p = subprocess.run(COMMANDS[name], cwd=cwd, capture_output=True, text=True,
                           timeout=120 if name == "tier1-tests" else 10, check=False)
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
