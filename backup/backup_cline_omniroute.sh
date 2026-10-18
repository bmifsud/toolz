#!/usr/bin/env bash
set -euo pipefail

# Detect Android Shared Storage mount point
if [ -d "/mnt/shared" ] && [ -w "/mnt/shared" ]; then
  ANDROID_OUT="/mnt/shared/ClineOmniRouteBackups"
elif [ -d "/sdcard" ] && [ -w "/sdcard" ]; then
  ANDROID_OUT="/sdcard/ClineOmniRouteBackups"
else
  ANDROID_OUT="$HOME/ClineOmniRouteBackups"
fi

mkdir -p "$ANDROID_OUT"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
WORK_DIR=$(mktemp -d /tmp/cline_omni_backup.XXXXXX)
trap 'rm -rf "$WORK_DIR"' EXIT

MODE="${1:-backup}"
WORKSPACE_DIR="${2:-$(pwd)}"

if [ "$MODE" = "--restore" ]; then
  ARCHIVE_PATH="${2:-}"
  TARGET_WORKSPACE="${3:-$(pwd)}"
  if [ -z "$ARCHIVE_PATH" ] || [ ! -f "$ARCHIVE_PATH" ]; then
    echo "Usage: $0 --restore /path/to/backup.tar.gz.gpg [/path/to/workspace]"
    exit 1
  fi

  echo "[1/4] Decrypting and extracting backup archive..."
  gpg --decrypt "$ARCHIVE_PATH" | tar -xzp -C "$WORK_DIR"

  echo "[2/4] Restoring Cline CLI global configuration & permissions..."
  mkdir -p ~/.cline/data/settings
  if [ -d "$WORK_DIR/home/.cline/data" ]; then
    cp -a "$WORK_DIR/home/.cline/data/." ~/.cline/data/
  fi
  if [ -f ~/.cline/data/secrets.json ]; then
    chmod 600 ~/.cline/data/secrets.json
  fi

  echo "[3/4] Restoring OmniRoute database, systemd unit, and combos..."
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

  # Re-register combos from JSON export if OmniRoute is listening
  if [ -f "$WORK_DIR/omniroute/combos_export.json" ] && curl -fsS http://localhost:20128/health >/dev/null 2>&1; then
    jq -c '.[] | select(.id == "cline-plan-combo" or .id == "cline-act-combo")' "$WORK_DIR/omniroute/combos_export.json" | while read -r combo; do
      echo "$combo" > "$WORK_DIR/temp_combo.json"
      omniroute api combos post-api-combos --body @"$WORK_DIR/temp_combo.json" >/dev/null 2>&1 || true
    done
  fi

  echo "[4/4] Restoring workspace rules, memory bank, and scripts to $TARGET_WORKSPACE..."
  if [ -d "$WORK_DIR/workspace" ]; then
    mkdir -p "$TARGET_WORKSPACE"
    cp -a "$WORK_DIR/workspace/." "$TARGET_WORKSPACE/"
    [ -f "$TARGET_WORKSPACE/.cline/scripts/verify.sh" ] && chmod +x "$TARGET_WORKSPACE/.cline/scripts/verify.sh"
  fi

  echo "Restore complete!"
  exit 0
fi

echo "[1/4] Backing up OmniRoute SQLite DB, .env, and active JSON combos..."
mkdir -p "$WORK_DIR/omniroute" "$WORK_DIR/systemd"
if [ -f ~/.omniroute/storage.sqlite ]; then
  sqlite3 ~/.omniroute/storage.sqlite ".backup '$WORK_DIR/omniroute/storage.sqlite'"
fi
[ -f ~/.omniroute/.env ] && cp -a ~/.omniroute/.env "$WORK_DIR/omniroute/.env"
[ -f ~/.config/systemd/user/omniroute.service ] && cp -a ~/.config/systemd/user/omniroute.service "$WORK_DIR/systemd/omniroute.service"
if curl -fsS http://localhost:20128/api/combos >/dev/null 2>&1; then
  curl -fsS http://localhost:20128/api/combos > "$WORK_DIR/omniroute/combos_export.json"
fi

echo "[2/4] Backing up Cline CLI global state, secrets, and MCP settings..."
mkdir -p "$WORK_DIR/home/.cline/data/settings"
for file in globalState.json secrets.json; do
  [ -f "$HOME/.cline/data/$file" ] && cp -a "$HOME/.cline/data/$file" "$WORK_DIR/home/.cline/data/$file"
done
[ -d ~/.cline/data/settings ] && cp -a ~/.cline/data/settings/. "$WORK_DIR/home/.cline/data/settings/"

echo "[3/4] Backing up Workspace (.clinerules, .memory, .cline/scripts)..."
mkdir -p "$WORK_DIR/workspace"
for dir in .clinerules .memory .cline; do
  [ -d "$WORKSPACE_DIR/$dir" ] && cp -a "$WORKSPACE_DIR/$dir" "$WORK_DIR/workspace/"
done

echo "[4/4] Compressing and encrypting archive to Android storage..."
OUT_FILE="$ANDROID_OUT/cline_omniroute_backup_${TIMESTAMP}.tar.gz.gpg"
tar -czp -C "$WORK_DIR" . | gpg --symmetric --cipher-algo AES256 -o "$OUT_FILE"

# Keep only the 5 most recent backups on Android storage
ls -1t "$ANDROID_OUT"/cline_omniroute_backup_*.tar.gz.gpg 2>/dev/null | tail -n +6 | xargs -r rm -f

echo "Backup saved and encrypted at: $OUT_FILE"
