# Debian receipt alignment intent

- Owner: repository maintainer.
- Baseline: dc91663886e8a1137f4279c350e600d823eddbc1.
- Problem: Debian diagnostic plans have no accepted receipt identifiers; non-ASCII IDs can raise TypeError rather than a validation rejection.
- Acceptance: planner/receipt allowlists agree; malformed IDs and Unicode output fail with ValueError; combined output is limited to 16384 UTF-8 bytes.
- Scope: offline validator, boundary tests and architecture documentation.
- Plan: reuse planner diagnostic sets, validate correlation grammar before constant-time comparison, test valid Debian receipts and exact output boundaries.
- Risk: callers must use the same 8–64 ASCII ID grammar as audit_event. Receipt validation does not authenticate device origin.
- Validation: offline bridge unit discovery, ADLC links and complete CI fixture gate.
- Rollback: revert through review; no production data changes.
- Release: standing review/device/backup gates unchanged.
- Evidence: [record](evidence.md).

