# OmniRoute & Cline CLI Backup, Restore & Google Drive Sync Utility

This utility provides automated, secure backup, AES-256 encryption, Google Drive cloud sync, and restoration for **OmniRoute** and **Cline CLI** running in Android Linux terminal environments (Android Linux Terminal VMs or Termux `proot-distro` Debian).

---

## Technical Constraints Addressed

1. **SQLite WAL Locking on OmniRoute**: OmniRoute stores provider keys and routing rules in `~/.omniroute/storage.sqlite` using Write-Ahead Logging (WAL) mode. Simple `cp` commands while the daemon is listening on port `20128` can cause snapshot corruption. This script uses the SQLite Online Backup API (`sqlite3 .backup`) to ensure atomic hot backups.
2. **Container Reset Volatility**: Android terminal environments can be reset or clear app data, wiping `~/`. This script exports backups directly to Android shared storage (`/mnt/shared` or `/sdcard`) and syncs them to Google Drive via `rclone`.
3. **Shared Storage Permission Stripping**: Moving files to Android shared storage strips file permission protections (`chmod 600`), exposing API keys in `secrets.json` and `.env`. This script uses symmetric AES-256 encryption (`gpg --symmetric`) before writing to shared storage or cloud sync.

---

## Components Backed Up

| Component | Target Paths | Backup Method |
|---|---|---|
| **OmniRoute Database & `.env`** | `~/.omniroute/storage.sqlite`, `~/.omniroute/.env` | SQLite Online Backup API (`sqlite3 .backup`) + `chmod 600` |
| **OmniRoute Routing Combos** | `http://localhost:20128/api/combos` | JSON API Export (`cline-plan-combo`, `cline-act-combo`) |
| **OmniRoute Systemd Service** | `~/.config/systemd/user/omniroute.service` | File Archive |
| **Cline CLI Global Config & Auth** | `~/.cline/data/globalState.json`, `~/.cline/data/secrets.json`, `~/.cline/data/settings/` | Encrypted Tarball (excluding heavy logs) |
| **Workspace Context & Tooling** | `.clinerules/`, `.memory/`, `.cline/scripts/verify.sh` | Workspace Archive + Git Version Control |

---

## Usage Guide

### 1. Prerequisites & Installation
Ensure `sqlite3`, `gpg`, `jq`, `curl`, `tar`, and `rclone` are installed:
```bash
sudo apt-get update && sudo apt-get install -y sqlite3 gnupg jq curl tar rclone
```
Configure your Google Drive remote in `rclone`:
```bash
rclone config
# Create a remote named 'gdrive' (Google Drive)
```

### 2. Make Script Executable
```bash
chmod +x ~/backup_cline_omniroute.sh
```

### 3. Execution Modes

- **Run Backup & Google Drive Sync**:
  ```bash
  ~/backup_cline_omniroute.sh backup "$(pwd)"
  ```
  *(Optional: export `BACKUP_PASSPHRASE="your_passphrase"` for non-interactive GPG encryption).*

- **Restore from Local Encrypted Backup**:
  ```bash
  ~/backup_cline_omniroute.sh --restore /mnt/shared/ClineOmniRouteBackups/cline_omniroute_backup_YYYYMMDD_HHMMSS.tar.gz.gpg /path/to/workspace
  ```

- **Restore Directly from Google Drive**:
  ```bash
  ~/backup_cline_omniroute.sh --restore-gdrive /path/to/workspace
  ```

---

## Tier-2 Rootfs Snapshots, Cron Scheduling & Full-Flow Tests

The Tier-1 utility documented above is retained unchanged. Additional development-stage components now live alongside it:

| File | Purpose |
| --- | --- |
| [`pre_snapshot_clean.sh`](pre_snapshot_clean.sh) | Runs Tier-1 and prepares Debian for a quiet snapshot |
| [`snapshot_andronix_debian.sh`](snapshot_andronix_debian.sh) | Creates AES-256 encrypted Classic Andronix rootfs snapshots, optionally uploading to Google Drive; supports guarded restore |
| [`TIER2_README.md`](TIER2_README.md) | Tier-2 compatibility, manual backup and recovery instructions |
| [`install_backup_cron.sh`](install_backup_cron.sh) | Adds managed cron entries while preserving unrelated entries |
| [`run_scheduled_backup.sh`](run_scheduled_backup.sh) | Serialized scheduled runs, logging, decryption/archive checks and remote comparison |
| [`SCHEDULING.md`](SCHEDULING.md) | Detailed scheduling, prerequisites, environment setup and safety limitations |
| [`test_full_flow.sh`](test_full_flow.sh) | Shell syntax checks and both isolated Python regression suites |
| [`tests/test_tier2.py`](tests/test_tier2.py) and [`tests/test_backup_flow.py`](tests/test_backup_flow.py) | Snapshot, restore, scheduling and failure-path tests |

### Planned backup cadence (device local time)

- **Tier-1:** Every day at **09:00 and 21:00**, designed for low-disruption application-state backups.
- **Tier-2:** **Monday, Wednesday and Friday at 03:00**, only when Debian PRoot is stopped and a fresh readiness marker exists.

