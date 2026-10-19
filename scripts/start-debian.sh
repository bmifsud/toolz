#!/usr/bin/env bash
# ==============================================================================
# File:        scripts/start-debian.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Andronix Debian + AI Workspace launcher supporting 1, 2, or 3
#              sessions (defaults to 3 sessions unless specified via flags or
#              AI_SESSION_COUNT).
#
# Companion Scripts:
#   - scripts/start-debian-1.sh  Launches Debian with 1 AI session (Antigravity)
#   - scripts/start-debian-2.sh  Launches Debian with 2 AI sessions (Antigravity, Codex)
#   - scripts/start-debian-3.sh  Launches Debian with 3 AI sessions (Antigravity, Codex, Jules)
#
# Execution Contexts:
#   1. Outer Termux Shell:
#      Persists the requested session count (1, 2, or 3) and orientation into
#      the Debian rootfs (~/.andronix/distros/debian/rootfs/home/b) and starts
#      Debian via proot (or DEBIAN_LAUNCHER if set).
#   2. Inside Debian (proot):
#      Directly invokes launch-ai-tmux.sh with the requested session count.
#
# Usage:
#   ./start-debian.sh [--sessions 1|2|3] [-1|-2|-3] [--portrait|--landscape|--auto] [--no-attach]
# ==============================================================================

set -euo pipefail

DEFAULT_SESSIONS="${AI_SESSION_COUNT:-3}"
SESSION_COUNT="$DEFAULT_SESSIONS"
PASSTHROUGH_ARGS=()
ORIENTATION_OVERRIDE="${AI_ORIENTATION:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sessions|--panes|-n)
            if [[ $# -lt 2 ]]; then
                echo "Error: $1 requires a value (1, 2, or 3)" >&2
                exit 1
            fi
            SESSION_COUNT="$2"
            shift 2
            ;;
        --sessions=*|--panes=*)
            SESSION_COUNT="${1#*=}"
            shift
            ;;
        -1|--1|1)
            SESSION_COUNT=1
            shift
            ;;
        -2|--2|2)
            SESSION_COUNT=2
            shift
            ;;
        -3|--3|3)
            SESSION_COUNT=3
            shift
            ;;
        --portrait|--vertical|--stack)
            ORIENTATION_OVERRIDE="portrait"
            PASSTHROUGH_ARGS+=("--portrait")
            shift
            ;;
        --landscape|--horizontal)
            ORIENTATION_OVERRIDE="landscape"
            PASSTHROUGH_ARGS+=("--landscape")
            shift
            ;;
        --auto)
            ORIENTATION_OVERRIDE="auto"
            PASSTHROUGH_ARGS+=("--auto")
            shift
            ;;
        --no-attach)
            PASSTHROUGH_ARGS+=("--no-attach")
            shift
            ;;
        -h|--help)
            sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            echo "Usage: $0 [--sessions 1|2|3] [-1|-2|-3] [--portrait|--landscape|--auto] [--no-attach]" >&2
            exit 1
            ;;
    esac
done

if [[ ! "$SESSION_COUNT" =~ ^[123]$ ]]; then
    echo "Error: Session count must be 1, 2, or 3 (got '$SESSION_COUNT')" >&2
    exit 1
fi

export AI_SESSION_COUNT="$SESSION_COUNT"
if [[ -n "$ORIENTATION_OVERRIDE" ]]; then
    export AI_ORIENTATION="$ORIENTATION_OVERRIDE"
fi

# ------------------------------------------------------------------------------
# Context 1: Already Inside Debian (proot) -> Delegate to launch-ai-tmux.sh
# ------------------------------------------------------------------------------
if [[ -f /etc/debian_version || "${ANDRONIX_DISTRO:-}" == "debian" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -x "${SCRIPT_DIR}/launch-ai-tmux.sh" ]]; then
        exec "${SCRIPT_DIR}/launch-ai-tmux.sh" --sessions "$SESSION_COUNT" "${PASSTHROUGH_ARGS[@]}"
    elif [[ -x "$HOME/toolz/scripts/launch-ai-tmux.sh" ]]; then
        exec "$HOME/toolz/scripts/launch-ai-tmux.sh" --sessions "$SESSION_COUNT" "${PASSTHROUGH_ARGS[@]}"
    elif command -v launch-ai-tmux.sh >/dev/null 2>&1; then
        exec launch-ai-tmux.sh --sessions "$SESSION_COUNT" "${PASSTHROUGH_ARGS[@]}"
    else
        echo "Error: launch-ai-tmux.sh not found inside Debian." >&2
        exit 1
    fi
