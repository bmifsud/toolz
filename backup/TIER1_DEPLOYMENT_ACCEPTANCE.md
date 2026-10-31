# Tier-1 Termux / Debian deployment and acceptance

The Termux scheduler invokes `backup/run_debian_noninteractive.sh`, but the backup producer runs from **Debian's separate checkout** at `/home/b/toolz/backup/backup_cline_omniroute.sh`. Updating the Termux checkout alone does not update the Debian copy. An older Debian producer can ignore `ANDROID_OUT` and fall back to `/sdcard`, leaving the scheduler unable to locate its archive even after upload.

## Deploy without touching existing archives

Run in **outer Termux**, with no backup running. Inspect `git status --short` and confirm the intended checkout/branch before deploying. The following uses the configured rootfs when available and preserves the previous Debian producer:

```bash
set -euo pipefail
cd "$HOME/toolz"
source "$HOME/.config/toolz-backup/config"
ROOT="${ROOTFS_DIR:-${ANDRONIX_ROOTFS:-$HOME/.andronix/distros/debian/rootfs}}"
SRC="$PWD/backup/backup_cline_omniroute.sh"
DST="$ROOT/home/${DEBIAN_USER:-b}/toolz/backup/backup_cline_omniroute.sh"
test -f "$SRC" && test -f "$DST"
bash -n "$SRC"
mkdir -p "$HOME/.local/state/toolz-backup"
exec 9>"$HOME/.local/state/toolz-backup/backup.lock"
flock -n 9 || { echo 'Backup already running'; exit 75; }
cp -p "$DST" "$DST.pre-path-fix"
cp -p "$SRC" "$DST"
chmod 700 "$DST"
bash -n "$DST"
cmp -s "$SRC" "$DST" || { echo 'Producer deployment mismatch'; exit 1; }
echo 'Debian producer synchronized'
```

Check the environment mapping through the launcher (this does **not** create a backup):

```bash
source "$HOME/.config/toolz-backup/config"
export BACKUP_PASSPHRASE="$(cat "$BACKUP_PASSPHRASE_FILE")"
bash backup/run_debian_noninteractive.sh /usr/bin/env | grep '^ANDROID_OUT='
unset BACKUP_PASSPHRASE
```

Expected for the standard layout: `ANDROID_OUT=/home/b/ClineOmniRouteBackups`.

## Acceptance criteria

1. Controlled backup through the updated launcher creates a new encrypted archive in configured `TIER1_LOCAL_DIR`, not the `/sdcard` fallback.
2. GPG decrypt plus tar listing succeeds.
3. Complete `rclone cat` readback of the remote archive has the same SHA-256 as the local archive.
4. Isolated extraction into a private temporary directory succeeds, and `PRAGMA integrity_check` reports `ok` when OmniRoute SQLite is present.
5. Do **not** use the producer's `--restore` mode for isolated testing: it modifies live Cline/OmniRoute state.
6. Retention and scheduled-runner behavior require separate validation; controlled backup tests do not exercise automatic cleanup or catch-up.

Device acceptance on 2026-10-27 (user-reported terminal output): archive `cline_omniroute_backup_20261027_010357.tar.gz.gpg` passed configured destination, decryption, remote SHA-256 comparison, isolated extraction, and SQLite integrity. This was after manually synchronizing the Debian producer. Tier-2 remains disabled pending its own acceptance.
