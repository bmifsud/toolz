# ADLC alignment intent

- Owner: repository maintainer; implementation prepared by Codex.
- Baseline: 24ca10df53ca75672a20b838b4ecaa400bee5c41.
- Problem: docs describe missing components; test runner omits maintained Python suites; no automated consistency gate.
- Scope: current-source documentation, offline runner, read-only CI, link/record validator and negative tests.
- Acceptance: no broken local Markdown links; docs distinguish source from plans; runner discovers both maintained test directories and fails on errors; CI supplies fixture prerequisites without provider secrets.
- Exclusions: restore/production execution, schedules, retention, external model calls, merges and repository administration.
- Risk: medium; CI/test selection changes can expose existing failures. Do not weaken failing tests to obtain green checks.
- Plan: inventory source, reconcile docs, implement consistency gate, run independent negative cases and available tests, submit draft PR.
- Validation: Python ADLC checker; unittest discovery; shell syntax; full runner where prerequisites exist.
- Rollback: revert this change through review. No data migration or operational rollback required.
- Review: required human/CI approval and standing emulator/tablet plus both backup gates remain mandatory.
- Evidence: [verification record](evidence.md).
