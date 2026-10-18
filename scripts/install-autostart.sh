#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/install-autostart.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Configures the Andronix Debian and Termux environments so that
#              launching Debian from Termux or Termux:Widget (.shortcut /
#              .shortcuts) automatically prepares and attaches to the 1-, 2-,
#              or 3-pane orientation-aware AI workspace:
#                1. Repairs any interrupted dpkg state and installs tmux if missing.
#                2. Creates global symlinks in /usr/local/bin and ~/ for agy,
#                   antigravity, codex, launch-ai-tmux.sh, start-debian.sh,
#                   start-debian-1.sh, start-debian-2.sh, and start-debian-3.sh.
#                3. Populates .shortcut/ and .shortcuts/ (in repo, ~/, and
#                   /sdcard/Download) with start-debian-{1,2,3}.sh and
#                   start-debian.sh (chmod 700 dirs, chmod +x scripts).
#                4. Adds an idempotent, loop-guarded auto-launch hook to ~/.bashrc.
#
# Usage:
#   ./scripts/install-autostart.sh
# ==============================================================================

set -euo pipefail

# Resolve repository and script paths dynamically.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCHER_SCRIPT="${SCRIPT_DIR}/launch-ai-tmux.sh"
BASHRC_FILE="${HOME}/.bashrc"

echo "==> [1/5] Verifying script permissions..."
chmod +x "${SCRIPT_DIR}"/*.sh

echo "==> [2/5] Populating .shortcut and .shortcuts directories..."
SHORTCUT_SCRIPTS=(start-debian.sh start-debian-1.sh start-debian-2.sh start-debian-3.sh)
SHORTCUT_TARGETS=(
    "${REPO_ROOT}/.shortcut"
    "${REPO_ROOT}/.shortcuts"
    "${HOME}/.shortcut"
    "${HOME}/.shortcuts"
)

if [[ -d /sdcard/Download ]]; then
    SHORTCUT_TARGETS+=(
        "/sdcard/Download/.shortcut"
        "/sdcard/Download/.shortcuts"
    )
fi

for target_dir in "${SHORTCUT_TARGETS[@]}"; do
    mkdir -p "$target_dir" 2>/dev/null || true
    chmod 700 "$target_dir" 2>/dev/null || true
    for sc in "${SHORTCUT_SCRIPTS[@]}"; do
        if [[ -f "${SCRIPT_DIR}/${sc}" ]]; then
            cp -f "${SCRIPT_DIR}/${sc}" "${target_dir}/${sc}" 2>/dev/null || true
            chmod +x "${target_dir}/${sc}" 2>/dev/null || true
        fi
    done
done
echo "    Installed ${SHORTCUT_SCRIPTS[*]} into .shortcut and .shortcuts."

# If invoked in outer Termux (outside Debian), also copy start-debian*.sh into Termux ~/
if [[ ! -f /etc/debian_version && "${ANDRONIX_DISTRO:-}" != "debian" ]]; then
    for sc in "${SHORTCUT_SCRIPTS[@]}"; do
        cp -f "${SCRIPT_DIR}/${sc}" "${HOME}/${sc}" 2>/dev/null || true
        chmod +x "${HOME}/${sc}" 2>/dev/null || true
    done
    echo "    Installed ${SHORTCUT_SCRIPTS[*]} into outer Termux home (${HOME}) and ~/.shortcut(s)."
    exit 0
fi

echo "==> [3/5] Checking tmux installation inside Debian..."
if ! command -v tmux >/dev/null 2>&1; then
    echo "    Installing tmux via apt-get..."
    sudo dpkg --configure -a
    sudo apt-get update
    sudo apt-get install -y tmux
else
    echo "    Found $(tmux -V)"
fi

echo "==> [4/5] Configuring /usr/local/bin and ~/ symlinks for CLI tools & launchers..."
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

for script_name in launch-ai-tmux.sh start-debian.sh start-debian-1.sh start-debian-2.sh start-debian-3.sh; do
    if [[ -f "${SCRIPT_DIR}/${script_name}" ]]; then
        sudo ln -sf "${SCRIPT_DIR}/${script_name}" "/usr/local/bin/${script_name}"
        if [[ "$script_name" == start-debian*.sh ]]; then
            ln -sf "${SCRIPT_DIR}/${script_name}" "${HOME}/${script_name}"
        fi
        if [[ -d /sdcard/Download ]]; then
            cp -f "${SCRIPT_DIR}/${script_name}" "/sdcard/Download/${script_name}" 2>/dev/null || true
        fi
    fi
done

echo "==> [5/5] Ensuring auto-launch hook is present in ${BASHRC_FILE}..."
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
Available Session Launchers (in ~/, ~/.shortcut/, ~/.shortcuts/, /usr/local/bin/):
  - start-debian-1.sh  Launches 1 session  (Pane 0: Antigravity)
  - start-debian-2.sh  Launches 2 sessions (Pane 0: Antigravity, Pane 1: Codex)
  - start-debian-3.sh  Launches 3 sessions (Pane 0: Antigravity, Pane 1: Codex, Pane 2: Jules)
  - start-debian.sh    Launches 3 sessions by default (or pass -1, -2, -3)

Orientation Behavior:
  - Portrait orientation:  Stacks active sessions vertically on top of each
                           other (even-vertical: Top to Bottom).
  - Landscape orientation: Arranges active sessions side-by-side in equal
                           columns (even-horizontal: Left to Right).
  - Rotating your device automatically switches between stacked and
    side-by-side layouts in real time.

Install Launchers & .shortcut in Outer Termux:
  Run this inside your outer Termux shell (outside Debian) to install all
  start-debian-{1,2,3}.sh scripts into Termux ~/, ~/.shortcut/, and ~/.shortcuts/:

    ~/.andronix/distros/debian/rootfs/home/b/toolz/scripts/install-autostart.sh
================================================================================
EOF
