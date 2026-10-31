"""Versioned contract for Toolz-managed CLI integrations.

This module defines the shared, non-executing integration boundary for
Cline, Codex CLI, Gemini CLI, and Jules. It deliberately does not launch
processes, connect to Termux, invoke cloud services, or accept arbitrary
shell commands.

Security model:
- Toolz authorizes, schedules, tracks, and audits work.
- An adapter may only expose a fixed capability set.
- A task request must be explicitly approved before execution.
- Credentials never enter this contract, logs, prompts, or receipts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Mapping
import uuid

CONTRACT_VERSION = 1
MAX_TASK_ID_LENGTH = 128
MAX_CAPABILITIES = 64
MAX_METADATA_KEYS = 32
MAX_METADATA_VALUE_LENGTH = 512
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


TERMINAL_STATES = frozenset(
    {
        TaskState.SUCCEEDED,
        TaskState.FAILED,
        TaskState.TIMED_OUT,
        TaskState.CANCELLED,
    }
)


class IntegrationError(ValueError):
    """Raised when an integration request violates the Toolz contract."""


class UnknownIntegrationError(IntegrationError):
    """Raised when an adapter is not registered."""


class DuplicateTaskError(IntegrationError):
    """Raised when a task ID is reused."""


class ApprovalRequiredError(IntegrationError):
    """Raised when a capability requires a fresh human approval token."""


@dataclass(frozen=True)
class IntegrationDescriptor:
    """Immutable registration metadata for one CLI or cloud integration."""

    name: str
    version: str
    capabilities: frozenset[str]
    requires_approval: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _TASK_ID_RE.fullmatch(self.name):
            raise IntegrationError("invalid integration name")
        if not isinstance(self.version, str) or not self.version.strip():
            raise IntegrationError("invalid integration version")
        if not isinstance(self.capabilities, frozenset):
            raise IntegrationError("capabilities must be a frozenset")
        if not self.capabilities or len(self.capabilities) > MAX_CAPABILITIES:
            raise IntegrationError("invalid capability count")
        if any(not isinstance(c, str) or not _CAPABILITY_RE.fullmatch(c) for c in self.capabilities):
            raise IntegrationError("invalid capability name")
        if not isinstance(self.requires_approval, frozenset):
            raise IntegrationError("requires_approval must be a frozenset")
        unknown = self.requires_approval - self.capabilities
        if unknown:
            raise IntegrationError("approval-required capability is not declared")

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True)
class TaskRequest:
    """A validated request to invoke one declared integration capability."""

    task_id: str
    integration: str
    capability: str
    request_id: str
    contract_version: int = CONTRACT_VERSION
    approval_token: str | None = None

    def __post_init__(self) -> None:
        if type(self.contract_version) is not int or self.contract_version != CONTRACT_VERSION:
            raise IntegrationError("unsupported contract version")
        if not isinstance(self.task_id, str) or not _TASK_ID_RE.fullmatch(self.task_id):
            raise IntegrationError("invalid task ID")
        if not isinstance(self.integration, str) or not _TASK_ID_RE.fullmatch(self.integration):
            raise IntegrationError("invalid integration name")
        if not isinstance(self.capability, str) or not _CAPABILITY_RE.fullmatch(self.capability):
            raise IntegrationError("invalid capability")
        if not isinstance(self.request_id, str) or not _TASK_ID_RE.fullmatch(self.request_id):
            raise IntegrationError("invalid request ID")
        if self.approval_token is not None and (
            not isinstance(self.approval_token, str) or not self.approval_token.strip()
        ):
            raise IntegrationError("invalid approval token")


def new_request_id() -> str:
    """Return an opaque, URL-safe request correlation identifier."""

    return "req_" + uuid.uuid4().hex


def validate_metadata(metadata: Mapping[str, object] | None) -> dict[str, str]:
    """Validate a small, flat metadata mapping without accepting secrets."""

    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping) or len(metadata) > MAX_METADATA_KEYS:
        raise IntegrationError("invalid metadata")
    result: dict[str, str] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not _CAPABILITY_RE.fullmatch(key):
            raise IntegrationError("invalid metadata key")
        if not isinstance(value, str) or len(value) > MAX_METADATA_VALUE_LENGTH:
            raise IntegrationError("invalid metadata value")
        result[key] = value
    return result


class IntegrationRegistry:
    """Registry of immutable adapter descriptors.

    The registry performs contract validation only. Execution, transport,
    cancellation, and receipt persistence remain responsibilities of the
    integrating Toolz gateway.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, IntegrationDescriptor] = {}
        self._task_ids: set[str] = set()

    def register(self, descriptor: IntegrationDescriptor) -> None:
        if not isinstance(descriptor, IntegrationDescriptor):
            raise IntegrationError("descriptor required")
        if descriptor.name in self._adapters:
            raise IntegrationError("integration already registered")
        self._adapters[descriptor.name] = descriptor

    def get(self, name: str) -> IntegrationDescriptor:
        if not isinstance(name, str):
            raise IntegrationError("invalid integration name")
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise UnknownIntegrationError("unknown integration") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def validate_request(self, request: TaskRequest) -> IntegrationDescriptor:
        if not isinstance(request, TaskRequest):
            raise IntegrationError("task request required")
        if request.task_id in self._task_ids:
            raise DuplicateTaskError("task ID already used")
        descriptor = self.get(request.integration)
        if not descriptor.supports(request.capability):
            raise IntegrationError("capability not supported")
        if request.capability in descriptor.requires_approval and not request.approval_token:
            raise ApprovalRequiredError("fresh approval required")
        return descriptor

    def reserve_task(self, request: TaskRequest) -> IntegrationDescriptor:
        """Validate a request and reserve its task ID.

        Callers must persist the resulting task and receipt themselves. The
        registry only prevents duplicate IDs within this process.
        """

        descriptor = self.validate_request(request)
        self._task_ids.add(request.task_id)
        return descriptor

    def release_task(self, task_id: str) -> None:
        if not isinstance(task_id, str) or not _TASK_ID_RE.fullmatch(task_id):
            raise IntegrationError("invalid task ID")
        self._task_ids.discard(task_id)
