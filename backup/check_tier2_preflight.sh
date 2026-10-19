#!/usr/bin/env bash
# Read-only Tier-2 preflight for the user's actual Andronix layout.
set -euo pipefail
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]] || { echo "Run in outer Termux" >&2; exit 1; }
ROOTFS="${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}"
LAUNCHER="${START_SCRIPT:-$HOME/start-debian.sh}"
CONFIG="${BACKUP_CONFIG_FILE:-$HOME/.config/toolz-backup/config}"
if [[ -f "$CONFIG" ]]; then
  [[ ! -L "$CONFIG" && "$(stat -c %a "$CONFIG")" == 600 ]] || { echo "FAIL: unsafe config permissions" >&2; exit 1; }
  source "$CONFIG"
fi
ROOTFS="${ROOTFS_DIR:-${ANDRONIX_ROOTFS:-$ROOTFS}}"
LAUNCHER="${START_SCRIPT:-$LAUNCHER}"
status=0
check(){ if "$@" >/dev/null 2>&1; then echo "PASS: $*"; else echo "FAIL: $*"; status=1; fi; }
echo "Tier-2 READ-ONLY preflight; no snapshots or restores performed"
check test -d "$ROOTFS"
check test -f "$LAUNCHER"
check command -v tar
check command -v gpg
check command -v rclone
check command -v python3
check command -v flock
check test -s "${BACKUP_PASSPHRASE_FILE:-/nonexistent}"
if pgrep -f '[p]root.*debian' >/dev/null 2>&1; then
 echo "BLOCKED: Debian PRoot appears active. Never snapshot while active."
 status=1
else echo "PASS: no matching Debian PRoot process"; fi
if [[ "$ROOTFS" == "$HOME/debian-fs" ]]; then
 echo "PASS: classic Tier-2 rootfs layout"
else
 echo "BLOCKED: current snapshot/restore script expects classic HOME/debian-fs layout; actual rootfs is $ROOTFS"
 status=1
fi
if [[ "$status" -ne 0 ]]; then
 echo "NOT READY: do not run Tier-2 snapshot or restore yet"
else echo "Preflight checks passed; manual restore validation still required"; fi
exit "$status"
