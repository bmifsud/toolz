#!/usr/bin/env bash
# Install isolated Termux crond entries without replacing unrelated crontab entries.
set -euo pipefail
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]] || { echo 'Run in Termux host' >&2; exit 1; }
command -v crontab >/dev/null || { echo 'Install cronie: pkg install cronie' >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.local/state/toolz-backup"
CURRENT="$(mktemp)"; trap 'rm -f "$CURRENT"' EXIT
crontab -l > "$CURRENT" 2>/dev/null || true
sed -i '/^# BEGIN TOOLZ BACKUP$/,/^# END TOOLZ BACKUP$/d' "$CURRENT"
cat >> "$CURRENT" <<EOF
# BEGIN TOOLZ BACKUP
0 9,21 * * * /data/data/com.termux/files/usr/bin/bash "$HERE/run_scheduled_backup.sh" tier1
0 3 * * 1,3,5 /data/data/com.termux/files/usr/bin/bash "$HERE/run_scheduled_backup.sh" tier2
# END TOOLZ BACKUP
EOF
crontab "$CURRENT"
echo 'Cron entries installed. Start crond using: crond; arrange Termux:Boot and battery-exemption separately.'
