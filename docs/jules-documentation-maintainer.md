# Jules documentation maintainer — direct-to-main design

Tracks #66; separate from the Jules/Codex cloud code-review workflow (#61). **Not yet connected or enabled.**

## Policy
Jules maintains both developer/internal and public/external documentation after verified code changes. Routine documentation-only updates should go **straight to `main` without PRs or review** once a supported integration, credentials, path validation and repository permissions are tested and approved.

A public GitHub repository makes all committed documentation public: never put sensitive internal runbooks, tokens, host details or private user/device data there. Use a private repository for confidential internal documentation.

## Pipeline
1. On successful merge or manual dispatch, capture the exact `main` SHA and changed-file manifest.
2. Ask an authenticated Jules session to update relevant docs with source references and distinguish implemented behavior from proposed or unverified behavior.
3. Validate proposed changes using a strict explicit allowlist (`README.md`, `docs/**/*.md`, and other individually approved Markdown files); reject any changes to source code, workflows, scripts, settings, secrets, archives, symlinks or unapproved paths.
4. Check Markdown/link integrity, secrets and unsupported assertions; bound output and run time.
5. If the change is docs-only and all gates pass, push a normal commit to `main` using a dedicated minimally privileged automation identity, only if branch rules allow it. Never force push or bypass protection. Abort/retry on main SHA drift.
6. Publish an audit receipt with Jules session, source SHA, files, checks and resulting commit; prevent trigger loops.
7. On failure, create or update a tracking issue instead of pushing.

## Tests required before enabling
- Allowlisted docs edit passes; source/config/workflow edit fails.
- Secret, symlink/path traversal, private-data and unverified claim attempts fail.
- Stale main SHA, concurrent edits, repeated trigger, Jules outage and authentication errors fail safely.
- No review/PR required for valid documentation-only changes; existing code/security/device/backup verification gates remain intact.

**Implementation note:** Confirm the supported Jules integration and GitHub permissions before wiring any publishing job. No speculative API calls, credentials or direct-to-main automation are included in this document.
