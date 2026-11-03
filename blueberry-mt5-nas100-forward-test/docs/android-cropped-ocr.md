# Verified one-shot MT5 quote OCR

The 1200x1920 T65 MT5 split-screen screenshot dated 2026-11-03 02:28:53 UTC was manually inspected and its NAS100 row recognized by a locally unpacked Tesseract 5.5.0 engine. The output matched bid 28098.84, ask 28100.06, MT5 spread 122 (price difference 1.22). Full-screen OCR was too slow; cropping the quote row and limiting OpenMP to one thread worked.

```bash
PATH=/tmp/mt5-ocr-local/usr/bin:$PATH LD_LIBRARY_PATH=/tmp/mt5-ocr-local/usr/lib/aarch64-linux-gnu TESSDATA_PREFIX=/tmp/mt5-ocr-local/usr/share/tesseract-ocr/5/tessdata python3 android_cropped_quote.py local_mt5_captures/<capture>.png
```

Requires `ffmpeg`, `tesseract`, fixed 1200x1920 resolution, and the NAS100 row at its observed coordinates. This is **one capture**, not a verified continuous quote stream. OCR result is always `tradable=false`. No paper or live orders are placed. Screen/layout changes, stale quotes and Blueberry server provenance still require validation.
