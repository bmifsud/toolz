#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/install-autostart.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Configures the Andronix Debian environment so that launching
#              Debian from Termux (via start-debian.sh) automatically prepares
#              and attaches to the 3-pane side-by-side AI workspace:
#                1. Repairs any interrupted dpkg state and installs tmux if missing.
#                2. Creates global symlinks in /usr/local/bin for agy, antigravity,
#                   codex, and launch-ai-tmux.sh.
#                3. Adds an idempotent, loop-guarded auto-launch hook to ~/.bashrc.
#                4. Copies launch-ai-tmux.sh to /sdcard/Download for easy access
#                   from outer Android/Termux if needed.
#
# Usage:
#   ./scripts/install-autostart.sh
# ==============================================================================

set -euo pipefail

# Resolve repository and script paths dynamically.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER_SCRIPT="${SCRIPT_DIR}/launch-ai-tmux.sh"
BASHRC_FILE="${HOME}/.bashrc"

echo "==> [1/4] Verifying launch-ai-tmux.sh permissions..."
chmod +x "$LAUNCHER_SCRIPT"

echo "==> [2/4] Checking tmux installation inside Debian..."
if ! command -v tmux >/dev/null 2>&1; then
    echo "    Installing tmux via apt-get..."
    sudo dpkg --configure -a
    sudo apt-get update
    sudo apt-get install -y tmux
else
    echo "    Found $(tmux -V)"
fi

echo "==> [3/4] Configuring /usr/local/bin symlinks for CLI tools..."
# Ensure ~/.local/bin exists and link 'antigravity' -> 'agy'
mkdir -p "${HOME}/.local/bin"
if [[ -x "${HOME}/.local/bin/agy" ]]; then
    ln -sf "${HOME}/.local/bin/agy" "${HOME}/.local/bin/antigravity"
    sudo ln -sf "${HOME}/.local/bin/agy" /usr/local/bin/agy
    sudo ln -sf "${HOME}/.local/bin/agy" /usr/local/bin/antigravity
fi

if [[ -x "${HOME}/.local/bin/codex" ]]; then
    sudo ln -sf "${HOME}/.local/bin/codex" /usr/local/bin/codex
fi

sudo ln -sf "$LAUNCHER_SCRIPT" /usr/local/bin/launch-ai-tmux.sh

# Optionally export a copy to shared storage (/sdcard/Download) if mounted
if [[ -d /sdcard/Download ]]; then
    cp -f "$LAUNCHER_SCRIPT" /sdcard/Download/launch-ai-tmux.sh 2>/dev/null || true
fi

echo "==> [4/4] Ensuring auto-launch hook is present in ${BASHRC_FILE}..."
MARKER="# Auto-launch 3-pane AI workspace (Antigravity, Codex, Jules) on interactive Debian login"

if ! grep -Fq "$MARKER" "$BASHRC_FILE" 2>/dev/null; then
    cat >> "$BASHRC_FILE" <<EOF

${MARKER}
if [[ \$- == *i* ]] && [[ -z "\${TMUX:-}" ]] && [[ -z "\${AI_TMUX_AUTO_LAUNCHED:-}" ]] && [[ -z "\${ANTIGRAVITY_AGENT:-}" ]] && [[ -z "\${SKIP_AI_TMUX:-}" ]]; then
    export AI_TMUX_AUTO_LAUNCHED=1
    if [[ -x "${LAUNCHER_SCRIPT}" ]]; then
        "${LAUNCHER_SCRIPT}"
    fi
fi
EOF
    echo "    Added auto-launch hook to ${BASHRC_FILE}."
else
    echo "    Auto-launch hook already present in ${BASHRC_FILE}."
fi

cat <<'EOF'

================================================================================
Installation Complete!
================================================================================
What happens now:
  - Whenever ~/start-debian.sh runs in Termux, Debian's ~/.bashrc automatically
    launches (or attaches to) the 3-pane side-by-side 'ai' tmux workspace.

Optional (Outer Termux Auto-Start):
  To make opening a new Termux window automatically run ~/start-debian.sh,
  run this one-liner inside your outer Termux shell (outside Debian):

    grep -q "start-debian.sh" ~/.bashrc 2>/dev/null || \
      echo '[ -z "$DEBIAN_STARTED" ] && export DEBIAN_STARTED=1 && exec ~/start-debian.sh' >> ~/.bashrc
================================================================================
EOF
