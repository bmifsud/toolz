#!/usr/bin/env bash
set -euo pipefail

# Detect Android Shared Storage or Andronix Debian rootfs backup output directory
if [ -n "${ANDROID_OUT:-}" ]; then
  :
elif [ -n "${TIER1_LOCAL_DIR:-}" ]; then
  ANDROID_OUT="$TIER1_LOCAL_DIR"
elif [ -n "${ROOTFS_DIR:-}" ]; then
  ANDROID_OUT="${ROOTFS_DIR}/home/${DEBIAN_USER:-b}/ClineOmniRouteBackups"
elif [ -d "$HOME/.andronix/distros/debian/rootfs" ]; then
  ANDROID_OUT="$HOME/.andronix/distros/debian/rootfs/home/${DEBIAN_USER:-b}/ClineOmniRouteBackups"
elif [ -d "/mnt/shared" ] && [ -w "/mnt/shared" ]; then
  ANDROID_OUT="/mnt/shared/ClineOmniRouteBackups"
elif [ -d "/sdcard" ] && [ -w "/sdcard" ]; then
  ANDROID_OUT="/sdcard/ClineOmniRouteBackups"
else
  ANDROID_OUT="$HOME/ClineOmniRouteBackups"
fi

GDRIVE_REMOTE="gdrive:ClineOmniRouteBackups"
mkdir -p "$ANDROID_OUT"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
WORK_DIR=$(mktemp -d /tmp/cline_omni_backup.XXXXXX)
trap 'rm -rf "$WORK_DIR"' EXIT

MODE="${1:-backup}"

# Optional: Pull newest archive directly from Google Drive before restoring
if [ "$MODE" = "--restore-gdrive" ]; then
  TARGET_WORKSPACE="${2:-$(pwd)}"
  echo "[0/4] Fetching latest encrypted backup from $GDRIVE_REMOTE..."
  LATEST_FILE=$(rclone lsf "$GDRIVE_REMOTE/" --files-only | grep '^cline_omniroute_backup_.*\.tar\.gz\.gpg$' | sort | tail -n 1)
  if [ -z "$LATEST_FILE" ]; then
    echo "Error: No backup archives found in $GDRIVE_REMOTE"
    exit 1
  fi
  rclone copy "$GDRIVE_REMOTE/$LATEST_FILE" "$ANDROID_OUT/" --progress
  set -- "--restore" "$ANDROID_OUT/$LATEST_FILE" "$TARGET_WORKSPACE"
  MODE="--restore"
fi

if [ "$MODE" = "--restore" ]; then
  ARCHIVE_PATH="${2:-}"
  TARGET_WORKSPACE="${3:-$(pwd)}"
  if [ -z "$ARCHIVE_PATH" ] || [ ! -f "$ARCHIVE_PATH" ]; then
    echo "Usage:"
    echo "  $0 backup [/path/to/workspace]"
    echo "  $0 --restore /path/to/backup.tar.gz.gpg [/path/to/workspace]"
    echo "  $0 --restore-gdrive [/path/to/workspace]"
    exit 1
  fi

  echo "[1/4] Decrypting and extracting backup archive..."
  if [ -n "${BACKUP_PASSPHRASE:-}" ]; then
    gpg --batch --yes --pinentry-mode loopback --passphrase "$BACKUP_PASSPHRASE" --decrypt "$ARCHIVE_PATH" | tar -xzp -C "$WORK_DIR"
  else
    gpg --decrypt "$ARCHIVE_PATH" | tar -xzp -C "$WORK_DIR"
  fi

  echo "[2/4] Restoring Cline CLI global state, MCP settings, and chmod 600 secrets..."
  mkdir -p ~/.cline/data/settings
  if [ -d "$WORK_DIR/home/.cline/data" ]; then
    cp -a "$WORK_DIR/home/.cline/data/." ~/.cline/data/
  fi
  [ -f ~/.cline/data/secrets.json ] && chmod 600 ~/.cline/data/secrets.json

  echo "[3/4] Restoring OmniRoute SQLite DB, .env, systemd service, and routing combos..."
  mkdir -p ~/.omniroute
  if [ -f "$WORK_DIR/omniroute/storage.sqlite" ]; then
    systemctl --user stop omniroute.service 2>/dev/null || true
    cp -a "$WORK_DIR/omniroute/storage.sqlite" ~/.omniroute/storage.sqlite
    rm -f ~/.omniroute/storage.sqlite-wal ~/.omniroute/storage.sqlite-shm
  fi
  if [ -f "$WORK_DIR/omniroute/.env" ]; then
    cp -a "$WORK_DIR/omniroute/.env" ~/.omniroute/.env
    chmod 600 ~/.omniroute/.env
  fi
  if [ -f "$WORK_DIR/systemd/omniroute.service" ]; then
    mkdir -p ~/.config/systemd/user
    cp -a "$WORK_DIR/systemd/omniroute.service" ~/.config/systemd/user/omniroute.service
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now omniroute.service 2>/dev/null || true
  fi

  if [ -f "$WORK_DIR/omniroute/combos_export.json" ] && curl -fsS http://localhost:20128/health >/dev/null 2>&1; then
    jq -c '.[] | select(.id == "cline-plan-combo" or .id == "cline-act-combo")' "$WORK_DIR/omniroute/combos_export.json" | while read -r combo; do
      echo "$combo" > "$WORK_DIR/temp_combo.json"
      omniroute api combos post-api-combos --body @"$WORK_DIR/temp_combo.json" >/dev/null 2>&1 || true
    done
  fi

  echo "[4/4] Restoring workspace (.clinerules, .memory, .cline/scripts) to $TARGET_WORKSPACE..."
  if [ -d "$WORK_DIR/workspace" ]; then
    mkdir -p "$TARGET_WORKSPACE"
    cp -a "$WORK_DIR/workspace/." "$TARGET_WORKSPACE/"
    [ -f "$TARGET_WORKSPACE/.cline/scripts/verify.sh" ] && chmod +x "$TARGET_WORKSPACE/.cline/scripts/verify.sh"
  fi

  echo "Restore complete!"
  exit 0
