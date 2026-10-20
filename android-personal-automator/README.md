# Android Personal Automator — supervised POC

Implements toolz issue #2 in draft PR #1. Native Kotlin UI; no AI engine, secrets, unattended automation, GitHub writes, or deployment.

## Build

Use JDK 17 and Android SDK platform 36 on a supported Android build host. From this directory run:

```sh
./gradlew --no-daemon :app:assembleDebug :app:lintDebug :app:testDebugUnitTest
```

The checked-in wrapper pins Gradle and verifies its distribution checksum. Android CI runs these checks. An APK build is not evidence of successful device testing. SDK native tools/emulators may not support ARM64 Linux hosts; use CI or a supported workstation.

## Consent and demo

1. Install the debug APK and read the in-app disclosure.
2. Explicitly enable the service through Android Accessibility Settings. Enabling alone does not arm a session.
3. Return to the app and explicitly arm the supervised session.
4. Use **Open PR #299** to dispatch only https://github.com/bmifsud/POC-ARTRIOUT/pull/299.
5. Pause blocks new actions; Resume only resumes a paused session. Stop removes the overlay and ends authorization. Explicit arming is required again.

The glowing pointer represents the app's authorized demo interaction, not a tracked system cursor. It does not observe arbitrary browser taps or inspect page contents. The URL opens through an Android VIEW intent; successful dispatch does not prove the page loaded. The receiving browser/GitHub app remains under the user's control: this app cannot make that external UI read-only or undo manual actions.

## Architecture and safety boundary

- `SessionController`: pure Kotlin allowlist, STOPPED/READY/PAUSED state machine, bounded in-memory audit (last 50 events). No session restoration after process/service recreation.
- Accessibility service: lifecycle owner and accessibility-overlay renderer. Explicit user enablement; no screen-content retrieval or gesture injection capability requested.
- Activity: disclosure, settings access, explicit arming, session controls and audit visibility.
- Executor: fixed URL only; no arbitrary command, URL, credential, approve, merge, or deployment path.

Accessibility overlays avoid requesting general draw-over-other-apps permission. Stop cancels app-owned visual work and removes the overlay; it does not close an already opened browser. Service interruption/disconnection fails closed. Disabling the service in Android Settings remains the OS-level emergency stop.

## Android restrictions

Android 16/API 36 is the target; minimum supported API is 26. Accessibility must be enabled by the device owner. Sideloaded apps may require Android's **Allow restricted settings** flow; managed devices/OEM policies may prohibit enablement. Never bypass these restrictions. Overlays are not guaranteed on lock screens, system-protected surfaces, or every OEM UI. Controls are not universally available over all system screens. No background action queues or foreground-service workaround are included. Store distribution requires a separate accessibility-policy and disclosure review; this is not declared an accessibility tool for users with disabilities.

## Device acceptance checklist (not yet verified)

Use an Android 16 device or supported emulator, plus API 26 if claiming minimum-SDK compatibility.

- Fresh install: service disabled, no overlay or authorized action; readable disclosure with large fonts and TalkBack.
- Enable service: no auto-arm. Explicit arm shows pointer and labeled controls above the browser.
- Open demo: exactly the allowlisted URL; pointer pulses for this interaction only. No automated taps, credentials, or GitHub mutations.
- Pause: no URL dispatch. Resume restores authorization only from PAUSED.
- Stop: removes overlay/cancels animation immediately; Resume cannot restart; explicit arm required.
- Disable/interrupt service or kill/recreate process: authorization not restored, no stale overlay or pending action.
- Rotate, change font/display scale, test gesture/three-button navigation: controls remain reachable without blocking unrelated touches.
- Lock/unlock and protected surfaces: document overlay restrictions; no queued action fires on return.
- Missing URL handler/launch failure: app stays responsive and audit reports failure, not success.
- Audit distinguishes authorization from dispatch, is bounded, and contains no page content or credentials.

Unit tests cover policy transitions, fail-closed recreation, and bounded audit. They do not replace device testing of overlay, OEM, browser, or accessibility lifecycle behavior.
