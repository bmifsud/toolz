# Planner fail-closed intent

- Owner: repository maintainer.
- Baseline: d5fde7f50ce4aaba13d525aff2d2c4b423764382.
- Problem: unknown permission/action states and non-boolean flags can yield ready plans; Debian destination is lost and ambiguous requests become local-only.
- Acceptance: invalid shapes/states/flags return denied with no operation; ambiguity requires clarification; Debian destination preserved across connection states.
- Scope: offline planner, regression tests and documentation. Independent of open PR #119.
- Plan: validate state combinations and strict boolean inputs before planning, preserve target, test malformed/denied paths.
- Risk: callers depending on undocumented or malformed inputs will now receive denied plans. No authentication or execution capability added.
- Validation: offline bridge unit discovery, ADLC checks and complete CI.
- Rollback: revert through reviewed PR; no data or installation changes.
- Release: required reviews, CI, emulator/tablet and both backup-tier gates remain mandatory.
- Evidence: [record](evidence.md).
