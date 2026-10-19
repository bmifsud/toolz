# Tier-2 Andronix Rootfs Backup

This document supplements the existing `backup/README.md` and **does not replace Tier-1**.

| Tier | Script | Shell | Purpose |
|---|---|---|---|
| Tier-1 | `backup_cline_omniroute.sh` (existing, unchanged) | Debian | OmniRoute/Cline state backup |
| Tier-2 preparation | `pre_snapshot_clean.sh` | Debian | Tier-1 backup, stop OmniRoute, checkpoint SQLite |
| Tier-2 snapshot | `snapshot_andronix_debian.sh` | Termux host | Encrypt full Classic Andronix rootfs and optionally upload to Drive |

## Compatibility and limitations

Only **Classic Andronix** with `~/debian-fs` and `~/start-debian.sh` is implemented. Andronix 2.0 is not supported. Confirm your actual installation layout before running. No script in this change modifies the existing Tier-1 backup script. Unit tests are not proof of live device compatibility.

## Backup procedure

In Debian, with Tier-1 dependencies and rclone configured:

```bash
cd ~/toolz/backup
bash -n pre_snapshot_clean.sh snapshot_andronix_debian.sh
python3 -m pytest -v tests/
./pre_snapshot_clean.sh ~/toolz
exit
```

Exit all Debian PRoot shells and stop VNC. On Termux host, install `gnupg tar rclone python` with `pkg`, run `termux-setup-storage`, and configure `gdrive:` if needed:

```bash
bash /sdcard/ClineOmniRouteBackups/snapshot_andronix_debian.sh --gdrive
rclone lsf gdrive:ClineOmniRouteBackups/AndronixSnapshots/
```

For unattended GPG, set `BACKUP_PASSPHRASE_FILE` to a protected `chmod 600` file outside the rootfs and Android shared storage; store a recovery copy of the secret off-device. Only the two newest local encrypted snapshots are retained. Cloud retention targets matching snapshots older than 60 days.

## Disaster recovery

Install Termux dependencies, configure `gdrive:`, and obtain the snapshot script on the replacement device. Only restore into a **clean** Termux home with no `debian-fs`, `start-debian.sh`, or `debian-binds` already present.

```bash
CONFIRM_RESTORE=RESTORE bash ~/snapshot_andronix_debian.sh --restore-gdrive
./start-debian.sh
```

Then use the **existing** Tier-1 restore procedure as documented by its script, and verify SQLite, OmniRoute API, Cline MCP, and combos. Never run a restore test against the active development rootfs.

## Automated tests

```bash
cd ~/toolz/backup
python3 -m pytest -q tests/test_tier2.py
```

The 12 isolated tests cover syntax, encrypted snapshots, missing rootfs, bad arguments, refusal to overwrite, Tier-1 presence/failure, encrypted round-trip, wrong passphrase, local retention, mocked cloud upload and scoped deletion, and upload failure preservation. Tests use real GPG but mock rclone.

## Pending device acceptance

Validate actual Debian service shutdown and WAL checkpoint; inspect rootfs layout; confirm cloud upload and retrieval using the real remote; test restore on a disposable Termux installation; verify boot and application state; inspect archive metadata, symlink behavior, interruption and low-disk scenarios. Treat the implementation as **development-stage** until those checks pass.
