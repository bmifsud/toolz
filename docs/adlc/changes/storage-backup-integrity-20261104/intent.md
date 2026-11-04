# Change intent — Storage and backup integrity verification (2026-11-04)

This document defines the scope, safety boundaries, and acceptance criteria for
the read-only storage inventory and independent Tier-1 and Tier-2 backup
integrity verification conducted on November 4, 2026.

- Change ID / issue: `storage-backup-integrity-20261104` ([#40](https://github.com/bmifsud/toolz/issues/40), [#105](https://github.com/bmifsud/toolz/issues/105), [#106](https://github.com/bmifsud/toolz/issues/106))
- Owner: Agent 4 — Storage and Backup Integrity
- Baseline revision: `356d3c12750882c5520d909c912f9efba86cfaa0`
- Problem and expected behavior:
  1. Account for the ~35–36 GB attributed to Termux by measuring exact byte
     usage across the Andronix Debian root filesystem (`/` and `/home/b`),
     `/sdcard` backup directories, caches, logs, worktrees, and `/tmp`, and
     documenting the outer Termux boundary outside the PRoot mount.
  2. Independently verify Tier-1 and Tier-2 backup archives locally and on
     Google Drive (`rclone` metadata, MD5, and streamed SHA-256 readback),
     OpenPGP AES-256 encryption packet structure, catch-up/retention logic, and
     isolated end-to-end backup/restore/SQLite `PRAGMA quick_check` in
     `/tmp/toolz-backup-verify-*`.
  3. Add a reusable, strictly read-only verification module
     ([`backup/verify_storage_and_backups.py`](../../../../backup/verify_storage_and_backups.py))
     with unit tests
     ([`backup/tests/test_verify_storage_and_backups.py`](../../../../backup/tests/test_verify_storage_and_backups.py)).
- Scope / exclusions:
  - Read-only storage inventory and archive/remote verification.
  - Isolated backup/decrypt/extract/restore testing in `/tmp/toolz-backup-verify-*`.
  - Exclusions: Do not delete any local or remote backup archives, do not alter
    live cron schedules or retention settings, do not stop live OmniRoute or
    Debian PRoot sessions, and never expose passphrases, tokens, or secrets.
- Acceptance criteria (observable, independent of implementation):
  1. Complete byte-level storage breakdown explaining the ~35–36 GB Termux
     footprint (`28,806,064,001` bytes / `26.83 GiB` / `28.81 GB` decimal in
     Debian rootfs `/` + `/home/b`, plus `8,375,475,470` bytes / `7.80 GiB` /
     `8.38 GB` decimal in `/sdcard` backup directories, plus outer Termux host
     packages/state outside the PRoot mount).
  2. Separate Tier-1 and Tier-2 verification evidence tables in
     [`evidence.md`](evidence.md) with exact archive paths, sizes, timestamps,
     GPG packet structure, local SHA-256/MD5 hashes, remote Google Drive hashes
     and streamed readback SHA-256, isolated restoration results, and explicit
     `PASS`, `FAIL`, or `BLOCKED` gate labels.
  3. All unit and regression tests pass (`pytest backup/tests/ -v`,
     `python3 scripts/check_adlc.py`, `bash tests/run-all-tests.sh`).
- Risk: Low; all live checks are strictly read-only and all restoration checks
  execute in private `/tmp/toolz-backup-verify-*` directories with `0700`
  permissions.
- Data, secrets, device, backup and permission implications:
  - No passphrases, keys, or tokens are read into logs or git history.
  - Live archives in `/home/b/ClineOmniRouteBackups`,
    `/sdcard/ClineOmniRouteBackups`, `/sdcard/Andronix/backups`, and
    `gdrive:ClineOmniRouteBackups` are preserved untouched.
- Affected source paths and dependencies:
  - [`backup/verify_storage_and_backups.py`](../../../../backup/verify_storage_and_backups.py)
  - [`backup/tests/test_verify_storage_and_backups.py`](../../../../backup/tests/test_verify_storage_and_backups.py)
  - [`docs/adlc/changes/storage-backup-integrity-20261104/intent.md`](intent.md)
  - [`docs/adlc/changes/storage-backup-integrity-20261104/evidence.md`](evidence.md)
  - [`docs/adlc/status.md`](../../status.md)
- Assumptions / unresolved decisions:
  - Inside the Debian PRoot session, outer Termux's `$HOME/.config/toolz-backup/config`,
    `$BACKUP_PASSPHRASE_FILE`, and outer Termux `crontab` / `$HOME/.local/state/toolz-backup`
    reside outside the PRoot rootfs mount (`/data/data/com.termux/files/home`).
    Consequently, live production archive decryption with the outer Termux
    passphrase file and live Tier-2 full-rootfs stop-and-snapshot require outer
    Termux host execution and remain labeled `BLOCKED` from inside active
    Debian PRoot.
- Implementation steps:
  1. Execute read-only filesystem and directory usage inventory across `/`,
     `/home/b`, and `/sdcard`.
  2. Verify Tier-1 and Tier-2 local archives, OpenPGP packet headers, local
     SHA-256/MD5 digests, and Google Drive remote counterparts.
  3. Execute isolated end-to-end Tier-1 and Tier-2 backup, verification,
     extraction, and SQLite `PRAGMA quick_check` / `integrity_check` in
     `/tmp/toolz-backup-verify-*`.
  4. Implement `backup/verify_storage_and_backups.py` and unit tests in
     `backup/tests/test_verify_storage_and_backups.py`.
  5. Record evidence in [`evidence.md`](evidence.md) and update
     [`docs/adlc/status.md`](../../status.md).
- Validation commands and environments:
  - `python3 -m pytest backup/tests/ -v`
  - `python3 scripts/check_adlc.py`
  - `bash tests/run-all-tests.sh`
- Failure and denied-action cases:
  - Missing or corrupted GPG headers, missing remote objects, size/MD5/SHA-256
    mismatches, and chronological retention blockers are detected and reported
    without deleting any files.
- Rollback / recovery:
  - Revert the branch commit; no live state or backup archives are modified.
- Required reviewer / approvals:
  - Repository maintainer human review on the pull request before merge.
- Evidence record:
  - [`docs/adlc/changes/storage-backup-integrity-20261104/evidence.md`](evidence.md)
