#!/usr/bin/env bash
set -euo pipefail
umask 077

MODE="${1:---apply}"
if [[ "$MODE" != "--apply" && "$MODE" != "--dry-run" ]]; then
  echo "Usage: $0 [--apply|--dry-run]" >&2
  exit 2
fi

# Independent backup-lock coordination (does not assume inherited fd 9)
STATE="$HOME/.local/state/toolz-backup"
mkdir -p "$STATE"
exec 8>"$STATE/backup.lock"
flock -n 8 || { echo 'Another backup or retention operation is running; skipping' >&2; exit 75; }

# Consistent Tier-1 backup output directory resolution
if [ -n "${ANDROID_OUT:-}" ]; then
  LOCAL_DIR="$ANDROID_OUT"
elif [ -n "${TIER1_LOCAL_DIR:-}" ]; then
  LOCAL_DIR="$TIER1_LOCAL_DIR"
elif [ -n "${ROOTFS_DIR:-}" ]; then
  LOCAL_DIR="${ROOTFS_DIR}/home/${DEBIAN_USER:-b}/ClineOmniRouteBackups"
elif [ -d "$HOME/.andronix/distros/debian/rootfs" ]; then
  LOCAL_DIR="$HOME/.andronix/distros/debian/rootfs/home/${DEBIAN_USER:-b}/ClineOmniRouteBackups"
elif [ -d "/mnt/shared" ] && [ -w "/mnt/shared" ]; then
  LOCAL_DIR="/mnt/shared/ClineOmniRouteBackups"
elif [ -d "/sdcard" ] && [ -w "/sdcard" ]; then
  LOCAL_DIR="/sdcard/ClineOmniRouteBackups"
else
  LOCAL_DIR="$HOME/ClineOmniRouteBackups"
fi

GDRIVE_REMOTE="${GDRIVE_REMOTE:-gdrive:ClineOmniRouteBackups}"

if [ ! -d "$LOCAL_DIR" ]; then
  echo "Local backup directory $LOCAL_DIR does not exist. Nothing to retain."
  exit 0
fi

command -v rclone >/dev/null || { echo "rclone required for cloud verification" >&2; exit 1; }
rclone listremotes | grep -q "^gdrive:$" || { echo "Google Drive remote 'gdrive:' not configured" >&2; exit 1; }

cd "$LOCAL_DIR"

# Select archives strictly matching cline_omniroute_backup_YYYYMMDD_HHMMSS.tar.gz.gpg
files=()
while IFS= read -r -d '' f; do
  files+=("$f")
done < <(find . -maxdepth 1 -type f -name 'cline_omniroute_backup_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9].tar.gz.gpg' -print0)

if [ ${#files[@]} -le 1 ]; then
  echo "Found ${#files[@]} archive(s). Keeping newest; no older archives to clean up."
  exit 0
fi

# Sort chronologically (oldest to newest)
IFS=$'\n' sorted_files=($(sort <<< "${files[*]}"))
unset IFS

# Preserve the newest archive unconditionally (last element)
newest="${sorted_files[-1]}"
echo "Newest archive preserved unconditionally: $newest"

# Older archives to verify and potentially clean up
older_files=("${sorted_files[@]:0:${#sorted_files[@]}-1}")

for old_file in "${older_files[@]}"; do
  name="$(basename "$old_file")"
  echo "Verifying older archive: $name"

  if [ ! -f "$old_file" ]; then
    echo "Error: Archive $old_file disappeared." >&2
    exit 1
  fi

  # Check remote object exists on Google Drive
  if ! rclone lsf "$GDRIVE_REMOTE/$name" --files-only 2>/dev/null | grep -q "^$name$"; then
    echo "Error: Archive $name not found on Google Drive ($GDRIVE_REMOTE). Preserving local copy." >&2
    exit 1
  fi

  # Capture local state before SHA-256 readback
  local_hash_before="$(sha256sum "$old_file" | awk '{print $1}')"
  mtime_before="$(stat -c %Y "$old_file")"

  # Complete SHA-256 readback from Google Drive
  remote_hash="$(rclone cat "$GDRIVE_REMOTE/$name" | sha256sum | awk '{print $1}')"

  # Capture local state after SHA-256 readback to ensure file did not change during verification
  local_hash_after="$(sha256sum "$old_file" | awk '{print $1}')"
  mtime_after="$(stat -c %Y "$old_file")"

  if [ "$local_hash_before" != "$local_hash_after" ] || [ "$mtime_before" != "$mtime_after" ]; then
    echo "Error: Local file $name changed during verification. Aborting deletion." >&2
    exit 1
  fi

  if [ "$local_hash_after" != "$remote_hash" ]; then
    echo "Error: Checksum mismatch for $name (local: $local_hash_after, remote: $remote_hash). Preserving local copy." >&2
    exit 1
  fi

  echo "VERIFIED OK: $name matches Google Drive copy."

  if [ "$MODE" == "--dry-run" ]; then
    echo "DRY-RUN: Would delete local archive: $old_file"
  else
    rm -f "$old_file"
    echo "Deleted verified local archive: $old_file"
  fi
done

echo "Tier-1 retention completed successfully."

