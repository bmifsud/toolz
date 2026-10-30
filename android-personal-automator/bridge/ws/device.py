#!/usr/bin/env python3
"""Termux read-only device listener. Requires explicit local start."""
import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from readonly_runner import COMMANDS
from replay_store import ReplayStore

# Remote diagnostics are intentionally read-only; git_sync_pr.py is local-only.
ALLOWED_DIAGNOSTICS = frozenset({"git-branch", "ssh-status"})

URL = os.environ["BRIDGE_WS_URL"].rstrip("/")
TOKEN = os.environ["BRIDGE_DEVICE_TOKEN"]
STOP = Path.home() / ".local/state/toolz-termux-bridge/STOP"
if not URL.startswith("wss://") or len(TOKEN) < 32:
    raise SystemExit("Require wss:// and a long device token")

class OutputLimitExceeded(Exception):
    """A subprocess emitted more data than the permitted receipt budget."""


async def _read_limited(stream, limit):
    """Read at most limit bytes; never buffer unlimited subprocess output."""
    chunks = []
    total = 0
    while True:
        chunk = await stream.read(min(1024, limit - total + 1))
        if not chunk:
            return b"".join(chunks)
        if total + len(chunk) > limit:
            raise OutputLimitExceeded()
        chunks.append(chunk)
        total += len(chunk)



async def _terminate_process_group(process):
    """Best-effort whole-group termination, even after the leader has exited.

    A process may leave children in its session after the parent has been
    reaped. The process return code is NOT proof that the group has stopped.
    On platforms where the group cannot be proven absent, fail closed.
    """
    pgid = process.pid  # start_new_session=True makes the leader the PGID.
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        return False

    for _ in range(20):
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            break
        except PermissionError:
            return False
        await asyncio.sleep(0.05)
    else:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            return False

    if process.returncode is None:
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except asyncio.TimeoutError:
            return False

    # killpg(..., 0) can still see unreaped zombies; conservative failure
    # is preferable to asserting successful termination without evidence.
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


async def run_diagnostic(ws, request_id, diagnostic):
    """Run a fixed allowlisted diagnostic with bounded memory and cancellation."""
    if diagnostic not in ALLOWED_DIAGNOSTICS:
        raise ValueError("diagnostic not remotely allowlisted")
    command = COMMANDS[diagnostic]
    cwd = None
    if diagnostic == "tier1-tests":
        checkout = Path.home() / "toolz-tier1-test"
        if not (checkout / "backup/tests/test_tier1.py").is_file():
            await ws.send(json.dumps({"type": "result", "id": request_id,
                "result": {"diagnostic": diagnostic, "error": "test checkout missing", "exit_code": 2}}))
            return
        cwd = str(checkout)
    process = await asyncio.create_subprocess_exec(
        *command, cwd=cwd, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, start_new_session=True)
    tasks = []
    try:
        tasks = [
            asyncio.create_task(_read_limited(process.stdout, 4096)),
            asyncio.create_task(_read_limited(process.stderr, 1024)),
            asyncio.create_task(process.wait()),
        ]
        try:
            stdout, stderr, _ = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=120 if diagnostic == "tier1-tests" else 10)
            result = {"diagnostic": diagnostic, "exit_code": process.returncode,
                      "stdout": stdout.decode("utf-8", errors="replace"),
                      "stderr": stderr.decode("utf-8", errors="replace")}
        except OutputLimitExceeded:
            result = {"diagnostic": diagnostic, "error": "output limit exceeded",
                      "exit_code": 125}
        except asyncio.TimeoutError:
            result = {"diagnostic": diagnostic, "error": "timeout", "exit_code": 124}
    finally:
        group_stopped = await _terminate_process_group(process)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    # Never report success when descendants may still be running.
    if not group_stopped:
        result = {"diagnostic": diagnostic, "error": "worker termination unverified",
                  "exit_code": 126}
    # Send a receipt only after any overflowed/timed-out worker has stopped.
    if not STOP.exists():
        await ws.send(json.dumps({"type": "result", "id": request_id, "result": result}))


async def main():
    # Commit IDs to disk before execution; restart must not permit replay.
    replay_store = ReplayStore()
    while not STOP.exists():
        try:
            async with connect(URL + "/device", additional_headers={"Authorization": "Bearer " + TOKEN}, max_size=8192, ping_interval=20) as ws:
                print("[bridge] Connected; waiting for authorized requests", flush=True)
                active = {}  # request id -> cancellable subprocess task
                try:
                    while not STOP.exists():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=1)
                        except asyncio.TimeoutError:
                            continue
                        except ConnectionClosed:
                            break
                        try:
                            data = json.loads(raw)
                            if not isinstance(data, dict):
                                continue
                            if data.get("type") == "cancel":
                                if set(data) != {"type", "id"}:
                                    continue
                                task = active.get(data["id"]) if isinstance(data["id"], str) else None
                                if task is not None:
                                    task.cancel()
                                continue
                            if data.get("type") != "request" or data.get("diagnostic") not in ALLOWED_DIAGNOSTICS:
                                continue
                            request_id = data.get("id")
                            if not isinstance(request_id, str) or not (8 <= len(request_id) <= 64) or not request_id.replace("-", "").replace("_", "").isalnum():
                                continue
                            if not replay_store.claim(request_id):
                                continue
                            print(f"[bridge] REQUEST {request_id}: {data['diagnostic']}", flush=True)
                            task = asyncio.create_task(run_diagnostic(ws, request_id, data["diagnostic"]))
                            active[request_id] = task
                            def forget(done, request_id=request_id):
                                if active.get(request_id) is done:
                                    active.pop(request_id, None)
                            task.add_done_callback(forget)
                        except (ValueError, TypeError, AttributeError):
                            continue
                finally:
                    tasks = list(active.values())
                    for task in tasks:
                        task.cancel()
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
        except (OSError, TimeoutError, InvalidHandshake) as exc:
            print(f"[bridge] Disconnected: {type(exc).__name__}; retrying", flush=True)
        if STOP.exists():
            break
        await asyncio.sleep(5)
    print("[bridge] STOP requested", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
