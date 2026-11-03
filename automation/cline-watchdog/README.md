# Cline stall watchdog (experimental)

This is an opt-in, fail-closed watchdog for an authorized Cline task runner. It does not assume that a process existing means useful work is progressing. The runner must write a heartbeat **only after confirming task progress** (not on a timer alone).

## Setup

1. Copy `config.example.json` to a private config file and set the correct working directory.
2. Integrate `heartbeat.py STATE_DIR` into the runner after a verified progress checkpoint.
3. First run `python3 watchdog.py --config CONFIG` (observe-only).
4. Once the exact resume command is tested manually, set `recovery_command` to an argv array. It must resume the existing task safely and exit or hand off; it must not create a new unrelated task.
5. Run `python3 watchdog.py --config CONFIG --recover` from an external supervisor (systemd timer or cron). Do not schedule until authenticated resume has been tested.

## Important limitations

- The heartbeat is a task-progress signal, **not** proof that Cline is alive. An idle but healthy agent may be reported stale.
- A recovery command must implement its own single-task ownership/locking and authenticated resume; the watchdog lock only prevents concurrent watchdog checks.
- Retry cooldown increases to at most one hour; attempts do not automatically reset. Recovery is not proven until a fresh progress heartbeat appears.
- This does not start Debian, Desktop Commander, an emulator, or any production service.
- Do not auto-merge, discard uncommitted files, or kill unknown processes. Preserve existing ADLC documentation modifications.
- Logs may contain agent output; keep the state directory private and avoid secrets in commands.

## Tests

`cd automation/cline-watchdog && python3 -m unittest -v test_watchdog.py`

## Required integration validation

Verify healthy/missing/stale/future heartbeats; concurrency; recovery command validation; no duplicate Cline tasks; cooldown; authorized session restoration; emulator CI and device execution. Until those pass, use observe-only mode.

## Persistent multi-task supervisor (offline integration foundation)

`supervisor.py` is separate from the legacy heartbeat watchdog. It processes every
registered task once per invocation, serially, and persists each outcome before returning.
Invoke with `--config /absolute/private/config.json`; observe-only is the default.
`--execute` invokes trusted adapters, not arbitrary tasks discovered from model output.
No daemon, timer, provider call or live session adoption is installed by this change.

Configuration shape:

```json
{
  "state_dir": "/absolute/private/supervisor-state",
  "timeout_seconds": 300,
  "tasks": [
    {
      "id": "existing-session-id",
      "cwd": "/absolute/existing/workspace",
      "adapter": ["/absolute/reviewed/session-adapter"]
    }
  ]
}
```

These paths are illustrative, not an executable deployment configuration. The adapter
receives the task ID as its final argument. It must resume that exact existing session,
never create another, retain interactive approval requirements, and run in the foreground
without detached children. Operator-managed config/state must not be writable by agents.
All invocations must share the same canonical private state directory and task IDs;
locks cannot protect against an independent existing runner or another state directory.
Transfer ownership explicitly before enabling any task. Do not run both watchdogs for it.

Adapter exits: **0 independently verified completion**, 10 transient API/connection
failure, 11 incomplete but safely resumable checkpoint, 20 approval needed, 21 auth/config
repair needed, 22 runtime repair needed. All other exits block for inspection. A raw Cline
exit of zero is NOT completion evidence: do not configure the Cline binary directly.
Adapter classification must use structured errors, never prompt/output text as authority.
Cline 3.0.74 defaults auto-approval to true: a future adapter must explicitly disable it
and prove denied/approval paths; this implementation does not invoke Cline.

Retries persist indefinitely at 60, 120, 240…3600 seconds, without sleeping or looping
inside the supervisor. An eventual external scheduler may tick at a conservative interval
only after authenticated integration review. Timeout, crash ambiguity, corrupt state,
changed configuration and permanent/approval failures require operator reconciliation;
they do not blindly retry. Completion and blocker records are sticky. To resume a blocked
task, an operator must first establish no old runner/children remain, resolve the reason,
and reconcile its state under exclusive ownership. Never delete state merely to force replay.
The direct subprocess is killed on timeout; any nonconforming detached children require
manual reconciliation, hence timeout blocks rather than launching replacements.

State writes use atomic replacement and fsync; per-task locks span execution. Output is
discarded to avoid unbounded logs/secrets; only status codes and reasons are recorded.
Tests use Python fixture adapters and no providers. The maintained offline gate includes
both watchdog and supervisor tests. Global live coverage remains BLOCKED until complete
session inventory, trusted completion verification, approval preservation, ownership
transfer and authenticated restart/cancellation tests have been demonstrated.
