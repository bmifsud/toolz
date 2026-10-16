#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/launch-ai-tmux.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Launches a 3-pane side-by-side (non-overlapping) tmux workspace
#              inside Andronix Debian (on Termux) running:
#                - Pane 0 (Left):   Antigravity CLI (agy)
#                - Pane 1 (Middle): OpenAI Codex CLI (codex --no-daemon)
#                - Pane 2 (Right):  Google Jules CLI (jules)
#
# Execution Contexts Supported:
#   1. Outer Termux Shell:
#      Detects that it is running outside Debian and automatically invokes the
#      Andronix launcher (~/start-debian.sh or ~/start_debian.sh).
#   2. Inside Debian (proot):
#      Creates (or attaches to) the "ai" tmux session with 3 evenly tiled
#      horizontal panes, mouse/touch support enabled, and top title bars.
#
# Environment Variables:
#   DEBIAN_LAUNCHER  Path to the Andronix Debian startup script in Termux.
#                    Defaults to ~/start-debian.sh (falls back to ~/start_debian.sh).
#   AI_SESSION_NAME  Name of the tmux session to create/attach (default: "ai").
#   AI_WORKDIR       Initial working directory for all 3 panes (default: "$HOME").
#
# Flags:
#   --no-attach      Create and configure the 3-pane tmux session in the
#                    background without attaching the current terminal.
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Step 1: Detect Execution Environment (Outer Termux vs. Inside Debian proot)
# ------------------------------------------------------------------------------
# If neither /etc/debian_version nor ANDRONIX_DISTRO=debian is present, we are
# running in the outer Android Termux environment and need to enter Debian first.
if [[ ! -f /etc/debian_version && "${ANDRONIX_DISTRO:-}" != "debian" ]]; then
    if [[ -z "${DEBIAN_LAUNCHER:-}" ]]; then
        if [[ -x "$HOME/start-debian.sh" ]]; then
            DEBIAN_LAUNCHER="$HOME/start-debian.sh"
        elif [[ -x "$HOME/start_debian.sh" ]]; then
            DEBIAN_LAUNCHER="$HOME/start_debian.sh"
        else
            echo "Error: Debian launcher not found or not executable." >&2
            echo "Checked: $HOME/start-debian.sh and $HOME/start_debian.sh" >&2
            exit 1
        fi
    fi
    exec "$DEBIAN_LAUNCHER"
fi

# ------------------------------------------------------------------------------
# Step 2: Ensure CLI Paths and Dependencies Inside Debian
# ------------------------------------------------------------------------------
# Antigravity (agy) and Codex install into ~/.local/bin by default, while Jules
# installs into /usr/local/bin. Explicitly prepend both to PATH.
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

if ! command -v tmux >/dev/null 2>&1; then
    echo "Error: tmux is not installed in Debian." >&2
    echo "Install it with: sudo apt-get update && sudo apt-get install -y tmux" >&2
    exec bash
fi

SESSION="${AI_SESSION_NAME:-ai}"
WINDOW="AI-Workspace"
WORKDIR="${AI_WORKDIR:-$HOME}"

# ------------------------------------------------------------------------------
# Step 3: Create the 3-Pane Side-by-Side Workspace (If Not Already Running)
# ------------------------------------------------------------------------------
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    # Pane 0 (Left): Antigravity CLI (agy)
    # After agy exits, 'exec bash -i' keeps the pane open at an interactive prompt.
    tmux new-session -d -s "$SESSION" -n "$WINDOW" -c "$WORKDIR" -x 180 -y 45 \
        "export PATH=\"\$HOME/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Antigravity\033\\'; agy; exec bash -i"

    # Pane 1 (Middle): Codex CLI
    # NOTE: '--no-daemon' is required inside Andronix proot to bypass Unix domain
    # socket connection errors with the background app-server daemon.
    tmux split-window -h -t "${SESSION}:${WINDOW}" -c "$WORKDIR" \
        "export PATH=\"\$HOME/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Codex\033\\'; codex --no-daemon; exec bash -i"

    # Pane 2 (Right): Google Jules CLI
    tmux split-window -h -t "${SESSION}:${WINDOW}" -c "$WORKDIR" \
        "export PATH=\"\$HOME/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Jules\033\\'; jules; exec bash -i"

    # --------------------------------------------------------------------------
    # Step 4: Configure Touch/Mouse Navigation and Window Borders
    # --------------------------------------------------------------------------
    # Enable mouse mode so tapping any pane on Android focuses it and dragging
    # pane dividers resizes them interactively.
    tmux set-option -t "$SESSION" -g mouse on

    # Display a distinct header bar at the top of each pane showing its index,
    # agent title, and active command.
    tmux set-option -t "$SESSION" -g pane-border-status top
    tmux set-option -t "$SESSION" -g pane-border-format " #[bold]#{pane_index}: #{pane_title} (#{pane_current_command}) "

    # Arrange all 3 panes side-by-side in equal horizontal columns so no window
    # is stacked or hidden behind another.
    tmux select-layout -t "${SESSION}:${WINDOW}" even-horizontal

    # Focus Pane 0 (Antigravity) by default.
    tmux select-pane -t "${SESSION}:${WINDOW}.0"
fi

# ------------------------------------------------------------------------------
# Step 5: Attach to the Workspace (Unless --no-attach Was Requested)
# ------------------------------------------------------------------------------
if [[ "${1:-}" == "--no-attach" ]]; then
    exit 0
fi

exec tmux attach-session -t "$SESSION"
