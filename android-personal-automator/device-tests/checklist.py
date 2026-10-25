#!/usr/bin/env python3
"""Local, human-operated device test. No screen access, shell execution or networking."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

CASES = [
    ("installation", "Install only the checksum-verified APK using Android's installer. "
     "Record Android version and build/run ID. Do not uninstall to work around a signature mismatch."),
    ("consent", "Acknowledge disclosure, enable the service yourself in Accessibility settings, "
     "then Arm. Open 'Inspect one screenshot locally'. Allow notifications yourself if requested, "
     "then tap capture again. Confirm an Android screen-sharing dialog appears. "
     "No image may appear before you approve. Each new capture must ask again."),
    ("denial", "Cancel/deny the Android screen-sharing dialog. Expect no preview, projection "
     "indicator or capture notification. Reopen capture: a fresh OS consent request is required."),
    ("notification_denial", "Deny app notifications, then separately disable the Screen capture "
     "notification channel in Android Settings and retry. Both must prevent capture. Restore "
     "notifications manually for later tests; do not use permission-grant commands."),
    ("termux_preview", "In Termux type: printf 'LOCAL CAPTURE TEST - no secrets\\n'. Put Termux "
     "and the capture activity side by side in split screen, with the capture activity visible. "
     "Request capture and explicitly approve the entire display in Android's dialog. "
     "Expect the Termux marker in the app's local preview; its secure pane may be black. "
     "Do not press Share, upload or save an image. If OEM split screen is unsupported, mark pending."),
    ("foreground_notification", "Repeat capture and inspect the notification shade during the "
     "short active projection. Expect 'One-shot screen capture active' with STOP. It disappears "
     "after the first frame. If too fast to observe, mark pending rather than pass."),
    ("notification_stop", "On a fresh explicitly consented capture, tap the capture notification's "
     "STOP while projection is active. Expect no later frame, no preview and notification removal. "
     "If you cannot tap before one-shot completion, mark pending. Synthetic STOP is insufficient."),
    ("preview_discard", "After a successful frame, tap STOP / discard in the capture activity. "
     "The preview must disappear. Separately repeat and wait 30 seconds: automatic discard. "
     "Reopen: no old image. Overlay Stop must also revoke capture and remove the overlay."),
    ("resource_cleanup", "With an already authorized ADB connection, compare 'adb shell dumpsys "
     "media_projection' and 'adb shell dumpsys activity services org.aief.personalautomator' "
     "during capture and after STOP/timeout. No active projection or CaptureService should remain. "
     "Check private files via the debug APK's run-as, before/after: 'adb shell run-as "
     "org.aief.personalautomator find files cache -type f'. No new image files. Inspect names "
     "locally; do not upload private files. Without authorized ADB, mark this pending."),
    ("background", "After granting capture, press Home or switch fully to Termux; also background "
     "a visible preview. Expect capture/preview discarded with no silent restart. Switching to "
     "a selected single app may cancel this fail-closed design; use split screen for the preview test."),
    ("rotation", "Rotate while consent is open, during capture, and during preview, using a fresh "
     "request each time. Expect cancellation/discard, no old preview and no token reuse. "
     "A new attempt requires explicit Android consent."),
    ("process_interruption", "Using Android Settings > Apps > Supervised URL demo > Force stop "
     "(or your already-authorized ADB: adb shell am force-stop org.aief.personalautomator), "
     "interrupt both active capture and preview. Expect projection/notification gone. Reopen: "
     "no preview, session stopped; explicitly Arm and consent again. OS reclaims process memory; "
     "onDestroy is not guaranteed on force stop."),
    ("no_transmission", "Cancel AI requests and do not tap Send or Test connection. Using an "
     "already trusted local VPN/firewall monitor, observe this app UID during capture, preview "
     "and STOP: no capture-related outbound requests (including localhost/OmniRoute). "
     "Repeat capture offline as a separate check. Offline success alone does not prove no "
     "transmission. Do not upload screenshots or packet contents. Without UID monitoring mark pending."),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", action="store_true", help="Write all cases as pending without prompts")
    parser.add_argument("--output", type=Path, default=Path.home() /
                        ".local/state/toolz-device-test/results.json")
    args = parser.parse_args()
    os.umask(0o077)
    results = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "evidence_type": "human-reported; not automatic verification",
               "device": "unrecorded", "build": "unrecorded", "tests": [
                   {"id": name, "status": "pending", "instructions": instructions, "note": ""}
                   for name, instructions in CASES]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        parser.error("Output exists; use a new --output path to preserve earlier results")

    def save():
        temp = args.output.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(results, stream, indent=2)
        temp.replace(args.output)

    save()
    try:
        if not args.initialize:
            results["device"] = input("Android version / tablet model (no serial): ")
            results["build"] = input("Installed build/run ID or APK SHA256: ")
            for test in results["tests"]:
                print(f"\n{test['id']}: {test['instructions']}")
                answer = input("Observed result [pass/fail/pending; Enter=pending]: ").strip().lower()
                test["status"] = answer if answer in ("pass", "fail") else "pending"
                test["note"] = input("Short observation (no secrets), or Enter: ")
                save()
    except (EOFError, KeyboardInterrupt):
        print("\nInterrupted; uncompleted tests stay pending.")
    finally:
        save()
    print(f"Local report: {args.output}. Nothing was transmitted.")


if __name__ == "__main__":
    main()
