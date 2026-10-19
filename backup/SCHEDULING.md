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


## Noninteractive launcher implementation

The new [`run_debian_noninteractive.sh`](run_debian_noninteractive.sh) uses the same PRoot rootfs location, Debian user, bind mounts and command environment as the repository's interactive `start-debian.sh`, but runs a single command using `bash --noprofile --norc` and exits. The scheduler uses it by default for Tier-1, executing `/home/b/toolz/backup/backup_cline_omniroute.sh backup /home/b/toolz`. Override `DEBIAN_USER` or `TIER1_COMMAND` if your paths differ. It never intentionally launches tmux.

**Termux configuration** (after confirming paths and using a unique off-device-recoverable secret):

```bash
mkdir -p ~/.config/toolz-backup
chmod 700 ~/.config/toolz-backup
# Create a protected passphrase file with a secure editor; do not commit it.
# Example: nano ~/.config/toolz-backup/passphrase
chmod 600 ~/.config/toolz-backup/passphrase
cat > ~/.config/toolz-backup/config <<'EOF'
BACKUP_PASSPHRASE_FILE="$HOME/.config/toolz-backup/passphrase"
ANDRONIX_ROOTFS="$HOME/.andronix/distros/debian/rootfs"
ROOTFS_DIR="$ANDRONIX_ROOTFS"
START_SCRIPT="$HOME/start-debian.sh"
EOF
chmod 600 ~/.config/toolz-backup/config
```

The scheduler sources this file from `$HOME/.config/toolz-backup/config` in both manual and cron runs. It must be mode `600`, not a symlink. **This file is shell code: edit it only yourself, keep it private and never download it from an untrusted source.** Confirm `START_SCRIPT` is a regular file and the rootfs is correct. Test from the Termux host:

```bash
bash ~/toolz/backup/run_scheduled_backup.sh tier1
```

Logs are under `~/.local/state/toolz-backup/`. Tier-1 now checks decrypted tar readability and streams the encrypted cloud object through SHA-256 to compare against the local archive. This uses cloud bandwidth proportional to the backup size.

**Caution:** The Tier-2 snapshot script currently requires the rootfs and launcher to be immediate children of Termux `$HOME` and archives using fixed Classic Andronix names. Simply setting `ROOTFS_DIR` to `~/.andronix/distros/debian/rootfs` is **not sufficient** for Tier-2. Keep Tier-2 cron disabled until a matching snapshot/restore layout is implemented and tested; do not try it against your live rootfs. Tier-2 readiness marker and active-PRoot safety restrictions still apply.

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
