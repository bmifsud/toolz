# Persistent diagnostic task controller (draft)

This is an **offline state-machine prototype**, not a running service. It persists
allowlisted diagnostic requests and bounded execution receipts to SQLite. No shell
execution, listener, HTTP route, worker, or ChatGPT integration is enabled.

- States: queued, running, succeeded, failed, cancelled.
- Expired deadlines and worker leases fail closed. Tasks are not automatically
  replayed because an external command may already have executed.
- Cancellation prevents acceptance of a late receipt; stopping a running process
  requires a future authenticated worker with cooperative cancellation.
- The trusted caller must authenticate, authorize each request, enforce rate
  limits, and restrict database access. Never expose SQLite directly.
- The gateway and this controller must not be deployed until independently
  reviewed, tested and explicitly approved.
- No arbitrary script execution. A future `--allow-full-script` option, if added,
  must require separate authentication, explicit consent, and safety checks.

Offline tests (when Python is available):
`cd android-personal-automator/bridge/ws && python -m unittest test_task_controller.py`
