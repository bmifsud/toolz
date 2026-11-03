# Read-only Android MT5 screen capture

Requires authorized wireless ADB and MT5 in the foreground, with NAS100 bid and ask visible.

```bash
cd blueberry-mt5-nas100-forward-test
python3 android_capture.py --serial <adb-device-id>
```

Captures a PNG to `local_mt5_captures/` with a SHA-256 and UTC capture timestamp. Optional `tesseract` produces a raw OCR TSV for offline evaluation. **No quote is automatically accepted or forwarded to the paper ledger.** OCR output is unverified, screenshots may show stale prices, and capture time is not the broker tick timestamp. No orders or credential extraction.

Screenshots may include sensitive account details. Keep local, restrict directory access, and delete after validation. This tool does not run continuously; invoke it manually while MT5 is visible. To enable OCR, install a trusted Tesseract package on the Debian device.
