# Toolz

Toolz currently contains Termux/Andronix backup scripts, fixture tests and optional AI advisory clients.
Device access uses **Remote Desktop Commander**. Offline routing/planning and receipt validation are available; device plans target Desktop Commander rather than direct Termux/Andronix connections. The Android app, network bridge and CLI executors remain absent; plans do not execute actions.

## Start here

- [ADLC workflow](docs/adlc/README.md): intent, plan, implementation, verification and release.
- [Architecture](docs/architecture.md): current components and trust boundaries.
- [Verification](docs/verification.md): prerequisites, safe checks and pending device evidence.
- [Release ledger](docs/adlc/status.md): blockers and evidence requirements.

## Offline checks

In a disposable environment with Python, pytest, Bash, GnuPG, SQLite CLI and GNU archive tools:

```bash
bash tests/run-all-tests.sh
```

The runner checks documentation, shell syntax and all maintained Python tests. It does not prove live cloud uploads, scheduling, device behavior or restoration acceptance.

## Operational scripts

`backup/` includes producers, snapshot/cleanup helpers, cron/catch-up installers and retention.
These can alter services, schedules and data. Review the exact script and target before explicitly authorized use; never run them as diagnostics.
Schedules and retention are unchanged by the ADLC setup. No live deployment is implied.

## Device access

Use Remote Desktop Commander to select the authorized device and confirm its environment before running commands. Legacy `@Termux` and `@Debian` request labels are recognized only as environment hints and route to `desktop_commander`; they do not connect to those environments directly. `@Desktop Commander` and `@Remote Desktop Commander` explicitly select the same planning destination.

Planning does not call Desktop Commander or establish a session. Availability flags are caller-supplied hints, not authentication. The tool must independently check device selection, authorization and operation scope. Backup environment paths and scheduling helpers remain necessary and unchanged.
