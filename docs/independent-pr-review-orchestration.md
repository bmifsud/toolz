# Independent PR review orchestration (initial scaffold)

Tracks #61. This is **not yet** a Jules or Codex cloud integration.

## Current behavior
Manually dispatch `Independent PR review intake (scaffold)` with a numeric open PR number. It fetches immutable PR metadata and publishes a receipt containing head/base SHAs. Workflow permissions are read-only; no checkout of untrusted PR code, reviewer API calls, issue writes, fixes, deployments, merges or backup operations.

## Next implementation gates
1. Verify officially supported authenticated integration methods for **Jules** and **Codex cloud**. Do not invent endpoints or grant secrets to untrusted fork PRs.
2. Introduce separate bounded, least-privilege review jobs pinned to the same PR head SHA. Keep raw reviewer outputs as receipts; normalize severity, evidence, file/line, provenance and disagreement.
3. Implement deterministic finding fingerprints and deduplicated GitHub issues; link to source review comment and head SHA. Ignore non-actionable feedback.
4. Add a separate opt-in fixer that produces draft PRs on isolated branches. Enforce file-level concurrency, retry budgets, independent re-review and a human escalation path.
5. Add integration tests for invalid PRs, API outages, rate limits, prompt injection, stale SHAs, duplicates, disagreement and attempted secret disclosure.
6. Require human review before enabling any issue-write or code-write permissions. Never auto-merge high-risk changes or claim that CI/reviewer agreement substitutes for physical Android, relay authorization, or encrypted backup/restore verification.

## Security notes
The intake workflow runs only by explicit manual dispatch. It does not execute PR code. Future review jobs must treat diffs, issue bodies and comments as untrusted data. Credentials should remain in approved secrets and never appear in receipts. No production use is implied by a passing scaffold workflow.
