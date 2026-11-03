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
