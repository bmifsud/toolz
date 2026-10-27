#!/usr/bin/env python3
"""Termux read-only device listener. Requires explicit local start."""
import asyncio
import json
import os
import ssl
import sys
from pathlib import Path
from websockets.asyncio.client import connect
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from readonly_runner import run

URL = os.environ["BRIDGE_WS_URL"].rstrip("/")
TOKEN = os.environ["BRIDGE_DEVICE_TOKEN"]
STOP = Path.home() / ".local/state/toolz-termux-bridge/STOP"
if not URL.startswith("wss://") or len(TOKEN) < 32:
    raise SystemExit("Require wss:// and a long device token")

async def main():
    seen = set()
    while not STOP.exists():
        try:
            async with connect(URL + "/device", additional_headers={"Authorization": "Bearer " + TOKEN}, max_size=8192, ping_interval=20) as ws:
                print("[bridge] Connected; waiting for authorized requests", flush=True)
                async for raw in ws:
                    if STOP.exists():
                        break
                    try:
                        data = json.loads(raw)
                        if data.get("type") != "request" or data.get("diagnostic") not in ("git-branch", "tier1-tests"):
                            continue
                        request_id = data.get("id")
                        if not isinstance(request_id, str) or not (8 <= len(request_id) <= 64) or not request_id.replace("-", "").replace("_", "").isalnum() or request_id in seen:
                            continue
                        seen.add(request_id)
                        print(f"[bridge] REQUEST {request_id}: {data['diagnostic']}", flush=True)
                        result = run(data["diagnostic"])
                        print(f"[bridge] exit={result.get('exit_code')} stdout={result.get('stdout', '').rstrip()}", flush=True)
                        await ws.send(json.dumps({"type":"result","id":request_id,"result":result}))
                    except (ValueError, TypeError, AttributeError):
                        continue
        except (OSError, TimeoutError) as exc:
            print(f"[bridge] Disconnected: {type(exc).__name__}; retrying", flush=True)
        await asyncio.sleep(5)
    print("[bridge] STOP requested", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
