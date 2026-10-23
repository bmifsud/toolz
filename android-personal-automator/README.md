# Android Personal Automator — supervised POC

Implements toolz issue #2 in draft PR #1. Native Kotlin UI with an optional authenticated HTTPS AI proposal bridge. No unattended automation, screen reading, gesture injection, GitHub writes, or automatic deployment.

## Local OmniRoute on your Android tablet (0.3.0)

No Render service or bridge is needed when OmniRoute runs on the same tablet.

1. Keep OmniRoute running at `http://localhost:20128`.
2. Install the 0.3.0 APK, acknowledge the disclosure, enable the service, and arm.
3. Leave **Use OmniRoute running on this tablet** checked (the default).
4. Enter an OmniRoute inference token and the exact model/combo ID from its dashboard.
5. Type `Open the demo PR`, send, review, and explicitly approve or reject.

Only the app-to-OmniRoute loopback hop uses HTTP; only localhost/127.0.0.1 on port
20128 with the `/v1/chat/completions` path is accepted. Other app connections require
HTTPS. OmniRoute may forward your typed task to its upstream providers. Tokens are
kept in memory, not saved in app state or preferences. No screen content is sent.
The app does not start OmniRoute or discover its credentials/models automatically.
Unknown actions, tool calls, truncated output and malformed proposals are rejected.
Changing connection modes discards pending requests and approval.

Device checks: verify successful local inference, wrong token/model, stopped OmniRoute,
malformed output, pause/stop/background invalidation, and inability to use non-loopback HTTP.

## AI proposals (0.2.0)

The app sends a typed task to the included [bridge](bridge/README.md).
This is **not a connection to an existing ChatGPT conversation**. A hosted server
and separately configured provider API access are required; installing the APK does not host a server.

1. Host the bridge behind HTTPS as described in its README.
2. Install the new APK, acknowledge the updated disclosure, and arm the session.
3. Enter the trusted server's full `https://…/proposal` URL and its bridge token.
   Never put your OpenAI API key in the app.
4. Type `Open the demo PR` and tap **Send task to AI server**.
5. Review the explanation and exact fixed URL. Tap **Approve: open demo PR #299**
   or **Reject / cancel AI request**. No returned action executes automatically.

Only `OPEN_DEMO` and `NONE` are accepted. Extra fields, arbitrary URLs,
unknown actions, redirects, oversized responses and failed requests are rejected.
Pause, Stop, service replacement, backgrounding, rotation, rejection and a new request
invalidate pending work; resume/rearm never restores approval. Tokens and typed tasks
are not saved by the app. A cancelled request may already have reached the server/provider;
cancellation prevents local approval and execution but cannot undo transmission.
No screenshots, accessibility nodes, account data, or audit are sent.
Provider/server privacy and retention policies still apply.

### Additional device checks

- Valid bridge/token: explanation appears, browser opens only after approval; dispatch once.
- Unsupported task: `NONE` explanation, approval disabled.
- Wrong token, bad URL, offline, timeout, redirect, malformed/oversized/unknown proposal: no action.
- During requests and after proposals: pause/resume, stop/rearm, disable service,
  background, rotate, cancel, and submit a new task; stale responses never enable approval.
- Instructions proposing taps, shell commands or a different URL fail the local policy.
- Existing fixed-URL controls still work. HTTPS networking and lifecycle need device testing.

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
