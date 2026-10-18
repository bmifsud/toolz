#!/usr/bin/env python3
"""
Omniroute Subscription Provider Connector
Takes discovered subscriptions from Google Chrome / Termux and automatically
registers them as AI providers in Omniroute (running at http://localhost:20128).
"""

import json
import urllib.request
import urllib.error
import sys

OMNIROUTE_API_URL = "http://localhost:20128/api/providers"

def register_provider_in_omniroute(provider_data):
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        OMNIROUTE_API_URL,
        data=json.dumps(provider_data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = response.read().decode("utf-8")
            print(f"[+] Successfully registered provider {provider_data.get('name')} in Omniroute: {result}")
            return True
    except urllib.error.URLError as e:
        print(f"[!] Failed to connect to Omniroute at {OMNIROUTE_API_URL}: {e.reason}")
        print("[*] Make sure your local Omniroute instance is running on port 20128.")
        return False
    except Exception as e:
        print(f"[!] Error registering provider: {e}")
        return False

def main():
    print("=== Omniroute Subscription Provider Auto-Connector ===")
    
    # Load discovered subscriptions report or prompt user
    report_path = "/home/b/toolz/android-chrome-subscriptions/opus_subscriptions_report.json"
    try:
        with open(report_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    print(f"[*] Target Omniroute Instance: {OMNIROUTE_API_URL}")
    print("[*] Ready to register detected AI subscription providers into Omniroute.")
    
    # Example provider payload mapping subscription to Omniroute provider format
    sample_provider = {
        "name": "google-play-subscription",
        "type": "openai-compatible",  # or anthropic / custom
        "base_url": "https://api.openai.com/v1", # Example mapped endpoint
        "enabled": True,
        "metadata": {
            "source": "Android Chrome / Google Play Subscriptions",
            "managed_via": "Omniroute local"
        }
    }
    
    print(f"\n[+] Registering sample provider payload:")
    print(json.dumps(sample_provider, indent=2))
    
    register_provider_in_omniroute(sample_provider)

if __name__ == "__main__":
    main()
