#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/start-debian-2.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Launches Andronix Debian and opens a 2-session (2-pane) AI
#              workspace (stacked vertically in portrait, side-by-side in
#              landscape) running:
#                - Pane 0 (Top / Left):     Antigravity CLI (agy)
#                - Pane 1 (Bottom / Right): OpenAI Codex CLI (codex --no-daemon)
#
# Works from Termux:Widget (~/.shortcut / ~/.shortcuts), Outer Termux, and
# Inside Debian (proot).
# Usage:
#   ./start-debian-2.sh [--portrait | --landscape | --auto] [--no-attach]
# ==============================================================================

set -euo pipefail

export AI_SESSION_COUNT=2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS_SCRIPTS="${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}/home/b/toolz/scripts"

if [[ -x "${SCRIPT_DIR}/start-debian.sh" ]]; then
    exec "${SCRIPT_DIR}/start-debian.sh" --sessions 2 "$@"
elif [[ -x "${ROOTFS_SCRIPTS}/start-debian.sh" ]]; then
    exec "${ROOTFS_SCRIPTS}/start-debian.sh" --sessions 2 "$@"
elif [[ -x "$HOME/toolz/scripts/start-debian.sh" ]]; then
    exec "$HOME/toolz/scripts/start-debian.sh" --sessions 2 "$@"
elif command -v start-debian.sh >/dev/null 2>&1; then
    exec start-debian.sh --sessions 2 "$@"
elif [[ -f /etc/debian_version || "${ANDRONIX_DISTRO:-}" == "debian" ]]; then
    exec launch-ai-tmux.sh --sessions 2 "$@"
else
    DEBIAN_HOME="${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}/home/b"
    [[ -d "$DEBIAN_HOME" ]] && echo "2" > "${DEBIAN_HOME}/.ai_session_count" 2>/dev/null || true
    exec "$HOME/start-debian.sh"
fi
