# ADLC release ledger

Updated 2026-11-02. Baseline: 46d1c058bd1eaa2e59b006e7c860fd590dc211da.

| Workstream | Phase | Status | Evidence / next action |
| --- | --- | --- | --- |
| Repository ADLC | Verify | Offline CI passed | [Main run](https://github.com/bmifsud/toolz/actions/runs/41515187070); does not establish live acceptance |
| Device-access architecture | Implement | Commander selected | [Merged PR #123](https://github.com/bmifsud/toolz/pull/123); all device environments plan through Desktop Commander |
| Custom replay guard | Plan | Superseded | [PR #121](https://github.com/bmifsud/toolz/pull/121) closed without merge; do not restore obsolete custom transport work |
| Commander acceptance | Verify | Pending | Pin target device and checkout; verify authorized diagnostics, denied operations, interruption and recovery through Commander |
| Branch protection | Verify | Unverified | Earlier protection read denied (403); maintainer verification still needed |
| Tier-1 | Verify | Pending | Revision-bound scheduled execution, encrypted upload/readback and catch-up |
| Tier-2 | Verify | Pending | Safe OmniRoute shutdown/WAL handling, snapshot/upload and isolated restore integrity |
| Release | Release | Blocked | Required reviews/CI, operational evidence and unresolved inherited gates |

Desktop Commander is the selected access mechanism. It does not replace Termux/Andronix
backup data, paths or schedules. Do not delete backup functionality when removing obsolete
connection designs. Historical bridge/emulator/tablet requirements remain unresolved;
changing architecture does not silently mark them passed or waive release protection.

Earlier Commander backup observations were reported in another session; fresh acceptance
must link the exact checkout, procedure and redacted artifacts. Online device discovery
alone is not command execution, backup integrity or restore evidence.
