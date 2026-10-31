# Installation prerequisites and verification map

Use this guide with the [current architecture map](architecture.md). It describes the same pinned `main` source baseline, not an instruction to deploy draft code or operate an existing tablet. No device connection is required for the offline commands below.

## Local source and prerequisites

Use a reviewed checkout and a disposable Linux development environment for Bash/backup tests. Keep personal credential files, real cloud remotes, production archives and live services outside that environment. Test fixtures replace selected commands, but isolation must be checked before broadening the suite or switching branches.

- Python: CI uses Python 3.12 for the backup/router jobs. Standard-library bridge/router tests do not need provider credentials or API calls. Backup fixtures additionally need `pytest`, GnuPG (`gpg` and `gpgconf`), the SQLite command-line tool, Bash and GNU core tools; archive tests use tools such as `tar` and `gzip`. A Python SQLite module alone does not provide the `sqlite3` executable.
- Android: use JDK 17, the checked-in Gradle 8.11.1 wrapper and SDK platform 36/build-tools 36.0.0. Source pins Android Gradle plugin 8.10.1 and Kotlin 2.2.0. The app supports API 26 and newer; compile/target SDK is 36. See the [app build configuration](../android-personal-automator/app/build.gradle.kts) and [Android workflow](../.github/workflows/android.yml).
- Emulator: Android instrumentation additionally needs an installed emulator/system image and a capable host. KVM availability, boot completion and ADB must be observed, not assumed from a Linux/PRoot environment.
- Operational integration: Termux, Termux:Boot, PRoot/Andronix, Cline, OmniRoute, cloud configuration and credentials are separate target-specific prerequisites. Do not install or configure them merely to run offline routing tests.

An optional Python test environment can be prepared from the repository root:

```bash
python3 -m venv .venv-tests
. .venv-tests/bin/activate
python -m pip install pytest
```

Install system prerequisites through the environment's supported package manager; no package installation is performed by these commands except `pytest` inside the virtual environment. Network access and third-party package downloads may be needed during setup. Keep test results tied to the actual interpreter and tool versions used.

## Offline verification commands

Run from the repository root after prerequisites are present:

```bash
python -m unittest discover -s android-personal-automator/bridge/tests -p 'test_*.py' -v
python -m unittest discover -s android-personal-automator/bridge -p 'test_*.py' -v
python -m unittest discover -s android-personal-automator/device-tests -p 'test_*.py' -v
python -m pytest android-personal-automator/bridge/test_*static.py -q
python -m pytest backup/tests/ -q
```

The first command exercises classification, planning, fixed Debian specifications and receipt validation. The second covers proposal server/static setup/supervisor behavior with test fixtures. The third tests device-checklist and artifact-provenance helpers offline. The explicit pytest static-file command also collects function-style shell/setup source checks that unittest discovery does not collect. These commands do not establish an authenticated remote diagnostic, Android instrumentation pass or real device lifecycle result.

The backup command executes real local GPG/SQLite/archive operations against fixture homes and directories; selected cloud/service commands are mocked. It is not a command to back up or restore a production installation. GPG fixtures use a short private home and stop only that fixture's agents; ensure a short writable temporary path is available. Review failures and expected-failure markers rather than equating process success with complete restoration acceptance.

For the existing CI-selected backup subset and syntax checks:

```bash
bash backup/test_full_flow.sh
```

That script explicitly names five modules; it does not discover every `backup/tests` module. The full pytest discovery command above covers additional modules present in this revision. Neither invocation measures Bash branch coverage or verifies cloud/device behavior.

Android compilation, lint and JVM unit tests can run from the Android project directory:

```bash
cd android-personal-automator
./gradlew --no-daemon :app:assembleDebug :app:lintDebug :app:testDebugUnitTest
```

This downloads build dependencies and writes build outputs. Running `connectedDebugAndroidTest` instead requires an explicitly selected disposable emulator/device and executes instrumentation; it is a separate gate, not an offline source check. Build success does not prove capture consent, permissions or network persistence on a physical tablet.

## Existing entry-point caveats

| Entry point | What it actually does |
| --- | --- |
| [Test Suite workflow](../.github/workflows/test.yml) | Checks for the removed legacy `scripts/` component and skips its test when absent. A green result is not proof that current backup/router/Android suites ran |
| [Master shell runner](../tests/run-all-tests.sh) | Changes script executable bits, then runs the legacy shell backup suite. It does not discover all maintained tests |
| [Legacy backup shell tests](../tests/test-backup.sh) | Use a temporary HOME but inherit other environment/tool state; they contain a five-archive retention expectation that differs from the producer's preserve-all behavior. Do not use this as the current isolated acceptance gate |
| [Backup regression workflow](../.github/workflows/backup-regression.yml) | Installs dependencies and invokes the explicitly selected fixture subset, not all backup tests |
| [Hybrid Router Tests workflow](../.github/workflows/hybrid-router-tests.yml) | Runs the offline routing test directory |
| [Android workflow](../.github/workflows/android.yml) | Separate build/lint/JVM/offline checks and API 36 emulator instrumentation jobs. App instrumentation is distinct from the draft Termux gateway end-to-end scenario |

## Commands that change installation or data

Do not treat backup producers, `--restore`/`--restore-gdrive`, scheduled runners, retention `--apply`, snapshot/cleanup scripts, cron/catch-up installers, secure-start/boot installers or supervisor start/stop as harmless verification commands. They can create/delete archives, overwrite Cline/OmniRoute state, invoke services, alter startup configuration or launch a listener. Inspect the exact script, configuration and target before authorized operational use.

The Tier-1 producer's restore mode writes into the selected HOME and workspace and can invoke service commands. An isolated recovery test needs a genuinely separate environment and controlled fixtures; pointing only the workspace argument at a temporary directory is insufficient. Do not use existing encrypted archives or real cloud remotes for fixture testing. Keep backup schedules and archive retention unchanged during independent validation.

Never commit provider keys, bearer tokens, GPG passphrases, credential files, environment dumps or unredacted device output. Configure distinct controller/device credentials through approved mechanisms only when transport is ready. Source-level token checks and output bounds are not evidence that a deployed service is securely configured.

## Evidence and completion

For this documentation change, relative links/paths were checked and the three offline unittest discovery groups above passed on the managed Python 3.12 runner (28 routing, 20 bridge and 7 device-helper tests). The explicit pytest static-file command also passed all five collected tests. The bridge tests emitted existing unclosed-pipe resource warnings; their assertions passed. This does not rerun every documented platform command on a clean machine. Android build/instrumentation, real Termux/PRoot operation, Cline interface compatibility, actual cloud upload/readback, scheduled catch-up, failure recovery and isolated production-compatible restore remain separate evidence requirements.

For each workstream, record the exact reviewed revision, environment, reproducible command, expected/observed result and redacted artifact. Require security/failure-path checks and appropriate emulator/device evidence before integration. Verify the merged revision independently before closing its task. Keep unavailable checks explicitly pending; green CI alone is insufficient.