fi

WORKSPACE_DIR="${2:-$(pwd)}"

echo "[1/5] Performing safe hot SQLite backup of OmniRoute DB, .env, and JSON combos..."
mkdir -p "$WORK_DIR/omniroute" "$WORK_DIR/systemd"
if [ -f ~/.omniroute/storage.sqlite ]; then
  sqlite3 ~/.omniroute/storage.sqlite ".backup '$WORK_DIR/omniroute/storage.sqlite'"
fi
[ -f ~/.omniroute/.env ] && cp -a ~/.omniroute/.env "$WORK_DIR/omniroute/.env"
[ -f ~/.config/systemd/user/omniroute.service ] && cp -a ~/.config/systemd/user/omniroute.service "$WORK_DIR/systemd/omniroute.service"
if curl -fsS http://localhost:20128/api/combos >/dev/null 2>&1; then
  curl -fsS http://localhost:20128/api/combos > "$WORK_DIR/omniroute/combos_export.json"
fi

echo "[2/5] Backing up Cline CLI globalState.json, secrets.json, and MCP settings..."
mkdir -p "$WORK_DIR/home/.cline/data/settings"
for file in globalState.json secrets.json; do
  [ -f "$HOME/.cline/data/$file" ] && cp -a "$HOME/.cline/data/$file" "$WORK_DIR/home/.cline/data/$file"
done
[ -d ~/.cline/data/settings ] && cp -a ~/.cline/data/settings/. "$WORK_DIR/home/.cline/data/settings/"

echo "[3/5] Backing up Workspace (.clinerules, .memory, .cline/scripts)..."
mkdir -p "$WORK_DIR/workspace"
for dir in .clinerules .memory .cline; do
  [ -d "$WORKSPACE_DIR/$dir" ] && cp -a "$WORKSPACE_DIR/$dir" "$WORK_DIR/workspace/"
done

echo "[4/5] Compressing and encrypting archive (AES-256) to $ANDROID_OUT..."
OUT_FILE="$ANDROID_OUT/cline_omniroute_backup_${TIMESTAMP}.tar.gz.gpg"
if [ -n "${BACKUP_PASSPHRASE:-}" ]; then
  tar -czp -C "$WORK_DIR" . | gpg --batch --yes --pinentry-mode loopback --passphrase "$BACKUP_PASSPHRASE" --symmetric --cipher-algo AES256 -o "$OUT_FILE"
else
  tar -czp -C "$WORK_DIR" . | gpg --symmetric --cipher-algo AES256 -o "$OUT_FILE"
fi

echo "Local encrypted backup saved: $OUT_FILE"

echo "[5/5] Syncing encrypted archive to Google Drive ($GDRIVE_REMOTE)..."
if command -v rclone >/dev/null 2>&1 && rclone listremotes | grep -q "^gdrive:$"; then
  rclone copy "$OUT_FILE" "$GDRIVE_REMOTE/" --progress
  echo "Google Drive upload complete!"
else
  echo "Warning: rclone remote 'gdrive:' not configured. Skipping cloud upload (run 'rclone config' to enable)."
fi