### Test commands

```bash
cd ~/toolz/backup
bash -n backup_cline_omniroute.sh pre_snapshot_clean.sh snapshot_andronix_debian.sh install_backup_cron.sh run_scheduled_backup.sh
bash test_full_flow.sh
```

The GitHub Actions workflow at [`../.github/workflows/backup-regression.yml`](../.github/workflows/backup-regression.yml) runs the regression entrypoint on relevant changes.

### Important deployment limitations

**This is not yet a verified production backup system.** The expanded tests have been committed but their current pass status and 100% code coverage have not been established. Tier-2 cron cannot automatically create a consistent snapshot while an active PRoot development session is running; it skips instead of killing processes. Its preflight readiness marker must be produced following a successful Debian preparation and shutdown. Cron also requires device-specific launcher and credential configuration, and Android power management may prevent scheduled execution.

The current runner checks decryptability, archive readability and cloud size comparison, but **does not prove end-to-end remote cryptographic integrity or recoverability**. Validate the actual device layout and perform a disposable full restore before enabling unattended backups. See [SCHEDULING.md](SCHEDULING.md) for the setup and acceptance checklist.

---

## Where to Run Each Backup Script

The workflow spans **two separate environments**: the **Andronix Debian shell** (where OmniRoute/Cline run) and the **outer Termux host** (which owns the Debian rootfs and cron daemon). The two environments may have different `$HOME` directories and independent `~/toolz` clones.

| Script | Run in | Purpose |
| --- | --- | --- |
| `backup_cline_omniroute.sh` | Andronix Debian | Existing Tier-1 hot application-state backup |
| `pre_snapshot_clean.sh` | Andronix Debian | Tier-1 backup, OmniRoute checks and preparation before a rootfs snapshot |
| `snapshot_andronix_debian.sh` | Outer Termux host | Tier-2 encrypted rootfs snapshot/upload or guarded restore |
| `install_backup_cron.sh` | Outer Termux host | Install the managed cron entries |
| `run_scheduled_backup.sh` | Outer Termux host | Scheduled Tier-1/Tier-2 orchestration and verification |
| `test_full_flow.sh` | Compatible Linux test environment (Debian is suitable) | Isolated regression tests; not a real-device acceptance test |

### Step 1 — In Andronix Debian

Use the Debian terminal where your application state resides:

```bash
cd ~/toolz
git pull --ff-only origin main
cd backup

# Regression suite: run before relying on new backup code
bash test_full_flow.sh

# Prepare for a manual Tier-2 snapshot
bash pre_snapshot_clean.sh ~/toolz
```

The pre-snapshot step calls the existing Tier-1 backup script and checks SQLite/OmniRoute. **Do not run the full rootfs snapshot while Debian PRoot is still active.** Exit every Debian session, including tmux/VNC-related sessions, before the Termux snapshot.

### Step 2 — In the outer Termux host

Return to the original Termux prompt (outside Debian). Ensure the repository scripts are available in the **Termux filesystem**: `~/toolz/backup` here is **not necessarily** the same location as Debian's `~/toolz/backup`. If the repository is not present in Termux, clone it there or use a confirmed Termux-accessible path.

```bash
pkg install cronie gnupg tar rclone python coreutils util-linux

cd ~/toolz/backup
git pull --ff-only origin main

# Inspect and syntax-check before scheduling
bash -n install_backup_cron.sh run_scheduled_backup.sh snapshot_andronix_debian.sh
```

For a **manual** Tier-2 snapshot after Debian has exited and prerequisites are configured:

```bash
bash snapshot_andronix_debian.sh --gdrive
```

The Tier-2 script currently expects the Classic Andronix `~/debian-fs` and `~/start-debian.sh` layout, unless the relevant environment variables are set. Check these paths against your actual installation first.

### Step 3 — Install cron only after configuring and validating it

The scheduler requires a **tested** Debian launcher command (`TIER1_COMMAND`), a protected `BACKUP_PASSPHRASE_FILE`, a working `gdrive:` rclone remote, and a Termux-accessible repository path. Cron does **not** automatically inherit variables exported in an interactive shell; see [SCHEDULING.md](SCHEDULING.md) for environment setup, readiness markers and the Tier-2 safety gate.

After completing those checks:

```bash
cd ~/toolz/backup
bash install_backup_cron.sh
crond
crontab -l
```

The installed schedule uses the **device's local time**:

| Tier | Schedule |
| --- | --- |
| Tier-1 | Daily at **09:00 and 21:00** |
| Tier-2 | **Monday, Wednesday, Friday at 03:00** |

**Current limitations:** Tier-2 is not fully unattended; it skips if Debian is active or a fresh preflight readiness marker is missing. Android battery restrictions or Termux shutdown can prevent cron from running. The expanded test suite has not been confirmed passing with 100% measured coverage, and a disposable full restore is still required before treating this as production-ready.

See also [TIER2_README.md](TIER2_README.md), [SCHEDULING.md](SCHEDULING.md) and [test_full_flow.sh](test_full_flow.sh).
