# Missed Tier-1 backup recovery (Termux)

Run in **outer Termux**:

```bash
pkg install cronie util-linux rclone termux-api
cd ~/toolz
bash backup/install_catchup.sh
crond
bash backup/check_missed_backups.sh
```

Install the separate **Termux:Boot** Android app and launch it once. Allow background execution and disable battery optimization for Termux and Termux:Boot as appropriate. Android may still delay background execution.

The existing 09:00/21:00 Tier-1 cron schedule is preserved. The new watchdog runs every 15 minutes while cron is alive; the boot hook starts cron and checks for missed backups on reboot. An offline or suspended device cannot run scripts; recovery occurs when Android permits Termux to run and Google Drive is reachable. If the phone reconnects while cron is running, the next watchdog check catches up.

Only one catch-up is run for missed slots, not one per slot. A log with `SUCCESS tier1` is required; upload alone does not count. Failed attempts are rate-limited to 30 minutes. The existing scheduler performs encryption, upload, verification and result notifications. Tier-2 is not changed or enabled.

**Caution:** local changes to `backup/run_debian_noninteractive.sh` should be preserved; do not reset or force-checkout the working tree. This installer adds only a new cron line and a dedicated boot hook. To uninstall, remove that cron line and `~/.termux/boot/20-toolz-backup-catchup`.
