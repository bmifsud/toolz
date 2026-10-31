# Perplexity documentation maintainer — design only

Tracks #66. Replaces the proposed Jules documentation role with Perplexity. **Not connected or enabled.**

## Scope
Generate and maintain public/external developer documentation and non-sensitive internal technical documentation based on verified code changes. In a public repository, all committed content is public: confidential internal runbooks, private device details, credentials and secrets must be stored privately.

## Proposed publishing flow
1. After successful merge or manual dispatch, pin the exact `main` SHA and relevant changes.
2. Request documentation suggestions through an authenticated Perplexity API integration using bounded, non-sensitive source context; verify citations and distinguish implemented features from proposals.
3. Restrict edits to an explicit allowlist (e.g. `README.md` and approved `docs/**/*.md`), rejecting source code, workflows, settings, scripts, binaries, symlinks and path traversal.
4. Check factual accuracy, Markdown links, secret exposure, and unsupported claims. Save redacted receipts with inputs, source SHA and checks.
5. Only when a dedicated minimally privileged publisher has been verified and branch protection permits it, commit validated documentation directly to `main` without a PR. Never force push or bypass branch rules; abort on SHA drift.
6. If any validation fails, open or update a tracking issue instead of publishing. Prevent recursive triggers.

## Activation tests
Allowlisted edit; blocked code/config edit; leak and private-data detection; outdated source SHA; concurrent writes; authentication/API outages; retries; and branch protection failures must all be tested.

**Status:** This document is a proposal, not an active automation. A separate implementation with authenticated API integration, credentials and validation is required.
