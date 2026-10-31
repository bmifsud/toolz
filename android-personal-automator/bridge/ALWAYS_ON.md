# Always-on Termux bridge (opt-in)

The supervisor is **not installed automatically**. It restarts the existing listener when it exits and uses a lock to avoid duplicate supervisors. Android can still kill Termux; this is best-effort recovery, not a guarantee of 24/7 uptime.

## Prerequisites

Install Termux and Termux:Boot from the same trusted distribution source. Open Termux:Boot once to enable its boot receiver. Disable restrictive battery optimization for Termux and Termux:Boot, if your Android settings permit.

The device listener and its Python dependencies must already work. Keep the device token private; never put it in Git or the boot script.

## Credentials

Provide BRIDGE_WS_URL and BRIDGE_DEVICE_TOKEN through a protected local environment before starting. The supervisor deliberately does not read credentials from the repository or print them. A future dedicated credential loader should use a user-owned mode-600 file and must never expose tokens to GitHub Actions or logs.

## Manual start

From the checkout, with credentials already exported:

```bash
bash android-personal-automator/bridge/termux-bridge-supervisor.sh --start
```

The supervisor defaults to `$HOME/toolz-ws-bridge/device.py`. Set `BRIDGE_DEVICE_SCRIPT` to override it.

## Stop

```bash
bash android-personal-automator/bridge/termux-bridge-supervisor.sh --stop
```

The STOP file is also recognized by the current device listener. A running listener may take a moment to exit.

## Boot integration (not yet enabled)

Do **not** install a boot hook until a secure credential loader is implemented and verified on the device. Boot must not prompt for tokens or place them in plaintext shell history. The boot hook should invoke this supervisor with its protected environment, avoid duplicate starts, and write a receipt to the local state directory.

## Verification gates

1. Shell syntax and isolated supervisor tests.
2. Reconnect after listener crash and Wi-Fi loss.
3. One active supervisor despite repeated starts.
4. STOP cleanly ends the listener.
5. Boot after restart, with visible Android notification.
6. No credentials in stdout, logs, commits, or receipts.

All device checks remain pending until run on an actual tablet.
