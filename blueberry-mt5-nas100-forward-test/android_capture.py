"""Read-only MT5 Android ADB screenshot collector. No trading or remote uploads."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

MT5_PACKAGE = "net.metaquotes.metatrader5"

def capture(out_dir, serial=None):
    adb = ["adb"] + (["-s", serial] if serial else [])
    focus = subprocess.run(adb + ["shell", "dumpsys", "window"], capture_output=True, text=True, timeout=15, check=True)
    if MT5_PACKAGE not in "\n".join(line for line in focus.stdout.splitlines() if "mCurrentFocus" in line):
        raise RuntimeError("MT5 is not foreground; capture refused")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    screenshot = directory / ("mt5_" + stamp + ".png")
    with screenshot.open("wb") as f:
        subprocess.run(adb + ["exec-out", "screencap", "-p"], stdout=f, timeout=20, check=True)
    data = screenshot.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        screenshot.unlink(missing_ok=True)
        raise RuntimeError("Invalid screenshot")
    result = {"status": "CAPTURED_UNVERIFIED", "tradable": False,
              "source": "Blueberry MT5 Android visible screen", "captured_at_utc": stamp,
              "screenshot": str(screenshot), "sha256": hashlib.sha256(data).hexdigest()}
    if shutil.which("tesseract"):
        ocr = subprocess.run(["tesseract", str(screenshot), "stdout", "tsv"],
                             capture_output=True, text=True, timeout=30)
        if ocr.returncode == 0:
            result["ocr_status"] = "RAW_TEXT_ONLY_NOT_VALIDATED"
            result["ocr_tsv"] = str(screenshot.with_suffix(".tsv"))
            screenshot.with_suffix(".tsv").write_text(ocr.stdout)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="local_mt5_captures")
    p.add_argument("--serial")
    args = p.parse_args()
    try:
        print(json.dumps(capture(args.out, args.serial)))
        return 0
    except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
        print(json.dumps({"status": "UNAVAILABLE", "tradable": False, "reason": str(exc)}))
        return 2

if __name__ == "__main__":
    sys.exit(main())
