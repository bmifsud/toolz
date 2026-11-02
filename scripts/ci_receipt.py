"""Minimal CI provenance receipt; no credential, environment or device-output dump."""
import json
import os
from pathlib import Path
import platform
import re
import subprocess


def receipt(commit, outcome, run_id, attempt, event):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected full tested Git commit")
    if outcome not in {"success", "failure", "cancelled", "skipped"}:
        raise ValueError("Unknown gate outcome")
    if not run_id.isdigit() or not attempt.isdigit():
        raise ValueError("Expected numeric CI run identifiers")
    return {
        "schema_version": 1,
        "tested_commit": commit,
        "offline_gate_outcome": outcome,
        "run_id": run_id,
        "run_attempt": attempt,
        "event": event,
        "python_version": platform.python_version(),
        "command": "bash tests/run-all-tests.sh",
        "scope": "offline fixtures only",
        "device_and_live_backup_acceptance": "unverified",
    }


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    data = receipt(commit, os.environ["GATE_OUTCOME"], os.environ["GITHUB_RUN_ID"],
                   os.environ["GITHUB_RUN_ATTEMPT"], os.environ["GITHUB_EVENT_NAME"])
    directory = Path(os.environ["EVIDENCE_DIRECTORY"])
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "receipt.json").write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
