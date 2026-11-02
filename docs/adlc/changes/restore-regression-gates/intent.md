# Restore regression gates intent

- Owner: repository maintainer.
- Baseline: 88f0f18cc77ec7e82aa134fd240e45c68a0a811c.
- Problem: two restore tests unexpectedly pass but still carry non-strict expected-failure markers, which can hide regressions.
- Acceptance: successful isolated restore and wrong-passphrase rejection become mandatory checks; failed decryption preserves destination secrets/database and avoids service invocation/workspace creation.
- Plan: remove obsolete markers, strengthen failure assertions, run CI on the exact PR revision, record results.
- Risk: low; test-only change plus evidence updates. No production backup logic, schedules or retention changes.
- Validation: ADLC checker, shell syntax, unit discovery and complete CI fixture suite.
- Rollback: revert through review; do not weaken restore assertions to obtain green checks.
- Release: existing emulator/tablet and both backup-tier gates remain mandatory.
- Evidence: [record](evidence.md).
