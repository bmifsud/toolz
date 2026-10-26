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
for c in tar gpg rclone sha256sum python3; do command -v "$c" >/dev/null || fail "Missing $c"; done
if pgrep -f '[p]root.*debian' >/dev/null; then fail 'Stop Debian before snapshot'; fi
[[ ! -L "$ROOTFS_DIR" ]] || fail 'Rootfs must not be symlink'
case "$MODE" in
  --preflight)
    echo "Rootfs: $ROOTFS_DIR"
    du -sh --exclude=sdcard "$ROOTFS_DIR"
    df -h "$HOME" "$SNAP_DIR" 2>/dev/null || df -h "$HOME"
    echo 'Preflight only; no backup created.'
    ;;
  --gdrive|snapshot)
    [[ -n "${BACKUP_PASSPHRASE_FILE:-}" && -r "$BACKUP_PASSPHRASE_FILE" ]] || fail 'Protected BACKUP_PASSPHRASE_FILE required'
    mkdir -p "$SNAP_DIR"
    name="andronix-debian-$(date +%Y%m%d_%H%M%S).tar.gz.gpg"
    out="$SNAP_DIR/$name"
    [[ ! -e "$out" ]] || fail 'Archive already exists'
    partial="$out.partial"
    trap 'rm -f -- "$partial"' EXIT
    # Archive relative to Termux HOME, retaining Andronix 2.0 directory structure.
    tar -C "$HOME" -czpf - --one-file-system \
      --exclude='./.andronix/distros/debian/rootfs/sdcard' \
      --exclude='./.andronix/distros/debian/rootfs/proc' \
      --exclude='./.andronix/distros/debian/rootfs/sys' \
      --exclude='./.andronix/distros/debian/rootfs/dev' \
      --exclude='./.andronix/distros/debian/rootfs/tmp' \
      --exclude='./.andronix/distros/debian/rootfs/run' \
      --exclude='./.andronix/distros/debian/rootfs/var/cache/apt/archives' \
      .andronix/distros/debian/rootfs start-debian.sh \
      | gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --symmetric --cipher-algo AES256 --output "$partial"
    [[ -s "$partial" ]] || fail 'Empty archive'
    gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$partial" | tar -tzf - >/dev/null
    mv -- "$partial" "$out"
    trap - EXIT
    echo "Locally verified: $out"
    if [[ "$MODE" == --gdrive ]]; then
      rclone copyto "$out" "$REMOTE/$name"
      local_hash="$(sha256sum "$out" | awk '{print $1}')"
      remote_hash="$(rclone cat "$REMOTE/$name" | sha256sum | awk '{print $1}')"
      [[ "$local_hash" == "$remote_hash" ]] || fail 'Cloud SHA256 mismatch; retain local archive'
      echo "Cloud SHA256 verified: $name"
    fi
    ;;
  --verify-restore)
    [[ $# == 3 ]] || fail 'Usage: script --verify-restore ARCHIVE EMPTY_DIRECTORY'
    archive="$2"; destination="$3"
    [[ -f "$archive" && -d "$destination" ]] || fail 'Archive or destination missing'
    [[ -z "$(ls -A "$destination")" ]] || fail 'Destination must be empty'
    [[ "$destination" != "$HOME" && "$destination" != / && "$destination" != "$ROOTFS_DIR" ]] || fail 'Unsafe destination'
    [[ -n "${BACKUP_PASSPHRASE_FILE:-}" && -r "$BACKUP_PASSPHRASE_FILE" ]] || fail 'Passphrase file required'
    # Only allow known paths; reject traversal and links before extracting.
    manifest="$(mktemp)"
    trap 'rm -f "$manifest"' EXIT
    gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$archive" | tar -tzf - > "$manifest"
    python3 - "$manifest" <<'PY'
import pathlib,sys
for raw in pathlib.Path(sys.argv[1]).read_text().splitlines():
    p=pathlib.PurePosixPath(raw)
    if p.is_absolute() or '..' in p.parts or not (raw.startswith('.andronix/distros/debian/rootfs/') or raw == '.andronix/distros/debian/rootfs' or raw == 'start-debian.sh'):
        sys.exit('Unsafe archive path: '+raw)
PY
    # Do not extract arbitrary archives: verify symlinks/hardlinks separately before implementing extraction.
    echo 'Archive decrypts and paths validated. Extraction intentionally disabled pending link safety review.'
    ;;
  *) fail 'Usage: script [--preflight|snapshot|--gdrive|--verify-restore ARCHIVE EMPTY_DIRECTORY]' ;;
esac
