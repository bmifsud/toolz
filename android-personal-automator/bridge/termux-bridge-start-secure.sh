#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
umask 077
CONFIG="$HOME/.config/toolz-bridge/device.env"
[[ -f "$CONFIG" && ! -L "$CONFIG" ]] || { echo "Missing protected device credentials" >&2; exit 1; }
mode="$(stat -c %a "$CONFIG")"
[[ "$mode" == "600" || "$mode" == "400" ]] || { echo "Credentials must have mode 600 or 400" >&2; exit 1; }
[[ "$(stat -c %u "$CONFIG")" == "$(id -u)" ]] || { echo "Credentials owner mismatch" >&2; exit 1; }
set -a
# shellcheck disable=SC1090
source "$CONFIG"
set +a
[[ -n "${BRIDGE_WS_URL:-}" && -n "${BRIDGE_DEVICE_TOKEN:-}" ]] || { echo "Missing bridge configuration" >&2; exit 1; }
exec bash "$(dirname "$0")/termux-bridge-supervisor.sh" --start
