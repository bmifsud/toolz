# Android-only Blueberry website quote probe

Run from Android Andronix Debian:

```bash
cd blueberry-mt5-nas100-forward-test
python3 website_quote_probe.py
```

This reads the public Blueberry indices HTML without login or anti-bot bypass. It returns JSON status `UNAVAILABLE` and nonzero exit code for blocked requests, missing fields, placeholders, or invalid spreads.

A numeric response is **indicative and unverified**, not broker execution-quality or a verified live feed. Retrieval time is not the market quote timestamp. No website quote can trigger a paper trade until independently compared to MT5 bid/ask, freshness and trading hours. Do not poll aggressively; respect website access restrictions. This tool does not scrape behind authentication.
