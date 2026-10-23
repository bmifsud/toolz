#!/usr/bin/env bash
# Install Tier-1 catch-up without modifying the existing backup schedule.
set -euo pipefail
[[ -n "${PREFIX:-}" && -d "$PREFIX" ]] || { echo 'Run in outer Termux' >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v crontab >/dev/null || { echo 'Install cronie first' >&2; exit 1; }
command -v flock >/dev/null || { echo 'Install util-linux first' >&2; exit 1; }
mkdir -p "$HOME/.termux/boot" "$HOME/.local/state/toolz-backup"
# This boot hook requires the separate Termux:Boot Android app.
boot="$HOME/.termux/boot/20-toolz-backup-catchup"
backup_dir="$HOME/.local/state/toolz-backup/boot-hook-backups"
mkdir -p "$backup_dir"
# Termux:Boot executes executable files in ~/.termux/boot, including backup copies.
# Preserve prior copies outside that directory and migrate old installer backups.
for old in "$HOME/.termux/boot/20-toolz-backup-catchup.bak."*; do
  [[ -f "$old" ]] || continue
  mv -n "$old" "$backup_dir/"
done
if [[ -f "$boot" ]]; then cp -p "$boot" "$backup_dir/20-toolz-backup-catchup.bak.$(date +%Y%m%d_%H%M%S)"; fi
cat > "$boot" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
export PATH="/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets:\$PATH"
mkdir -p "\$HOME/.local/state/toolz-backup"
echo "\$(date -Is) Termux:Boot hook executed" >> "\$HOME/.local/state/toolz-backup/boot.log"
pgrep -x crond >/dev/null 2>&1 || crond
/data/data/com.termux/files/usr/bin/bash "$HERE/check_missed_backups.sh" >> "\$HOME/.local/state/toolz-backup/boot.log" 2>&1 &
EOF
chmod 700 "$boot"
bash -n "$boot"
line="*/15 * * * * $PREFIX/bin/bash \"$HERE/check_missed_backups.sh\""
current="$(crontab -l 2>/dev/null || true)"
if ! grep -Fq 'check_missed_backups.sh' <<<"$current"; then
  { printf '%s\n' "$current"; printf '%s\n' "$line"; } | crontab -
fi
echo 'Installed Tier-1 catch-up: boot hook + 15-minute watchdog.'
echo 'Install/open Termux:Boot once to enable Android boot execution.'
echo 'Tier-2 schedule unchanged.'
