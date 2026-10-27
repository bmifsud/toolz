#!/usr/bin/env bash
# Opt-in bridge live-update supervisor. Run once in Termux; Ctrl-C stops it.
set -Eeuo pipefail
REPO_DIR="${TOOLZ_REPO_DIR:-$HOME/toolz-tier1-test}"
BRANCH="feat/termux-readonly-bridge-20261027"
SOURCE="android-personal-automator/bridge"
DEST="${TMPDIR:?Termux TMPDIR is required}/toolz-bridge"
INTERVAL="${BRIDGE_UPDATE_INTERVAL:-60}"
case "$INTERVAL" in *[!0-9]*|'') echo "Invalid interval" >&2; exit 2;; esac
if (( INTERVAL < 30 || INTERVAL > 3600 )); then echo "Interval must be 30-3600s" >&2; exit 2; fi
mkdir -p "$DEST"
chmod 700 "$DEST"
cd "$REPO_DIR"
child=""
stop() {
  trap - INT TERM
  if [[ -n "$child" ]]; then kill "$child" 2>/dev/null || :; wait "$child" 2>/dev/null || :; fi
  echo "[bridge] Stopped"
  exit 0
}
trap stop INT TERM
current=""
while :; do
  if [[ -f "$HOME/.local/state/toolz-termux-bridge/STOP" ]]; then
    echo "[bridge] STOP file present; exiting"; stop
  fi
  if git fetch --quiet origin "$BRANCH"; then
    revision="$(git rev-parse FETCH_HEAD)"
    if [[ "$revision" != "$current" ]]; then
      echo "[bridge] Preparing revision ${revision:0:12}"
      temp="$(mktemp -d "$DEST/.update.XXXXXXXX")"
      valid=1
      for file in readonly_runner.py github_issue_worker.py; do
        git show "$revision:$SOURCE/$file" > "$temp/$file" || valid=0
      done
      if [[ "$valid" == 1 ]] && python -m py_compile "$temp/"*.py; then
        # Restart only after new code passes syntax validation.
        if [[ -n "$child" ]]; then kill "$child" 2>/dev/null || :; wait "$child" 2>/dev/null || :; fi
        mv -f "$temp/"*.py "$DEST/"
        current="$revision"
        echo "[bridge] Activated ${revision:0:12}"
        python -u "$DEST/github_issue_worker.py" --interval 10 &
        child=$!
      else
        echo "[bridge] Update rejected: missing files or syntax error" >&2
      fi
      rm -rf "$temp"
    fi
  else
    echo "[bridge] Fetch failed; retaining existing worker" >&2
  fi
  if [[ -n "$child" ]] && ! kill -0 "$child" 2>/dev/null; then
    wait "$child" || :
    echo "[bridge] Worker exited; not restarting until next revision" >&2
    child=""
  fi
  sleep "$INTERVAL" &
  wait $! || :
done
