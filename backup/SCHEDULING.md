# Scheduled backups (Termux cron)

**Development-stage scheduling.** The existing Tier-1 script is unchanged. Do not enable unattended backups until a dry run, cloud verification and disposable restore succeed.

## Schedule (device local time)

- Tier-1 hot state backup: 09:00 and 21:00 daily
- Tier-2 full rootfs snapshot: 03:00 Monday, Wednesday and Friday

## Setup

In the Termux host shell:

```bash
pkg install cronie gnupg tar rclone python coreutils util-linux
cd ~/toolz/backup
chmod +x install_backup_cron.sh run_scheduled_backup.sh
```

Configure the launcher used to run the existing Debian Tier-1 backup from Termux. The correct launcher depends on your Andronix installation; do **not** guess it. Export `TIER1_COMMAND` to a previously tested command that launches Debian, executes `backup_cline_omniroute.sh backup /path/to/workspace`, and exits. Set `BACKUP_PASSPHRASE_FILE` to a mode-600 file containing the backup password; set `TIER1_LOCAL_DIR` if the Tier-1 output is not `/sdcard/ClineOmniRouteBackups`.

**Important:** Cron does not inherit interactive shell exports. Provide these variables through a restricted wrapper or controlled crond environment. Never store the passphrase itself in the crontab. The existing Tier-1 script accepts `BACKUP_PASSPHRASE` and has broad cloud pruning; review that behavior before enabling automatic runs.

After confirming the environment and a manual run:

```bash
bash install_backup_cron.sh
crond
crontab -l
```

The installer preserves unrelated crontab entries and replaces only its own marked section. Cron will not run reliably if Android kills Termux; configure Termux:Boot and disable aggressive battery restrictions where appropriate. Scheduled tasks missed while the device is asleep/off are not automatically caught up.


## Confirmed launcher: `~/start-debian.sh`

The interactive Debian launcher is `~/start-debian.sh` in the outer Termux shell. The repository implementation at [`scripts/start-debian.sh`](../scripts/start-debian.sh) ends by launching `proot ... /bin/bash -l`; its `--no-attach` flag only affects AI workspace attachment and **does not execute a supplied backup command or exit automatically**. **Do not set `TIER1_COMMAND="~/start-debian.sh --no-attach"`**: this would start an interactive session, potentially hang cron, and interfere with Tier-2.

The repository launcher uses a configurable `ANDRONIX_ROOTFS` (default `~/.andronix/distros/debian/rootfs`), whereas the Tier-2 snapshot script defaults to `~/debian-fs`. Before attempting Tier-2, explicitly confirm the actual rootfs location and set `ROOTFS_DIR` appropriately. Do not assume these defaults are interchangeable.

For unattended Tier-1, a separate **tested noninteractive PRoot command wrapper** is still required. It must use the same rootfs/bind mounts and Debian user as `start-debian.sh`, bypass the tmux auto-launch, invoke the Tier-1 script once, propagate its exit code, and terminate. The cron runner's `TIER1_COMMAND` should then point to that wrapper. No automatic launcher wrapper has yet been validated against your device.

## Tier-2 safety gate

A rootfs snapshot requires all Debian PRoot sessions to have exited. The runner **skips**, rather than kills, an active session. The operator must run `pre_snapshot_clean.sh` in Debian, exit all PRoot sessions, and then create a readiness marker:

```bash
mkdir -p ~/.local/state/toolz-backup
touch ~/.local/state/toolz-backup/tier2-ready
```

The marker expires after two hours and is removed after a verified run. **Therefore Tier-2 is not yet fully unattended**: a reliable device-specific stop/checkpoint/exit mechanism is required to safely automate preflight. Do not automatically create the marker from cron without those checks.

## Verification and logs

The runner uses `flock` to prevent overlap, decrypts each archive and lists its tar entries to verify GPG and tar integrity, and calls `rclone check` to compare the local encrypted archive against its remote counterpart. Review the exact `rclone check` behavior with your installed rclone version before deployment; a remote size match alone is not a cryptographic integrity guarantee. Logs are written to `~/.local/state/toolz-backup/`. A failed run exits nonzero, but cron itself does not notify you; add an explicit notification or monitoring system for unattended failure reporting.

## Acceptance tests

Test the runner manually with the actual launcher, check logs and remote files, simulate missing rclone credentials, wrong passphrase, concurrent runs, and an active PRoot session, then perform a disposable restore. A successful archive check is not a substitute for a full restore drill.
