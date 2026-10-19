#!/usr/bin/env bash
# Termux Tier-1 catch-up: called at boot and periodically by cron.
set -euo pipefail
umask 077
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HOME/.local/state/toolz-backup"
mkdir -p "$STATE"
exec 8>"$STATE/catchup.lock"
flock -n 8 || exit 0
# Tier-2 is intentionally not part of catch-up.
now="$(date +%s)"
today="$(date +%F)"
yesterday="$(date -d 'yesterday' +%F)"
due=0
for day in "$yesterday" "$today"; do
  for hour in 09 21; do
    slot="$(date -d "$day $hour:00:00" +%s)"
    if ((slot <= now && slot > due)); then due="$slot"; fi
  done
done
((due > 0)) || exit 0
# Only verified SUCCESS lines count, never mere uploads.
last=0
shopt -s nullglob
for log in "$STATE"/tier1-*.log; do
  if grep -q '^SUCCESS tier1 ' "$log"; then
    stamp="${log##*/tier1-}"
    stamp="${stamp%.log}"
    if [[ "$stamp" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
      t="$(date -d "${stamp:0:4}-${stamp:4:2}-${stamp:6:2} ${stamp:9:2}:${stamp:11:2}:${stamp:13:2}" +%s 2>/dev/null || echo 0)"
      ((t > last)) && last="$t"
    fi
  fi
done
((last < due)) || exit 0
# Limit failed retries to once every 30 minutes.
attempt="$STATE/tier1-catchup-last-attempt"
if [[ -f "$attempt" ]]; then
  prev="$(cat "$attempt" 2>/dev/null || echo 0)"
  [[ "$prev" =~ ^[0-9]+$ ]] || prev=0
  ((now - prev >= 1800)) || exit 0
fi
# Don't start if the scheduler is already running a backup.
exec 7>"$STATE/backup.lock"
flock -n 7 || exit 0
flock -u 7
# Connectivity probe must succeed; do not run offline.
command -v rclone >/dev/null || exit 0
if ! rclone lsf 'gdrive:ClineOmniRouteBackups' --max-depth 1 >/dev/null 2>&1; then
  exit 0
fi
printf '%s\n' "$now" > "$attempt"
if command -v termux-notification >/dev/null 2>&1; then
  termux-notification --id 6104 --title 'Backup catch-up started' --content 'Missed Tier-1 backup detected; starting recovery.' >/dev/null 2>&1 || true
fi
# Scheduler owns the main lock, verification, and success/failure notifications.
"$HERE/run_scheduled_backup.sh" tier1
