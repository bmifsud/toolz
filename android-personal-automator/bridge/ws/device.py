#!/usr/bin/env python3
"""Termux read-only device listener. Requires explicit local start."""
import asyncio
import json
import os
import ssl
import sys
from pathlib import Path
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from readonly_runner import run

URL = os.environ["BRIDGE_WS_URL"].rstrip("/")
TOKEN = os.environ["BRIDGE_DEVICE_TOKEN"]
STOP = Path.home() / ".local/state/toolz-termux-bridge/STOP"
if not URL.startswith("wss://") or len(TOKEN) < 32:
    raise SystemExit("Require wss:// and a long device token")

async def run_diagnostic(ws, request_id, diagnostic):
    """Run the fixed allowlisted diagnostic without blocking the event loop."""
    result = await asyncio.to_thread(run, diagnostic)
    if STOP.exists():
        return
    print(f"[bridge] exit={result.get('exit_code')} stdout={result.get('stdout', '').rstrip()}", flush=True)
    await ws.send(json.dumps({"type": "result", "id": request_id, "result": result}))

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
