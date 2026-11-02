# Offline bridge recovery intent

- Owner: repository maintainer.
- Baseline: 656758095e66fa09cb8728e763205eed0957e4a8.
- Problem: main lacks the bridge source required to progress toward device validation.
- Scope: recover four standard-library planning/receipt/diagnostic modules and their four test files from pinned source; include them in the maintained CI gate.
- Source: fix/bridge-ci-bounded-ws-tests-20261030 at 8a66e540d9ca7a25e3d325ca81269ed9e57fb3a2.
- Acceptance: existing offline tests pass; unknown diagnostics and mutation attempts remain denied; no subprocess/network/device execution introduced.
- Exclusions: network transport, app, executor, listeners, provider calls, startup/service operations, schedules and retention.
- Risks: classifier heuristics are not authorization; caller booleans are not proof of authentication. Receipt validator supports Termux diagnostics only. Do not connect an executor without separate security review and lifecycle tests.
- Plan: inspect source/dependencies, recover bounded slice, update capability docs and CI selection, verify offline tests.
- Rollback: revert slice and CI/docs updates through review; no installation/data changes.
- Release: existing CI, review, device and backup gates remain mandatory.
- Evidence: [record](evidence.md).
