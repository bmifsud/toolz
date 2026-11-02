"""Verify bounded diagnostic receipts without accepting arbitrary remote execution."""
from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from typing import Any, Mapping

MAX_OUTPUT = 16384
try:
    from .routing_adapter import HOST_DIAGNOSTICS, DEBIAN_DIAGNOSTICS
except ImportError:
    from routing_adapter import HOST_DIAGNOSTICS, DEBIAN_DIAGNOSTICS

VALID_DIAGNOSTICS = HOST_DIAGNOSTICS | DEBIAN_DIAGNOSTICS
REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")

@dataclass(frozen=True)
class VerifiedReceipt:
    request_id: str
    diagnostic: str
    exit_code: int
    stdout: str
    stderr: str
    output_sha256: str

def verify_receipt(payload: Mapping[str, Any], *,
                   expected_request_id: str,
                   expected_diagnostic: str) -> VerifiedReceipt:
    """Validate shape and correlation. Caller must authenticate transport first.

    This is NOT cryptographic proof of device origin; transport authentication and
    server-side request tracking must be enforced by the integrating bridge.
    """
    if not isinstance(expected_request_id, str) or not REQUEST_ID.fullmatch(expected_request_id):
        raise ValueError("invalid expected request ID")
    if not isinstance(expected_diagnostic, str) or expected_diagnostic not in VALID_DIAGNOSTICS:
        raise ValueError("diagnostic not allowlisted")
    if not isinstance(payload, dict):
        raise ValueError("invalid receipt")
    request_id = payload.get("request_id")
    diagnostic = payload.get("diagnostic")
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id) or not hmac.compare_digest(request_id, expected_request_id):
        raise ValueError("request ID mismatch")
    if not isinstance(diagnostic, str) or diagnostic not in VALID_DIAGNOSTICS or not hmac.compare_digest(diagnostic, expected_diagnostic):
        raise ValueError("diagnostic mismatch")
    code = payload.get("exit_code")
    if type(code) is not int or not (-1 <= code <= 255):
        raise ValueError("invalid exit code")
    stdout, stderr = payload.get("stdout"), payload.get("stderr")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise ValueError("invalid output")
    try:
        output_bytes = len(stdout.encode("utf-8")) + len(stderr.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ValueError("invalid UTF-8 output") from error
    if output_bytes > MAX_OUTPUT:
        raise ValueError("output exceeds receipt limit")
    digest = hashlib.sha256(json.dumps(
        [request_id, diagnostic, code, stdout, stderr],
        ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    return VerifiedReceipt(request_id, diagnostic, code, stdout, stderr, digest)
