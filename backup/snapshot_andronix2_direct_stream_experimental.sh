#!/usr/bin/env bash
# EXPERIMENTAL: no local full-size archive. Never invoke from cron.
set -euo pipefail
umask 077
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]] || fail 'Run from outer Termux'
[[ "${1:-}" == --preflight || "${1:-}" == --gdrive-stream ]] || fail 'Usage: script --preflight|--gdrive-stream'
ROOTFS="$HOME/.andronix/distros/debian/rootfs"
LAUNCHER="$HOME/start-debian.sh"
REMOTE="${GDRIVE_SNAP_REMOTE:-gdrive:ClineOmniRouteBackups/AndronixSnapshots}"
[[ -d "$ROOTFS" && ! -L "$ROOTFS" && -f "$LAUNCHER" ]] || fail 'Expected Debian rootfs and launcher missing'
for cmd in tar gpg rclone python3 sha256sum flock grep pgrep; do command -v "$cmd" >/dev/null || fail "Missing $cmd"; done
[[ -s "$ROOTFS/etc/passwd" && -s "$ROOTFS/etc/os-release" ]] || fail "Debian identity files missing or empty"
if pgrep -f '[p]root.*debian' >/dev/null; then fail 'Stop Debian before backup'; fi
if [[ "${1:-}" == --preflight ]]; then
  echo "EXPERIMENTAL: direct streaming not yet recovery-approved"
  du -sh --exclude=sdcard "$ROOTFS"
  rclone about "${REMOTE%%:*}:" || fail 'Remote unavailable'
  exit 0
fi
[[ "${TIER2_EXPERIMENTAL_STREAM_CONFIRM:-}" == 'I_UNDERSTAND_EXPERIMENTAL' ]] ||
  fail 'Explicit experimental confirmation required'
PASSFILE="${BACKUP_PASSPHRASE_FILE:-}"
[[ -n "$PASSFILE" && -f "$PASSFILE" && -r "$PASSFILE" && ! -L "$PASSFILE" ]] ||
  fail 'Protected passphrase file required'
[[ "$(stat -c %a "$PASSFILE")" == 600 ]] || fail 'Passphrase must have mode 600'
LOCK="$HOME/.local/state/toolz-backup/tier2-stream.lock"
mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK"
flock -n 9 || fail 'Another direct-stream backup is running'
# Also exclude simultaneous runs of the local-first producer.
LOCAL_LOCK="${SNAP_DIR:-/sdcard/Andronix/backups}/.tier2-snapshot.lock"
if [[ -d "$(dirname "$LOCAL_LOCK")" ]]; then
  exec 8>"$LOCAL_LOCK"
  flock -n 8 || fail 'Another Tier-2 snapshot is running'
fi
name="andronix-debian-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(16))').tar.gz.gpg"
staged="$REMOTE/$name.uploading"
final="$REMOTE/$name"
# Fail closed if cloud directory cannot be listed; no cleanup of remote objects.
listing="$(rclone lsf "$REMOTE" --files-only)" || fail 'Cannot list remote'
if printf '%s\n' "$listing" | grep -Fxq -- "$name" ||
   printf '%s\n' "$listing" | grep -Fxq -- "$name.uploading"; then
  fail 'Remote filename collision'
fi
echo "Uploading encrypted stream to $staged"
# pipefail is essential: a tar, encryption or upload failure must stop publication.
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
  | gpg --batch --yes --pinentry-mode loopback --passphrase-file "$PASSFILE" \
      --symmetric --cipher-algo AES256 \
  | rclone rcat --immutable "$staged" ||
  fail "Stream failed; staged cloud object may remain at $staged"
echo 'Validating complete staged encrypted archive from Google Drive'
rclone cat "$staged" |
  gpg --batch --pinentry-mode loopback --passphrase-file "$PASSFILE" --decrypt |
  python3 "$(dirname "$0")/validate_andronix2_archive.py" --require-debian-identity ||
  fail "Staged verification failed; object retained: $staged"
staged_hash="$(rclone cat "$staged" | sha256sum | awk '{print $1}')" ||
  fail 'Cannot hash staged cloud object'
[[ -n "$staged_hash" ]] || fail 'Empty staged hash'
rclone moveto --immutable "$staged" "$final" ||
  fail "Publication failed; check both $staged and $final"
final_hash="$(rclone cat "$final" | sha256sum | awk '{print $1}')" ||
  fail 'Cannot hash published cloud object'
[[ "$staged_hash" == "$final_hash" ]] || fail 'Published cloud checksum mismatch'
rclone cat "$final" |
  gpg --batch --pinentry-mode loopback --passphrase-file "$PASSFILE" --decrypt |
  python3 "$(dirname "$0")/validate_andronix2_archive.py" --require-debian-identity ||
  fail 'Published archive failed structural verification'
echo "PASS: Encrypted stream, published checksum and archive structure verified: $final"
echo 'No full-size local archive was created.'
