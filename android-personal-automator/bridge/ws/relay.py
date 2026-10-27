#!/usr/bin/env python3
"""Minimal opt-in WebSocket relay; no shell execution on server."""
import asyncio
import json
import os
import secrets
from urllib.parse import urlsplit
from websockets.asyncio.server import serve

HOST = os.environ.get("BRIDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
DEVICE_TOKEN = os.environ["BRIDGE_DEVICE_TOKEN"]
CONTROLLER_TOKEN = os.environ["BRIDGE_CONTROLLER_TOKEN"]
if len(DEVICE_TOKEN) < 32 or len(CONTROLLER_TOKEN) < 32 or DEVICE_TOKEN == CONTROLLER_TOKEN:
    raise SystemExit("Use distinct random tokens of at least 32 characters")
device = None

async def handler(ws):
    global device
    path = urlsplit(ws.request.path)
    role = path.path
    authorization = ws.request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    expected = DEVICE_TOKEN if role == "/device" else CONTROLLER_TOKEN if role == "/controller" else ""
    if path.query or not expected or not secrets.compare_digest(token, expected):
        await ws.close(code=1008, reason="Unauthorized")
        return
    if role == "/device":
        if device is not None:
            await ws.close(code=1008, reason="Device already connected")
            return
        device = ws
        try:
            async for message in ws:
                # Device results are forwarded only to the controller that requested them.
                try:
                    payload = json.loads(message)
                    if not isinstance(payload, dict) or payload.get("type") != "result":
                        continue
                    request_id = payload.get("id")
                    if not isinstance(request_id, str):
                        continue
                    target = pending.pop(request_id, None)
                    if target is not None:
                        await target.send(json.dumps(payload))
                except (ValueError, TypeError):
                    continue
        finally:
            if device is ws:
                device = None
    else:
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    if not isinstance(data, dict) or set(data) != {"id", "diagnostic"}:
                        continue
                    if data["diagnostic"] != "git-branch" or not isinstance(data["id"], str) or not (8 <= len(data["id"]) <= 64) or not data["id"].replace("-", "").replace("_", "").isalnum():
                        continue
                    if device is None:
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"device offline"}))
                        continue
                    if data["id"] in pending:
                        continue
                    pending[data["id"]] = ws
                    await device.send(json.dumps({"type":"request", **data}))
                except (ValueError, TypeError):
                    continue
        finally:
            for key, value in list(pending.items()):
                if value is ws:
                    pending.pop(key, None)

pending = {}
async def main():
    async with serve(handler, HOST, PORT, max_size=8192, ping_interval=20, ping_timeout=20):
        print(f"Relay listening on {HOST}:{PORT}", flush=True)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
