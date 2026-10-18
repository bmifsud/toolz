#!/usr/bin/env python3
"""
Android Chrome Subscription Discovery & Secure Opus Connector Script
This script uses ADB and Chrome DevTools Protocol (CDP) to inspect active browser tabs
on Android Google Chrome, detect subscription/billing pages, and compile a secure inventory
ready for Opus integration.
"""

import subprocess
import json
import urllib.request
import urllib.error
import sys
import time

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip()}"

def check_adb():
    print("[*] Checking ADB connection...")
    devices = run_cmd("adb devices")
    print(devices)
    lines = devices.splitlines()
    active_devices = [l for l in lines[1:] if l.strip() and not l.startswith("*")]
    if not active_devices:
        print("\n[!] No active Android devices found via ADB.")
        print("[*] Please connect your Android device via USB, enable USB Debugging, and authorize this computer.")
        return False
    return True

def setup_devtools_forward():
    print("[*] Setting up Chrome DevTools port forwarding (tcp:9222)...")
    res = run_cmd("adb forward tcp:9222 localabstract:chrome_devtools_remote")
    if "ERROR" in res:
        print(f"[!] Warning on port forwarding: {res}")
        print("[*] Make sure Chrome is open on your Android device and remote debugging is available.")
    else:
        print("[+] Port forwarding established successfully.")

def get_chrome_tabs():
    print("[*] Fetching active Chrome tabs via DevTools Protocol...")
    url = "http://localhost:9222/json"
    try:
        req = urllib.request.urlopen(url, timeout=3)
        data = json.loads(req.read().decode('utf-8'))
        return data
    except Exception as e:
        print(f"[!] Could not connect to Chrome DevTools endpoint: {e}")
        print("[*] TIP: Open Chrome on Android, go to 'chrome://inspect' or ensure remote debugging is active.")
        return []

def analyze_subscriptions(tabs):
    known_subscription_keywords = [
        "subscription", "billing", "play.google.com/store/account", 
        "invoice", "payment", "account", "opus", "openai", "stripe",
        "patreon", "spotify", "netflix", "youtube", "discord", "github"
    ]
    
    discovered = []
    print(f"\n[*] Scanning {len(tabs)} active Chrome tab(s) for subscription/billing info...")
    for tab in tabs:
        title = tab.get('title', '')
        tab_url = tab.get('url', '')
        print(f"  - [Tab] {title} ({tab_url})")
        
        score = sum(1 for kw in known_subscription_keywords if kw in tab_url.lower() or kw in title.lower())
        if score > 0 or "play.google.com" in tab_url:
            discovered.append({
                "title": title,
                "url": tab_url,
                "relevance_score": score
            })
            
    return discovered

def main():
    print("=== Android Chrome Subscription & Opus Connection Tool ===")
    if not check_adb():
        print("\n[INFO] Saving helper instructions and template since no device is currently attached.")
        save_fallback_instructions()
        return
        
    setup_devtools_forward()
    time.sleep(1)
    tabs = get_chrome_tabs()
    
    if not tabs:
        print("\n[!] No tabs retrieved. Opening Google Play Subscriptions & Google Account Purchases in Chrome automatically...")
        run_cmd("adb shell am start -a android.intent.action.VIEW -d 'https://play.google.com/store/account/subscriptions' com.android.chrome")
        time.sleep(3)
        tabs = get_chrome_tabs()
        
    discovered = analyze_subscriptions(tabs)
    
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "device_status": "connected",
        "discovered_subscriptions_pages": discovered,
        "recommendation": "Use these authenticated billing endpoints to securely sync subscription data with Opus."
    }
    
    out_path = "/home/b/opus_subscriptions_report.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
        
    print(f"\n[+] Subscription scan complete! Report saved securely to: {out_path}")
    print(json.dumps(output, indent=2))

def save_fallback_instructions():
    fallback = {
        "instructions": [
            "1. Connect your Android phone to this computer via USB.",
            "2. Enable Developer Options & USB Debugging on your Android phone.",
            "3. Open Google Chrome on your Android phone.",
            "4. Re-run this script: python3 /home/b/check_subscriptions.py"
        ],
        "manual_subscription_links": [
            "https://play.google.com/store/account/subscriptions",
            "https://myaccount.google.com/purchases",
            "https://billing.stripe.com/"
        ]
    }
    with open("/home/b/opus_subscriptions_report.json", "w") as f:
        json.dump(fallback, f, indent=2)
    print("[+] Saved fallback instructions to /home/b/opus_subscriptions_report.json")

if __name__ == "__main__":
    main()
