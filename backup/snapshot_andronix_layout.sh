#!/usr/bin/env bash
# Andronix modern-layout encrypted snapshot / SAFE STAGING restore.
set -euo pipefail
umask 077
usage(){ echo "Usage: $0 snapshot|--gdrive|--verify FILE|--restore-test FILE DESTINATION"; }
mode="${1:-}"
case "$mode" in snapshot|--gdrive) [[ $# == 1 ]] || { usage; exit 2; };; --verify) [[ $# == 2 ]] || { usage; exit 2; };; --restore-test) [[ $# == 3 ]] || { usage; exit 2; };; *) usage; exit 2;; esac
[[ "${PREFIX:-}" == /data/data/com.termux/files/usr || "${ALLOW_TEST_HOST:-0}" == 1 ]] || { echo "ERROR: outer Termux required" >&2; exit 1; }
home="$(cd "$HOME" && pwd -P)"
root="${ROOTFS_DIR:-${ANDRONIX_ROOTFS:-$home/.andronix/distros/debian/rootfs}}"
launcher="${START_SCRIPT:-$home/start-debian.sh}"
snap="${SNAP_DIR:-$home/.local/share/toolz-backup/tier2}"
remote="${GDRIVE_SNAP_REMOTE:-gdrive:ClineOmniRouteBackups/AndronixSnapshots}"
pass="${BACKUP_PASSPHRASE_FILE:?Set BACKUP_PASSPHRASE_FILE}"
[[ -s "$pass" && ! -L "$pass" ]] || { echo "ERROR: protected passphrase file missing" >&2; exit 1; }
for tool in tar gpg sha256sum python3; do command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 1; }; done
if pgrep -f '[p]root.*debian' >/dev/null 2>&1 && [[ "${ALLOW_TEST_HOST:-0}" != 1 ]]; then echo "ERROR: active Debian PRoot; refusing operation" >&2; exit 75; fi
mkdir -p "$snap"
# Do not allow archive traversal or symlinked rootfs/launcher paths.
[[ "$root" == "$home/.andronix/distros/debian/rootfs" && ! -L "$root" && -d "$root" ]] || { echo "ERROR: unexpected rootfs path/layout" >&2; exit 1; }
[[ "$launcher" == "$home/start-debian.sh" && -f "$launcher" && ! -L "$launcher" ]] || { echo "ERROR: unexpected launcher" >&2; exit 1; }
validate_archive(){
 local archive="$1" tmp="$2"
 gpg --batch --yes --pinentry-mode loopback --passphrase-file "$pass" --decrypt --output "$tmp" "$archive"
 python3 - "$tmp" <<'PY'
import sys,tarfile,pathlib
p=sys.argv[1]
with tarfile.open(p,'r:gz') as tar:
 names=tar.getmembers()
 if not names: raise SystemExit('Empty archive')
 for m in names:
  path=pathlib.PurePosixPath(m.name)
  if path.is_absolute() or '..' in path.parts or not (m.name=='start-debian.sh' or m.name.rstrip('/') in ('.andronix','.andronix/distros','.andronix/distros/debian','.andronix/distros/debian/rootfs') or m.name.startswith('.andronix/distros/debian/rootfs/')):
   raise SystemExit('Unsafe archive member: '+m.name)
  if m.issym() or m.islnk() or m.isdev() or m.isfifo():
   raise SystemExit('Unsupported special member: '+m.name)
PY
}
if [[ "$mode" == --verify || "$mode" == --restore-test ]]; then
 archive="$2"; [[ -s "$archive" ]] || { echo "ERROR: missing archive" >&2; exit 1; }
 tmp="$(mktemp "${TMPDIR:-$snap}/tier2-verify.XXXXXXXX.tar.gz")"
 trap 'rm -f -- "$tmp"' EXIT
 validate_archive "$archive" "$tmp"
 if [[ "$mode" == --restore-test ]]; then
  dest="$3"
  [[ ! -e "$dest" && ! -L "$dest" ]] || { echo "ERROR: destination must not exist" >&2; exit 1; }
  [[ "$dest" == /* && "$dest" != "$home" && "$dest" != "$root" && "$dest" != "$home/.andronix"* ]] || { echo "ERROR: use absolute staging destination outside Andronix" >&2; exit 1; }
  mkdir -m 700 "$dest"
  tar -xzpf "$tmp" -C "$dest" --no-same-owner --no-same-permissions
  [[ -d "$dest/.andronix/distros/debian/rootfs" && -f "$dest/start-debian.sh" ]] || { echo "ERROR: staged restore incomplete" >&2; exit 1; }
  echo "RESTORE TEST COMPLETE: $dest (live installation untouched)"
 else echo "VERIFIED: archive decrypts, parses, and passes member safety checks"; fi
 exit 0
fi
stamp="$(date +%Y%m%d_%H%M%S)"
archive="$snap/andronix-debian-$stamp.tar.gz.gpg"
[[ ! -e "$archive" ]] || { echo "ERROR: timestamp collision" >&2; exit 1; }
tmp="$(mktemp "${TMPDIR:-$snap}/tier2-build.XXXXXXXX.tar.gz")"
trap 'rm -f -- "$tmp"' EXIT
tar -czpf "$tmp" --exclude='.andronix/distros/debian/rootfs/tmp/*' --exclude='.andronix/distros/debian/rootfs/proc/*' --exclude='.andronix/distros/debian/rootfs/sys/*' --exclude='.andronix/distros/debian/rootfs/dev/*' -C "$home" .andronix/distros/debian/rootfs start-debian.sh
tar -tzf "$tmp" >/dev/null
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$pass" --symmetric --cipher-algo AES256 --output "$archive" "$tmp"
[[ -s "$archive" ]] || exit 1
if [[ "$mode" == --gdrive ]]; then
 command -v rclone >/dev/null || exit 1
 rclone copyto "$archive" "$remote/$(basename "$archive")"
 localhash="$(sha256sum "$archive" | awk '{print $1}')"
 remotehash="$(rclone cat "$remote/$(basename "$archive")" | sha256sum | awk '{print $1}')"
 [[ "$localhash" == "$remotehash" ]] || { echo "ERROR: cloud SHA-256 mismatch" >&2; exit 1; }
 echo "CLOUD VERIFIED: $(basename "$archive")"
fi
echo "SNAPSHOT READY: $archive"
