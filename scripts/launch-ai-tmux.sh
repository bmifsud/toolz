#!/usr/bin/env bash
# Launch Debian with three distinct side-by-side tmux panes:
#   1) Antigravity CLI (agy)
#   2) Codex CLI (codex)
#   3) Google Jules CLI (jules)
# Works when invoked either from Termux (via start-debian.sh) or directly inside Debian.

set -euo pipefail

# If running in outer Termux (outside Debian proot), enter Debian first.
if [[ ! -f /etc/debian_version && "${ANDRONIX_DISTRO:-}" != "debian" ]]; then
    if [[ -z "${DEBIAN_LAUNCHER:-}" ]]; then
        if [[ -x "$HOME/start-debian.sh" ]]; then
            DEBIAN_LAUNCHER="$HOME/start-debian.sh"
        elif [[ -x "$HOME/start_debian.sh" ]]; then
            DEBIAN_LAUNCHER="$HOME/start_debian.sh"
        else
            echo "Debian launcher not found or not executable: tried $HOME/start-debian.sh and $HOME/start_debian.sh" >&2
            exit 1
        fi
    fi
    exec "$DEBIAN_LAUNCHER"
fi

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed in Debian. Install it with: sudo apt-get install -y tmux" >&2
    exec bash
fi

SESSION="ai"

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
     WORKDIR="${AI_WORKDIR:-$HOME}"
    # Create session with Pane 0: Antigravity CLI
    tmux new-session -d -s "$SESSION" -n "AI-Workspace" -c "$WORKDIR" -x 180 -y 45 \
        "export PATH=\"\$HOME/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Antigravity\033\\'; agy; exec bash -i"

    # Split horizontally for Pane 1: Codex CLI (--no-daemon avoids proot unix socket conflicts)
    tmux split-window -h -t "${SESSION}:AI-Workspace" -c "$WORKDIR" \
        "export PATH=\"\$HOME/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Codex\033\\'; codex --no-daemon; exec bash -i"

    # Split horizontally for Pane 2: Google Jules CLI
    tmux split-window -h -t "${SESSION}:AI-Workspace" -c "$WORKDIR" \
        "export PATH=\"\$HOME/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Jules\033\\'; jules; exec bash -i"

    # Enable touch/mouse support and distinct labeled window borders for each pane
    tmux set-option -t "$SESSION" -g mouse on
    tmux set-option -t "$SESSION" -g pane-border-status top
    tmux set-option -t "$SESSION" -g pane-border-format " #[bold]#{pane_index}: #{pane_title} (#{pane_current_command}) "

    # Arrange all 3 panes side-by-side so none are stacked/hidden behind each other
    tmux select-layout -t "${SESSION}:AI-Workspace" even-horizontal
    tmux select-pane -t "${SESSION}:AI-Workspace.0"
fi

if [[ "${1:-}" == "--no-attach" ]]; then
    exit 0
fi

exec tmux attach-session -t "$SESSION"
