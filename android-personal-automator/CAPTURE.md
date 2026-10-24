# Local one-shot screenshot inspection (issue #10)

This feature captures **one frame after fresh Android MediaProjection consent**.
It does not inspect accessibility nodes, bypass FLAG_SECURE, run commands, or send
pixels to AI. There is deliberately no screenshot upload/share path: external
transmission is unsupported, not implicitly approved by arming or OS consent.

## Installation and use

Build with JDK 17 and the pinned SDK using `./gradlew :app:assembleDebug
:app:lintDebug :app:testDebugUnitTest`, or download the debug APK from this branch's
Android CI artifacts. Install manually on your test device; no automatic deployment.
Do not uninstall an existing app merely to bypass a signing mismatch, as that can
remove its saved connection data. Use a disposable test profile if necessary.

1. Acknowledge the existing disclosure and explicitly arm the supervised session.
2. Tap **Inspect one screenshot locally**. Read the capture-specific disclosure.
3. Tap **Request one-shot OS consent**. On Android 13+, grant notification permission
   if desired, then tap again. Denial prevents capture; no settings are changed for you.
4. Approve Android's capture dialog and select the intended app/screen. A foreground
   notification identifies capture and offers STOP. Disabled notifications/channel
   prevent capture. OS protected content remains black/hidden.
5. Inspect the local preview. Projection ends after one frame (maximum dimension 1024).
   **STOP / discard**, leaving the activity, session pause/stop, or 30 seconds removes
   the preview. Capture without a frame times out. Every new capture needs new consent.

Pixels remain only in process memory, not shared storage, files, backups, saved
instance state or the connection vault. Preview uses FLAG_SECURE to prevent recursive
capture of that window. Recycling releases app references; it is not a guarantee of
forensic memory erasure. Capturing the preview window itself can yield a black image;
choose the target app in Android's selector. This is a local inspection primitive,
not the complete AI automation workflow.

## Lifecycle and security

The capture activity and service are not exported. The foreground service declares
`mediaProjection` and its Android 14+ permission. OS consent is consumed once, a
callback is registered before creating the virtual display, and the service is not
sticky. Tokens are never saved or reused. Session identity/revision binds consent:
pause/resume, stop/rearm or service replacement invalidates it. Rotation does not
restore authorization. Existing proposal/connection behavior remains separate.

## Verification gates (not yet physical-device verified)

Six pure policy tests cover single-use consent, stopped sessions, pause/resume,
stop/rearm, replacement/recreation, and discard. These do not prove service behavior.
Run the following on **Android 14, 15 and 16** before claiming compatibility:

- Deny OS capture and notification permissions; no pixels or ongoing service.
- Block the capture notification channel; fail closed.
- Capture a harmless target app; one preview, projection immediately ends.
- Capture protected content; no bypass; inspect expected blank regions.
- Stop via notification, Android projection chip, and app controls during capture.
- Pause/stop accessibility session during consent and capture; no stale preview.
- Disable accessibility, rotate, background, lock, force-stop and restart the app;
  authorization is never restored. Restart capture requires fresh consent.
- Leave consent pending for over 60 seconds and capture pending for over 8 seconds;
  both clean up. Preview disappears after 30 seconds.
- Confirm no screenshot file, network request or upload, and rerun existing saved
  connection/proposal tests. Test notification revocation during active capture.

Local build currently requires an unavailable JDK; CI receipts must be checked
before installing. Real-device permission, OEM lifecycle, Android process restart,
visual sizing and notification behavior remain acceptance gates.
