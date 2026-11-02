# Toolz

## Current state and capabilities

Reviewed 2026-11-02 against the default branch `main` (source tree `9ebcecaf2f18406358ab35f6f658ff796ab85ea9`). This is a source/documentation review; no application, device, external API or test suite was executed for this README update.

Backup tooling and offline request-planning/receipt modules; Remote Desktop Commander is the selected device-access mechanism.

Includes Tier-1/Tier-2 producers, preflight/cleanup, catch-up/cron/retention helpers, offline routing validation, advisory clients and ADLC checks.

Source entry points: [docs/architecture.md](docs/architecture.md) · [docs/adlc/status.md](docs/adlc/status.md).

**Verification:** Latest workflow observed: [success](https://github.com/bmifsud/toolz/actions/runs/41518239288) at commit `9ebcecaf2f18406358ab35f6f658ff796ab85ea9` on `main`. This result applies to that run's scope, not all capabilities.

**Limitations / pending validation:** Android app, network bridge and CLI executors are absent. Plans do not execute commands. Commander acceptance, both tiers' live upload/restore evidence and inherited release gates remain pending; no schedules or retention were changed.

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
