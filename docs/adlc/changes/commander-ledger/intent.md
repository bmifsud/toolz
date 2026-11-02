# Commander architecture reconciliation intent

- Owner: repository maintainer.
- Baseline: 46d1c058bd1eaa2e59b006e7c860fd590dc211da.
- Problem: the release ledger still directs custom bridge recovery after Commander migration.
- Acceptance: active docs identify Commander as sole access path, preserve backups and unresolved gates, and distinguish discovery from verified operations.
- Scope: documentation and disposition of superseded draft PR #121.
- Plan: inspect merged migration/main CI, close superseded draft, reconcile ledger/architecture/verification.
- Risk: historical lifecycle gate applicability remains unresolved; no waiver or protection change.
- Validation: changed Markdown relative links checked against the pinned repository tree; no runtime changes.
- Rollback: revert docs through review; no installation/data changes.
- Evidence: [record](evidence.md).
