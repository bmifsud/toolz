# Change intent

- Change ID: cline-supervisor
- Owner: repository maintainer; implementation by Cline
- Baseline: 4457f3855b7fac636b88a3c9e17b14687b3c6640
- Problem: global heartbeat watchdog cannot supervise independent tasks or establish completion and may launch duplicate recovery processes.
- Scope: offline persistent multi-task supervisor with trusted adapter protocol. No service installation, model calls, session discovery/adoption, approval changes or backup changes.
- Acceptance: each registered task persists retries with capped delay; independent tasks progress; concurrent ticks cannot duplicate execution; ambiguous interrupted attempts block; only adapter-verified completion terminates successfully; approvals and permanent failures block with actionable reasons; dry-run launches nothing.
- Risk: high for eventual live deployment; this change remains opt-in offline infrastructure.
- Data/permissions: private local state, no prompts/output persisted; trusted operator config is executable policy, not model-generated input. Existing human approvals remain required.
- Plan: add Python stdlib supervisor alongside legacy watchdog, isolated adapter tests, maintained gate integration and documentation.
- Validation: focused pytest and maintained offline gate in isolated fixtures; no provider/device calls.
- Recovery: stop invoking supervisor; retain state for reconciliation; do not delete running markers to force retries.
- Unresolved: authenticated Cline adapter, authoritative full task inventory, ownership transfer from existing runners, completion verifier and live lifecycle validation.
- Required approvals: maintainer review and required CI on final revision; all standing ADLC gates apply.
- Evidence: [evidence](evidence.md).