fi

# ------------------------------------------------------------------------------
# Context 2: Outer Android Termux Shell -> Enter Debian via proot
# ------------------------------------------------------------------------------
DISTRO_DIR="${ANDRONIX_DISTRO_DIR:-$HOME/.andronix/distros/debian}"
ROOTFS_DIR="${ANDRONIX_ROOTFS:-${DISTRO_DIR}/rootfs}"
SYSDATA_DIR="${DISTRO_DIR}/sysdata"
DEBIAN_USER="${DEBIAN_USER:-b}"
DEBIAN_HOME="${ROOTFS_DIR}/home/${DEBIAN_USER}"

if [[ -d "$DEBIAN_HOME" ]]; then
    echo "$SESSION_COUNT" > "${DEBIAN_HOME}/.ai_session_count" 2>/dev/null || true
    if [[ -n "$ORIENTATION_OVERRIDE" ]]; then
        echo "$ORIENTATION_OVERRIDE" > "${DEBIAN_HOME}/.ai_orientation" 2>/dev/null || true
    fi
    if [[ -n "${AI_PANE0_TITLE:-}" ]]; then
        echo "$AI_PANE0_TITLE" > "${DEBIAN_HOME}/.ai_pane0_title" 2>/dev/null || true
    fi
    if [[ -n "${AI_PANE0_CMD:-}" ]]; then
        echo "$AI_PANE0_CMD" > "${DEBIAN_HOME}/.ai_pane0_cmd" 2>/dev/null || true
    fi
    if [[ -n "${AI_PANE1_TITLE:-}" ]]; then
        echo "$AI_PANE1_TITLE" > "${DEBIAN_HOME}/.ai_pane1_title" 2>/dev/null || true
    fi
    if [[ -n "${AI_PANE1_CMD:-}" ]]; then
        echo "$AI_PANE1_CMD" > "${DEBIAN_HOME}/.ai_pane1_cmd" 2>/dev/null || true
    fi
    if [[ -n "${AI_PANE2_TITLE:-}" ]]; then
        echo "$AI_PANE2_TITLE" > "${DEBIAN_HOME}/.ai_pane2_title" 2>/dev/null || true
    fi
    if [[ -n "${AI_PANE2_CMD:-}" ]]; then
        echo "$AI_PANE2_CMD" > "${DEBIAN_HOME}/.ai_pane2_cmd" 2>/dev/null || true
    fi

    # Automatically populate ~/.shortcut and ~/.shortcuts in outer Termux
    if [[ -d "${DEBIAN_HOME}/toolz/scripts" ]]; then
        for sc_dir in "${HOME}/.shortcut" "${HOME}/.shortcuts"; do
            mkdir -p "$sc_dir" 2>/dev/null || true
            chmod 700 "$sc_dir" 2>/dev/null || true
            for sc_file in start-debian.sh start-debian-1.sh start-debian-2.sh start-debian-3.sh start-cline-1.sh start-cline-2.sh start-cline-3.sh; do
                if [[ -f "${DEBIAN_HOME}/toolz/scripts/${sc_file}" ]]; then
                    cp -f "${DEBIAN_HOME}/toolz/scripts/${sc_file}" "${sc_dir}/${sc_file}" 2>/dev/null || true
                    chmod +x "${sc_dir}/${sc_file}" 2>/dev/null || true
                fi
            done
        done
    fi
fi

# If a custom DEBIAN_LAUNCHER is explicitly provided (and is not this script itself), run it.
SELF_PATH="$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
if [[ -n "${DEBIAN_LAUNCHER:-}" ]]; then
    LAUNCHER_PATH="$(realpath "$DEBIAN_LAUNCHER" 2>/dev/null || echo "$DEBIAN_LAUNCHER")"
    if [[ "$LAUNCHER_PATH" != "$SELF_PATH" ]]; then
        exec "$DEBIAN_LAUNCHER"
    fi
fi

