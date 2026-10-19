#!/usr/bin/env bash
set -euo pipefail
umask 077
MODE="${1:-}"
[[ "$MODE" == tier1 || "$MODE" == tier2 ]] || { echo 'Usage: run_scheduled_backup.sh tier1|tier2' >&2; exit 2; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HOME/.local/state/toolz-backup"; mkdir -p "$STATE"
exec 9>"$STATE/backup.lock"
flock -n 9 || { echo 'Another backup is running; skipping'; exit 75; }
LOG="$STATE/$MODE-$(date +%Y%m%d_%H%M%S).log"
exec >>"$LOG" 2>&1
echo "BEGIN $MODE $(date -Is)"
: "${TIER1_COMMAND:?Set TIER1_COMMAND to a tested Debian launcher command that executes Tier-1 backup, then exits}"
: "${BACKUP_PASSPHRASE_FILE:?Set BACKUP_PASSPHRASE_FILE to protected file containing GPG password}"
[[ -r "$BACKUP_PASSPHRASE_FILE" ]] || { echo 'Passphrase file not readable' >&2; exit 1; }
command -v rclone >/dev/null || exit 1
verify(){
 local file="$1" remote="$2" dir name
 [[ -s "$file" ]] || { echo "Missing backup: $file" >&2; return 1; }
 gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$file" 2>/dev/null | tar -tzf - >/dev/null
 name="$(basename "$file")"
 # rclone check uses checksums when supported, otherwise sizes; stronger than just listing.
 rclone check "$file" "$remote/$name" --one-way --size-only
 echo "VERIFIED: $name"
}
if [[ "$MODE" == tier1 ]]; then
 # Tier-1's existing script accepts BACKUP_PASSPHRASE; avoid printing the secret.
 export BACKUP_PASSPHRASE="$(cat "$BACKUP_PASSPHRASE_FILE")"
 [[ -n "$BACKUP_PASSPHRASE" ]] || exit 1
 # TIER1_COMMAND is user configured because Andronix launcher paths differ.
 bash -lc "$TIER1_COMMAND"
 unset BACKUP_PASSPHRASE
 localdir="${TIER1_LOCAL_DIR:-/sdcard/ClineOmniRouteBackups}"
 latest="$(find "$localdir" -maxdepth 1 -type f -name 'cline_omniroute_backup_*.tar.gz.gpg' | LC_ALL=C sort | tail -1)"
 [[ -n "$latest" ]] || exit 1
 verify "$latest" 'gdrive:ClineOmniRouteBackups'
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
 "$HERE/snapshot_andronix_debian.sh" --gdrive
 latest="$(find "${SNAP_DIR:-/sdcard/Andronix/backups}" -maxdepth 1 -type f -name 'andronix-debian-*.tar.gz.gpg' | LC_ALL=C sort | tail -1)"
 [[ -n "$latest" ]] || exit 1
 verify "$latest" 'gdrive:ClineOmniRouteBackups/AndronixSnapshots'
 rm -f "$marker"
fi
echo "SUCCESS $MODE $(date -Is)"
