#!/usr/bin/env python3
"""Opt-in, fixed-target Git sync. Never accepts shell commands or branch arguments."""
import os
import subprocess
import sys
from pathlib import Path

BRANCH = "feat/termux-readonly-bridge-20261027"
ROOT = Path.home() / "toolz-bridge-test"


def git(*args, timeout=120):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                          capture_output=True, timeout=timeout)


def main():
    if os.environ.get("BRIDGE_ALLOW_GIT_WRITE") != "yes":
        print("DENIED: set BRIDGE_ALLOW_GIT_WRITE=yes locally before starting device listener")
        return 3
    if not (ROOT / ".git").exists():
        print("DENIED: isolated checkout missing")
        return 3
    try:
        if git("status", "--porcelain").stdout.strip():
            print("DENIED: working tree is dirty")
            return 3
        if git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != BRANCH:
            print("DENIED: checkout must be on the exact PR branch")
            return 3
        if git("remote", "get-url", "origin").stdout.strip() not in (
            "https://github.com/bmifsud/toolz",
            "https://github.com/bmifsud/toolz.git",
            "git@github.com:bmifsud/toolz.git",
        ):
            print("DENIED: origin is not bmifsud/toolz")
            return 3
        git("fetch", "origin", "main", BRANCH)
        if git("rev-parse", "HEAD").stdout.strip() != git("rev-parse", "refs/remotes/origin/" + BRANCH).stdout.strip():
            print("DENIED: local PR branch differs from origin; reconcile manually")
            return 3
        git("merge", "--no-edit", "origin/main")
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover",
            "-s", "android-personal-automator/bridge/ws", "-p", "test_*.py"],
            cwd=ROOT, capture_output=True, text=True, timeout=180)
        if tests.returncode:
            print("FAILED: tests did not pass; push skipped")
            return 1
        git("push", "origin", "HEAD:refs/heads/" + BRANCH)
        print("PASS: main integrated, bridge tests passed, PR branch pushed")
        return 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print("FAILED: git operation or tests failed; push not confirmed (" + type(exc).__name__ + ")")
        return 1


if __name__ == "__main__":
    sys.exit(main())
