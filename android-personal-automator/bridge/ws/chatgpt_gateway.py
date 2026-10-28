"""Draft authenticated HTTP-to-WebSocket diagnostic gateway.

Run separately from the public relay. Do not expose without HTTPS, rate limiting,
and an approved ChatGPT tool integration. No arbitrary commands or scripts.
"""
import asyncio
import hmac
import os
import re
import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import websockets

ALLOWED = frozenset({"git-branch", "ssh-status", "tier1-tests"})
MAX_RESPONSE_BYTES = 16384
app = FastAPI(title="Toolz diagnostic gateway", docs_url=None, redoc_url=None, openapi_url=None)


class DiagnosticRequest(BaseModel):
    diagnostic: str = Field(min_length=1, max_length=40)


def check_auth(header: str | None) -> None:
    expected = os.environ.get("BRIDGE_GATEWAY_TOKEN", "")
    if not expected or not header or not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    if not hmac.compare_digest(header[7:], expected):
        raise HTTPException(status_code=401, detail="unauthorized")


async def execute(diagnostic: str) -> dict:
    import json
    url = os.environ.get("BRIDGE_WS_URL", "")
    token = os.environ.get("BRIDGE_CONTROLLER_TOKEN", "")
    if not url.startswith("wss://") or not token:
        raise RuntimeError("secure controller configuration unavailable")
    request_id = secrets.token_hex(12)
    async with websockets.connect(
        url.rstrip("/") + "/controller",
        additional_headers={"Authorization": "Bearer " + token},
        open_timeout=8, close_timeout=3, max_size=MAX_RESPONSE_BYTES,
    ) as socket:
        await socket.send(json.dumps({"id": request_id, "diagnostic": diagnostic}))
        raw = await asyncio.wait_for(socket.recv(), timeout=30)
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise RuntimeError("invalid or oversized response")
        response = json.loads(raw)
        if response.get("id") != request_id:
            raise RuntimeError("response correlation mismatch")
        return response


@app.post("/diagnostic")
async def diagnostic(request: DiagnosticRequest, authorization: str | None = Header(default=None)):
    check_auth(authorization)
    if request.diagnostic not in ALLOWED:
        raise HTTPException(status_code=400, detail="diagnostic not allowlisted")
    try:
        result = await execute(request.diagnostic)
    except (OSError, TimeoutError, RuntimeError, ValueError, websockets.exceptions.WebSocketException):
        raise HTTPException(status_code=502, detail="bridge unavailable")
    # Preserve protocol result but never forward a relay's arbitrary extra fields.
    payload = result.get("result")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="invalid device result")
    return {
        "id": result["id"], "diagnostic": request.diagnostic,
        "exit_code": payload.get("exit_code"),
        "stdout": str(payload.get("stdout", ""))[:8192],
        "stderr": str(payload.get("stderr", ""))[:8192],
    }
