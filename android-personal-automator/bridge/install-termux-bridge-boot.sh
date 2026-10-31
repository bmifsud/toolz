#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ -f "$HOME/.config/toolz-bridge/device.env" ]] || { echo "Configure protected credentials first" >&2; exit 1; }
mkdir -p "$HOME/.termux/boot"
HOOK="$HOME/.termux/boot/30-toolz-bridge"
printf '#!/data/data/com.termux/files/usr/bin/bash\nexec bash %q >/dev/null 2>&1\n' "$ROOT/termux-bridge-start-secure.sh" > "$HOOK"
chmod 700 "$HOOK"
echo "Boot hook installed. Open Termux:Boot once and exempt Termux from battery restrictions."
