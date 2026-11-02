# release-readiness-gate

## Purpose
Check branch protection, CI, approvals, open blockers and docs/adlc/status.md. For device/backup changes require authenticated emulator and tablet lifecycle evidence, Tier-1 encrypted upload/catch-up verification and Tier-2 safe snapshot and restore evidence as applicable. Output PASS/BLOCKED/UNKNOWN with links. Never merge or bypass approvals.

## Procedure
1. Read repository ADLC guidance, AGENTS.md and relevant task scope.
2. Inspect actual source and existing capabilities before recommending changes.
3. Collect reproducible evidence with file paths, commit IDs and CI links where available.
4. Report findings, severity, proposed actions, verification steps and unknowns.
5. Require explicit approval before repository writes, operational changes or releases.

## Output
- Scope and inspected revision
- Findings with evidence
- Risks, blockers and unknowns
- Recommended changes and acceptance tests
- Status: proposed, verified or blocked

## Guardrails
Do not expose secrets, operate live backups/devices, modify schedules, or merge PRs without separate authorization. Never equate CI success with end-to-end operational verification.
