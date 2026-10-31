# Independent PR review orchestration (Perplexity + Codex design)

Tracks #61. Replaces the proposed Jules review role with Perplexity. **External reviewer calls are not yet enabled.**

## Current behavior
The manually dispatched `Independent PR review intake (scaffold)` validates an open PR, captures immutable head/base SHAs and uploads a receipt. It does not execute untrusted PR code or contact external models.

## Proposed review flow
1. Collect the exact PR head SHA, diff and bounded context using read-only GitHub permissions.
2. Run **Codex** and **Perplexity** as independent reviewers against the *same* immutable head SHA; validate supported APIs, credentials, costs and data handling before enabling either.
3. Capture redacted receipts with provenance, severity, evidence, changed file/line, and disagreement. Treat PR content as untrusted; never execute reviewer-generated commands.
4. Deduplicate actionable findings into tracked issues or review comments only after separate write-permission approval. Do not confuse AI feedback with a formally required human approval.
5. Fix through separately authorized, isolated draft PRs; rerun CI and independent review. Disallow concurrent edits to the same branches and preserve the existing device and backup verification gates.
6. Merge only after all CI, branch protection, required independent human reviews, and emulator/tablet/backup evidence applicable to the PR have passed. Never auto-merge high-risk changes merely on AI consensus.

## Before activation
- Validate API authentication and rate-limit, outage, timeout and spending controls.
- Ensure secrets cannot be read by fork PRs or leaked into prompts, artifacts or logs.
- Test stale SHAs, prompt injection, duplicate feedback, review disagreement and unauthorized write attempts.
- Require a separate human-reviewed change to enable reviewer API calls or GitHub write actions.

No Perplexity API key or functioning review integration is implied by this design.
