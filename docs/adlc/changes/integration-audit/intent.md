# ADLC integration audit intent

- Change ID: integration-audit; requested isolated local audit, no remote issue created.
- Owner: repository maintainer; implementation by coding agent, not release approver.
- Baseline: 9ebcecaf2f18406358ab35f6f658ff796ab85ea9.
- Problem: support documents are not required by the structural gate, empty records pass, CI inherits its runner environment, and receipt event metadata is unbounded.
- Scope: ADLC validation/tests, CI isolation and provenance, audit evidence and guidance only.
- Exclusions: original dirty checkout, backup implementation/schedules/retention, devices, secrets, external model calls, branch protection, merge and deployment.
- Acceptance: missing required support files and empty change records fail; unsupported receipt events and non-positive/non-ASCII run identifiers fail; supported CI outcomes retain unverified operational status; CI gate uses a fresh HOME and allowlisted environment; maintained offline and backup fixture gates pass with exact results recorded.
- Risk: low; stricter validation may reject malformed metadata. Environment isolation is defense in depth, not a network sandbox.
- Source inspected: scripts/check_adlc.py, scripts/ci_receipt.py, their tests, CI workflow, offline runner, backup fixture setup and verification guidance.
- Dependencies/permissions: existing Python/pytest/Bash/GPG/SQLite/archive tools; no new dependency or permission.
- AI inventory: not applicable to implementation; no prompt, model, provider or runtime tool permission changes.
- Steps: strengthen structural checks and negative tests; constrain receipts; isolate CI invocation; run fixture gates; record audit matrix and review diff.
- Validation: isolated baseline/final offline gate, focused negative tests, backup suite, diff whitespace check.
- Rollback: reviewed revert of this audit commit; no operational recovery needed.
- Required review: independent maintainer review and CI on final revision remain pending.
- Evidence: [record](evidence.md).
