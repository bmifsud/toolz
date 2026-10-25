# MediaProjection tablet validation

## Result: physical-device validation pending

Reviewed on 25 October 2026. This environment has no Android tablet connection,
ADB transport, or Termux-control connector. No tablet screenshot was taken or
displayed here, and no Android permissions were granted by this review.

| Requested check | Confirmed evidence | Tablet status |
| --- | --- | --- |
| Obtain trusted successful APK | Downloaded the main-push artifact below; ZIP and APK SHA256 verified | Installation pending |
| Explicit screen-capture consent | Source uses Android `createScreenCaptureIntent`, validates RESULT_OK, and consumes authorization once | Pending real system dialog and repeated-consent test |
| Local Termux screenshot | Source displays one Bitmap in a secure ImageView, without saving it | Pending split-screen capture and visible marker |
| Foreground notification and STOP | Notification declares mediaProjection type and STOP PendingIntent; first frame stops projection | Pending actual notification and tapping STOP during projection |
| Cleanup | Source releases VirtualDisplay, closes ImageReader, stops projection, removes notification and recycles preview; no screenshot-file write path | Pending resource dumps and before/after file inventory |
| Background, rotation, denial, process interruption | Existing emulator lifecycle tests cover ownership revocation/recreation and unauthorized synthetic frames | Pending all real tablet scenarios |
| No unauthorized screenshot transmission | Capture classes have no network, file or sharing calls; ProposalClient accepts typed task text only | Pending UID-level traffic observation |

Source review supports a local-only capture path. It does **not** prove runtime
network behavior or successful real MediaProjection capture on this tablet.
The app has INTERNET permission for separately requested AI proposals.

## Reviewed APK and provenance

