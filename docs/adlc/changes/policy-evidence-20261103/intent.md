# Current policy evidence intent

- Owner: repository maintainer.
- Baseline: `338889249cd0aaa0bd1792a152dd24ff97d41c1f`.
- Problem: the ledger points to old CI and treats protection as unknown despite newly observable missing controls.
- Scope: documentation-only reconciliation of verified postmerge CI, absent protection, missing recorded review and pending current operational evidence.
- Acceptance: identify PR head and merged main separately; accurately record 134 postmerge tests; retain all release gates; do not promote offline or historical logs to live acceptance.
- Plan: inspect GitHub endpoints and uploaded evidence through Commander, obtain Cline text-only review, update ledger and evidence on a separate branch, check links and diff, submit a draft PR.
- Exclusions: repository settings, live lifecycle tests, backup/restore, scheduling/retention, credential/provider changes and edits to active emulator/trading/global-retry worktrees.
- Risk: metadata is a dated observation; temporary host logs are not durable, revision-bound release artifacts.
- Validation: ADLC structure/local-link check, git diff --check and PR CI.
- Rollback: revert documentation through review; no production state changes.
- Evidence: [record](evidence.md).
