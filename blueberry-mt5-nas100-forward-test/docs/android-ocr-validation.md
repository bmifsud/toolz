# MT5 Android OCR validation

This experimental parser accepts **only** the T65 tablet's 1200x1920 screenshot with the NAS100 row in its verified split-screen position. It requires Tesseract installed in Debian. It rejects missing labels, low-confidence tokens, ambiguous prices, invalid spreads, or layout changes.

```bash
cd blueberry-mt5-nas100-forward-test
python3 android_capture.py --serial 172.20.10.2:40201
python3 android_quote_ocr.py local_mt5_captures/<capture>.png
```

Output is always `tradable: false` and `OCR_UNVERIFIED` even if two numbers are found. A capture timestamp is **not** a broker quote timestamp. Manual comparison against visible MT5 and repeated reliability tests are required before any integration with the paper ledger. Never capture account credentials or share screenshots publicly. Keep local snapshots private.

Install Tesseract through the operating system's trusted package manager with appropriate permissions; installation is not performed automatically by this PR.
