"""Fail-closed integration planning for hybrid routing.

This module never executes a connector call, shell command, or device diagnostic.
A separate authenticated executor must validate and authorize any proposed action.
"""
from dataclasses import dataclass
from typing import Optional

try:
    from .request_router import Decision
except ImportError:
    from request_router import Decision

TERMUX_DIAGNOSTICS = frozenset({"git-branch", "tier1-tests"})
DEBIAN_DIAGNOSTICS = frozenset({"debian-identity", "debian-disk"})

@dataclass(frozen=True)
class ExecutionPlan:
    destination: str
    status: str
    operation: Optional[str]
    reason: str

def plan_execution(decision: Decision, diagnostic: Optional[str] = None,
                   *, bridge_authenticated: bool = False,
                   user_approved: bool = False) -> ExecutionPlan:
    target = getattr(decision, "destination", None)
    permission = getattr(decision, "permission", None)
    action = getattr(decision, "action", None)
    reason = getattr(decision, "reason", None)
    if not all(isinstance(value, str) for value in (target, permission, action, reason)):
        return ExecutionPlan("unknown", "denied", None, "invalid decision shape")
    if type(bridge_authenticated) is not bool or type(user_approved) is not bool:
        return ExecutionPlan(target, "denied", None, "authentication and approval flags must be boolean")
    allowed = {
        "chatgpt": {("none", "answer"), ("clarify", "none")},
        "github": {("connector_scoped", "propose_connector"), ("approval_required", "propose_only")},
        "termux": {("allowlisted_only", "propose_diagnostic"), ("approval_required", "propose_only")},
        "debian": {("allowlisted_only", "propose_diagnostic"), ("approval_required", "propose_only")},
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
    if decision.destination in ("termux", "debian"):
        target = decision.destination
        allowlist = TERMUX_DIAGNOSTICS if target == "termux" else DEBIAN_DIAGNOSTICS
        if not isinstance(diagnostic, str) or diagnostic not in allowlist:
            return ExecutionPlan(target, "denied", None, "unknown or missing allowlisted diagnostic")
        if not bridge_authenticated:
            return ExecutionPlan(target, "bridge_disconnected", None, "authenticated device bridge unavailable")
        if decision.permission == "approval_required":
            return ExecutionPlan(target, "denied", None, "mutating device actions not supported")
        return ExecutionPlan(target, "ready_for_executor", diagnostic,
                             "requires separate authenticated executor and receipt")
    return ExecutionPlan(decision.destination, "denied", None, "unknown destination")
