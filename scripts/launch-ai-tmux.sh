#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/launch-ai-tmux.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Launches a 3-pane orientation-aware (non-overlapping) tmux
#              workspace inside Andronix Debian (on Termux) running:
#                - Pane 0 (Top / Left):     Antigravity CLI (agy)
#                - Pane 1 (Middle):         OpenAI Codex CLI (codex --no-daemon)
#                - Pane 2 (Bottom / Right): Google Jules CLI (jules)
#
# Orientation Behavior:
#   - Portrait Orientation (even-vertical):
#       Stacks all 3 agent sessions vertically on top of each other (Top,
#       Middle, Bottom) so each pane gets the full terminal width.
#   - Landscape Orientation (even-horizontal):
#       Arranges all 3 agent sessions side-by-side in equal columns (Left,
#       Middle, Right).
#   - Dynamic Rotation Hooks:
#       Registers tmux hooks (client-attached, client-resized, window-resized)
#       so rotating the Android device between portrait and landscape
#       automatically restacks or unstacks the panes in real time.
#
# Execution Contexts Supported:
#   1. Outer Termux Shell:
#      Detects that it is running outside Debian and automatically invokes the
#      Andronix launcher (~/start-debian.sh or ~/start_debian.sh).
#   2. Inside Debian (proot):
#      Creates (or attaches to) the "ai" tmux session with 3 evenly tiled
#      panes, mouse/touch support enabled, and top title bars.
#
# Environment Variables:
#   DEBIAN_LAUNCHER        Path to the Andronix Debian startup script in Termux.
#                          Defaults to ~/start-debian.sh (falls back to ~/start_debian.sh).
#   AI_SESSION_NAME        Name of the tmux session to create/attach (default: "ai").
#   AI_WORKDIR             Initial working directory for all 3 panes (default: "$HOME").
#   AI_ORIENTATION         Layout mode: "auto" (default), "portrait", or "landscape".
#   AI_MIN_LANDSCAPE_COLS  Minimum terminal width (columns) required to use the
#                          3-column side-by-side layout in "auto" mode (default: 115).
#                          Ensures portrait mode stays vertically stacked even when
#                          the Android on-screen keyboard reduces terminal height.
#
# Flags:
#   --no-attach            Create and configure the 3-pane tmux session in the
#                          background without attaching the current terminal.
#   --portrait             Force portrait layout (stack panes on top of each other).
#   --landscape            Force landscape layout (side-by-side columns).
#   --auto                 Auto-detect orientation and switch dynamically (default).
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Step 0: Parse Command-Line Flags
# ------------------------------------------------------------------------------
NO_ATTACH=0
ORIENTATION_MODE="${AI_ORIENTATION:-auto}"
MIN_LANDSCAPE_COLS="${AI_MIN_LANDSCAPE_COLS:-115}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-attach)
            NO_ATTACH=1
            shift
            ;;
        --portrait|--vertical|--stack)
            ORIENTATION_MODE="portrait"
            shift
            ;;
        --landscape|--horizontal)
            ORIENTATION_MODE="landscape"
            shift
            ;;
        --auto)
            ORIENTATION_MODE="auto"
            shift
            ;;
        -h|--help)
            sed -n '2,47p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            echo "Usage: $0 [--no-attach] [--portrait | --landscape | --auto]" >&2
            exit 1
            ;;
    esac
done

# Normalize ORIENTATION_MODE
case "${ORIENTATION_MODE,,}" in
    portrait|vertical|stack)
        ORIENTATION_MODE="portrait"
        ;;
    landscape|horizontal)
        ORIENTATION_MODE="landscape"
        ;;
    *)
        ORIENTATION_MODE="auto"
        ;;
