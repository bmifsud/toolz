#!/usr/bin/env bash
# Opt-in, read-only Termux health report via GitHub Issues.
# No remote command execution, no credentials or backup logs are uploaded.
set -euo pipefail
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || { echo "Run in outer Termux" >&2; exit 1; }
command -v gh >/dev/null || { echo "Install GitHub CLI: pkg install gh" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Authenticate first with: gh auth login" >&2; exit 1; }
REPO="${TERMUX_BRIDGE_REPO:-bmifsud/toolz}"
HOOK="$HOME/.termux/boot/20-toolz-backup-catchup"
STATE="$HOME/.local/state/toolz-backup"
status=no; [[ -f "$HOOK" ]] && status=yes
syntax=missing
if [[ -f "$HOOK" ]]; then
  if bash -n "$HOOK" >/dev/null 2>&1; then syntax=pass; else syntax=fail; fi
fi
executable=no; [[ -x "$HOOK" ]] && executable=yes
cron=stopped; pgrep -x crond >/dev/null 2>&1 && cron=running
log=absent
if [[ -f "$STATE/boot.log" ]]; then
  log=present
fi
watchdog=no
crontab -l 2>/dev/null | grep -Fq 'check_missed_backups.sh' && watchdog=yes || true
# Deliberately excludes log contents, device identifiers, paths, tokens, and secrets.
body="$(printf 'Read-only Termux diagnostics (user-triggered)\n\n- Boot hook present: %s\n- Boot hook executable: %s\n- Boot hook syntax: %s\n- Boot log exists: %s\n- crond: %s\n- Catch-up cron entry: %s\n- Tier-2: not modified\n' "$status" "$executable" "$syntax" "$log" "$cron" "$watchdog")"
echo "This will create a GitHub issue in $REPO with:"
printf '%s\n' "$body"
read -r -p "Publish these diagnostics? [y/N] " answer
[[ "$answer" == [yY] ]] || { echo "Cancelled"; exit 0; }
gh issue create --repo "$REPO" --title "Termux health report $(date +%Y-%m-%d)" --body "$body"
