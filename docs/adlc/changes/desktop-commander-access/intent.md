# Desktop Commander device access intent

- Owner: bmifsud; requested removal of direct Termux/Andronix connection paths.
- Baseline: 9b0de14; the Android app and live bridge are already absent on main.
- Problem: offline plans still name separate device bridges, implying obsolete connection paths.
- Acceptance: device requests produce only Desktop Commander plans; legacy destination objects are denied; arbitrary commands and mutations remain denied; no network or device execution is added.
- Scope: offline router, planner, related tests, current access guidance. Preserve backup environment paths, schedules, retention, receipts and historical evidence.
- Plan: unify device routing; replace bridge availability terminology; retain bounded diagnostics; update docs and run the maintained offline gate.
- Risk: medium; destination and keyword API change for offline callers. No callers outside the maintained fixtures were found in this revision.
- Permissions/data: no credentials, live producers, restores or external models used. Desktop Commander owns device selection and authorization separately; a planning boolean proves neither.
- Validation: fail-closed planner tests and maintained offline gate in an isolated HOME, GnuPG and rclone configuration.
- Rollback: revert this PR. Required CI, human review and standing release gates still apply.
- Evidence: [verification](evidence.md).
