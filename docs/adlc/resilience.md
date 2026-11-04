# ADLC resilience boundaries

Reuse the existing [watchdog and supervisor](../../automation/cline-watchdog/README.md).
Do not deploy another runner merely because one request times out.

## Retry and ownership rules

| Outcome | Required behavior |
| --- | --- |
| Read-only connection failure | Bounded retries with backoff; retain missing evidence as unverified |
| Pending remote call | Poll its returned call ID; do not replay the original side effect |
| Ambiguous write outcome | Re-read authoritative state and reconcile; no blind write replay |
| Transient adapter result | Persist cooldown/attempt state; the existing supervisor caps delay at one hour |
| Approval, authentication or runtime failure | Preserve blocked state and repair/escalate; do not auto-approve or bypass controls |
| Interrupted/timeout execution | Reconcile runner/child ownership before any retry; no duplicate execution |
| Completion | Require independently verified task evidence, not process existence or a raw Cline exit 0 |

The existing supervisor persists state atomically with fsync and holds a per-task lock
across execution. All invocations must use the same canonical task/state identity.
Locks cannot coordinate an unrelated existing runner or a second state directory.
An authorized adapter must preserve approvals and run in the foreground; session
ownership must be explicitly transferred before enabling it. No live adapter is
deployed by this documentation update.

## Administrative reconciliation

The recorded main protection was applied as a guarded transaction: verified identity
and admin permission, inspected prior configuration, preserved a private snapshot,
sent one write, and read back every requested control. A temporary device interruption
did not justify repeating an unknown write. The confirmed-unstarted attempt was retried
under a single-instance lock. Current configuration has also been independently read back.

Do not automatically restore the earlier unprotected configuration. Main's read-only
lock enforces the existing release hold until an accountable decision follows verified
operational gates. Neither a supervisor nor a model may unlock it as failure recovery.

## What the tests establish

Nineteen existing host-fixture tests cover persistent backoff/cap, cooldown, independent
task state, sticky completion/blockers, approval/auth/runtime classification, concurrency,
interrupted attempts, corruption, configuration drift and observe-only behavior.
They are offline checks, not proof of authenticated session restoration or production
recovery on Android/PRoot.

Remaining live integration acceptance includes authenticated existing-session resume,
no duplicate ownership, cancellation/restart and child reconciliation, denied/approval
paths, fresh progress evidence and independently verified completion. Coordinate with
the separately owned emulator/tablet work. Do not kill unknown processes, change
production startup/schedules, or perform live backup/restore to satisfy a fixture test.
