"""Bounded executor for an authorized host; not a ChatGPT connector.

The caller must supply an authenticated controller executable and credentials via
its environment. No model-provided shell commands or arguments are accepted.
"""
from dataclasses import dataclass
import os
import subprocess

ALLOWED = frozenset({"git-branch", "tier1-tests"})
MAX_BYTES = 16384

@dataclass(frozen=True)
class Result:
    diagnostic: str
    exit_code: int
    stdout: str
    stderr: str

def execute(diagnostic: str, *, controller_path: str, timeout: int = 30, controller_interface_verified: bool = False) -> Result:
    if controller_interface_verified is not True:\n        raise RuntimeError('controller --diagnostic interface has not been verified')\n    if diagnostic not in ALLOWED:
        raise ValueError("diagnostic not allowlisted")
    if not isinstance(controller_path, str) or not os.path.isabs(controller_path):
        raise ValueError("absolute controller path required")
    if not 1 <= timeout <= 120:
        raise ValueError("invalid timeout")
    if not os.environ.get("BRIDGE_CONTROLLER_TOKEN"):
        raise RuntimeError("controller authentication unavailable")
    if not os.environ.get("BRIDGE_WS_URL", "").startswith("wss://"):
        raise RuntimeError("secure relay URL required")
    # This interface requires a controller supporting an explicit diagnostic
    # argument; do not use until that contract is verified on the host.
    proc = subprocess.run(
        ["python", controller_path, "--diagnostic", diagnostic],
        capture_output=True, timeout=timeout, check=False, shell=False,
    )
    if len(proc.stdout) + len(proc.stderr) > MAX_BYTES:
        raise ValueError("controller output exceeds limit")
    return Result(diagnostic, proc.returncode,
                  proc.stdout.decode("utf-8", errors="replace"),
                  proc.stderr.decode("utf-8", errors="replace"))
