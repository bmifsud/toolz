# ADLC release ledger

Updated 2026-11-04 against main `356d3c12750882c5520d909c912f9efba86cfaa0`.
See the [policy evidence record](changes/policy-evidence-20261103/evidence.md).

| Workstream | Phase | Status | Evidence / next action |
| --- | --- | --- | --- |
| ADLC audit implementation | Implement | Merged | [PR #141](https://github.com/bmifsud/toolz/pull/141), reviewed source head `9a7772b38e5cda4fc984b0f98d064ca440e3b48d`; merge is not approval evidence |
| Merged revision verification | Verify | Offline passed | [Main CI](https://github.com/bmifsud/toolz/actions/runs/41587424340), receipt matches main SHA above; 134 tests, zero failures/errors/skips |
| Required review evidence | Verify | Missing | PR #141 review endpoint returned an empty list; independent approval not established |
| Branch protection | Verify | Control absent | Main protection endpoint returned HTTP 404 “Branch not protected”; repository rulesets returned an empty list; settings unchanged |
| Device-access architecture | Implement | Commander selected | [PR #123](https://github.com/bmifsud/toolz/pull/123); no custom direct-device bridge recovery |
| Secure OpenSSH alternative | Implement / Verify | Complete (PR unmerged) | See [evidence](changes/parallel-ssh-alternative/evidence.md); 159 offline tests pass; key auth & private/localhost only |
| Commander lifecycle/security | Verify | Pending | Read-only access observed; authenticated disconnect/reconnect/cancel/restart/denial acceptance not verified; coordinate separate emulator/tablet work |
| Tier-1 | Verify | Pending | [Issue #105](https://github.com/bmifsud/toolz/issues/105) and [#106](https://github.com/bmifsud/toolz/issues/106); live integrity/restore and scheduled/catch-up evidence incomplete |
| Tier-2 selected workflow | Plan / Verify | Pending | User-selected Andronix Backup Debian + Google Drive needs implementation/acceptance evidence; existing snapshot scripts do not establish the replacement workflow |
| Release | Release | Blocked | Protection/review controls, operational gates and accountable release decision remain unresolved |

## Evidence boundaries

The current CI receipt explicitly records **offline fixtures only**, with device/live-backup
acceptance unverified. It is not signed origin proof or human approval.

Existing device records from 2026-11-02 separately show an offline run with 119 tests
passing and an older installed-checkout run exiting 1 with four failures, 36 passes and
two expected failures. A decryption-error indication is also present. Those temporary
records are not fresh acceptance of the merged revision and are not durable release
evidence. Do not infer a regression in current main or a successful live restore from them.

Desktop Commander is the access mechanism. Preserve backup data, paths, schedules and
retention. The selected Tier-2 redesign does not silently waive consistency, cloud
readback, isolated recovery, or inherited lifecycle requirements.

## Required next actions

- Obtain authorized repository-settings work to enforce PR review and the observed
  `offline` CI check on the final reviewed revision. This record does not enable controls.
- Record independent approval and reviewed revision; do not retroactively assert it.
- Verify Commander lifecycle/security through the approved separate device work.
- Capture revision-bound Tier-1 scheduling/upload/readback/catch-up/restore evidence.
- Establish the selected Andronix Tier-2 workflow and its safe consistency, upload/readback,
  and isolated recovery evidence before treating that gate as satisfied.

No settings, live-device, backup, restore, schedule or retention operations are authorized
by this ledger. Release remains blocked; missing evidence stays missing.