- Repository: `bmifsud/toolz`; workflow: `.github/workflows/android.yml`.
- [Successful main-push run 40146989153](https://github.com/bmifsud/toolz/actions/runs/40146989153), created 2026-10-25 00:30:52 UTC.
- Commit: `8b5b651f2531baa1a1d5f34d05a0da9eeb8b4330`.
- [Artifact android-debug-apk, ID 12580678663](https://github.com/bmifsud/toolz/actions/runs/40146989153/artifacts/12580678663).
- ZIP SHA256: `3edfa59dec87fd11a3a5c606a4272753a59b78a7db8d34110d1d9aa5bc5865a5`.
- Extracted `app-debug.apk` SHA256: `5ce53a5cee8ac47f2ebf962beb8a0b9547ecf3673274e4657663214f562fd8f6`.
- APK: version 0.4.0 / code 5; Android 8+; target SDK 36.
- Both build and Android 16 emulator jobs succeeded. Job logs report 10 completed
  instrumentation tests. Those tests do not grant real capture consent or capture
  real screen pixels. The build job also ran lint, JVM tests and bridge tests.

This was the latest successful Android main-push run when the review began.
The downloader deliberately pins that reviewed build; it never silently selects
a newer PR, fork, failed run or replacement artifact. Trust is based on repository,
workflow, main-push identity and exact downloaded bytes. The commit is unsigned;
no release-key identity or artifact attestation has been verified. This is a
debug build. Android's installer still checks its APK signature.

The capture source at the reviewed commit matches main at `4da11ce` before this
PR's changes. The pinned APK does **not** contain this PR's service cleanup fixes.
After merge, review a new successful main-push build and update the pinned IDs
and hashes before claiming the fixed APK was tested.

## Safe Termux installation

Use a fresh checkout of this PR branch for these scripts (after merge, use main).
Do not overwrite a working checkout or existing test reports.

```bash
pkg install git python gh
git clone --single-branch --branch fix/android-capture-device-validation \
  https://github.com/bmifsud/toolz.git "$HOME/toolz-capture-validation"
cd "$HOME/toolz-capture-validation/android-personal-automator"
gh auth status
# If authentication is missing, authenticate yourself with gh auth login.
python3 device-tests/fetch_apk.py
termux-open --view --content-type application/vnd.android.package-archive \
  "$HOME/.local/share/toolz-device-test/build-40146989153/app-debug.apk"
```

The downloader checks completed/success, push, main, workflow path, source
repository, commit, artifact ID/name/expiry/digest, archive member and APK hash
before writing an APK. It refuses overwriting an existing APK. It needs `gh`
with read access to the workflow artifact, not a token pasted into a script.
Alternatively download the artifact ZIP from the run page while signed in, and
check both hashes above locally before opening its APK.

Approve installation in Android's package installer yourself. If Android asks,
allow installation from Termux through the normal Settings screen, then disable
that allowance after installation. Stop if Android blocks installation or reports
a signature mismatch. CI debug signing keys can differ across builds: do not
uninstall the existing app to force an update (that would remove its saved state).
Never use root, silent installation, permission-grant commands, or automated taps
to accept consent. Enable Accessibility and notifications only through Android's
own UI after reviewing the app disclosure. Do not enter tokens for capture tests.

## Run the executable checklist

```bash
python3 device-tests/checklist.py
```

It guides 13 manual cases and writes a private local JSON report at
`~/.local/state/toolz-device-test/results.json`. All cases start **pending**.
Pass/fail entries are explicitly human-reported observations. Unobserved,
interrupted, unavailable, or too-fast-to-test cases stay pending. Use `--output`
with a new filename for a second run; existing reports are preserved. To create
an all-pending report without prompts:

```bash
python3 device-tests/checklist.py --initialize --output "$HOME/capture-pending.json"
```

Neither checklist mode runs ADB, captures pixels, grants permissions, installs
anything or sends results. The APK downloader only contacts GitHub. Do not commit
private reports, screenshots, tokens, device serials or packet contents.

### Termux capture and lifetime expectations

Show only a harmless marker in Termux: `printf 'LOCAL CAPTURE TEST - no secrets\n'`.
Arrange Termux beside the capture activity using Android split screen. Keep both
visible and explicitly select the entire display in Android's consent dialog.
The preview should show the Termux pane; the app's own FLAG_SECURE pane can be
black. Protected content must stay hidden. No image file needs to be created.

Switching fully to another app cancels capture/preview by design. Android's
single-app selector can launch the selected app and background the host, so that
route may cancel too. Record that result; do not loosen lifecycle checks or bypass
permissions to obtain a screenshot. If split screen is unavailable, keep the
Termux preview test pending. On older Android versions, use only the screen-sharing
options the OS actually offers.

Projection ends after the first frame, with an eight-second service deadline and
a ten-second activity deadline. Preview lasts at most 30 seconds. The foreground
notification can disappear before a person can tap its STOP action. Observing a
preview or pressing its discard button does not prove notification STOP worked.
Mark that case pending if the live window cannot be tested. Check overlay Stop,
notification STOP, preview discard, timeout, Home, rotation, consent denial and
Force stop separately, with fresh OS consent for each attempt.

After Force stop Android reclaims process resources; callbacks such as onDestroy
are not guaranteed. There are no persisted screenshot files to recover, and a
fresh process must not restore an armed session or preview. For resource/file
inspection, use only an ADB connection you already authorized through Android.
The checklist supplies read-only dumps and debug `run-as` inventory commands.

## Fixes and verification in this PR

- Start the service from the visible consent activity with `startService`, then
  immediately promote it to a mediaProjection foreground service before acquiring
  a projection. Android background-start restrictions still apply. The first PR
  emulator run exposed a process crash when `startForegroundService` was followed
  by notification/promotion rejection and shutdown without promotion. Removing
  that outstanding foreground-start promise lets rejection stop cleanly. No
  capture occurs without successful foreground promotion and real OS consent.
- Revoke capture activity ownership immediately when foreground startup fails
  (for example, blocked notifications) or a service start has no authorization,
  rather than leaving it until the activity timeout.
- Refuse queued starts on an already closed service. A listener-detachment error
  no longer prevents the remaining release/close/stop steps.
- Add emulator regressions for denied consent, invalid service start and the STOP
  command, without successful consent tokens or real screen pixels. These do not
  substitute for tablet notification/permission tests.
- Add offline downloader/checklist tests to the Android build workflow.

Local verification: 7 device-tool tests and 11 bridge tests passed; `git diff
--check` passed. Gradle could not download its distribution because this runtime
cannot reach services.gradle.org, so local Kotlin compilation, lint and emulator
execution are blocked. Check the PR's Android CI results separately. No physical
device results are claimed by this PR.

Platform references: [Android MediaProjection consent and cleanup](https://developer.android.com/media/grow/media-projection)
and [single-app sharing behavior](https://android-developers.googleblog.com/2024/03/enhanced-screen-sharing-capabilities-in-android-14.html).