esac
export AI_ORIENTATION="$ORIENTATION_MODE"

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
# Step 3: Detect Terminal Geometry & Orientation (Portrait vs. Landscape)
# ------------------------------------------------------------------------------
# Read active terminal dimensions from controlling TTY, attached tmux client,
# or environment so detached creation uses accurate screen proportions.
detect_terminal_size() {
    local rows="" cols="" tty_size=""

    if tty_size="$(stty size </dev/tty 2>/dev/null)" && [[ -n "$tty_size" ]]; then
        read -r rows cols <<<"$tty_size"
    fi

    if [[ -z "$rows" || -z "$cols" || "$rows" -le 0 || "$cols" -le 0 ]] 2>/dev/null; then
        if tty_size="$(tmux list-clients -t "$SESSION" -F "#{client_height} #{client_width}" 2>/dev/null | head -n 1)" && [[ -n "$tty_size" ]]; then
            read -r rows cols <<<"$tty_size"
        elif tty_size="$(tmux list-clients -F "#{client_height} #{client_width}" 2>/dev/null | head -n 1)" && [[ -n "$tty_size" ]]; then
            read -r rows cols <<<"$tty_size"
        fi
    fi

    if [[ -z "$rows" || -z "$cols" || "$rows" -le 0 || "$cols" -le 0 ]] 2>/dev/null; then
        if [[ "$ORIENTATION_MODE" == "portrait" ]]; then
            rows=65
            cols=92
        else
            rows=45
            cols=180
        fi
    fi

    echo "$rows $cols"
}

is_portrait_geometry() {
    local rows="$1"
    local cols="$2"

    if [[ "$ORIENTATION_MODE" == "portrait" ]]; then
        return 0
    elif [[ "$ORIENTATION_MODE" == "landscape" ]]; then
        return 1
    fi

    # Terminal character cells have an ~1:2 width-to-height pixel aspect ratio,
    # so cols < rows * 2 indicates a portrait pixel viewport. Additionally, if
    # total width is below MIN_LANDSCAPE_COLS (default 115), keep panes stacked
    # vertically so opening the Android soft keyboard in portrait mode does not
    # flip the workspace into cramped 3-column strips.
    if (( cols < rows * 2 || cols < MIN_LANDSCAPE_COLS )); then
        return 0
    fi
    return 1
}

read -r INIT_ROWS INIT_COLS <<<"$(detect_terminal_size)"

if is_portrait_geometry "$INIT_ROWS" "$INIT_COLS"; then
    SPLIT_FLAG="-v"
    INITIAL_LAYOUT="even-vertical"
else
    SPLIT_FLAG="-h"
    INITIAL_LAYOUT="even-horizontal"
fi

# ------------------------------------------------------------------------------
# Step 4: Create the 3-Pane Workspace (If Not Already Running)
# ------------------------------------------------------------------------------
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    # Pane 0 (Top in portrait / Left in landscape): Antigravity CLI (agy)
    # After agy exits, 'exec bash -i' keeps the pane open at an interactive prompt.
    tmux new-session -d -s "$SESSION" -n "$WINDOW" -c "$WORKDIR" -x "$INIT_COLS" -y "$INIT_ROWS" \
        "export HOME=\"${HOME}\" PATH=\"${HOME}/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Antigravity\033\\'; agy; exec bash -i"

    # Pane 1 (Middle): Codex CLI
    # NOTE: '--no-daemon' is required inside Andronix proot to bypass Unix domain
    # socket connection errors with the background app-server daemon.
    tmux split-window "$SPLIT_FLAG" -t "${SESSION}:${WINDOW}" -c "$WORKDIR" \
        "export HOME=\"${HOME}\" PATH=\"${HOME}/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Codex\033\\'; codex --no-daemon; exec bash -i"

    # Pane 2 (Bottom in portrait / Right in landscape): Google Jules CLI
    tmux split-window "$SPLIT_FLAG" -t "${SESSION}:${WINDOW}" -c "$WORKDIR" \
        "export HOME=\"${HOME}\" PATH=\"${HOME}/.local/bin:/usr/local/bin:\$PATH\"; printf '\033]2;Jules\033\\'; jules; exec bash -i"

    # Focus Pane 0 (Antigravity) by default.
    tmux select-pane -t "${SESSION}:${WINDOW}.0"
