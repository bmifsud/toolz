# NAS100 multi-capture reliability

On 2026-11-03 three authorized MT5 Android foreground screenshots were captured at UTC 02:41:34, 02:41:37 and 02:41:40. Cropped OCR returned:

| UTC capture | Bid | Ask | MT5 points |
| --- | ---: | ---: | ---: |
| 02:41:34 | 28108.96 | 28110.18 | 122 |
| 02:41:37 | 28108.27 | 28109.49 | 122 |
| 02:41:40 | 28108.17 | 28109.39 | 122 |

These values passed internal consistency checks; this does not independently verify OCR against the screenshot for all captures, broker server time, account server, quote freshness, or 24/5 reliability. No paper trades authorized.

`android_quote_reliability.py` evaluates JSONL observations with capture timestamps and returns **tradable=false in all cases**. It rejects stale, unordered, malformed, or spread-inconsistent captures. A local capture time alone cannot establish market quote freshness. Do not use this as an execution signal.
