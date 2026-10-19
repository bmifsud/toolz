#!/usr/bin/env bash
# Install Tier-1 catch-up without modifying the existing backup schedule.
set -euo pipefail
[[ -n "${PREFIX:-}" && -d "$PREFIX" ]] || { echo 'Run in outer Termux' >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v crontab >/dev/null || { echo 'Install cronie first' >&2; exit 1; }
command -v flock >/dev/null || { echo 'Install util-linux first' >&2; exit 1; }
mkdir -p "$HOME/.termux/boot"
# This boot hook requires the separate Termux:Boot Android app.
boot="$HOME/.termux/boot/20-toolz-backup-catchup"
cat > "$boot" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
export PATH="/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets:\$PATH"
pgrep -x crond >/dev/null 2>&1 || crond
"$HERE/check_missed_backups.sh" >/dev/null 2>&1 &
EOF
chmod 700 "$boot"
line="*/15 * * * * $PREFIX/bin/bash \"$HERE/check_missed_backups.sh\""
current="$(crontab -l 2>/dev/null || true)"
if ! grep -Fq 'check_missed_backups.sh' <<<"$current"; then
  { printf '%s\n' "$current"; printf '%s\n' "$line"; } | crontab -
fi
echo 'Installed Tier-1 catch-up: boot hook + 15-minute watchdog.'
echo 'Install/open Termux:Boot once to enable Android boot execution.'
echo 'Tier-2 schedule unchanged.'