if [[ ! -d "$ROOTFS_DIR" ]]; then
    echo "Error: Andronix Debian rootfs not found at $ROOTFS_DIR" >&2
    exit 1
fi

# Start PulseAudio in Termux if available
if command -v pulseaudio >/dev/null 2>&1; then
    pulseaudio --start --exit-idle-time=-1 2>/dev/null || true
fi

unset LD_PRELOAD
PROOT_BIN="$(command -v proot || echo "/data/data/com.termux/files/usr/bin/proot")"

PROOT_ARGS=(
    --kill-on-exit
    --link2symlink
    --sysvipc
    -L
    "--kernel-release=6.12.0-andronix"
    "--change-id=10265:10265"
    -w "/home/${DEBIAN_USER}"
    -r "$ROOTFS_DIR"
    -b /dev
    -b /proc
    -b /sys
    -b /dev/urandom:/dev/random
)

[[ -d "${DISTRO_DIR}/shm" ]] && PROOT_ARGS+=(-b "${DISTRO_DIR}/shm:/dev/shm")
[[ -f "${SYSDATA_DIR}/loadavg" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/loadavg:/proc/loadavg")
[[ -f "${SYSDATA_DIR}/stat" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/stat:/proc/stat")
[[ -f "${SYSDATA_DIR}/uptime" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/uptime:/proc/uptime")
[[ -f "${SYSDATA_DIR}/version" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/version:/proc/version")
[[ -f "${SYSDATA_DIR}/vmstat" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/vmstat:/proc/vmstat")
[[ -f "${SYSDATA_DIR}/cap_last_cap" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/cap_last_cap:/proc/sys/kernel/cap_last_cap")
[[ -f "${SYSDATA_DIR}/max_user_watches" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/max_user_watches:/proc/sys/fs/inotify/max_user_watches")
[[ -f "${SYSDATA_DIR}/overflowuid" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/overflowuid:/proc/sys/kernel/overflowuid")
[[ -f "${SYSDATA_DIR}/overflowgid" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/overflowgid:/proc/sys/kernel/overflowgid")
[[ -e "${SYSDATA_DIR}/empty" ]] && PROOT_ARGS+=(-b "${SYSDATA_DIR}/empty:/sys/fs/selinux")
[[ -d /storage/emulated/0 ]] && PROOT_ARGS+=(-b /storage/emulated/0:/sdcard)

PROOT_ENV=(
    "HOME=/home/${DEBIAN_USER}"
    "USER=${DEBIAN_USER}"
    "LOGNAME=${DEBIAN_USER}"
    "SHELL=/bin/bash"
    "TERM=${TERM:-xterm-256color}"
    "LANG=C.UTF-8"
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games"
    "PULSE_SERVER=127.0.0.1"
    "TMPDIR=/tmp"
    "ANDRONIX_DISTRO=debian"
    "LIBGL_DRI3_DISABLE=1"
    "COLORTERM=${COLORTERM:-truecolor}"
    "AI_SESSION_COUNT=${SESSION_COUNT}"
    "AI_ORIENTATION=${ORIENTATION_OVERRIDE:-auto}"
)
[[ -n "${AI_PANE0_TITLE:-}" ]] && PROOT_ENV+=("AI_PANE0_TITLE=${AI_PANE0_TITLE}")
[[ -n "${AI_PANE0_CMD:-}" ]] && PROOT_ENV+=("AI_PANE0_CMD=${AI_PANE0_CMD}")
[[ -n "${AI_PANE1_TITLE:-}" ]] && PROOT_ENV+=("AI_PANE1_TITLE=${AI_PANE1_TITLE}")
[[ -n "${AI_PANE1_CMD:-}" ]] && PROOT_ENV+=("AI_PANE1_CMD=${AI_PANE1_CMD}")
[[ -n "${AI_PANE2_TITLE:-}" ]] && PROOT_ENV+=("AI_PANE2_TITLE=${AI_PANE2_TITLE}")
[[ -n "${AI_PANE2_CMD:-}" ]] && PROOT_ENV+=("AI_PANE2_CMD=${AI_PANE2_CMD}")

exec "$PROOT_BIN" "${PROOT_ARGS[@]}" /usr/bin/env -i "${PROOT_ENV[@]}" /bin/bash -l
