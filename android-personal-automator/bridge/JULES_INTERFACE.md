# Jules Cloud Agent & Task Orchestration Interface

This document specifies the supported Jules interface for Toolz's direct server-based integration layer.
Jules operates as a cloud AI conductor: it proposes plans and tasks while Toolz validates, authorizes, schedules, executes, and audits approved work. Jules is **not** an unrestricted local shell path.

---

## Supported REST API Contract

All calls to the Jules integration service MUST use protected server-side HTTPS credentials (`Bearer` tokens) and adhere to the following contract.

### 1. Task Submission
- **Endpoint**: `POST /v1/tasks`
- **Request Body**:
  ```json
  {
    "task_id": "string (A-Za-z0-9_-{8,64})",
    "project_id": "string",
    "description": "string",
    "workspace_path": "string (relative to task root)",
    "plan": { ... }
  }
  ```
- **Response**: `201 Created` or `400 Bad Request` / `409 Conflict` (for duplicate task IDs / replay).

### 2. Plan Proposal
- **Endpoint**: `POST /v1/plans/propose`
- **Request Body**:
  ```json
  {
    "task_id": "string",
    "steps": [
      {
        "step_id": "string",
        "action": "string",
        "command": "string (optional)",
        "target_path": "string (optional)"
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "plan_id": "string",
    "task_id": "string",
    "status": "PROPOSED",
    "requires_approval": true,
    "reasons": ["string"]
  }
  ```

### 3. Status and Bounded Output Retrieval
- **Endpoint**: `GET /v1/tasks/{task_id}`
- **Response**:
  ```json
  {
    "task_id": "string",
    "project_id": "string",
    "status": "PENDING | RUNNING | COMPLETED | FAILED | CANCELLED | TIMED_OUT",
    "exit_code": 0,
    "stdout": "string (max 16KB, secret redacted)",
    "stderr": "string (max 16KB, secret redacted)",
    "error_message": "string | null",
    "retries_count": 0,
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601"
  }
  ```

### 4. Task Cancellation
- **Endpoint**: `POST /v1/tasks/{task_id}/cancel`
- **Response**: `200 OK` with updated task status set to `CANCELLED`.

---

## Security Boundaries & Rules

1. **Authentication & Credentials**:
   - Authenticate using protected server-side credentials (`JULES_API_TOKEN` / `JULES_API_KEY`).
   - Tokens MUST NEVER be exposed in repository files, logs, prompts, or execution receipts.

2. **Plan & Task Validation**:
   - All proposed plans are validated before execution.
   - Any mutating or restricted operation REQUIRES explicit human/user approval:
     - Dependency installation (`npm install`, `pip install`, `apt`, etc.)
     - Git operations mutating repository state (`git commit`, `git push`, `git merge`, etc.)
     - Deployment or remote infrastructure changes
     - Modification of secrets, credentials, or `.env` files
     - Deletion or restoration of files or directories
     - Any operations attempting path traversal (`..`, absolute paths outside workspace, symlink escape).

3. **Execution Guarantees**:
   - **Durable Task IDs & Replay Protection**: Duplicate task IDs or replayed tasks are rejected.
   - **Concurrency Limits**: Maximum concurrent active tasks are strictly bounded.
   - **Output Bounds**: Combined stdout + stderr output is bounded to 16,384 bytes (16KB). Oversized output is safely truncated or rejected.
   - **Secret Redaction**: Sensitive strings and API keys are automatically redacted from logs, outputs, and receipts.
   - **Timeouts & Cancellation**: Tasks exceeding configured timeouts are terminated with status `TIMED_OUT`.
   - **Audit Receipts**: Execution generates correlated receipts containing task ID, request ID, status, exit status, and SHA-256 fingerprint of the output.
