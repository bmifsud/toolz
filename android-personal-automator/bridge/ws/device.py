#!/usr/bin/env python3
"""Termux read-only device listener. Requires explicit local start."""
import asyncio
import json
import os
import ssl
import signal
import sys
from pathlib import Path
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from readonly_runner import COMMANDS

URL = os.environ["BRIDGE_WS_URL"].rstrip("/")
TOKEN = os.environ["BRIDGE_DEVICE_TOKEN"]
STOP = Path.home() / ".local/state/toolz-termux-bridge/STOP"
if not URL.startswith("wss://") or len(TOKEN) < 32:
    raise SystemExit("Require wss:// and a long device token")

async def run_diagnostic(ws, request_id, diagnostic):
    """Execute only allowlisted commands; stop the subprocess on cancellation."""
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
    try:
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=120 if diagnostic == "tier1-tests" else 10)
            result = {"diagnostic": diagnostic, "exit_code": process.returncode,
                      "stdout": stdout.decode("utf-8", errors="replace")[:4096],
                      "stderr": stderr.decode("utf-8", errors="replace")[:1024]}
        except asyncio.TimeoutError:
            result = {"diagnostic": diagnostic, "error": "timeout"}
            raise
        if not STOP.exists():
            await ws.send(json.dumps({"type": "result", "id": request_id, "result": result}))
    except asyncio.TimeoutError:
        if not STOP.exists():
            await ws.send(json.dumps({"type": "result", "id": request_id, "result": result}))
    finally:
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()

async def main():
    seen = set()
    while not STOP.exists():
        try:
            async with connect(URL + "/device", additional_headers={"Authorization": "Bearer " + TOKEN}, max_size=8192, ping_interval=20) as ws:
                print("[bridge] Connected; waiting for authorized requests", flush=True)
                active = set()
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
                            if not isinstance(data, dict) or data.get("type") != "request" or data.get("diagnostic") not in ("git-branch", "tier1-tests"):
                                continue
                            request_id = data.get("id")
                            if not isinstance(request_id, str) or not (8 <= len(request_id) <= 64) or not request_id.replace("-", "").replace("_", "").isalnum() or request_id in seen:
                                continue
                            seen.add(request_id)
                            print(f"[bridge] REQUEST {request_id}: {data['diagnostic']}", flush=True)
                            task = asyncio.create_task(run_diagnostic(ws, request_id, data["diagnostic"]))
                            active.add(task)
                            task.add_done_callback(active.discard)
                        except (ValueError, TypeError, AttributeError):
                            continue
                finally:
                    for task in active:
                        task.cancel()
                    if active:
                        await asyncio.gather(*active, return_exceptions=True)
        except (OSError, TimeoutError) as exc:
            print(f"[bridge] Disconnected: {type(exc).__name__}; retrying", flush=True)
        if STOP.exists():
            break
        await asyncio.sleep(5)
    print("[bridge] STOP requested", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
