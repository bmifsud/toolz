# OmniRoute & Cline CLI Backup & Restore Utility for Android Debian Environments

This utility provides automated, secure backup and restoration for **OmniRoute** and **Cline CLI** running in Android Linux terminal environments (such as native Android Linux Terminal VMs or Termux `proot-distro` Debian).

---

## Technical Constraints Addressed

1. **SQLite WAL Locking on OmniRoute**: OmniRoute stores provider keys and routing rules in `~/.omniroute/storage.sqlite` using Write-Ahead Logging (WAL) mode. Simple `cp` commands while the daemon is listening on port `20128` can cause snapshot corruption. This script uses the SQLite Online Backup API (`sqlite3 .backup`) to ensure atomic hot backups.
2. **Container Reset Volatility**: Android terminal environments can be reset or clear app data, wiping `~/`. This script exports backups directly to Android shared storage (`/mnt/shared` or `/sdcard`).
3. **Shared Storage Permission Stripping**: Moving files to Android shared storage strips file permission protections (`chmod 600`), exposing API keys in `secrets.json` and `.env`. This script uses symmetric AES-256 encryption (`gpg --symmetric`) before writing to shared storage.

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

### 1. Prerequisites
Ensure `sqlite3`, `jq`, `curl`, and `gnupg` are installed:
```bash
sudo apt-get update && sudo apt-get install -y sqlite3 jq curl gnupg
```

### 2. Make Script Executable
```bash
chmod +x backup_cline_omniroute.sh
```

### 3. Run a Backup
Run the script from your project repository root (you will be prompted for a GPG passphrase):
```bash
./backup_cline_omniroute.sh backup "$(pwd)"
```

### 4. Verify Backup Archive
Inspect the backup archive manifest without extracting to disk:
```bash
gpg --decrypt /mnt/shared/ClineOmniRouteBackups/cline_omniroute_backup_*.tar.gz.gpg 2>/dev/null | tar -tzv
```
*(Replace `/mnt/shared` with `/sdcard` if running under Termux).*

### 5. Restore from Backup
```bash
./backup_cline_omniroute.sh --restore /mnt/shared/ClineOmniRouteBackups/cline_omniroute_backup_YYYYMMDD_HHMMSS.tar.gz.gpg /path/to/workspace
```
