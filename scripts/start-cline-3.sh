#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/start-cline-3.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Launches Andronix Debian and opens a 3-session (3-pane) AI
#              workspace running Cline in all panes:
#                - Pane 0 (Top / Left):     Cline CLI (cline)
#                - Pane 1 (Middle):         Cline CLI (cline)
#                - Pane 2 (Bottom / Right): Cline CLI (cline)
# ==============================================================================

set -euo pipefail

export AI_SESSION_COUNT=3
export AI_PANE0_TITLE="Cline-1"
export AI_PANE0_CMD="cline"
export AI_PANE1_TITLE="Cline-2"
export AI_PANE1_CMD="cline"
export AI_PANE2_TITLE="Cline-3"
export AI_PANE2_CMD="cline"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS_SCRIPTS="${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}/home/b/toolz/scripts"

if [[ -x "${SCRIPT_DIR}/start-debian.sh" ]]; then
    exec "${SCRIPT_DIR}/start-debian.sh" --sessions 3 "$@"
elif [[ -x "${ROOTFS_SCRIPTS}/start-debian.sh" ]]; then
    exec "${ROOTFS_SCRIPTS}/start-debian.sh" --sessions 3 "$@"
elif [[ -x "$HOME/toolz/scripts/start-debian.sh" ]]; then
    exec "$HOME/toolz/scripts/start-debian.sh" --sessions 3 "$@"
elif command -v start-debian.sh >/dev/null 2>&1; then
    exec start-debian.sh --sessions 3 "$@"
elif [[ -f /etc/debian_version || "${ANDRONIX_DISTRO:-}" == "debian" ]]; then
    exec launch-ai-tmux.sh --sessions 3 "$@"
else
    DEBIAN_HOME="${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}/home/b"
    if [[ -d "$DEBIAN_HOME" ]]; then
        echo "3" > "${DEBIAN_HOME}/.ai_session_count" 2>/dev/null || true
        echo "Cline-1" > "${DEBIAN_HOME}/.ai_pane0_title" 2>/dev/null || true
        echo "cline" > "${DEBIAN_HOME}/.ai_pane0_cmd" 2>/dev/null || true
        echo "Cline-2" > "${DEBIAN_HOME}/.ai_pane1_title" 2>/dev/null || true
        echo "cline" > "${DEBIAN_HOME}/.ai_pane1_cmd" 2>/dev/null || true
        echo "Cline-3" > "${DEBIAN_HOME}/.ai_pane2_title" 2>/dev/null || true
        echo "cline" > "${DEBIAN_HOME}/.ai_pane2_cmd" 2>/dev/null || true
    fi
    exec "$HOME/start-debian.sh"
fi
