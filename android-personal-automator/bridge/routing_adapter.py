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
    if decision.destination == "chatgpt":
        return ExecutionPlan("chatgpt", "local_only", None, decision.reason)
    if decision.permission == "clarify":
        return ExecutionPlan(decision.destination, "clarification_required", None, decision.reason)
    if decision.permission == "approval_required" and not user_approved:
        return ExecutionPlan(decision.destination, "approval_required", None, "explicit approval required")
    if decision.destination == "github":
        return ExecutionPlan("github", "connector_required", None,
                             "scoped GitHub connector must authorize and execute separately")
    if decision.destination in ("termux", "debian"):
        target = decision.destination
        allowlist = TERMUX_DIAGNOSTICS if target == "termux" else DEBIAN_DIAGNOSTICS
        if diagnostic not in allowlist:
            return ExecutionPlan(target, "denied", None, "unknown or missing allowlisted diagnostic")
        if not bridge_authenticated:
            return ExecutionPlan("termux", "bridge_disconnected", None, "authenticated device bridge unavailable")
        if decision.permission == "approval_required":
            return ExecutionPlan("termux", "denied", None, "mutating device actions not supported")
        return ExecutionPlan("termux", "ready_for_executor", diagnostic,
                             "requires separate authenticated executor and receipt")
    return ExecutionPlan(decision.destination, "denied", None, "unknown destination")
