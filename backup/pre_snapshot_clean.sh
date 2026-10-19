#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${1:-$(pwd)}"
OMNI_DB="${OMNI_DB:-$HOME/.omniroute/storage.sqlite}"
STAGE_DIR="${STAGE_DIR:-/sdcard/ClineOmniRouteBackups}"
if [[ -x "$SCRIPT_DIR/backup_cline_omniroute.sh" ]]; then
  "$SCRIPT_DIR/backup_cline_omniroute.sh" backup "$WORKSPACE_DIR"
elif [[ -x "$HOME/backup_cline_omniroute.sh" ]]; then
  "$HOME/backup_cline_omniroute.sh" backup "$WORKSPACE_DIR"
else
  echo 'ERROR: Tier-1 backup script missing; refusing snapshot preparation' >&2; exit 1
fi
if command -v systemctl >/dev/null 2>&1; then systemctl --user stop omniroute.service 2>/dev/null || true; fi
if command -v pgrep >/dev/null 2>&1 && pgrep -f '[o]mniroute' >/dev/null 2>&1; then
  echo 'ERROR: OmniRoute still running; stop it manually before snapshot' >&2; exit 1
fi
if [[ -f "$OMNI_DB" ]]; then
  if ! command -v sqlite3 >/dev/null 2>&1; then echo 'ERROR: sqlite3 required for WAL checkpoint' >&2; exit 1; fi
  sqlite3 "$OMNI_DB" 'PRAGMA wal_checkpoint(TRUNCATE);' >/dev/null
  result="$(sqlite3 "$OMNI_DB" 'PRAGMA quick_check;')"
  [[ "$result" == ok ]] || { echo "ERROR: SQLite quick_check: $result" >&2; exit 1; }
fi
if command -v apt-get >/dev/null 2>&1; then
  if [[ "${SKIP_APT_CLEAN:-0}" != 1 ]]; then
    if [[ "$EUID" -eq 0 ]]; then apt-get clean; elif command -v sudo >/dev/null 2>&1; then sudo apt-get clean; fi
  fi
fi
# Do not wipe /tmp or application logs: development may still rely on them.
if [[ -d /sdcard && -w /sdcard || "${ALLOW_CUSTOM_STAGE:-0}" == 1 ]]; then
  mkdir -p "$STAGE_DIR"
  cp "$SCRIPT_DIR/snapshot_andronix_debian.sh" "$STAGE_DIR/snapshot_andronix_debian.sh"
  chmod 700 "$STAGE_DIR/snapshot_andronix_debian.sh" 2>/dev/null || true
fi
echo 'Pre-snapshot checks passed. Exit every Debian/PRoot session before Termux snapshot.'
