"""Pure hybrid request router: no network calls or device execution."""
from dataclasses import dataclass
import hashlib
import json
import re
from datetime import datetime, timezone

PREFIX = re.compile(r"^\s*@(ChatGPT|GitHub|Termux|Debian)\b\s*:?[ \t]*", re.I)
TERMUX = re.compile(r"\b(termux|tablet|android device|on my device|cron|local backup|device logs)\b", re.I)
DEBIAN = re.compile(r"\\b(debian|andronix|proot|rootfs|tier-2|tier 2)\\b", re.I)
GITHUB = re.compile(r"\b(github|pull request|\bpr\b|repository|commit|workflow|actions|branch)\b", re.I)
MUTATE = re.compile(r"\b(delete|remove|install|uninstall|restart|stop|start|modify|write|push|merge|deploy|backup now|run backup)\b", re.I)
TEST = re.compile(r"\b(test|pytest|verify|validation|check suite)\b", re.I)

@dataclass(frozen=True)
class Decision:
    destination: str
    permission: str
    action: str
    reason: str

def route(message: str) -> Decision:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Nonempty message required")
    match = PREFIX.match(message)
    explicit = match.group(1).lower() if match else None
    body = message[match.end():] if match else message
    if not body.strip():
        return Decision("chatgpt", "clarify", "none", "empty prefixed request")
    if explicit:
        target = {"chatgpt": "chatgpt", "github": "github", "termux": "termux", "debian": "debian"}[explicit]
    else:
        targets = [name for name, found in (("termux", TERMUX.search(body)), ("debian", DEBIAN.search(body)), ("github", GITHUB.search(body))) if found]
        if len(targets) > 1:
            return Decision("chatgpt", "clarify", "none", "multiple execution targets")
        target = targets[0] if targets else "chatgpt"
    if target == "chatgpt":
        return Decision(target, "none", "answer", "local response or clarification")
    if MUTATE.search(body):
        return Decision(target, "approval_required", "propose_only", "mutating operation")
    if target in ("termux", "debian"):
        if TEST.search(body):
            return Decision(target, "allowlisted_only", "propose_diagnostic", "bounded test requested")
        return Decision(target, "allowlisted_only", "propose_diagnostic", "read-only diagnostic")
    return Decision(target, "connector_scoped", "propose_connector", "GitHub connector required")

def audit_event(message: str, decision: Decision, request_id: str, at=None) -> str:
    """Return JSONL record without raw prompts, credentials or command arguments."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", request_id):
        raise ValueError("Invalid request id")
    at = at or datetime.now(timezone.utc)
    return json.dumps({
        "timestamp": at.isoformat(), "request_id": request_id,
        "request_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
        "destination": decision.destination, "permission": decision.permission,
        "action": decision.action, "reason": decision.reason,
    }, sort_keys=True)
