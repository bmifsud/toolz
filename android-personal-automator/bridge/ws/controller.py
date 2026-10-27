#!/usr/bin/env python3
"""Explicitly invoked, read-only WebSocket controller. Never stores credentials."""
import asyncio
import json
import os
import secrets
import sys
from websockets.asyncio.client import connect

URL = os.environ.get("BRIDGE_WS_URL", "wss://toolz-termux-ws-relay.onrender.com").rstrip("/")
TOKEN = os.environ.get("BRIDGE_CONTROLLER_TOKEN", "")

async def main():
    if not URL.startswith("wss://") or len(TOKEN) < 32:
        raise SystemExit("Set BRIDGE_CONTROLLER_TOKEN (32+ characters) and a wss:// URL")
    diagnostic = sys.argv[1] if len(sys.argv) > 1 else "git-branch"
    if diagnostic not in ("git-branch", "tier1-tests", "ssh-status"):
        raise SystemExit("Unsupported diagnostic")
    request_id = "cli-" + secrets.token_hex(12)
    print(f"[controller] connecting to {URL}/controller", flush=True)
    async with connect(URL + "/controller", additional_headers={"Authorization": "Bearer " + TOKEN}, open_timeout=15, max_size=8192) as ws:
        await ws.send(json.dumps({"id": request_id, "diagnostic": diagnostic}))
        print(f"[controller] sent {request_id}: {diagnostic}", flush=True)
        while True:
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if response.get("id") != request_id:
                continue
            if response.get("type") == "error":
                print(f"[controller] error: {response.get('message')}", flush=True)
                return 2
            if response.get("type") == "result":
                result = response.get("result", {})
                print(f"[controller] exit={result.get('exit_code')}", flush=True)
                print(result.get("stdout", ""), end="", flush=True)
                if result.get("stderr"):
                    print(result["stderr"], file=sys.stderr, flush=True)
                return 0 if result.get("exit_code") == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (OSError, TimeoutError) as exc:
        raise SystemExit(f"[controller] connection or response failed: {type(exc).__name__}") from exc
