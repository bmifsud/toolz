# ADLC release ledger

Updated 2026-11-03 against main `356d3c12750882c5520d909c912f9efba86cfaa0`.
See [policy evidence](changes/policy-evidence-20261103/evidence.md) and the newer
[conformance and resilience record](changes/conformance-resilience-20261103/evidence.md).

| Workstream | Phase | Status | Evidence / next action |
| --- | --- | --- | --- |
| ADLC audit implementation | Implement | Merged | [PR #141](https://github.com/bmifsud/toolz/pull/141); implementation is distinct from human approval |
| Current-main verification | Verify | Offline passed | [Main CI](https://github.com/bmifsud/toolz/actions/runs/41589158363) passed; local isolated full gate passed 153 tests on the baseline above |
| Required review | Verify | Enforced; approval pending | One approving review and latest-push approval required; stale reviews dismissed. Self/model review is not independent human approval |
| Main protection | Verify | Verified | Strict `offline` check bound to GitHub Actions app 15368; administrator enforcement, resolved conversations, no force pushes/deletion |
| Release hold | Release | Enforced | Main is read-only locked. Do not unlock as a retry/recovery action or to merge this documentation |
| Resilience mechanisms | Verify | Offline verified | Existing watchdog/supervisor: 19 fixture tests passed. Live session adoption/recovery is not established by those tests |
| Device-access architecture | Implement | Commander selected | [PR #123](https://github.com/bmifsud/toolz/pull/123); no custom direct-device bridge recovery |
| Commander lifecycle/security | Verify | Pending | Authenticated reconnect, cancellation, restart and denial paths require separate accepted emulator/tablet evidence |
| Tier-1 | Verify | Pending | [#105](https://github.com/bmifsud/toolz/issues/105), [#106](https://github.com/bmifsud/toolz/issues/106): revision-bound live integrity/restore and scheduled/catch-up evidence incomplete |
| Tier-2 selected workflow | Plan / Verify | Pending | Requested Andronix Backup Debian + Google Drive workflow requires implementation/acceptance evidence; old snapshot fixtures do not prove it |
| Overall operational conformance | Release | Blocked | Live acceptance, actual independent approval and accountable release decision are not yet verified |

## Evidence boundaries

Main protection was enabled during earlier user-directed conformity work and has now
been independently read back. This ledger update performs no settings changes.
The dated [control snapshot](changes/conformance-resilience-20261103/branch-controls.json)
is an observation, not a signed attestation or permanent guarantee against later drift.

The [test summaries](changes/conformance-resilience-20261103/test-summaries.json) retain
the inspected JUnit counts and SHA-256 digests. Raw local logs are temporary; the hashes
and summaries do not independently prove real-device or live-backup behavior.
Older installed-checkout failures are historical and are not labeled current-main failures.

## Required next actions

- Keep main locked while operational acceptance remains incomplete. No automatic rollback
  to the prior unprotected state is permitted.
- Obtain actual independent review of the final revision. Do not manufacture approval or
  substitute AI consensus.
- Complete the separately owned Commander/emulator/tablet acceptance work without launching
  duplicate runners or disturbing another worktree.
- Verify current Tier-1 and selected Andronix Tier-2 operations with revision-bound,
  redacted upload/readback, scheduling/catch-up and isolated recovery evidence.
- Enable live recovery only after explicit ownership transfer, approved adapters and the
  [resilience integration requirements](resilience.md) are verified.

Backup data, schedules, retention and credentials are unchanged by this record.
Passing offline tests and enforcing the hold are progress, not full operational conformity.
