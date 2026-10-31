"""Jules Cloud Agent & Task Orchestration Adapter for Toolz.

Jules operates as a cloud AI conductor: it proposes plans and tasks while Toolz
validates, authorizes, schedules, executes, and audits approved work.

This module provides protected server-side integration, task contract validation,
replay protection, concurrency limits, secret redaction, and correlated receipts.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import json
import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


TASK_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
REQUEST_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

# Patterns for detecting mutating or restricted operations in plans
MUTATING_PATTERNS = {
    "dependency_install": re.compile(
        r"\b(npm\s+install|pip\s+install|apt(-get)?\s+install|apk\s+add|cargo\s+install|brew\s+install|yarn\s+add|pnpm\s+add|gem\s+install)\b",
        re.I,
    ),
    "git_mutation": re.compile(
        r"\b(git\s+(commit|push|merge|rebase|reset|checkout\s+-b|tag|branch\s+-[dD]))\b",
        re.I,
    ),
    "deployment": re.compile(
        r"\b(kubectl|docker\s+push|helm\s+(install|upgrade)|terraform\s+apply|aws\s+s3|gcloud\s+app\s+deploy|deploy)\b",
        re.I,
    ),
    "secret_modification": re.compile(
        r"\b(\.env|secrets\.json|chmod\s+600|export\s+[A-Za-z0-9_]*SECRET|export\s+[A-Za-z0-9_]*TOKEN|export\s+[A-Za-z0-9_]*KEY)\b",
        re.I,
    ),
    "deletion_restoration": re.compile(
        r"\b(rm\s+-rf|rm\s+|unlink|remove|restore|--restore)\b",
        re.I,
    ),
}

# Path traversal and absolute path validation regexes
ABSOLUTE_PATH_REGEX = re.compile(r"^\s*([a-zA-Z]:[/\\]|/|~)", re.I)
PATH_TRAVERSAL_REGEX = re.compile(
    r"(\.\./|\.\.\\|/etc/|/var/|/tmp/|/root/|/home/|ln\s+-s)", re.I
)

# Standard secret pattern regex for output redaction
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_.-]+", re.I),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[\"']?([A-Za-z0-9_.-]{8,})[\"']?"),
]


@dataclass(frozen=True)
class JulesConfig:
    api_token: str
    base_url: str = "https://api.jules.ai/v1"
    max_concurrency: int = 5
    timeout_seconds: int = 30
    max_output_bytes: int = 16384
    max_retries: int = 2
    additional_secrets: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.api_token, str) or len(self.api_token.strip()) < 16:
            raise ValueError("Jules API token must be a string of at least 16 characters")

        url = urlsplit(self.base_url)
        loopback = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (
            not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or url.scheme not in ("https", "http")
            or (url.scheme == "http" and not loopback)
        ):
            raise ValueError("base_url requires HTTPS, or HTTP on loopback only")

        if not (1 <= self.max_concurrency <= 100):
            raise ValueError("max_concurrency must be between 1 and 100")
        if not (1 <= self.timeout_seconds <= 300):
            raise ValueError("timeout_seconds must be between 1 and 300")
        if not (1024 <= self.max_output_bytes <= 1048576):
            raise ValueError("max_output_bytes must be between 1024 and 1048576")
        if not (0 <= self.max_retries <= 10):
            raise ValueError("max_retries must be between 0 and 10")

    def __repr__(self) -> str:
        return f"JulesConfig(base_url={self.base_url!r}, max_concurrency={self.max_concurrency}, timeout_seconds={self.timeout_seconds})"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    action: str
    command: Optional[str] = None
    target_path: Optional[str] = None


@dataclass(frozen=True)
class Plan:
    plan_id: str
    task_id: str
    steps: List[PlanStep]


@dataclass(frozen=True)
class PlanValidationResult:
    is_valid: bool
    requires_approval: bool
    reasons: List[str]


@dataclass
class Task:
    task_id: str
    project_id: str
    description: str
    workspace_path: str
    plan: Plan
    status: TaskStatus = TaskStatus.PENDING
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    retries_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class VerifiedReceipt:
    task_id: str
    request_id: str
    status: str
    exit_code: int
    output_sha256: str
    timestamp: str
    digest: str


def redact_secrets(text: str, secrets: Optional[List[str]] = None) -> str:
    """Replace sensitive keys, tokens, and configured secrets with [REDACTED]."""
    if not isinstance(text, str) or not text:
        return text or ""

    redacted = text

    # Redact explicitly configured secrets first
    if secrets:
        for secret in secrets:
            if isinstance(secret, str) and len(secret) >= 4:
                redacted = redacted.replace(secret, "[REDACTED]")

    # Redact standard secret patterns
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)

    return redacted


def validate_plan(plan: Plan) -> PlanValidationResult:
    """Validate plan for path traversal and mutating operations.

    Path traversal or prohibited actions render the plan INVALID.
    Mutating operations (dependency install, git mutate, deploy, secrets, delete)
    require explicit user approval before execution.
    """
    reasons: List[str] = []
    is_valid = True
    requires_approval = False

    if not isinstance(plan, Plan) or not plan.steps:
        return PlanValidationResult(
            is_valid=False, requires_approval=False, reasons=["Empty or invalid plan structure"]
        )

    for step in plan.steps:
        # Check target_path directly for absolute path or path traversal
        if step.target_path:
            tp = step.target_path.strip()
            if ABSOLUTE_PATH_REGEX.search(tp) or PATH_TRAVERSAL_REGEX.search(tp):
                is_valid = False
                reasons.append(
                    f"Step '{step.step_id}' target_path '{step.target_path}' contains unauthorized absolute path or traversal"
                )

        # Check command directly for path traversal or absolute paths in arguments
        if step.command:
            cmd = step.command.strip()
            if PATH_TRAVERSAL_REGEX.search(cmd):
                is_valid = False
                reasons.append(
                    f"Step '{step.step_id}' command contains unauthorized path traversal or restricted directory reference"
                )

        content = f"{step.action} {step.command or ''} {step.target_path or ''}"

        # Check for mutating operation patterns
        for category, pattern in MUTATING_PATTERNS.items():
            if pattern.search(content):
                requires_approval = True
                reasons.append(
                    f"Step '{step.step_id}' contains mutating operation ({category}): requires explicit user approval"
                )

    return PlanValidationResult(
        is_valid=is_valid,
        requires_approval=requires_approval,
        reasons=reasons,
    )


class JulesIntegration:
    """Adapter for Jules task orchestration and execution management."""

    def __init__(self, config: JulesConfig):
        self.config = config
        self._lock = threading.Lock()
        self._tasks: Dict[str, Task] = {}
        self._seen_task_ids: Set[str] = set()
        self._request_correlations: Dict[str, str] = {}

    def _get_secrets(self) -> List[str]:
        return [self.config.api_token] + self.config.additional_secrets

    def propose_plan(self, task_id: str, plan_id: str, raw_steps: List[Dict[str, Any]]) -> Plan:
        """Construct a structured Plan object from raw proposed steps."""
        if not TASK_ID_REGEX.match(task_id):
            raise ValueError("Invalid task ID format")

        steps: List[PlanStep] = []
        for idx, step_data in enumerate(raw_steps):
            step_id = str(step_data.get("step_id", f"step-{idx + 1}"))
            action = str(step_data.get("action", "execute"))
            command = step_data.get("command")
            target_path = step_data.get("target_path")
            steps.append(
                PlanStep(
                    step_id=step_id,
                    action=action,
                    command=str(command) if command is not None else None,
                    target_path=str(target_path) if target_path is not None else None,
                )
            )

        return Plan(plan_id=plan_id, task_id=task_id, steps=steps)

    def submit_task(
        self,
        task_id: str,
        project_id: str,
        description: str,
        workspace_path: str,
        plan: Plan,
        *,
        user_approved: bool = False,
    ) -> Task:
        """Submit a task for orchestration after validating plan and enforcing bounds."""
        if not TASK_ID_REGEX.match(task_id):
            raise ValueError("Invalid task ID format")
        if not project_id or not isinstance(project_id, str):
            raise ValueError("Project ID required")

        # Path traversal check on workspace path
        if ABSOLUTE_PATH_REGEX.search(workspace_path) or PATH_TRAVERSAL_REGEX.search(workspace_path):
            raise ValueError("Workspace path contains invalid path traversal or absolute reference")

        with self._lock:
            # Replay protection / duplicate ID rejection
            if task_id in self._seen_task_ids:
                raise ValueError(f"Duplicate task ID or replayed submission: {task_id}")

            # Validate plan
            validation = validate_plan(plan)
            if not validation.is_valid:
                raise ValueError(f"Plan validation failed: {'; '.join(validation.reasons)}")

            if validation.requires_approval and not user_approved:
                raise PermissionError(
                    f"Plan requires explicit user approval: {'; '.join(validation.reasons)}"
                )

            # Concurrency limit check
            active_count = sum(
                1 for t in self._tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            )
            if active_count >= self.config.max_concurrency:
                raise RuntimeError("Concurrency limit reached for active Jules tasks")

            now = datetime.now(timezone.utc).isoformat()
            task = Task(
                task_id=task_id,
                project_id=project_id,
                description=description,
                workspace_path=workspace_path,
                plan=plan,
                status=TaskStatus.PENDING,
                created_at=now,
                updated_at=now,
            )

            self._tasks[task_id] = task
            self._seen_task_ids.add(task_id)

            return task

    def get_task_status(self, task_id: str) -> Task:
        """Retrieve task details with bounded output and redacted secrets."""
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task not found: {task_id}")
            task = self._tasks[task_id]

            # Redact secrets
            secrets = self._get_secrets()
            stdout_redacted = redact_secrets(task.stdout, secrets)
            stderr_redacted = redact_secrets(task.stderr, secrets)
            error_redacted = redact_secrets(task.error_message or "", secrets) if task.error_message else None

            # Enforce combined output bounds (max_output_bytes) for both stdout and stderr
            stdout_bytes = stdout_redacted.encode("utf-8")
            stderr_bytes = stderr_redacted.encode("utf-8")
            total_bytes = len(stdout_bytes) + len(stderr_bytes)

            if total_bytes > self.config.max_output_bytes:
                half_limit = max(128, (self.config.max_output_bytes - 128) // 2)
                if len(stderr_bytes) > half_limit:
                    stderr_redacted = stderr_bytes[:half_limit].decode("utf-8", errors="ignore") + "\n[STDERR TRUNCATED: EXCEEDED SIZE LIMIT]"
                    stderr_bytes = stderr_redacted.encode("utf-8")

                remaining_for_stdout = max(128, self.config.max_output_bytes - len(stderr_bytes) - 64)
                if len(stdout_bytes) > remaining_for_stdout:
                    stdout_redacted = stdout_bytes[:remaining_for_stdout].decode("utf-8", errors="ignore") + "\n[STDOUT TRUNCATED: EXCEEDED SIZE LIMIT]"

            return Task(
                task_id=task.task_id,
                project_id=task.project_id,
                description=task.description,
                workspace_path=task.workspace_path,
                plan=task.plan,
                status=task.status,
                exit_code=task.exit_code,
                stdout=stdout_redacted,
                stderr=stderr_redacted,
                error_message=error_redacted,
                retries_count=task.retries_count,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )

    def cancel_task(self, task_id: str) -> Task:
        """Cancel a pending or running task."""
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task not found: {task_id}")
            task = self._tasks[task_id]

            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.now(timezone.utc).isoformat()

            return task

    def record_execution_result(
        self,
        task_id: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        error_message: Optional[str] = None,
    ) -> Task:
        """Record task execution status and output from orchestrator/executor."""
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task not found: {task_id}")
            task = self._tasks[task_id]

            if task.status == TaskStatus.CANCELLED:
                return task

            secrets = self._get_secrets()
            task.exit_code = exit_code
            task.stdout = redact_secrets(stdout, secrets)
            task.stderr = redact_secrets(stderr, secrets)
            task.error_message = redact_secrets(error_message or "", secrets) if error_message else None
            task.status = TaskStatus.COMPLETED if exit_code == 0 else TaskStatus.FAILED
            task.updated_at = datetime.now(timezone.utc).isoformat()

            return task

    def handle_timeout(self, task_id: str) -> Task:
        """Mark task as timed out."""
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task not found: {task_id}")
            task = self._tasks[task_id]

            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.TIMED_OUT
                task.error_message = f"Task execution exceeded timeout limit of {self.config.timeout_seconds} seconds"
                task.updated_at = datetime.now(timezone.utc).isoformat()

            return task

    def retry_task(self, task_id: str, *, user_approved: bool = False) -> Task:
        """Retry a failed or timed out task if retry budget remains."""
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task not found: {task_id}")
            task = self._tasks[task_id]

            if task.status not in (TaskStatus.FAILED, TaskStatus.TIMED_OUT):
                raise ValueError(f"Cannot retry task in status {task.status.value}")

            if task.retries_count >= self.config.max_retries:
                raise RuntimeError(f"Retry limit ({self.config.max_retries}) reached for task {task_id}")

            validation = validate_plan(task.plan)
            if validation.requires_approval and not user_approved:
                raise PermissionError("Retry requires explicit user approval for mutating plan")

            task.retries_count += 1
            task.status = TaskStatus.PENDING
            task.exit_code = None
            task.error_message = None
            task.updated_at = datetime.now(timezone.utc).isoformat()

            return task

    def create_receipt(self, task_id: str, request_id: str) -> VerifiedReceipt:
        """Generate a correlated execution receipt with SHA-256 fingerprint."""
        if not REQUEST_ID_REGEX.match(request_id):
            raise ValueError("Invalid request ID format")

        task = self.get_task_status(task_id)
        if task.status == TaskStatus.PENDING:
            raise ValueError("Cannot create receipt for pending task")

        secrets = self._get_secrets()
        redacted_stdout = redact_secrets(task.stdout, secrets)
        redacted_stderr = redact_secrets(task.stderr, secrets)

        exit_code_val = task.exit_code if task.exit_code is not None else -1
        output_content = f"{task.task_id}:{request_id}:{task.status.value}:{exit_code_val}:{redacted_stdout}:{redacted_stderr}"
        output_sha256 = hashlib.sha256(output_content.encode("utf-8")).hexdigest()

        now = datetime.now(timezone.utc).isoformat()
        raw_digest_payload = f"{request_id}|{task.task_id}|{task.status.value}|{output_sha256}|{now}"
        digest = hmac.new(
            self.config.api_token.encode("utf-8"),
            raw_digest_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        with self._lock:
            self._request_correlations[task_id] = request_id

        return VerifiedReceipt(
            task_id=task_id,
            request_id=request_id,
            status=task.status.value,
            exit_code=exit_code_val,
            output_sha256=output_sha256,
            timestamp=now,
            digest=digest,
        )

    def verify_receipt(
        self,
        receipt: VerifiedReceipt,
        expected_task_id: str,
        expected_request_id: str,
    ) -> bool:
        """Verify receipt authenticity, correlation, and integrity."""
        if not hmac.compare_digest(receipt.task_id, expected_task_id):
            raise ValueError("Task ID mismatch in receipt")
        if not hmac.compare_digest(receipt.request_id, expected_request_id):
            raise ValueError("Request ID mismatch in receipt")

        raw_digest_payload = f"{receipt.request_id}|{receipt.task_id}|{receipt.status}|{receipt.output_sha256}|{receipt.timestamp}"
        expected_digest = hmac.new(
            self.config.api_token.encode("utf-8"),
            raw_digest_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(receipt.digest, expected_digest):
            raise ValueError("Receipt digest verification failed")

        return True
