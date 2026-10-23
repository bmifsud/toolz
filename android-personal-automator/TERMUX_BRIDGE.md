# Termux diagnostic bridge (opt-in)

This is a **read-only reporting bridge**, not an SSH connection or an autonomous command executor. It lets a user publish a narrowly scoped health summary to GitHub Issues, which ChatGPT can inspect through the connected GitHub integration. It cannot run commands on the device from ChatGPT.

## Setup and use (outer Termux)

```bash
cd ~/toolz
git pull --ff-only origin main
pkg install gh
gh auth login
bash android-personal-automator/termux-diagnostic-bridge.sh
```

The script shows the exact fields and requests explicit confirmation before creating an issue. **Do not post private log contents or credentials.** Issues in public repositories are public. The script does not include tokens, device identifiers, or raw logs.

It reports only whether the boot hook exists, is executable, passes syntax validation, whether the boot log exists, whether crond runs, and whether the catch-up watchdog is installed. It does not start cron, reboot, change permissions, trigger backups, or enable Tier-2.

For actual remote command execution, a separately designed, authenticated, least-privilege agent with per-command approval and an audited transport is required; this script intentionally does not provide that capability.
