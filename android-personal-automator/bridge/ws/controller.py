#!/usr/bin/env python3
"""Explicitly invoked, read-only WebSocket controller. Never stores credentials."""
import asyncio
import json
import os
import secrets
import sys
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

URL = os.environ.get("BRIDGE_WS_URL", "wss://toolz-termux-ws-relay.onrender.com").rstrip("/")
TOKEN = os.environ.get("BRIDGE_CONTROLLER_TOKEN", "")
ALLOWED_DIAGNOSTICS = frozenset({"git-branch", "ssh-status"})

async def main():
    if not URL.startswith("wss://") or len(TOKEN) < 32:
        raise SystemExit("Set BRIDGE_CONTROLLER_TOKEN (32+ characters) and a wss:// URL")
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in TOKEN):
        raise SystemExit("[controller] invalid token characters; use a single-line printable ASCII token")
    diagnostic = sys.argv[1] if len(sys.argv) > 1 else "git-branch"
    if diagnostic not in ALLOWED_DIAGNOSTICS:
        raise SystemExit("Unsupported diagnostic")
    request_id = "cli-" + secrets.token_hex(12)
    print(f"[controller] connecting to {URL}/controller", flush=True)
    async with connect(URL + "/controller", additional_headers={"Authorization": "Bearer " + TOKEN}, open_timeout=15, max_size=8192) as ws:
        await ws.send(json.dumps({"id": request_id, "diagnostic": diagnostic}))
        print(f"[controller] sent {request_id}: {diagnostic}", flush=True)
        while True:
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=360))
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
    except (OSError, TimeoutError, ConnectionClosed, ValueError) as exc:
        print(f"[controller] connection or response failed: {type(exc).__name__} (credentials redacted)", file=sys.stderr)
        sys.exit(2)
