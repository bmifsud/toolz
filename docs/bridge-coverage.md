# Bridge routing coverage baseline

This is the first measured slice of the coverage work tracked by Toolz issue #46. It covers four maintained Python modules using the existing offline unittest suite. It does not represent repository-wide coverage or device acceptance.

## Reproduce

From the repository root, use Python 3.12.14 and an isolated virtual environment:

```bash
python3.12 -m venv .venv-coverage
.venv-coverage/bin/python -m pip install coverage==7.6.12
.venv-coverage/bin/python -m coverage erase --rcfile=coverage.bridge.ini
.venv-coverage/bin/python -m coverage run --rcfile=coverage.bridge.ini -m unittest discover -s android-personal-automator/bridge/tests -p 'test_*.py' -v
mkdir -p coverage-artifacts
.venv-coverage/bin/python -m coverage report --rcfile=coverage.bridge.ini > coverage-artifacts/coverage.txt
.venv-coverage/bin/python -m coverage xml --rcfile=coverage.bridge.ini
.venv-coverage/bin/python -m coverage json --rcfile=coverage.bridge.ini
```

The workflow **Bridge routing coverage** runs these tests on Ubuntu 24.04 with Python 3.12.14 and coverage.py 7.6.12. The runner image and action major versions can receive upstream updates; this pins the interpreter and coverage tool, not the entire OS image. The workflow publishes text, XML and JSON reports plus tool versions as the `bridge-routing-coverage` artifact. It runs on relevant pull requests, changes merged to main, and manual dispatch. Test failures fail the job; report collection is attempted even after a test failure. It uses read-only repository permissions, no device credentials, and no deployment steps.

## Initial measurement

Measured on 2026-10-28 at main revision `64be9874f64b1f3eeb60877b93beddef1f5d4094`, using Python 3.12.14 and coverage.py 7.6.12 on the managed Debian 13 runner. All 28 existing offline tests passed. The first [CI baseline run](https://github.com/bmifsud/toolz/actions/runs/40650231055) passed on revision `62ecc70da9b64dde7bd504a5badf41115d4a6053`, reproduced the 96.69% combined total, and published the four report files. This is pre-merge CI evidence, not post-merge or device verification.

| Module | Executed statements | Covered branch exits | Combined coverage |
| --- | ---: | ---: | ---: |
| `debian_diagnostics.py` | 16 / 16 | 2 / 2 | 100.00% |
| `request_router.py` | 45 / 45 | 18 / 18 | 100.00% |
| `routing_adapter.py` | 32 / 34 | 14 / 16 | 92.00% |
| `routing_receipts.py` | 35 / 36 | 13 / 14 | 96.00% |
| **Total in this scope** | **128 / 131 (97.71%)** | **47 / 50 (94.00%)** | **96.69%** |

Coverage.py's combined percentage counts executable statements and branch exits together. XML and JSON retain the underlying counts. No numerical threshold is introduced in this baseline change: first confirm this measurement in CI, review the remaining risk gaps, then set module-specific regression gates. A high combined percentage alone does not demonstrate correctness.

At this revision, missing paths include the adapter's early return for an unresolved route, its fallback for an unsupported target, and receipt rejection for a non-dictionary payload. These remain visible in reports; no lines or branches are marked excluded and no tests were added merely to inflate the baseline.

## Scope and exclusions

`coverage.bridge.ini` measures the bridge source directory and limits published reports to the four named modules. Commands select this dedicated configuration explicitly with `--rcfile`; unrelated coverage runs do not inherit this scope automatically. The explicit report scope keeps unrelated bridge code and tests out of this percentage; adding a new maintained module requires an explicit inventory update. These modules plan routing, define fixed diagnostic specifications, and validate receipts. Their test doubles and temporary launcher fixtures do not execute a real device command or prove remote authorization.

The remaining code is outside this initial measurement, not declared untestable:

- WebSocket relay/device/controller and bounded executor: require separate lifecycle, authentication, timeout, cancellation, restart and replay measurements, including integration evidence.
- Shell backup/scheduler/supervisor code: Python fixture tests do not measure shell line/branch coverage. Require a separate shell coverage approach plus isolated backup integrity/restore tests and approved device evidence.
- Kotlin/Android application and Gradle integration: require their own JVM/instrumentation reports and emulator/device flows.
- Cline, OmniRoute, SSH and Debian runtime integration: require authenticated readiness checks and end-to-end receipts; pure Python routing tests cannot establish connectivity.
- Cross-platform gateway packaging: needs platform-specific installation, upgrade, launch, credentials and failure validation.

Real emulator and physical-device round trips, backup upload/integrity/isolated restore, restart/disconnect and failure injection, independent post-merge verification, and the broader language/module inventory remain pending. This baseline does not close issue #46 or authorize merges or production changes.
