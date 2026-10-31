# Toolz CLI integrations

Toolz uses a **direct, server-based integration layer** for approved AI CLIs and cloud agents. SSH is not the integration transport.

## Trust model

```text
Approved AI conductor
        |
        v
Toolz server / gateway
        |
        v
CLI integration adapter
        |
        v
Isolated task workspace
        |
        v
Approved CLI or cloud agent
        |
        v
Correlated Toolz receipt
```

Toolz is always the authorization, task-state, receipt, and audit authority. An AI conductor may propose work, but Toolz decides whether it may run.

## Current status

| Integration | Role | Status |
|---|---|---|
| Cline | Local CLI executor; may use OmniRoute for model routing | Planned |
| Codex CLI | Local CLI conductor/executor | Planned |
| Gemini CLI | Local CLI conductor/executor | Planned |
| Jules | Cloud agent/conductor | Planned |
| OmniRoute through Cline | Model/router backend for Cline tasks | Planned |

This first implementation introduces only the shared contract and registry. It does **not** launch CLI processes, contact Termux, call cloud services, or execute tasks.

## Contract

The contract is versioned as `1` and is implemented in
`android-personal-automator/bridge/cli_integration.py`.

A task request contains:

- `task_id`: durable, unique identifier.
- `integration`: registered adapter name.
- `capability`: one capability declared by that adapter.
- `request_id`: correlation identifier for receipts and retries.
- `contract_version`: must be `1`.
- `approval_token`: required only for capabilities marked approval-required.

A descriptor declares:

- Adapter name and version.
- Supported capabilities.
- Capabilities that require fresh human approval.

## Security boundaries

- No arbitrary shell-string execution.
- No SSH transport.
- No direct external-AI-to-Termux connection.
- No credentials in repository files, prompts, logs, or receipts.
- No task execution without Toolz authorization.
- No destructive or repository-mutating action without fresh approval.
- No unbounded output, path traversal, symlink escape, replay, or duplicate task ID.

## Planned capabilities

| Capability | Meaning | Approval |
|---|---|---|
| `health` | Check adapter/configuration readiness | No |
| `run-task` | Run an approved task in an isolated workspace | Yes |
| `cancel-task` | Cancel a running task by task ID | No |
| `get-status` | Return bounded task status and receipt metadata | No |
| `get-output` | Return bounded, redacted task output | No |

Capability names are illustrative until each adapter implementation defines its final allow-list.

## Implementation roadmap

1. Shared contract and registry — this change.
2. Cline adapter with OmniRoute routing.
3. Codex CLI adapter.
4. Gemini CLI adapter.
5. Jules adapter.
6. Cross-adapter integration tests.
7. Authorized real-CLI and device validation.

## Non-goals

- SSH-based remote shell access.
- Autonomous destructive operations.
- Production backup changes.
- Direct AI-service access to Termux without Toolz authorization.