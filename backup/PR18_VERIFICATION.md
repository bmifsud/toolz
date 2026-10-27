# PR #18 full-suite isolation audit

Baseline: `2222649`. Prior run: 94 passed, 16 failed, 1 xfailed.

## Classification of every baseline failure

All 16 were fixture/environment isolation defects, not demonstrated production regressions.

| Module | Test | Evidence / cause |
|---|---|---|
| test_tier1 | test_backup_encrypts_sqlite_secrets_workspace_and_cloud | successful backup, then missing fixture-home archive |
| test_tier1 | test_local_restore_roundtrip_and_permissions | archive lookup failed before restore |
| test_tier1 | test_missing_rclone_remote_does_not_prevent_local_backup | successful local backup, missing fixture-home archive |
| test_tier1 | test_cloud_copy_failure_is_reported | upload failed as intended, retained archive lookup failed |
| test_tier1 | test_local_retention_max_five | seven fixture-home archives untouched; retention targeted another directory |
| test_tier2_direct_stream_integration | test_collision | running-Debian guard stopped execution before collision injection |
| test_tier2_direct_stream_integration | test_success | running-Debian guard stopped execution |
| test_tier2_mock_cloud_failures | test_interrupted_upload_retains_local | running-Debian guard stopped execution before archive creation |
| test_tier2_mock_cloud_failures | test_listing_failure_retains_local | same |
| test_tier2_mock_cloud_failures | test_publication_failure_retains_local | same |
| test_tier2_mock_cloud_failures | test_published_checksum_failure_retains_local | same |
| test_tier2_mock_cloud_failures | test_remote_publication_collision_retains_local | same |
| test_tier2_mock_cloud_failures | test_remote_staged_collision_retains_local | same |
| test_tier2_mock_cloud_failures | test_staged_checksum_failure_retains_local | same |
| test_tier2_mock_cloud_failures | test_success_removes_local_only_after_cloud_verification | same |
| test_tier2_mock_cloud_failures | test_upload_failure_retains_local | same |

Tier-1 evidence: retained mocked-rclone call log referenced `/sdcard/ClineOmniRouteBackups`, while the fixture expected its temporary HOME. The old suite was not actually isolated from shared storage; its retention could affect pre-existing matching files. No conclusion about historical deletion is possible from this evidence. Do not rerun the old fixtures on a tablet.

Tier-2 evidence: stderr `ERROR: Stop Debian before snapshot` (or `before backup`). After isolating pgrep, a second host limitation surfaced: `flock: 8: Function not implemented`. Fixtures now model both process state and lock availability with temporary executables; production guards are unchanged. New negative tests assert running Debian and lock denial stop before archive/cloud output. These mocks are NOT evidence of real device locking support.

## Fixes and coverage

- Tier-1 executes a checked temporary copy with shared-storage paths relocated inside its fixture, preserving selection/retention logic. Added priority/fallback and untouched nonselected-storage tests.
- Removed obsolete wrong-password xfail: production already supports batch passphrase input and the isolated test passes.
- Tier-2 fixtures use private GPG homes and controlled environments, process and lock doubles. No production scripts or restoration code changed in this follow-up.
- Full runner now discovers all `backup/tests` from repository root and syntax-checks all backup shell scripts. Actions publishes JUnit results, including failures.

## Verification results

Complete runner: **117 passed, 0 failed, 0 skipped, 0 xfailed** in 124.06 seconds (`bash backup/test_full_flow.sh --junitxml=/tmp/pr18-final-results.xml`). The final private-GPG-home adjustment was additionally checked with its encrypted-roundtrip module: **3 passed** in 6.07 seconds. Shell syntax, generic verification, and `git diff --check` pass. Six additional cases account for 111 → 117 tests; the obsolete xfail is now a normal passing test.

The private GPG home also removes the encrypted-roundtrip fixture's dependency on host GPG state, observed during interrupted runs. No retries were added to tests. CI must independently run this complete suite after push; the old three-module CI results are not sufficient.

## Remaining security limitations

- Synthetic recovery tests do not authorize production restoration. Absolute Debian symlinks preserved in restored trees can resolve against the host if later followed by ordinary tools. Never use generic tar extraction, execute restored launchers, or traverse restored links outside a reviewed rootfs sandbox.
- Real filesystem concurrency, ancestor replacement races, resource exhaustion, hardlink compatibility and full encrypted-cloud recovery still require independent review/device acceptance.
- Cloud publication/locking are mocked here; real remote atomicity and Android flock availability are not proven.
- Read-only archive validation is structural validation, not proof of bootability or safe generic extraction. Existing encrypted snapshot verification remains pending on the tablet.
- PR must stay unmerged; Tier-2 scheduling remains disabled.

## Read-only tablet verification

Run from **outer Termux**, after stopping Debian normally. Use the PR checkout containing both the shell script and validator. The prompts avoid guessing existing archive/key paths. This reads the ciphertext twice for before/after SHA-256 and streams decryption without extracting or writing plaintext. GPG may update its own local state.

```bash
(
  set -euo pipefail
  read -r -p 'Absolute PR checkout path: ' REPO
  read -r -p 'Absolute existing encrypted snapshot path: ' ARCHIVE
  read -r -p 'Absolute existing protected passphrase-file path: ' KEY
  [[ "$REPO" = /* && "$ARCHIVE" = /* && "$KEY" = /* ]]
  [[ "${PREFIX:-}" = /data/data/com.termux/files/usr ]]
  [[ -f "$ARCHIVE" && ! -L "$ARCHIVE" ]]
  [[ -f "$KEY" && ! -L "$KEY" && "$(stat -c %a "$KEY")" = 600 ]]
  if pgrep -f '[p]root.*debian' >/dev/null; then
    echo 'Stop Debian normally, then retry from outer Termux.' >&2
    exit 1
  fi
  git -C "$REPO" rev-parse HEAD
  BEFORE=$(sha256sum -- "$ARCHIVE")
  rc=0
  env -u ROOTFS_DIR -u START_SCRIPT BACKUP_PASSPHRASE_FILE="$KEY" \
    bash "$REPO/backup/snapshot_andronix2_streaming.sh" \
    --verify-archive "$ARCHIVE" || rc=$?
  AFTER=$(sha256sum -- "$ARCHIVE")
  [[ "$BEFORE" = "$AFTER" ]] || { echo 'Ciphertext checksum changed'; exit 1; }
  printf 'Ciphertext unchanged: %s\nVerification exit: %s\n' "$AFTER" "$rc"
  exit "$rc"
)
```

Expected success: `PASS: validated full archive structure (no extraction performed)` and verification exit 0. Report complete stderr and exit status if it fails; do not weaken validation or recreate/delete the snapshot.
