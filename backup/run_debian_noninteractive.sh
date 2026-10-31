#!/usr/bin/env bash
# Termux-only, noninteractive Debian command launcher. Never starts tmux.
set -euo pipefail
umask 077
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr || "${ALLOW_TEST_HOST:-0}" == 1 ]] || { echo 'Run in outer Termux' >&2; exit 1; }
[[ $# -ge 1 ]] || { echo "Usage: $0 /absolute/debian/command [args...]" >&2; exit 2; }
DISTRO_DIR="${ANDRONIX_DISTRO_DIR:-$HOME/.andronix/distros/debian}"
ROOTFS="${ANDRONIX_ROOTFS:-$DISTRO_DIR/rootfs}"
USER_NAME="${DEBIAN_USER:-b}"
[[ -d "$ROOTFS/home/$USER_NAME" ]] || { echo "Missing Debian home: $ROOTFS/home/$USER_NAME" >&2; exit 1; }
command -v proot >/dev/null || { echo 'Install proot in Termux' >&2; exit 1; }
args=(--kill-on-exit --link2symlink --sysvipc -L --kernel-release=6.12.0-andronix --change-id=10265:10265 -w "/home/$USER_NAME" -r "$ROOTFS" -b /dev -b /proc -b /sys -b /dev/urandom:/dev/random)
[[ -d "$DISTRO_DIR/shm" ]] && args+=(-b "$DISTRO_DIR/shm:/dev/shm")
for f in loadavg stat uptime version vmstat cap_last_cap max_user_watches overflowuid overflowgid; do
 [[ -f "$DISTRO_DIR/sysdata/$f" ]] && args+=(-b "$DISTRO_DIR/sysdata/$f:/proc/$f")
done
[[ -e "$DISTRO_DIR/sysdata/empty" ]] && args+=(-b "$DISTRO_DIR/sysdata/empty:/sys/fs/selinux")
[[ -d /storage/emulated/0 ]] && args+=(-b /storage/emulated/0:/sdcard)
# Inherit only the required secret, never an interactive shell startup or tmux.
pass="${BACKUP_PASSPHRASE:-}"
[[ -n "$pass" ]] || { echo 'BACKUP_PASSPHRASE must be provided by the scheduler' >&2; exit 1; }
# Resolve the Termux archive destination to its Debian-visible path.
# This keeps the producer output and scheduler verification pointed at one directory.
host_out="${TIER1_LOCAL_DIR:-${ROOTFS_DIR:-$ROOTFS}/home/$USER_NAME/ClineOmniRouteBackups}"
case "$host_out" in
 "$ROOTFS"/*) debian_out="${host_out#"$ROOTFS"}" ;;
 /sdcard/*) debian_out="$host_out" ;;
 *) echo "Unsupported Tier-1 output path outside Debian rootfs or /sdcard: $host_out" >&2; exit 1 ;;
esac
unset LD_PRELOAD
exec proot "${args[@]}" /usr/bin/env -i HOME="/home/$USER_NAME" USER="$USER_NAME" LOGNAME="$USER_NAME" SHELL=/bin/bash TERM="${TERM:-xterm-256color}" LANG=C.UTF-8 PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin TMPDIR=/tmp ANDRONIX_DISTRO=debian SKIP_AI_TMUX=1 ANDROID_OUT="$debian_out" BACKUP_PASSPHRASE="$pass" /bin/bash --noprofile --norc -c 'exec "$@"' backup-runner "$@"
