#!/data/data/com.termux/files/usr/bin/bash
# Supervise the authenticated Termux bridge listener. No token logging.
set -Eeuo pipefail
umask 077
BASE="$HOME/.local/state/toolz-termux-bridge"
mkdir -p "$BASE"
STOP="$BASE/STOP"
LOCK="$BASE/supervisor.lock"
SCRIPT="${BRIDGE_DEVICE_SCRIPT:-$HOME/toolz-ws-bridge/device.py}"
PYTHON="${PREFIX:-/data/data/com.termux/files/usr}/bin/python"
LOG="$BASE/supervisor.log"
if [[ "${1:-}" == "--stop" ]]; then
  touch "$STOP"
  exit 0
fi
if [[ "${1:-}" != "--start" ]]; then
  echo "Usage: $0 --start | --stop" >&2
  exit 2
fi
[[ -f "$SCRIPT" ]] || { echo "Bridge listener not found" >&2; exit 1; }
[[ -n "${BRIDGE_DEVICE_TOKEN:-}" && -n "${BRIDGE_WS_URL:-}" ]] || {
  echo "Bridge credentials must be provided through a protected environment" >&2; exit 1;
}
command -v flock >/dev/null || { echo "flock required" >&2; exit 1; }
exec 9>"$LOCK"
flock -n 9 || exit 0
rm -f "$STOP"
delay=2
while [[ ! -e "$STOP" ]]; do
  printf '%s listener starting\n' "$(date -u +%FT%TZ)" >>"$LOG"
  "$PYTHON" -u "$SCRIPT" >>"$LOG" 2>&1 || true
  [[ -e "$STOP" ]] && break
  sleep "$delay"
  (( delay < 120 )) && delay=$((delay * 2))
done
printf '%s supervisor stopped\n' "$(date -u +%FT%TZ)" >>"$LOG"
