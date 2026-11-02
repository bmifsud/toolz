# Verification map

Run checks from the repository root in a disposable Linux environment, with no production credentials, cloud remotes, archives or services. Backup fixtures run real GPG, SQLite and archive operations; review their isolation before execution.

## Prerequisites

Python 3, pytest, Bash, GnuPG (`gpg`, `gpgconf`), SQLite CLI (`sqlite3`), GNU core/archive tools (`tar`, `gzip`, `sha256sum`). A Python SQLite module alone is insufficient. Use a private short writable temporary path for GPG sockets. Install pytest in a virtual environment when needed; no provider credentials are needed for tests.

## Maintained offline gate

```bash
bash tests/run-all-tests.sh
```

Runs ADLC consistency/link validation, syntax checks for repository shell scripts, and pytest discovery in `tests/`, `backup/tests/` and `android-personal-automator/bridge/tests/`. It fails on errors and does not change executable bits. Advisory client tests mock external HTTP calls.

Individual checks:

```bash
python3 scripts/check_adlc.py
python3 -m pytest tests/ backup/tests/ android-personal-automator/bridge/tests/ -q
```

`backup/test_full_flow.sh` remains a historical selected subset. `tests/test-backup.sh` is a legacy shell suite with different retention assumptions, excluded from the maintained gate. Neither is evidence of full live acceptance. Only offline bridge routing/planning/receipt modules are present. Android build/instrumentation and network/device execution commands still do not apply.

## CI and limitations

[ADLC checks](../.github/workflows/adlc.yml) uses a read-only token and runs the maintained gate without provider credentials. The checkout action is pinned. Branch-protection configuration is separate: this workflow being present does not make it a required check. A maintainer must configure the required check through approved repository administration.

No gate here proves branch coverage, production restoration, encrypted cloud readback, scheduled catch-up, or emulator/tablet lifecycle. Keep failures, skips and expected failures explicit in the [evidence record](adlc/templates/evidence.md). Do not count a mock or historical result as live evidence.

## Operational acceptance

Follow [Tier-1 acceptance](../backup/TIER1_DEPLOYMENT_ACCEPTANCE.md). Tier-2 requires safe OmniRoute shutdown/WAL handling, snapshot/upload and isolated restoration with data integrity. Bridge requires authenticated connect/reconnect/cancel/restart and security checks on emulator then tablet after reviewed source is available.

Do not run producers, restores, cleanup, retention apply, installers or service start/stop as harmless checks. A temporary workspace alone does not isolate restore: HOME, services and cloud configuration must also be separated. Preserve live schedules and retention.

Never commit tokens, passphrases, credential files, raw environment dumps or private device logs. Record exact revision, environment, commands, expected/observed results and redacted artifacts. Required reviews/CI and all standing release gates remain mandatory.

## Downloadable CI evidence

Each ADLC run preserves an `adlc-offline-<run-id>-<attempt>` artifact for 14 days,
even when the gate fails. `receipt.json` records the actual checkout HEAD, gate outcome,
run identifiers and Python version. On PR runs, checkout HEAD can be a synthetic merge
commit; it must not be mislabeled as the PR branch head. The run page supplies that association.

`tests.xml` contains pytest JUnit results when pytest is reached. If setup, ADLC checks
or shell syntax fail earlier, that report may be absent; inspect the receipt and run logs.
An artifact existing is not a passing result. Neither JSON nor JUnit is a signed attestation.
These artifacts contain fixture-only test output and must never be used with live credentials.
No HOME/environment dump, provider key, archive or device screenshot is uploaded.
Download evidence before retention expires if it is needed for a release record.

## Replay persistence tests

The maintained gate includes the recovered host-only replay-store tests. Individually:

```bash
python3 -m unittest discover -s android-personal-automator/bridge/ws -p 'test_replay_store.py' -v
```

These use only disposable SQLite paths and cover duplicates/restart, capacity, concurrent
claims, corruption, symlink/inode substitution and permission drift. They do not connect a
relay or device and do not prove Termux/PRoot filesystem compatibility. Instantiating
ReplayStore without an explicit fixture path would create private local state; do not do
that during offline tests.
