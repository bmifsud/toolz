# Verification evidence — Storage and backup integrity (2026-11-04)

This document records the read-only storage inventory accounting for the
~35–36 GB Termux footprint and the independent Tier-1 and Tier-2 backup
verification results produced on November 4, 2026.

- Change ID / issue / PR: `storage-backup-integrity-20261104` ([#40](https://github.com/bmifsud/toolz/issues/40), [#105](https://github.com/bmifsud/toolz/issues/105), [#106](https://github.com/bmifsud/toolz/issues/106))
- Exact tested commit: Baseline `356d3c12750882c5520d909c912f9efba86cfaa0` on branch `feat/storage-backup-integrity-20261104`
- Date and environment / tool versions: 2026-11-04, Andronix Debian 13 (PRoot on Android `/dev/block/dm-51`), Python 3.13.5, pytest 8.3.5, gpg 2.4.7, rclone, sqlite3
- Expected behavior: Complete read-only breakdown of the ~35–36 GB Termux storage usage, independent Tier-1 and Tier-2 local/remote cryptographic verification, isolated end-to-end recovery verification in `/tmp/toolz-backup-verify-*`, and automated tests in [`backup/tests/test_verify_storage_and_backups.py`](../../../../backup/tests/test_verify_storage_and_backups.py).
- Reviewer and reviewed revision: Pending independent human review on PR.

## 1. Read-only storage inventory (~35–36 GB Termux attribution)

Android mounts `/dev/block/dm-51` (`118,049,734,656` bytes / `110 GiB` total,
`83,316,748,288` bytes / `77.60 GiB` used, `34,598,768,640` bytes / `32.22 GiB`
available, `71%` used) for both internal app data (`/data/data/com.termux/files/...`,
where the Andronix Debian rootfs resides at
`$TERMUX_HOME/.andronix/distros/debian/rootfs`) and shared storage (`/sdcard` /
`/storage/emulated/0`).

| Category | Path | Exact bytes | Binary size (MiB / GiB) | Decimal size (MB / GB) | Notes |
| --- | --- | --- | --- | --- | --- |
| **Debian rootfs total** | `/` (excluding `/sdcard`, `/proc`, `/sys`, `/dev`) | `28,806,064,001` | `27,471.60 MiB` (`26.83 GiB`) | `28,806.06 MB` (`28.81 GB`) | Stored inside Termux private data (`$TERMUX_HOME/.andronix/distros/debian/rootfs`) |
| Debian system dirs (non-`/home/b`) | `/usr`, `/tmp`, `/var`, `/root`, `/etc`, `/opt` | `9,311,733,948` | `8,880.36 MiB` (`8.67 GiB`) | `9,311.73 MB` (`9.31 GB`) | Subtotal of rootfs outside `/home/b` |
| System packages & binaries | `/usr` | `5,648,738,312` | `5,387.06 MiB` (`5.26 GiB`) | `5,648.74 MB` (`5.65 GB`) | Installed Debian packages, toolchains, libraries |
| Temporary files | `/tmp` | `3,392,962,933` | `3,235.78 MiB` (`3.16 GiB`) | `3,392.96 MB` (`3.39 GB`) | Includes `artriout-pr277` (`557.08 MiB`), `artriout-pr287` (`540.12 MiB`), `artriout-pr284` (`531.62 MiB`), `poc-artriout-issue-243` (`508.98 MiB`), `tmp.AfyjLIZAXf` (`207.01 MiB`), and 32 stale `/tmp/cline_omni_backup.*` dirs (`~615.30 MiB`) |
| Variable state | `/var` (`/var/cache`: `4.07 MiB`, `/var/log`: `0.85 MiB`, `/var/tmp`: `0 B`) | `197,547,945` | `188.40 MiB` (`0.18 GiB`) | `197.55 MB` (`0.20 GB`) | `apt` lists/dpkg metadata and system logs |
| Root user home | `/root` | `70,563,094` | `67.29 MiB` (`0.07 GiB`) | `70.56 MB` (`0.07 GB`) | Root user config/cache |
| System configuration | `/etc` + `/opt` (`/opt` is `0 B`) | `1,921,426` | `1.83 MiB` (`0.002 GiB`) | `1.92 MB` (`0.002 GB`) | `/etc` configuration files |
| **Debian user home total** | `/home/b` | `19,494,330,053` | `18,591.24 MiB` (`18.16 GiB`) | `19,494.33 MB` (`19.49 GB`) | Primary contributor inside Debian rootfs |
| User caches | `/home/b/.cache` | `7,060,534,325` | `6,733.45 MiB` (`6.58 GiB`) | `7,060.53 MB` (`7.06 GB`) | `uv` cache (`4,996,977,566` B / `4.65 GiB`), `ms-playwright` (`1,964,768,113` B / `1.83 GiB`), `node-gyp` (`58.15 MiB`), `pip` (`29.86 MiB`), `antigravity` (`5.90 MiB`) |
| NPM cache & global packages | `/home/b/.npm` | `3,752,232,064` | `3,578.41 MiB` (`3.49 GiB`) | `3,752.23 MB` (`3.75 GB`) | Node/npm package cache (`_cacache`, `_npx`) |
| Codex data | `/home/b/.codex` | `2,843,056,451` | `2,711.35 MiB` (`2.65 GiB`) | `2,843.06 MB` (`2.84 GB`) | Codex CLI runtime/state |
| Gemini / Antigravity data | `/home/b/.gemini` | `1,576,872,916` | `1,503.82 MiB` (`1.47 GiB`) | `1,576.87 MB` (`1.58 GB`) | Gemini CLI / Antigravity state & browser profile |
| User local share/state/venv | `/home/b/.local` | `1,494,707,323` | `1,425.46 MiB` (`1.39 GiB`) | `1,494.71 MB` (`1.49 GB`) | Includes `toolz-backup` test state (`22.45 MiB`) and local packages |
| OmniRoute runtime & DB | `/home/b/.omniroute` | `572,834,621` | `546.30 MiB` (`0.53 GiB`) | `572.83 MB` (`0.57 GB`) | Includes `storage.sqlite` and `/home/b/.omniroute/backups` (`85,410,765` B / `81.45 MiB`) |
| Development worktrees & repos | `/home/b/artriout*`, `/home/b/POC-ARTRIOUT`, `/home/b/tier1-recovery`, `/home/b/toolz*`, `/home/b/AM` | `1,852,414,225` | `1,766.60 MiB` (`1.73 GiB`) | `1,852.41 MB` (`1.85 GB`) | `artriout-issue-247` (`533.69 MiB`), `POC-ARTRIOUT` (`509.29 MiB`), `artriout-pr-265` (`482.36 MiB`), `tier1-recovery` (`210.56 MiB`), `toolz` (`17.54 MiB`), 23 `toolz-*` worktrees (`~11.4 MiB`), `artriout-issue-301` (`1.38 MiB`), `AM` (`0.39 MiB`) |
| Cline CLI data & worktrees | `/home/b/.cline` (`/home/b/.cline/worktrees`: `699,346` B / `0.67 MiB`) | `191,664,260` | `182.79 MiB` (`0.18 GiB`) | `191.66 MB` (`0.19 GB`) | Cline task history, settings, secrets, worktrees |
| Local Tier-1 backups (Debian) | `/home/b/ClineOmniRouteBackups` | `136,413,621` | `130.09 MiB` (`0.13 GiB`) | `136.41 MB` (`0.14 GB`) | 29 `cline_omniroute_backup_*.tar.gz.gpg` archives + 1 `pre_open_hands_20261023_175607.tar.gz.gpg` |
| Agent skills & home logs | `/home/b/.agents` (`770,252` B) + `/home/b/*.log` (`308,421` B across 29 files) | `1,078,673` | `1.03 MiB` | `1.08 MB` | Skills definitions and log files |
| **Shared storage backups (`/sdcard`)** | `/sdcard/Andronix/backups` + `/sdcard/ClineOmniRouteBackups` | `8,375,475,470` | `7,987.48 MiB` (`7.80 GiB`) | `8,375.48 MB` (`8.38 GB`) | Tier-2 encrypted rootfs snapshot (`8,375,455,320` B) + 17 legacy 854–869 B Tier-1 files & `snapshot_andronix_debian.sh` (`20,150` B) |
| **Combined Debian rootfs + `/sdcard` backups** | `/` (Debian rootfs) + `/sdcard` backups | **`37,181,539,471`** | **`35,459.08 MiB` (`34.63 GiB`)** | **`37,181.54 MB` (`37.18 GB`)** | Exact match for the ~35–36 GB footprint |

### How the ~35–36 GB Termux footprint is explained

1. **Andronix Debian rootfs inside Termux app storage (`26.83 GiB` binary / `28.81 GB` decimal):**
   Because Andronix stores the Debian rootfs inside Termux's private app directory
   (`/data/data/com.termux/files/home/.andronix/distros/debian/rootfs`), Android
   attributes every byte inside the Debian rootfs directly to the `com.termux`
   application. Within that `28.81 GB`:
   - **Caches and package stores (`10.81 GB` decimal / `10.07 GiB`):** `/home/b/.cache/uv` (`5.00 GB`), `/home/b/.npm` (`3.75 GB`), and `/home/b/.cache/ms-playwright` (`1.96 GB`) alone consume `10.71 GB`.
   - **Installed Debian `/usr` packages (`5.65 GB` decimal / `5.26 GiB`)**.
   - **AI agent runtimes and state (`6.49 GB` decimal / `6.04 GiB`):** `.codex` (`2.84 GB`), `.gemini` (`1.58 GB`), `.local` (`1.49 GB`), `.omniroute` (`0.57 GB`), and `.cline` (`0.19 GB`).
   - **Temporary directories in `/tmp` (`3.39 GB` decimal / `3.16 GiB`):** Four `artriout` temporary checkouts (`~2.14 GiB`) and 32 leftover `/tmp/cline_omni_backup.*` staging directories (`~615.30 MiB`).
   - **Development worktrees in `/home/b` (`1.85 GB` decimal / `1.73 GiB`)** and **local Tier-1 archives in `/home/b/ClineOmniRouteBackups` (`0.14 GB` decimal / `130.09 MiB`)**.
2. **Tier-2 encrypted Debian snapshot on `/sdcard/Andronix/backups` (`7.80 GiB` binary / `8.38 GB` decimal):**
   Combined with the `26.83 GiB` Debian rootfs, the total is **`34.63 GiB` (`37.18 GB` decimal)**.
   Furthermore, outer Termux itself (`/data/data/com.termux/files/usr` and outer Termux `$HOME` outside the Debian PRoot bind mount) holds ~`6–7 GB` of Termux host packages (`proot`, `gnupg`, `rclone`, `python`, `nodejs`, `git`, `rust`) and Termux-level caches, which brings Android Settings' decimal app-storage total for `com.termux` (`28.81 GB` Debian rootfs + ~`6–7 GB` outer Termux host files) to **~35–36 GB**.

## 2. Tier-1 backup verification evidence table

| Gate / check | Exact command or procedure | Expected | Observed | Result | Redacted artifact / details |
| --- | --- | --- | --- | --- | --- |
| **1. Script & syntax audit** | `bash -n backup/backup_cline_omniroute.sh backup/run_scheduled_backup.sh backup/check_missed_backups.sh backup/install_backup_cron.sh backup/install_catchup.sh backup/tier1_retention.sh backup/run_debian_noninteractive.sh` | Exit `0` for all scripts | All 7 Tier-1 scripts exit `0`; `umask 077`, private `mktemp -d "${TMPDIR:-$HOME}/cline_omni_backup.XXXXXX"`, `flock`, and AES-256 symmetric GPG encryption confirmed | **PASS** | [`backup/backup_cline_omniroute.sh`](../../../../backup/backup_cline_omniroute.sh), [`backup/run_scheduled_backup.sh`](../../../../backup/run_scheduled_backup.sh) |
| **2. Local archive inventory & latest archives** | `stat -c '%s %Y %a %n' /home/b/ClineOmniRouteBackups/*.gpg` | Valid `0600` encrypted archives present | 34 `cline_omniroute_backup_*.tar.gz.gpg` archives + 1 `pre_open_hands_20261023_175607.tar.gz.gpg` (`167,957,685` B total after scheduled runs during audit). Verified archives: `cline_omniroute_backup_20261104_005547.tar.gz.gpg` (`6,118,381` B, mtime `1793750160`, mode `600`), `cline_omniroute_backup_20261104_034208.tar.gz.gpg` (`6,308,796` B, mtime `1793760132`, mode `600`), and `cline_omniroute_backup_20261104_100000.tar.gz.gpg` (`6,308,797` B, mtime `1793782802`, mode `600`). `/sdcard/ClineOmniRouteBackups` also contains 17 legacy 854–869 B `.gpg` files from Oct 27 / Nov 2 | **PASS** | `/home/b/ClineOmniRouteBackups/cline_omniroute_backup_20261104_100000.tar.gz.gpg` |
| **3. OpenPGP AES-256 encryption header inspection** | `head -c 4096 <archive> \| gpg --batch --no-tty --pinentry-mode cancel --list-packets` and `verify_storage_and_backups.inspect_gpg_header()` | Tag 3 symkey enc packet (version 4, cipher 9 = AES-256, S2K 3 = Iterated+Salted, hash 10 = SHA-512) + Tag 18 encrypted data packet (`mdc_method: 2`) | `20261104_005547` (salt `1239123DBDAD5A82`, count `65011712`), `20261104_034208` (salt `2F0DE1A874AF011C`, count `65011712`), and `20261104_100000` all have valid OpenPGP v4 AES-256 CFB + MDC headers | **PASS** | [`backup/verify_storage_and_backups.py`](../../../../backup/verify_storage_and_backups.py) |
| **4. Google Drive remote presence, size, & MD5 check** | `rclone lsjson --hash gdrive:ClineOmniRouteBackups --max-depth 1` and `rclone check /home/b/ClineOmniRouteBackups gdrive:ClineOmniRouteBackups --one-way --include 'cline_omniroute_backup_20261104_*.tar.gz.gpg'` | Remote objects present with matching byte size and MD5 | `20261104_005547` (GDrive ID `1BSVTDNJVm4PVxLQZioga5UUyno6am1fD`, `6,118,381` B, MD5 `073ad38cc5a5e9a547ede422cf15ae34`), `20261104_034208` (GDrive ID `1xXAZbjwm5qCUF1Go_Q4M4fnHDSdF8DXb`, `6,308,796` B, MD5 `1ea62e2c2638df0013900b34aea72121`), and `20261104_100000` (GDrive ID `1HYg4j5SplZEmzaa9gTqzf0VXhQkQ1z-W`, `6,308,797` B, MD5 `10bcf91bd254618540f51c5e765b4594`) match local size and MD5 (`0 differences found`) | **PASS** | `gdrive:ClineOmniRouteBackups` |
| **5. Full remote ciphertext readback SHA-256 (`rclone cat`)** | `rclone cat gdrive:ClineOmniRouteBackups/<name> \| sha256sum` vs local `sha256sum` | Bit-for-bit identical SHA-256 between local archive and streamed Google Drive readback | `20261104_005547`: local & remote SHA-256 = `8b66645700fb1281c6a816df12ec2cc63939688a49c55a288b7b835bf1253b86`; `20261104_034208`: local & remote SHA-256 = `233c4412f9adf23f7e75ef72be4ffd37136749beb4b2ece4b366661f2982da43`; `20261104_100000`: local & remote SHA-256 = `942c6641307b5087b15e723a7485b25c9b5a1dbcdd14fafa05077751085ddd0b`; `20261103_001506`: local & remote SHA-256 = `a636eb072991028f612b162efc7654f3528f5aa65466fd5ce87f145c9e2bee71` | **PASS** | Streamed 100% of ciphertext bytes from Google Drive |
| **6. Retention & catch-up interaction audit** | `rclone check /home/b/ClineOmniRouteBackups gdrive:ClineOmniRouteBackups --one-way --include 'cline_omniroute_backup_*.tar.gz.gpg'` + `detect_tier1_retention_blockers()` | All older local archives present on remote so `tier1_retention.sh --apply` succeeds and `run_scheduled_backup.sh` logs `SUCCESS tier1` | 26 of 29 local archives match GDrive, but 3 older local archives (`20261028_210001`, `20261029_091627`, `20261102_224957`) are absent on GDrive. `tier1_retention.sh` halts at `20261028_210001` (`exit 1`), preventing cleanup of the 25 verified older archives and causing `run_scheduled_backup.sh` to exit `1` at line 86 before writing `SUCCESS tier1`, which in turn causes `check_missed_backups.sh` to re-trigger catch-up every 30 minutes | **FAIL** | Non-destructive finding documented; no archives deleted per safety rules |
| **7. Outer Termux scheduler & live passphrase decryption boundary** | Check `$BACKUP_PASSPHRASE`, `/home/b/.config/toolz-backup/config`, `/home/b/.local/state/toolz-backup` inside Debian PRoot | Passphrase file and cron state reside in outer Termux host (`$TERMUX_HOME/.config/toolz-backup/config`, `$TERMUX_HOME/.local/state/toolz-backup`) outside Debian PRoot mount | Confirmed: `run_debian_noninteractive.sh` injects `BACKUP_PASSPHRASE` from outer Termux only during scheduled execution; passphrase is not stored inside Debian rootfs. Historical receipt `/home/b/.local/state/toolz-backup/local-test-20261102_210907/receipt.json` records `20261102_210907` (`4,328,042` B, SHA-256 `86493cd739f4964764f3a9e3211b6855a3e094f9020eea8481ecbe4d44980553`, `database_integrity: ok`). Live passphrase decryption of `20261104_034208` requires outer Termux host | **BLOCKED** | Boundary enforced by design (`run_debian_noninteractive.sh` line 20–21) |
| **8. Isolated end-to-end Tier-1 backup, readback, decrypt, restore, & SQLite `PRAGMA quick_check` / `integrity_check`** | Isolated `/tmp/toolz-backup-verify-tier1-*` sandbox seeded with hot `.backup` of live `/home/b/.omniroute/storage.sqlite`, running `backup_cline_omniroute.sh backup` and `--restore`, plus `pytest backup/tests/test_tier1.py` | Exit `0`, valid AES-256 archive (`6,305,588` B), local==remote SHA-256, safe extraction, `PRAGMA quick_check`=`ok`, `PRAGMA integrity_check`=`ok` across all 105 OmniRoute tables, restored `secrets.json` and `.env` mode `0600` | Archive `cline_omniroute_backup_20261104_040048.tar.gz.gpg` (`6,305,588` B, SHA-256 `3796c5bd75d62b49cbf57f65f8431e2d48b59111f8852caaf2e33afcb73d2cdd`) created, verified, decrypted, and restored in `/tmp/toolz-backup-verify-tier1-*`; `PRAGMA quick_check: ok`, `PRAGMA integrity_check: ok`, modes `0o600` verified | **PASS** | Isolated `/tmp/toolz-backup-verify-tier1-*` (cleaned on exit) + [`backup/tests/test_tier1.py`](../../../../backup/tests/test_tier1.py) |

## 3. Tier-2 backup verification evidence table

| Gate / check | Exact command or procedure | Expected | Observed | Result | Redacted artifact / details |
| --- | --- | --- | --- | --- | --- |
| **1. Script & syntax audit (`snapshot_andronix_debian.sh`, `snapshot_andronix2_streaming.sh`, `snapshot_andronix_layout.sh`, `check_tier2_preflight.sh`, `pre_snapshot_clean.sh`)** | `bash -n backup/*.sh` + static inspection of OmniRoute shutdown & SQLite WAL handling | All scripts exit `0`; `pre_snapshot_clean.sh` runs Tier-1 backup first, stops `omniroute.service`, verifies no `[o]mniroute` process is running, runs `PRAGMA wal_checkpoint(TRUNCATE);` and `PRAGMA quick_check;` | All scripts pass `bash -n` (`exit 0`). `run_scheduled_backup.sh` refuses Tier-2 when `[p]root.*debian` is active (`exit 75`) or when `$STATE/tier2-ready` marker is missing/older than 2 hours (`exit 75`), and delegates to `snapshot_andronix2_streaming.sh --gdrive` + `--verify-archive` | **PASS** | [`backup/pre_snapshot_clean.sh`](../../../../backup/pre_snapshot_clean.sh), [`backup/snapshot_andronix2_streaming.sh`](../../../../backup/snapshot_andronix2_streaming.sh) |
| **2. Local Tier-2 archive identity, byte size, & timestamp** | `stat -c '%s %Y %a %n' /sdcard/Andronix/backups/andronix-debian-20261027_013440.tar.gz.gpg` | Exact size `8,375,455,320` bytes (`7.80 GiB` / `8.38 GB`) | File `/sdcard/Andronix/backups/andronix-debian-20261027_013440.tar.gz.gpg`: size = `8,375,455,320` bytes, mtime = `1793063144` (`2026-10-27T01:05:44Z`), mode = `0660` | **PASS** | `/sdcard/Andronix/backups/andronix-debian-20261027_013440.tar.gz.gpg` |
| **3. Tier-2 OpenPGP AES-256 encryption packet structure** | `head -c 4096 /sdcard/Andronix/backups/andronix-debian-20261027_013440.tar.gz.gpg \| gpg --batch --no-tty --pinentry-mode cancel --list-packets` | Tag 3 symkey enc packet (version 4, cipher 9 = AES-256, S2K 3) + Tag 18 encrypted data packet (`mdc_method: 2`) | `# off=0 ctb=8c tag=3 hlen=2 plen=13 :symkey enc packet: version 4, cipher 9, aead 0, s2k 3, hash 8, salt F31601A76176CC0E, count 32505856 (239)` + `# off=15 ctb=d2 tag=18 hlen=2 plen=0 partial new-ctb :encrypted data packet: mdc_method: 2` (`AES256.CFB`) | **PASS** | Verified via `gpg --list-packets` and `inspect_gpg_header()` |
| **4. Local Tier-2 full-file cryptographic digests (8.38 GB read)** | Single-pass streaming digest over all `8,375,455,320` bytes of `/sdcard/Andronix/backups/andronix-debian-20261027_013440.tar.gz.gpg` | Complete 8.38 GB read without I/O error | Read `8,375,455,320` bytes in `57.31s`:<br>- Local SHA-256: `2ed97feb666c7513a043f7bde26e5a115fc422a132b2df10c36135dfbb0a1d87`<br>- Local SHA-1: `ea16baea012807af302e7bb37917964d52bc78a9`<br>- Local MD5: `ca65c04105fdab6c72aecd402303c350` | **PASS** | [`backup/verify_storage_and_backups.py`](../../../../backup/verify_storage_and_backups.py) |
| **5. Google Drive Tier-2 remote presence, size, & cryptographic MD5 verification** | `rclone lsjson --hash gdrive:ClineOmniRouteBackups/AndronixSnapshots --max-depth 1`, `rclone hashsum md5 ...`, and `rclone check /sdcard/Andronix/backups gdrive:ClineOmniRouteBackups/AndronixSnapshots --one-way --include 'andronix-debian-*.tar.gz.gpg'` | Remote object present with matching `8,375,455,320` byte size and matching MD5 digest | Remote object `gdrive:ClineOmniRouteBackups/AndronixSnapshots/andronix-debian-20261027_013440.tar.gz.gpg` (GDrive ID `1heu215KJDnzKh6gV6MiWjMPvxNw64xcC`, ModTime `2026-10-27T01:05:44.491Z`): size = `8,375,455,320` B, remote MD5 = `ca65c04105fdab6c72aecd402303c350` (**exact match** with local MD5); `rclone check` reports `0 differences found, 1 matching files` | **PASS** | `gdrive:ClineOmniRouteBackups/AndronixSnapshots` |
| **6. Live Tier-2 `andronix-debian-20261027_013440.tar.gz.gpg` full decryption & live rootfs snapshot execution** | Check outer Termux passphrase availability and active PRoot safety gate (`pgrep -f '[p]root.*debian'`) | Blocked from inside active Debian PRoot session (`snapshot_andronix2_streaming.sh` and `run_scheduled_backup.sh` require outer Termux with Debian stopped and outer Termux `$BACKUP_PASSPHRASE_FILE`) | Active Debian PRoot session is running Agent 2 / OmniRoute / RDC; per strict safety rules, live Debian/OmniRoute was not stopped and outer Termux passphrase file is outside PRoot | **BLOCKED** | Safety gate verified; must run from outer Termux with Debian stopped |
| **7. Isolated end-to-end Tier-2 snapshot, cloud SHA-256 verification, member safety check, & staged restore** | Isolated `/tmp/toolz-backup-verify-tier2-*` execution of `snapshot_andronix2_streaming.sh --gdrive`, `snapshot_andronix2_streaming.sh --verify-archive`, `snapshot_andronix_layout.sh --restore-test`, plus `pytest backup/tests/test_tier2.py backup/tests/test_backup_flow.py backup/tests/test_andronix2_runner_wiring.py` | Encrypted archive created, cloud SHA-256 verified, `--verify-archive` confirms member names/link targets safe and `/tmp` excluded, `--restore-test` extracts cleanly into isolated staging dir without touching live rootfs | `snapshot_andronix2_streaming.sh --gdrive` (`rc=0`), `--verify-archive` (`PASS: decrypted full archive and validated member names/types`), `snapshot_andronix_layout.sh --restore-test` (`RESTORE TEST COMPLETE`), sentinel restored (`andronix2-tier2-verified`), `rootfs/tmp/excluded.txt` excluded (`True`), and all 64 existing + 9 new pytest tests pass | **PASS** | Isolated `/tmp/toolz-backup-verify-tier2-*` + [`backup/tests/test_verify_storage_and_backups.py`](../../../../backup/tests/test_verify_storage_and_backups.py) |

## 4. Automated verification gates

| Check | Exact command or procedure | Expected | Observed | Result | Redacted artifact |
| --- | --- | --- | --- | --- | --- |
| Backup & storage unit/integration tests | `python3 -m pytest backup/tests/ -v` | 73 passed, 0 failed | 73 passed (`64` existing + `9` new in `test_verify_storage_and_backups.py`) | pass | [`backup/tests/test_verify_storage_and_backups.py`](../../../../backup/tests/test_verify_storage_and_backups.py) |
| ADLC structure & link checker | `python3 scripts/check_adlc.py` | `PASS: ADLC structure and local links` | `PASS: ADLC structure and local links` (exit `0`) | pass | [`scripts/check_adlc.py`](../../../../scripts/check_adlc.py) |
| Full offline repository test suite | `bash tests/run-all-tests.sh` | Exit `0` across all test suites | All shell syntax, ADLC, watchdog, bridge, trading, and backup tests pass | pass | [`tests/run-all-tests.sh`](../../../../tests/run-all-tests.sh) |
| Security / failure paths | Wrong passphrase, missing remote archive, checksum mismatch, unsafe member paths, active PRoot refusal, existing rootfs overwrite refusal | All fail closed without data loss | Verified in `test_tier1.py`, `test_tier2.py`, `test_backup_flow.py`, `test_retention.py`, and `test_verify_storage_and_backups.py` | pass | [`backup/tests/`](../../../../backup/tests) |
| Emulator lifecycle | Not in scope for storage/backup verification workstream | Not applicable to this PR | Handled by dedicated device/RDC workstream; standing release hold remains | not-applicable | [`docs/adlc/status.md`](../../status.md) |
| Tablet lifecycle | Not in scope for storage/backup verification workstream | Not applicable to this PR | Handled by dedicated device/RDC workstream; standing release hold remains | not-applicable | [`docs/adlc/status.md`](../../status.md) |

## 5. Summary of findings, limitations, and residual risks

- **Baseline failures / operational findings**:
  - Three historical local Tier-1 archives in `/home/b/ClineOmniRouteBackups`
    (`cline_omniroute_backup_20261028_210001.tar.gz.gpg`,
    `cline_omniroute_backup_20261029_091627.tar.gz.gpg`, and
    `cline_omniroute_backup_20261102_224957.tar.gz.gpg`) are not present on
    `gdrive:ClineOmniRouteBackups`. Because `backup/tier1_retention.sh`
    iterates chronologically from oldest to newest and exits `1` on the first
    older archive missing from Google Drive, local retention cleanup halts at
    `20261028_210001`, leaving 29 archives (`130.09 MiB`) in
    `/home/b/ClineOmniRouteBackups`. Furthermore, because
    `backup/run_scheduled_backup.sh` invokes `tier1_retention.sh --apply` under
    `set -euo pipefail` before writing `SUCCESS tier1`, scheduled runs exit `1`
    at the retention step even after uploading and verifying the newest archive,
    which causes `backup/check_missed_backups.sh` to re-run catch-up every 30
    minutes.
  - `/tmp` contains `3.16 GiB` (`3.39 GB`) of temporary artifacts, including
    four `artriout` worktrees (`~2.14 GiB`) and 32 stale
    `/tmp/cline_omni_backup.*` directories (`~615.30 MiB`).
- **Limitations / residual risks**:
  - Live passphrase decryption of production archives and live Tier-2
    full-rootfs stop-and-snapshot require outer Termux host access with Debian
    stopped; they were not forced from inside the active Debian PRoot session.
- **Blocking findings and follow-up issues**:
  - Upload or quarantine the 3 unuploaded historical local archives in
    `/home/b/ClineOmniRouteBackups` during an authorized maintenance window so
    `tier1_retention.sh --apply` and `run_scheduled_backup.sh` can complete
    cleanly (`#105`, `#106`).
- **Required CI / approvals on final revision**:
  - Pending GitHub Actions `offline` check and human review on PR.
- **Release decision and accountable human**:
  - Release remains **Blocked** pending human review, branch protection, and
    outer-Termux maintenance completion.
- **Merged revision and post-merge verification**:
  - Pending PR review and merge.
- **Rollback / recovery outcome**:
  - Strictly additive verification module, tests, and ADLC documentation; revert
    commit if rollback is needed.
