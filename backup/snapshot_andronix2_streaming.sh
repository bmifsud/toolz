#!/usr/bin/env bash
# Andronix 2.0 Tier-2 snapshot. Run from outer Termux with Debian stopped.
set -euo pipefail
umask 077
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
ROOTFS_DIR="${ROOTFS_DIR:-$HOME/.andronix/distros/debian/rootfs}"
START_SCRIPT="${START_SCRIPT:-$HOME/start-debian.sh}"
SNAP_DIR="${SNAP_DIR:-/sdcard/Andronix/backups}"
REMOTE="${GDRIVE_SNAP_REMOTE:-gdrive:ClineOmniRouteBackups/AndronixSnapshots}"
MODE="${1:---preflight}"
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]] || fail 'Run from outer Termux'
[[ -d "$ROOTFS_DIR" && -f "$START_SCRIPT" ]] || fail 'Rootfs or launcher missing'
[[ "$ROOTFS_DIR" == "$HOME/.andronix/distros/debian/rootfs" ]] || fail 'Unexpected rootfs path'
[[ "$START_SCRIPT" == "$HOME/start-debian.sh" ]] || fail 'Unexpected launcher path'
for c in tar gpg rclone sha256sum python3 flock; do command -v "$c" >/dev/null || fail "Missing $c"; done
if pgrep -f '[p]root.*debian' >/dev/null; then fail 'Stop Debian before snapshot'; fi
[[ ! -L "$ROOTFS_DIR" ]] || fail 'Rootfs must not be symlink'
case "$MODE" in
  --preflight)
    echo "Rootfs: $ROOTFS_DIR"
    du -sh --exclude=sdcard "$ROOTFS_DIR"
    df -h "$HOME" /sdcard 2>/dev/null || df -h "$HOME"
    echo 'Preflight only; no backup created.'
    ;;
  --gdrive|snapshot)
    [[ -n "${BACKUP_PASSPHRASE_FILE:-}" && -f "$BACKUP_PASSPHRASE_FILE" && -r "$BACKUP_PASSPHRASE_FILE" ]] || fail 'Protected BACKUP_PASSPHRASE_FILE required'
    [[ "$(stat -c %a "$BACKUP_PASSPHRASE_FILE")" == 600 ]] || fail 'Passphrase file must be chmod 600'
    [[ ! -L "$BACKUP_PASSPHRASE_FILE" ]] || fail 'Passphrase file must not be a symlink'
    mkdir -p "$SNAP_DIR"
    # Serialize backup producers on this device, including across timestamp collisions.
    # Keep the descriptor open until the script exits.
    exec 9>"$SNAP_DIR/.tier2-snapshot.lock"
    flock -n 9 || fail 'Another Tier-2 snapshot is already running'
    name="andronix-debian-$(date +%Y%m%d_%H%M%S)-$(python3 -c 'import secrets; print(secrets.token_hex(12))').tar.gz.gpg"
    out="$SNAP_DIR/$name"
    [[ ! -e "$out" ]] || fail 'Archive already exists'
    partial="$out.partial"
    trap 'rm -f -- "$partial"' EXIT
    [[ -d "$SNAP_DIR" && -w "$SNAP_DIR" ]] || fail 'Snapshot destination not writable'
    # Archive relative to Termux HOME, retaining Andronix 2.0 directory structure.
    tar -C "$HOME" -czpf - --one-file-system \
      --exclude='.andronix/distros/debian/rootfs/sdcard' \
      --exclude='.andronix/distros/debian/rootfs/proc' \
      --exclude='.andronix/distros/debian/rootfs/sys' \
      --exclude='.andronix/distros/debian/rootfs/dev' \
      --exclude='.andronix/distros/debian/rootfs/tmp' \
      --exclude='.andronix/distros/debian/rootfs/run' \
      --exclude='.andronix/distros/debian/rootfs/var/cache/apt/archives' \
      --exclude='.andronix/distros/debian/rootfs/home/b/.gnupg/S.gpg-agent*' \
      .andronix/distros/debian/rootfs start-debian.sh \
      | gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --symmetric --cipher-algo AES256 --output "$partial"
    [[ -s "$partial" ]] || fail 'Empty archive'
    gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$partial" | python3 "$(dirname "$0")/validate_andronix2_archive.py"
    mv -- "$partial" "$out"
    trap - EXIT
    echo "Locally verified: $out"
    if [[ "$MODE" == --gdrive ]]; then
      # Upload under a non-final name. The local encrypted archive is retained
      # on every failure, including failed verification and publication.
      remote_partial="$REMOTE/$name.uploading"
      remote_final="$REMOTE/$name"
      # An existence probe must distinguish missing objects from API errors.
      # rclone lsjson --stat exits nonzero when the object is missing.
      # Listing the parent is required to fail closed on authorization/network errors.
      remote_listing="$(rclone lsf "$REMOTE" --files-only)" ||
        fail 'Cannot list cloud destination; retain local archive'
      if printf '%s\n' "$remote_listing" | grep -Fxq -- "$name"; then
        fail 'Final cloud object already exists; retain local archive'
      fi
      if printf '%s\n' "$remote_listing" | grep -Fxq -- "$name.uploading"; then
        fail 'Staged cloud object already exists; retain local archive'
      fi
      rclone copyto --immutable "$out" "$remote_partial"
      local_hash="$(sha256sum "$out" | awk '{print $1}')"
      remote_hash="$(rclone cat "$remote_partial" | sha256sum | awk '{print $1}')"
      [[ "$local_hash" == "$remote_hash" ]] || fail 'Staged cloud SHA256 mismatch; retain local archive'
      # rclone moveto is not atomic on all remotes. Verify the final name
      # again before deleting the local copy.
      rclone moveto --immutable "$remote_partial" "$remote_final"
      final_hash="$(rclone cat "$remote_final" | sha256sum | awk '{print $1}')"
      [[ "$local_hash" == "$final_hash" ]] || fail 'Published cloud SHA256 mismatch; retain local archive'
      echo "PASS: Published cloud SHA256 verified: $name"
      if [[ "${TIER2_DELETE_LOCAL_AFTER_VERIFIED_UPLOAD:-0}" == 1 ]]; then
        rm -- "$out"
        echo "PASS: Removed local encrypted archive after verified cloud publication"
      else
        echo "Local encrypted archive retained (set TIER2_DELETE_LOCAL_AFTER_VERIFIED_UPLOAD=1 to opt in to deletion)"
      fi
    fi
    ;;
  --verify-archive)
    [[ $# == 2 ]] || fail 'Usage: script --verify-archive ARCHIVE'
    archive="$2"
    [[ -f "$archive" ]] || fail 'Archive missing'
    [[ -n "${BACKUP_PASSPHRASE_FILE:-}" && -r "$BACKUP_PASSPHRASE_FILE" ]] || fail 'Passphrase file required'
    # Read-only streaming structural validation. Never extract to live rootfs.
    gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$archive" | python3 "$(dirname "$0")/validate_andronix2_archive.py"
    # Archive verification is read-only. Restoration needs a separate safety-reviewed procedure.
    ;;
  *) fail 'Usage: script [--preflight|snapshot|--gdrive|--verify-archive ARCHIVE]' ;;
esac
