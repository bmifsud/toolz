#!/usr/bin/env bash
set -euo pipefail
umask 077
MODE="${1:-}"
[[ "$MODE" == tier1 || "$MODE" == tier2 ]] || { echo 'Usage: run_scheduled_backup.sh tier1|tier2' >&2; exit 2; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Restricted Termux-only configuration; cron does not inherit shell exports.
CONFIG="${BACKUP_CONFIG_FILE:-$HOME/.config/toolz-backup/config}"
if [[ -f "$CONFIG" ]]; then
  [[ ! -L "$CONFIG" && "$(stat -c %a "$CONFIG")" == 600 ]] || { echo "Config must be a regular chmod 600 file" >&2; exit 1; }
  source "$CONFIG"
fi
export ROOTFS_DIR="${ROOTFS_DIR:-${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}}"
export START_SCRIPT="${START_SCRIPT:-$HOME/start-debian.sh}"
STATE="$HOME/.local/state/toolz-backup"; mkdir -p "$STATE"
exec 9>"$STATE/backup.lock"
flock -n 9 || { echo 'Another backup is running; skipping'; command -v termux-notification >/dev/null 2>&1 && termux-notification --id 6103 --title "Backup skipped ($MODE)" --content "Another backup is running" >/dev/null 2>&1 || true; exit 75; }
LOG="$STATE/$MODE-$(date +%Y%m%d_%H%M%S).log"
exec >>"$LOG" 2>&1
notify(){
 local title="$1" message="$2"
 if command -v termux-notification >/dev/null 2>&1; then
   termux-notification --id "$([[ "$MODE" == tier1 ]] && echo 6101 || echo 6102)" --title "$title" --content "$message" >/dev/null 2>&1 || true
 fi
}
on_exit(){
 local status="$1"
 trap - EXIT
 if [[ "$status" == 0 ]]; then
   notify "Backup SUCCESS ($MODE)" "Backup completed and verified on Google Drive. Log: $LOG"
 elif [[ "$status" == 75 ]]; then
   notify "Backup SKIPPED ($MODE)" "Safe-skip condition; check log: $LOG"
 else
   notify "Backup FAILED ($MODE)" "Exit code $status; check log: $LOG"
 fi
 exit "$status"
}
trap 'on_exit "$?"' EXIT
echo "BEGIN $MODE $(date -Is)"
: "${BACKUP_PASSPHRASE_FILE:?Set BACKUP_PASSPHRASE_FILE to protected file containing GPG password}"
[[ -r "$BACKUP_PASSPHRASE_FILE" ]] || { echo 'Passphrase file not readable' >&2; exit 1; }
command -v rclone >/dev/null || exit 1
command -v gzip >/dev/null || { echo "Missing gzip: run pkg install gzip" >&2; exit 1; }
verify(){
 local file="$1" remote="$2" dir name
 [[ -s "$file" ]] || { echo "Missing backup: $file" >&2; return 1; }
 gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$file" 2>/dev/null | tar -tzf - >/dev/null
 name="$(basename "$file")"
 # rclone check uses checksums when supported, otherwise sizes; stronger than just listing.
 # Full streamed SHA-256 comparison (not just matching file size).
 local localhash remotehash
 localhash="$(sha256sum "$file" | awk '{print $1}')"
 remotehash="$(rclone cat "$remote/$name" | sha256sum | awk '{print $1}')"
 [[ "$localhash" == "$remotehash" ]] || { echo "Remote SHA-256 mismatch: $name" >&2; return 1; }
 echo "VERIFIED: $name"
}
if [[ "$MODE" == tier1 ]]; then
 # Tier-1's existing script accepts BACKUP_PASSPHRASE; avoid printing the secret.
 export BACKUP_PASSPHRASE="$(cat "$BACKUP_PASSPHRASE_FILE")"
 [[ -n "$BACKUP_PASSPHRASE" ]] || exit 1
 # TIER1_COMMAND is user configured because Andronix launcher paths differ.
 if [[ -n "${TIER1_COMMAND:-}" ]]; then
   bash -lc "$TIER1_COMMAND"
 else
   "$HERE/run_debian_noninteractive.sh" "/home/${DEBIAN_USER:-b}/toolz/backup/backup_cline_omniroute.sh" backup "/home/${DEBIAN_USER:-b}/toolz"
 fi
 unset BACKUP_PASSPHRASE
 if [ -d "/mnt/shared" ] && [ -w "/mnt/shared" ]; then
   DEFAULT_OUT="/mnt/shared/ClineOmniRouteBackups"
 elif [ -d "/sdcard" ] && [ -w "/sdcard" ]; then
   DEFAULT_OUT="/sdcard/ClineOmniRouteBackups"
 else
   DEFAULT_OUT="$HOME/ClineOmniRouteBackups"
 fi
 localdir="${TIER1_LOCAL_DIR:-${ANDROID_OUT:-$DEFAULT_OUT}}"
 latest="$(find "$localdir" -maxdepth 1 -type f -name 'cline_omniroute_backup_*.tar.gz.gpg' | LC_ALL=C sort | tail -1)"
 [[ -n "$latest" ]] || exit 1
 verify "$latest" 'gdrive:ClineOmniRouteBackups'
 "$HERE/tier1_retention.sh" --apply
else
 # Full rootfs cannot be snapshotted consistently with active PRoot sessions.
 if pgrep -f '[p]root.*debian' >/dev/null 2>&1; then
   echo 'SKIPPED: active Debian PRoot session; will retry at next scheduled window'; exit 75
 fi
 # A separate, successful pre_snapshot_clean.sh run must have occurred before this job.
 # Require a freshness marker created by the operator after a verified preflight.
 marker="${TIER2_READY_MARKER:-$STATE/tier2-ready}"
 [[ -f "$marker" ]] || { echo 'SKIPPED: no Tier-2 preflight readiness marker'; exit 75; }
 now="$(date +%s)"; stamp="$(stat -c %Y "$marker")"
 (( now-stamp <= 7200 )) || { echo 'SKIPPED: preflight marker older than two hours'; exit 75; }
 # The streaming script needs the filename of THIS run, not a potentially stale archive.
 export BACKUP_PASSPHRASE_FILE
 export SNAP_DIR="${SNAP_DIR:-/sdcard/Andronix/backups}"
 export GDRIVE_SNAP_REMOTE="${GDRIVE_SNAP_REMOTE:-gdrive:ClineOmniRouteBackups/AndronixSnapshots}"
 # Record an isolated list before starting; the script prints the completed output path.
 snapshot_log="$(mktemp "$STATE/tier2-snapshot.XXXXXXXX")"
 trap 'status=$?; rm -f -- "$snapshot_log"; on_exit "$status"' EXIT
 "$HERE/snapshot_andronix2_streaming.sh" --gdrive | tee "$snapshot_log"
 latest="$(sed -n 's/^Locally verified: //p' "$snapshot_log" | tail -1)"
 [[ -n "$latest" && -f "$latest" ]] || { echo 'No completed Tier-2 archive from current run' >&2; exit 1; }
 "$HERE/snapshot_andronix2_streaming.sh" --verify-archive "$latest"
 verify "$latest" "$GDRIVE_SNAP_REMOTE"
 rm -f -- "$snapshot_log"
 trap 'on_exit "$?"' EXIT
 rm -f "$marker"
fi
echo "SUCCESS $MODE $(date -Is)"
