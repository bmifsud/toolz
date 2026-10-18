# Android Chrome Subscription Discovery & Opus Connector

This toolset helps you discover your active subscriptions in Google Chrome on Android and securely connect them to Opus.

## Files included:
- `termux_script.py`: Run this script directly inside Termux on your Android phone to automatically launch Google Play Subscriptions, Google Account Purchases, and Google Pay billing portals in Chrome, generating a secure JSON export.
- `check_subscriptions.py`: Run this on your computer via ADB to inspect active Chrome tabs and subscription pages.
- `opus_subscriptions_report.json`: Template / report payload for secure integration.

## Usage (Termux):
1. Install Python in Termux: `pkg update && pkg install python`
2. Run script: `python3 termux_script.py`