fi

# ------------------------------------------------------------------------------
# Step 5: Configure Touch/Mouse Navigation, Borders & Dynamic Orientation Hooks
# ------------------------------------------------------------------------------
# Enable mouse mode so tapping any pane on Android focuses it and dragging
# pane dividers resizes them interactively.
tmux set-option -t "$SESSION" -g mouse on

# Display a distinct header bar at the top of each pane showing its index,
# agent title, and active command. Lock pane titles (allow-set-title off) so
# child CLIs cannot overwrite "Antigravity", "Codex", or "Jules".
tmux set-option -t "$SESSION" -g pane-border-status top
tmux set-option -t "$SESSION" -g pane-border-format " #[bold]#{pane_index}: #{pane_title} (#{pane_current_command}) "
tmux select-pane -t "${SESSION}:${WINDOW}.0" -T "Antigravity" 2>/dev/null || true
tmux select-pane -t "${SESSION}:${WINDOW}.1" -T "Codex" 2>/dev/null || true
tmux select-pane -t "${SESSION}:${WINDOW}.2" -T "Jules" 2>/dev/null || true
tmux set-option -w -t "${SESSION}:${WINDOW}" allow-set-title off 2>/dev/null || true

# Configure orientation hooks so rotating the device (or attaching from a new
# viewport) automatically stacks panes in portrait (even-vertical) or places
# them side-by-side in landscape (even-horizontal), unless a pane is zoomed.
if [[ "$ORIENTATION_MODE" == "portrait" ]]; then
    HOOK_CMD="if-shell -F '#{==:#{window_zoomed_flag},0}' 'select-layout -t ${SESSION}:${WINDOW} even-vertical'"
elif [[ "$ORIENTATION_MODE" == "landscape" ]]; then
    HOOK_CMD="if-shell -F '#{==:#{window_zoomed_flag},0}' 'select-layout -t ${SESSION}:${WINDOW} even-horizontal'"
else
    PORTRAIT_COND="#{||:#{e|<|:#{window_width},#{e|*|:#{window_height},2}},#{e|<|:#{window_width},${MIN_LANDSCAPE_COLS}}}"
    HOOK_CMD="if-shell -F '#{==:#{window_zoomed_flag},0}' \"if-shell -F '${PORTRAIT_COND}' 'select-layout -t ${SESSION}:${WINDOW} even-vertical' 'select-layout -t ${SESSION}:${WINDOW} even-horizontal'\""
fi

tmux set-hook -t "$SESSION" client-attached "$HOOK_CMD"
tmux set-hook -t "$SESSION" client-resized "$HOOK_CMD"
tmux set-hook -t "$SESSION" window-resized "$HOOK_CMD"

# Apply the appropriate layout immediately if no pane is currently zoomed.
if [[ "$(tmux display-message -t "${SESSION}:${WINDOW}" -p '#{window_zoomed_flag}' 2>/dev/null || echo 0)" == "0" ]]; then
    # Re-evaluate against the live tmux window dimensions if an active client is attached.
    LIVE_DIMS="$(tmux display-message -t "${SESSION}:${WINDOW}" -p '#{window_height} #{window_width}' 2>/dev/null || true)"
    if [[ -n "$LIVE_DIMS" ]]; then
        read -r LIVE_ROWS LIVE_COLS <<<"$LIVE_DIMS"
        if is_portrait_geometry "$LIVE_ROWS" "$LIVE_COLS"; then
            INITIAL_LAYOUT="even-vertical"
        else
            INITIAL_LAYOUT="even-horizontal"
        fi
    fi
    tmux select-layout -t "${SESSION}:${WINDOW}" "$INITIAL_LAYOUT"
fi

# ------------------------------------------------------------------------------
# Step 6: Attach to the Workspace (Unless --no-attach Was Requested)
# ------------------------------------------------------------------------------
if [[ "$NO_ATTACH" -eq 1 ]]; then
    exit 0
fi

exec tmux attach-session -t "$SESSION"
