#!/usr/bin/env python3
"""Minimal opt-in WebSocket relay; no shell execution on server."""
import asyncio
import json
import os
import secrets
from urllib.parse import urlsplit
from types import SimpleNamespace
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocketDisconnect
import uvicorn

HOST = os.environ.get("BRIDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
DEVICE_TOKEN = os.environ["BRIDGE_DEVICE_TOKEN"]
CONTROLLER_TOKEN = os.environ["BRIDGE_CONTROLLER_TOKEN"]
if len(DEVICE_TOKEN) < 32 or len(CONTROLLER_TOKEN) < 32 or DEVICE_TOKEN == CONTROLLER_TOKEN:
    raise SystemExit("Use distinct random tokens of at least 32 characters")
device = None
MAX_PENDING = 16
MAX_MESSAGE = 8192

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
                if len(message) > MAX_MESSAGE:
                    await ws.close(code=1009)
                    break
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
        except WebSocketDisconnect:
            pass  # Normal disconnect during mobile sleep or deployment.
        finally:
            if device is ws:
                device = None
    else:
        try:
            async for message in ws:
                if len(message) > MAX_MESSAGE:
                    await ws.close(code=1009)
                    break
                try:
                    data = json.loads(message)
                    if not isinstance(data, dict) or set(data) != {"id", "diagnostic"}:
                        continue
                    if data["diagnostic"] not in ("git-branch", "tier1-tests") or not isinstance(data["id"], str) or not (8 <= len(data["id"]) <= 64) or not data["id"].replace("-", "").replace("_", "").isalnum():
                        continue
                    if device is None:
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"device offline"}))
                        continue
                    if data["id"] in pending or len(pending) >= MAX_PENDING:
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"duplicate or busy"}))
                        continue
                    pending[data["id"]] = ws
                    try:
                        await asyncio.wait_for(device.send(json.dumps({"type":"request", **data})), timeout=5)
                    except (OSError, RuntimeError, ConnectionError, asyncio.TimeoutError):
                        pending.pop(data["id"], None)
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"device unavailable"}))
                except (ValueError, TypeError):
                    continue
        except WebSocketDisconnect:
            pass  # Controller disconnected without a close frame.
        finally:
            for key, value in list(pending.items()):
                if value is ws:
                    pending.pop(key, None)

pending = {}

async def process_request(connection, request):
    """Retained for the offline health endpoint contract test."""
    if request.path == "/healthz":
        return SimpleNamespace(status_code=200, body=b"ok\n")
    return None

class SocketAdapter:
    """Expose the existing relay handler interface over ASGI WebSockets."""
    def __init__(self, socket):
        self.socket = socket
        self.request = SimpleNamespace(
            path=socket.scope["path"] + ("?" + socket.scope["query_string"].decode("ascii") if socket.scope["query_string"] else ""),
            headers=socket.headers,
        )

    async def send(self, message):
        await self.socket.send_text(message)

    async def close(self, **kwargs):
        await self.socket.close(**kwargs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.socket.receive_text()
        except WebSocketDisconnect:
            raise StopAsyncIteration

async def websocket_endpoint(socket):
    await socket.accept()
    await handler(SocketAdapter(socket))

async def healthz(request):
    return PlainTextResponse("ok\n", headers={"Cache-Control": "no-store"})

app = Starlette(routes=[
    Route("/healthz", healthz, methods=["GET", "HEAD"]),
    WebSocketRoute("/device", websocket_endpoint),
    WebSocketRoute("/controller", websocket_endpoint),
])

async def main():
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
