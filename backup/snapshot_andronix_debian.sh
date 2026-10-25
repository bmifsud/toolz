#!/usr/bin/env bash
set -euo pipefail
umask 077
SNAP_DIR="${SNAP_DIR:-/sdcard/Andronix/backups}"
REMOTE="${GDRIVE_SNAP_REMOTE:-gdrive:ClineOmniRouteBackups/AndronixSnapshots}"
ROOTFS_DIR="${ROOTFS_DIR:-$HOME/debian-fs}"
START_SCRIPT="${START_SCRIPT:-$HOME/start-debian.sh}"
BINDS_DIR="${BINDS_DIR:-$HOME/debian-binds}"
MODE="${1:-snapshot}"
fail(){ echo "ERROR: $*" >&2; exit 1; }
usage(){ echo "Usage: $0 [snapshot|--gdrive|--restore ARCHIVE|--restore-gdrive]"; }
[[ $# -le 2 ]] || { usage; exit 2; }
case "$MODE" in snapshot|--gdrive) [[ $# -le 1 ]] || { usage; exit 2; };; --restore) [[ $# -eq 2 ]] || { usage; exit 2; };; --restore-gdrive) [[ $# -eq 1 ]] || { usage; exit 2; };; *) usage; exit 2;; esac
if [[ "${ALLOW_TEST_HOST:-0}" != 1 ]]; then
  [[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]] || fail 'Run from Termux host (PREFIX mismatch)'
  [[ -d /data/data/com.termux/files/usr ]] || fail 'Termux installation not found'
  if pgrep -f '[p]root.*debian' >/dev/null 2>&1; then fail 'Debian PRoot appears active'; fi
fi
for cmd in tar gpg rclone; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    if [[ "${AUTO_INSTALL:-0}" == 1 ]]; then pkg update && pkg install -y gnupg tar rclone; else fail "Missing $cmd (install with pkg install gnupg tar rclone)"; fi
  fi
done
mkdir -p "$SNAP_DIR"
RCLONE_CONFIG="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
if [[ "$MODE" == --gdrive || "$MODE" == --restore-gdrive ]]; then
  if ! rclone listremotes | grep -qx 'gdrive:'; then
    for candidate in "$ROOTFS_DIR/root/.config/rclone/rclone.conf" "$ROOTFS_DIR"/home/*/.config/rclone/rclone.conf "$HOME/.andronix/distros/debian/root/.config/rclone/rclone.conf"; do
      if [[ -f "$candidate" && ! -e "$RCLONE_CONFIG" ]]; then
        mkdir -p "$(dirname "$RCLONE_CONFIG")"; cp "$candidate" "$RCLONE_CONFIG"; chmod 600 "$RCLONE_CONFIG"; break
      fi
    done
    rclone listremotes | grep -qx 'gdrive:' || fail 'gdrive: not configured; use rclone config'
  fi
fi
restore_archive(){
  local archive="$1" tmpdir manifest
  [[ -f "$archive" ]] || fail "Archive missing: $archive"
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/tier2-restore.XXXXXX")"
  trap 'rm -rf -- "${RESTORE_TMPDIR:-}"' EXIT
  RESTORE_TMPDIR="$tmpdir"
  gpg --batch --pinentry-mode loopback ${BACKUP_PASSPHRASE_FILE:+--passphrase-file "$BACKUP_PASSPHRASE_FILE"} --decrypt --output "$tmpdir/archive.tar.gz" "$archive" || fail 'Decryption failed'
  manifest="$tmpdir/manifest.txt"
  tar -tzf "$tmpdir/archive.tar.gz" > "$manifest" || fail 'Archive invalid'
  python3 - "$manifest" <<'PY' || fail 'Archive contains unsafe paths'
import sys, pathlib
for raw in pathlib.Path(sys.argv[1]).read_text().splitlines():
    p=pathlib.PurePosixPath(raw)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] not in ('debian-fs','start-debian.sh','debian-binds'):
        sys.exit(1)
PY
  [[ "${CONFIRM_RESTORE:-}" == RESTORE ]] || fail 'Set CONFIRM_RESTORE=RESTORE after backing up existing installation'
  [[ ! -e "$ROOTFS_DIR" && ! -e "$START_SCRIPT" && ! -e "$BINDS_DIR" ]] || fail "Restore requires clean rootfs, launcher and binds destinations"
  tar -xzpf "$tmpdir/archive.tar.gz" -C "$HOME" --no-same-owner --no-same-permissions
  echo 'Restore complete; verify Debian boot and then restore Tier-1 application state.'
}
if [[ "$MODE" == --restore-gdrive ]]; then
  latest="$(rclone lsf "$REMOTE/" --files-only | grep -E '^andronix-debian-[0-9]{8}_[0-9]{6}\.tar\.gz\.gpg$' | LC_ALL=C sort | tail -n 1 || true)"
  [[ -n "$latest" ]] || fail 'No matching remote snapshots'
  rclone copyto "$REMOTE/$latest" "$SNAP_DIR/$latest"
  restore_archive "$SNAP_DIR/$latest"; exit
elif [[ "$MODE" == --restore ]]; then restore_archive "$2"; exit; fi
[[ -d "$ROOTFS_DIR" ]] || fail "Classic Debian rootfs not found: $ROOTFS_DIR (custom Andronix 2.0 layout not supported)"
[[ -f "$START_SCRIPT" ]] || fail "Launcher missing: $START_SCRIPT"
command -v python3 >/dev/null 2>&1 || fail 'python3 required for archive validation'
timestamp="$(date +%Y%m%d_%H%M%S)"
raw="$SNAP_DIR/andronix-debian-$timestamp.tar.gz"
enc="$raw.gpg"
[[ ! -e "$raw" && ! -e "$enc" ]] || fail 'Snapshot filename collision'
trap 'rm -f "$raw"' EXIT
items=("$(basename "$ROOTFS_DIR")" "$(basename "$START_SCRIPT")")
[[ -d "$BINDS_DIR" ]] && items+=("$(basename "$BINDS_DIR")")
[[ "$(dirname "$ROOTFS_DIR")" == "$HOME" && "$(dirname "$START_SCRIPT")" == "$HOME" ]] || fail 'Rootfs and launcher must be immediate HOME children'
tar -czpf "$raw" --exclude='debian-fs/tmp/*' --exclude='debian-fs/proc/*' --exclude='debian-fs/sys/*' --exclude='debian-fs/dev/*' --exclude='debian-fs/var/cache/apt/archives/*.deb' -C "$HOME" "${items[@]}"
tar -tzf "$raw" >/dev/null
if [[ -n "${BACKUP_PASSPHRASE_FILE:-}" ]]; then
  gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --symmetric --cipher-algo AES256 --output "$enc" "$raw"
else
  gpg --symmetric --cipher-algo AES256 --output "$enc" "$raw"
fi
[[ -s "$enc" ]] || fail 'Encrypted output empty'
rm -f "$raw"
if [[ "$MODE" == --gdrive ]]; then
  rclone copyto "$enc" "$REMOTE/$(basename "$enc")" || fail 'Cloud upload failed; encrypted local copy retained'
  rclone delete "$REMOTE/" --min-age 60d --include 'andronix-debian-*.tar.gz.gpg' || echo 'WARNING: Cloud retention failed' >&2
fi
mapfile -t old < <(find "$SNAP_DIR" -maxdepth 1 -type f -name 'andronix-debian-*.tar.gz.gpg' -printf '%f\n' | LC_ALL=C sort -r | tail -n +3)
for f in "${old[@]}"; do rm -f -- "$SNAP_DIR/$f"; done
echo "Snapshot ready: $enc"
