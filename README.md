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

### 4. Termux command bridge (experimental)

The existing GitHub issue worker provides a **read-only, polling-based** connection to Termux. An experimental **WebSocket push transport** has been added to avoid issue polling, but it is **not yet validated on the tablet**.

- **Complete setup, security, validation, and rollback guide:** [WebSocket bridge README](android-personal-automator/bridge/ws/README.md)
- **Source:** [relay](android-personal-automator/bridge/ws/relay.py), [Termux listener](android-personal-automator/bridge/ws/device.py), [local diagnostic runner](android-personal-automator/bridge/readonly_runner.py)
- **GitHub PR:** [#23](https://github.com/bmifsud/toolz/pull/23)
- **Render:** A separate `toolz-termux-ws-relay` service was created. Its first deployment failed because credentials were not configured. Do not mistake service creation for a working endpoint.
- **Safety:** Only the `git-branch` diagnostic is exposed via WebSocket; no arbitrary shell commands or backup mutations. The current ChatGPT connector cannot directly submit WebSocket messages.
- **Existing services:** The original Android bridge and Tier-1/Tier-2 backup automation are separate and should remain unchanged.

**Verified:** The GitHub issue worker executed `git branch --show-current` on the tablet and returned exit code 0. **Not yet verified:** WSS authentication, relay health, tablet connection, or live round-trip.

## Repository documentation

- [Current architecture and integration boundaries](docs/architecture.md)
- [Installation prerequisites and verification map](docs/verification.md)
