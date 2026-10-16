#!/data/data/com.termux/files/usr/bin/bash
# Launch Debian with three tmux windows: Antigravity, Codex, and Jules.
# Requires start_debian.sh to forward arguments after "--" into Debian.
set -euo pipefail
DEBIAN_LAUNCHER="${DEBIAN_LAUNCHER:-$HOME/start_debian.sh}"
if [[ ! -x "$DEBIAN_LAUNCHER" ]]; then
echo "Debian launcher not found or not executable: $DEBIAN_LAUNCHER" >&2
exit 1
fi
exec "$DEBIAN_LAUNCHER" -- /usr/bin/env bash -lc '
set -e
if ! command -v tmux >/dev/null 2>&1; then
echo "tmux is not installed in Debian. Install it with: apt install tmux" >&2
exec bash
fi
if tmux has-session -t ai 2>/dev/null; then
exec tmux attach-session -t ai
fi
tmux new-session -d -s ai -n Antigravity "antigravity; exec bash"
tmux new-window -t ai -n Codex "codex; exec bash"
tmux new-window -t ai -n Jules "jules; exec bash"
tmux select-window -t ai:Antigravity
exec tmux attach-session -t ai
'
