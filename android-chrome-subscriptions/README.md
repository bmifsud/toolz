# Android Chrome Subscription Discovery & Opus Connector

This toolset helps you discover your active subscriptions in Google Chrome on Android and securely connect them to Opus.

## Files included:
- `termux_script.py`: Run this script directly inside Termux on your Android phone to automatically launch Google Play Subscriptions, Google Account Purchases, and Google Pay billing portals in Chrome, generating a secure JSON export.
- `check_subscriptions.py`: Run this on your computer via ADB to inspect active Chrome tabs and subscription pages.
- `opus_subscriptions_report.json`: Template / report payload for secure integration.

## Usage (Termux):
1. Install Python in Termux: `pkg update && pkg install python`
2. Run script: `python3 termux_script.py`

## What to Do After Running the Script

Once you have executed `termux_script.py` on your Android device or `check_subscriptions.py` via ADB, follow these steps to securely connect your subscriptions to Opus:

1. **Review Opened Chrome Tabs & Portals**:
   - The script automatically navigates to your official Google and billing subscription management pages:
     - [Google Play Subscriptions](https://play.google.com/store/account/subscriptions)
     - [Google Account Purchases](https://myaccount.google.com/purchases)
     - [Google Pay](https://pay.google.com/)
   - Inspect the active subscriptions listed in your browser (e.g., streaming services, app subscriptions, cloud storage, AI tools like Opus).

2. **Locate the Generated JSON Payload**:
   - The script saves a structured JSON file locally on your device at `/sdcard/Download/opus_subscription_connect.json` (or `/home/b/opus_subscriptions_report.json` on desktop).

3. **Securely Connect to Opus**:
   - **Manual Verification**: Review the active items and note their service names, billing cycles, and renewal dates.
   - **API / Secure Sync**: Pass the generated JSON payload (`opus_subscription_connect.json`) to your Opus secure ingestion endpoint or webhook.
   - *Security Best Practice*: Ensure that any raw session cookies or sensitive auth tokens are stripped before transmitting, keeping only metadata (subscription name, status, renewal date) for Opus tracking.
