"""Fail-closed integration planning for hybrid routing.

This module never executes a connector call, shell command, or device diagnostic.
Remote Desktop Commander must select the device and authorize any proposed action separately.
"""
from dataclasses import dataclass
from typing import Optional

try:
    from .request_router import Decision
except ImportError:
    from request_router import Decision

HOST_DIAGNOSTICS = frozenset({"git-branch", "tier1-tests"})
DEBIAN_DIAGNOSTICS = frozenset({"debian-identity", "debian-disk"})

@dataclass(frozen=True)
class ExecutionPlan:
    destination: str
    status: str
    operation: Optional[str]
    reason: str

def plan_execution(decision: Decision, diagnostic: Optional[str] = None,
                   *, desktop_commander_available: bool = False,
                   user_approved: bool = False) -> ExecutionPlan:
    target = getattr(decision, "destination", None)
    permission = getattr(decision, "permission", None)
    action = getattr(decision, "action", None)
    reason = getattr(decision, "reason", None)
    if not all(isinstance(value, str) for value in (target, permission, action, reason)):
        return ExecutionPlan("unknown", "denied", None, "invalid decision shape")
    if type(desktop_commander_available) is not bool or type(user_approved) is not bool:
        return ExecutionPlan(target, "denied", None, "availability and approval flags must be boolean")
    allowed = {
        "chatgpt": {("none", "answer"), ("clarify", "none")},
        "github": {("connector_scoped", "propose_connector"), ("approval_required", "propose_only")},
        "desktop_commander": {("allowlisted_only", "propose_diagnostic"), ("approval_required", "propose_only")},
    }
    if (permission, action) not in allowed.get(target, set()):
        return ExecutionPlan(target, "denied", None, "unsupported decision state")
    if permission == "clarify":
        return ExecutionPlan(target, "clarification_required", None, reason)
    if decision.destination == "chatgpt":
        return ExecutionPlan("chatgpt", "local_only", None, decision.reason)
    if decision.permission == "approval_required" and not user_approved:
        return ExecutionPlan(decision.destination, "approval_required", None, "explicit approval required")
    if decision.destination == "github":
        return ExecutionPlan("github", "connector_required", None,
                             "scoped GitHub connector must authorize and execute separately")
    if decision.destination == "desktop_commander":
        target = decision.destination
        allowlist = HOST_DIAGNOSTICS | DEBIAN_DIAGNOSTICS
        if not isinstance(diagnostic, str) or diagnostic not in allowlist:
            return ExecutionPlan(target, "denied", None, "unknown or missing allowlisted diagnostic")
        if not desktop_commander_available:
            return ExecutionPlan(target, "desktop_commander_unavailable", None, "Remote Desktop Commander device access required")
        if decision.permission == "approval_required":
            return ExecutionPlan(target, "denied", None, "mutating device actions not supported")
        return ExecutionPlan(target, "ready_for_commander", diagnostic,
                             "planning only; Desktop Commander must verify device, authorization and receipt")
    return ExecutionPlan(decision.destination, "denied", None, "unknown destination")
