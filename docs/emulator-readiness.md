# Emulator readiness evidence

The **Android Emulator Readiness** workflow is the host/AVD readiness stage of Toolz issue #36. It boots a disposable Android 11/API 30 `google_apis` x86_64 image with the Pixel 2 hardware profile and explicitly addresses `emulator-5554`. It does not install the Toolz bridge, run a gateway/controller request, validate Cline or OmniRoute, or use a physical tablet.

The workflow selects Ubuntu 24.04. The emulator-runner action and SDK/system-image revisions may receive upstream updates; the API, target and ABI are fixed, not the complete system-image build. Artifact tool versions document the actual environment.

## Artifact contents

The `emulator-readiness` artifact is attempted with `always()`, including when emulator startup or boot times out:

- `host-capability.txt`: host OS/CPU, memory/disk availability, and KVM existence/access before emulator setup.
- `tool-versions.txt`: bounded ADB/emulator version and acceleration diagnostics after the emulator step. Individual probes have ten-second timeouts and may report missing tools if setup failed.
- `result.txt`: explicit `PASS` for boot completion plus ADB, or `NOT_READY` for an unsuccessful emulator step. Both labels state that gateway end-to-end validation was not run. A successful readiness result is not an issue-closure or merge approval.
- `android-version.txt`, `device-abi.txt`, `adb-devices.txt`: fixed diagnostic output captured only when the disposable AVD reaches the verification script. No full device property dump is collected.
- `emulator-console-tail.txt`: the last 64 KiB of the disposable emulator's console output, or an explicit notice when launch was not reached. Common bearer/token/password/secret patterns are redacted. This is bounded diagnostic evidence, not a general secret-scrubbing guarantee.

Every uploaded text file is capped at 64 KiB. No application or production credentials are supplied to this workflow; do not add secrets, user accounts or production app data to the readiness AVD. The raw temporary emulator console stays outside the artifact directory. The emulator action can terminate the AVD before the final collector, so the collector uses the console file rather than requiring a still-running emulator or logcat. Logs remain subject to GitHub runner/job cancellation limits; `always()` cannot guarantee artifacts after a forcibly terminated runner.

## Validation status

The existing readiness draft had successful CI runs before this evidence change. This change has only been validated locally for YAML structure, shell syntax and successful/failed/not-launched evidence collection using synthetic, non-secret fixtures. A local emulator is unavailable. The changed workflow still needs an actual draft CI run before its new boot/artifact behavior is considered verified.

After readiness passes, issue #36 still requires the separate authenticated gateway submission → durable queue → claim → allowlisted diagnostic → bounded receipt → status round trip and its negative/lifecycle cases on the emulator. Physical-device testing follows its own authorization and readiness gates. No readiness artifact alone establishes a live Termux connection or permission to merge/deploy.

## Post-boot ADB retry (2026-10-28)

CI run [40651085041](https://github.com/bmifsud/toolz/actions/runs/40651085041) reached `sys.boot_completed=1` in the emulator runner, but its post-boot unlock command stalled and the readiness script's subsequent single 10-second ADB query failed. This is an observed timing failure, **not** proof of a gateway or Termux connection. The workflow now retries the exact boot-property check for at most 12 attempts, with a 15-second per-query bound and 5-second pauses, and fails closed if no exact `1` is observed. Version/ABI probes have 30-second limits. A failure still uploads redacted, bounded readiness evidence. This change requires a fresh CI run on its exact commit before it can be considered verified.
