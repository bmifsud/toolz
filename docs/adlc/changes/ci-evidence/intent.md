# CI evidence intent

- Owner: repository maintainer.
- Baseline: 88f0f18cc77ec7e82aa134fd240e45c68a0a811c.
- Problem: CI verification has only logs, without a downloadable test report tied to the tested checkout.
- Acceptance: preserve JUnit when tests run and a minimal receipt with actual checkout SHA, run attempt and gate outcome, including failures.
- Scope: CI, receipt helper/tests and documentation; independent of open PR #115.
- Risks: fixture assertion output is included in JUnit; no live credentials/data may be used.
- Plan: add bounded metadata fields, verified immutable upload-action pin, 14-day retention and negative provenance tests.
- Validation: unit tests, ADLC/link checks and CI on the PR revision.
- Rollback: revert through review; no production state changes.
- Release: existing device/backup and approval gates unchanged.
- Evidence: [record](evidence.md).
