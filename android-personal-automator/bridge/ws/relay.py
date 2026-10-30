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
ALLOWED_DIAGNOSTICS = frozenset({"git-branch", "ssh-status"})
REQUEST_TIMEOUT = 360

async def expire_request(request_id, controller):
    try:
        await asyncio.sleep(REQUEST_TIMEOUT)
        entry = pending.get(request_id)
        if entry is not None and entry[0] is controller:
            await cancel_pending(request_id, controller)
            await controller.send(json.dumps({"type": "error", "id": request_id, "message": "request timeout"}))
    except (OSError, RuntimeError, ConnectionError):
        pass

def authorized(ws):
    """Check role and bearer token before accepting a WebSocket handshake."""
    path = urlsplit(ws.request.path)
    authorization = ws.request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    expected = DEVICE_TOKEN if path.path == "/device" else CONTROLLER_TOKEN if path.path == "/controller" else ""
    return not path.query and bool(expected) and secrets.compare_digest(token, expected)


async def cancel_pending(request_id, controller):
    """Cancel only a request owned by this authenticated controller.

    Dropping the pending entry prevents late results from reaching the caller.
    The device must separately acknowledge termination for end-to-end proof.
    """
    entry = pending.get(request_id)
    if entry is None or entry[0] is not controller:
        return False
    pending.pop(request_id, None)
    timer = entry[1]
    if timer is not asyncio.current_task():
        timer.cancel()
    if device is not None:
        try:
            await asyncio.wait_for(
                device.send(json.dumps({"type": "cancel", "id": request_id})),
                timeout=5)
        except (OSError, RuntimeError, ConnectionError, asyncio.TimeoutError):
            pass  # Fail closed for receipts; no claim of worker termination.
    return True


async def handler(ws):
    global device
    role = urlsplit(ws.request.path).path
    if not authorized(ws):
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
                    entry = pending.pop(request_id, None)
                    if entry is not None:
                        target, timer = entry
                        timer.cancel()
                        await target.send(json.dumps(payload))
                except (ValueError, TypeError):
                    continue
        except WebSocketDisconnect:
            pass  # Normal disconnect during mobile sleep or deployment.
        finally:
            if device is ws:
                device = None
                for key, (target, timer) in list(pending.items()):
                    pending.pop(key, None)
                    timer.cancel()
                    try:
                        await target.send(json.dumps({"type": "error", "id": key, "message": "device disconnected"}))
                    except (OSError, RuntimeError, ConnectionError):
                        pass
    else:
        try:
            async for message in ws:
                if len(message) > MAX_MESSAGE:
                    await ws.close(code=1009)
                    break
                try:
                    data = json.loads(message)
                    if not isinstance(data, dict):
                        continue
                    if data.get("type") == "cancel" and set(data) == {"type", "id"}:
                        request_id = data["id"]
                        if not isinstance(request_id, str) or not (8 <= len(request_id) <= 64):
                            continue
                        cancelled = await cancel_pending(request_id, ws)
                        await ws.send(json.dumps({"type": "error", "id": request_id,
                            "message": "cancellation attempted; worker termination unverified" if cancelled else "unknown request"}))
                        continue
                    if set(data) != {"id", "diagnostic"}:
                        continue
                    if data["diagnostic"] not in ALLOWED_DIAGNOSTICS or not isinstance(data["id"], str) or not (8 <= len(data["id"]) <= 64) or not data["id"].replace("-", "").replace("_", "").isalnum():
                        continue
                    if device is None:
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"device offline"}))
                        continue
                    if data["id"] in pending or len(pending) >= MAX_PENDING:
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"duplicate or busy"}))
                        continue
                    pending[data["id"]] = (ws, asyncio.create_task(expire_request(data["id"], ws)))
                    try:
                        await asyncio.wait_for(device.send(json.dumps({"type":"request", **data})), timeout=5)
                    except (OSError, RuntimeError, ConnectionError, asyncio.TimeoutError):
                        entry = pending.pop(data["id"], None)
                        if entry is not None:
                            entry[1].cancel()
                        await ws.send(json.dumps({"type":"error","id":data["id"],"message":"device unavailable"}))
                except (ValueError, TypeError):
                    continue
        except WebSocketDisconnect:
            pass  # Controller disconnected without a close frame.
        finally:
            # A disconnected controller must not leave its device workers running.
            await asyncio.gather(*(cancel_pending(key, ws) for key, value
                                   in list(pending.items()) if value[0] is ws))

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
    adapter = SocketAdapter(socket)
    # A successful handshake must never be logged for an unauthenticated peer.
    if not authorized(adapter):
        await socket.close(code=1008, reason="Unauthorized")
        return
    await socket.accept()
    await handler(adapter)

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
