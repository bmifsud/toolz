# Opt-in ADB reconnect watchdog

Run `python3 adb-watchdog/reconnect.py` from the repository root when an authorized Android device is temporarily disconnected. Use `--dry-run` to inspect discovery without connecting.

The script checks already-connected devices, discovers a **single** Android `_adb-tls-connect` mDNS service, attempts connection, and verifies that `adb devices` reports `device`. It does not pair, toggle wireless debugging, modify Android settings, keep the screen awake, or run trading commands. Multiple or missing endpoints fail closed. No background service or cron is installed by default.

For an optional supervised periodic run, configure a user-managed scheduler only after testing on the target Android/Termux environment. Wireless debugging can turn off, change ports, or require manual authorization. mDNS discovery may not work in proot/network namespaces; in that case report the failure and use Android's current displayed address. Never scan arbitrary ports or assume that a connection is secure without Android authorization.
