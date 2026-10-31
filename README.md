# Toolz

Toolz is an integrated repository providing automated backup & recovery management, an Android personal automator bridge (Termux/Android integration), and test suites.

## Architecture & Components

1. **Backup & Recovery (`backup/`)**
   - **`backup_cline_omniroute.sh`**: Main script for snapshotting and backing up Cline OmniRoute environments.
   - **`snapshot_andronix_debian.sh` & `snapshot_andronix_layout.sh`**: Snapshot creation utilities for Andronix Debian environments.
   - **`install_backup_cron.sh` & `run_scheduled_backup.sh`**: Cron setup and execution for scheduled backups.
   - **`check_missed_backups.sh` & `install_catchup.sh`**: Catch-up mechanisms for ensuring missed backup intervals are handled.

2. **Android Personal Automator (`android-personal-automator/`)**
   - **`bridge/server.py`**: Python server facilitating communication between Termux and Android automation components.
   - **`termux-diagnostic-bridge.sh`**: Diagnostic script for validating Termux-Android connectivity.
   - **`app/`**: Android application source files (Gradle-based build).

3. **Test Suites (`tests/`, `backup/tests/`)**
   - **`tests/run-all-tests.sh`**: Master test runner executing verification and test flows.
   - **`backup/tests/`**: Unit and integration tests (`test_tier1.py`, `test_tier2.py`, `test_backup_flow.py`) validating backup functionality.

---

## Usage Guide

### 1. Running Backups
Execute the backup script directly:
```bash
./backup/backup_cline_omniroute.sh
```
To install scheduled cron backups:
```bash
./backup/install_backup_cron.sh
```

### 2. Android Automator Bridge
To run the Termux bridge server:
```bash
python3 android-personal-automator/bridge/server.py
```
To run diagnostics:
```bash
./android-personal-automator/termux-diagnostic-bridge.sh
```

### 3. Running Tests
To run the master test suite:
```bash
./tests/run-all-tests.sh
```
To run backup tests specifically using pytest:
```bash
pytest backup/tests/
```

## Repository documentation

- [Current architecture and integration boundaries](docs/architecture.md)
- [Installation prerequisites and verification map](docs/verification.md)
