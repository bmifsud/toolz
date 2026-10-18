#!/usr/bin/env python3
"""
Termux-native Python script to be executed on your Android phone inside Termux.
This script launches Chrome directly to your subscription management pages
and prepares the secure data payload for Opus.
"""

import subprocess
import json
import sys

def open_url_in_termux(url):
    # Termux intent command to open URLs in Android browser (Chrome)
    cmd = f"am start -a android.intent.action.VIEW -d '{url}' com.android.chrome"
    print(f"[*] Opening URL in Android Chrome: {url}")
    subprocess.run(cmd, shell=True)

def main():
    print("==================================================")
    print("  Termux Android Subscription Scanner for Opus    ")
    print("==================================================")
    
    subscriptions_urls = [
        "https://play.google.com/store/account/subscriptions",
        "https://myaccount.google.com/purchases",
        "https://pay.google.com/"
    ]
    
    print("\n[+] Opening Google Play Subscriptions and Billing Portals in Chrome...")
    for url in subscriptions_urls:
        open_url_in_termux(url)
        
    print("\n[+] Instructions for connecting to Opus securely:")
    print(" 1. Review your active subscriptions in the opened Chrome tabs.")
    print(" 2. Note down your active service names, renewal dates, and billing IDs.")
    print(" 3. Pass the summary to Opus via secure API/JSON payload.")
    
    payload = {
        "device": "Android",
        "browser": "Google Chrome",
        "portals_checked": subscriptions_urls,
        "status": "Ready for Opus secure connection"
    }
    
    with open("/sdcard/Download/opus_subscription_connect.json", "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"\n[+] Secure connection payload saved to: /sdcard/Download/opus_subscription_connect.json")

if __name__ == "__main__":
    main()
