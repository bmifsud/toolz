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
