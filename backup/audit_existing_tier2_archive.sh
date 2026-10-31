#!/usr/bin/env bash
# Read-only local Tier-2 encrypted archive audit. Does not extract or upload.
set -euo pipefail
umask 077
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ $# -eq 1 ]] || fail "Usage: $0 /absolute/path/to/existing.tar.gz.gpg"
archive="$1"
[[ "$archive" = /* && -f "$archive" && ! -L "$archive" ]] || fail "Provide an existing absolute regular archive path (no symlink)"
for cmd in gpg python3 sha256sum stat df; do command -v "$cmd" >/dev/null || fail "Missing $cmd"; done
[[ -n "${BACKUP_PASSPHRASE_FILE:-}" ]] || fail "Set BACKUP_PASSPHRASE_FILE to the existing protected key file"
key="$BACKUP_PASSPHRASE_FILE"
[[ -f "$key" && -r "$key" && ! -L "$key" ]] || fail "Key file unavailable or symlink"
[[ "$(stat -c %a "$key")" == 600 ]] || fail "Key file must have mode 600"
echo "Archive: $archive"
stat -c 'Encrypted size: %s bytes' -- "$archive"
sha256sum -- "$archive"
echo "Free space for a future isolated restore (no allocation performed):"
df -h "$HOME"
echo "Decrypting and structurally validating the full stream (read-only)..."
# Avoid false PASS when GPG fails: pipefail checks both decrypt and validator.
gpg --batch --no-tty --pinentry-mode loopback --passphrase-file "$key" \
  --decrypt -- "$archive" | python3 "$HERE/validate_andronix2_archive.py"
echo "PASS: encrypted archive decrypted and structurally validated; no extraction performed"
