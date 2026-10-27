#!/usr/bin/env python3
"""Explicitly invoked bridge orchestration adapter. No credentials in receipts."""
import asyncio
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from websockets.asyncio.client import connect

ALLOWED = frozenset(("git-branch", "tier1-tests"))
DEFAULT_URL = "wss://toolz-termux-ws-relay.onrender.com"

def receipt(request_id, diagnostic, response):
    """Bounded, redacted audit receipt; stdout and stderr never included."""
    result = response.get("result", {}) if isinstance(response.get("result"), dict) else {}
    raw = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "toolz.bridge.receipt.v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "diagnostic": diagnostic,
        "response_type": response.get("type"),
        "exit_code": result.get("exit_code") if type(result.get("exit_code")) is int else None,
        "result_sha256": hashlib.sha256(raw).hexdigest(),
        "verified_origin": False,
    }

async def run(diagnostic, *, token=None, url=None):
    if diagnostic not in ALLOWED:
        raise ValueError("Diagnostic is not allowlisted")
    token = token if token is not None else os.environ.get("BRIDGE_CONTROLLER_TOKEN", "")
    url = (url or os.environ.get("BRIDGE_WS_URL", DEFAULT_URL)).rstrip("/")
    if len(token) < 32 or not url.startswith("wss://") or "?" in url or "#" in url:
        raise ValueError("Requires a private 32+ character controller token and wss:// URL")
    request_id = "orch-" + secrets.token_hex(12)
    async with connect(url + "/controller", additional_headers={"Authorization": "Bearer " + token}, open_timeout=15, max_size=8192) as ws:
        await ws.send(json.dumps({"id": request_id, "diagnostic": diagnostic}))
        while True:
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if not isinstance(response, dict) or response.get("id") != request_id:
                continue
            if response.get("type") not in ("result", "error"):
                continue
            return {"receipt": receipt(request_id, diagnostic, response),
                    "result": response.get("result") if response["type"] == "result" else None,
                    "error": response.get("message") if response["type"] == "error" else None}

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ALLOWED:
        raise SystemExit("Usage: python orchestration_adapter.py git-branch|tier1-tests")
    try:
        output = asyncio.run(run(sys.argv[1]))
        print(json.dumps(output, sort_keys=True))
        return 0 if output["receipt"]["exit_code"] == 0 else 1
    except (ValueError, OSError, TimeoutError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": "Bridge request failed"}))
        return 2

if __name__ == "__main__":
    sys.exit(main())
