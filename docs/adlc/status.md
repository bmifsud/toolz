# ADLC release ledger

Updated 2026-11-02. Initial template PR #113 merged; alignment is a separate draft change.

| Workstream | Phase | Status | Evidence / next action |
| --- | --- | --- | --- |
| Template | Implement | Merged | PR #113; not operational acceptance |
| Repository alignment | Verify | Partial | [Evidence](changes/adlc-alignment/evidence.md); full CI pending |
| Branch protection | Plan | Unverified | Maintainer to configure/verify required ADLC check without bypassing protections |
| Tier-1 | Verify | Pending | Scheduled run, encrypted upload/readback and catch-up |
| Tier-2 | Verify | Pending | OmniRoute shutdown/WAL handling, snapshot/upload and isolated restore |
| Bridge | Plan | Pending | Locate/integrate reviewed source; authenticated emulator and tablet lifecycle |
| Release | Release | Blocked | All standing gates and final-revision CI/approvals |

Do not convert pending to pass without revision-bound evidence. Local offline checks do not waive release gates.
