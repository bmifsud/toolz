# Google Gemini documentation maintainer — design only

Tracks #66. **Google Gemini** replaces Perplexity as the proposed documentation maintainer. Perplexity is reserved for PR code reviews, alongside Codex. **Documentation automation is not connected or enabled.**

## Scope
Maintain public/external developer documentation and non-sensitive internal technical documentation based on verified code changes. Do not put confidential internal runbooks, credentials, tokens, or private device data in this public repository.

## Proposed publishing flow
1. After a successful merge or manual dispatch, pin the exact `main` SHA and changed-file manifest.
2. Request documentation suggestions through an authenticated Google Gemini API integration, with bounded non-sensitive context and source references. Distinguish implemented functionality from proposals.
3. Allow edits only to approved Markdown paths such as `README.md` and explicit `docs/**/*.md` entries. Reject source code, workflows, scripts, configuration, symlinks, path traversal, and secrets.
4. Validate factual accuracy, links, private-data leakage, unsupported claims and output limits. Store redacted audit receipts.
5. Only after testing, approval and verification of a minimally privileged publisher, allow validated docs-only commits directly to `main` **if branch rules permit**. Never bypass protection or force push; abort on main SHA drift.
6. On failure, create/update a tracking issue rather than publishing. Prevent trigger loops.

## Activation gates
- Confirm supported Gemini API authentication, model, privacy and quota/billing policies; configure a separate `GEMINI_API_KEY` secret.
- Test allowed docs changes, rejected non-doc changes, secret detection, path traversal, stale SHA, concurrency, outages and repeated triggers.
- Require human-reviewed implementation and validation before enabling direct-to-main publishing.

**Status:** Design only. No Google Gemini API calls or automated documentation publishing are active.
