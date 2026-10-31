# Protected credentials and Termux boot

This phase adds opt-in startup. It does not install itself, create tokens, or enable remote script execution.

Store credentials locally at `~/.config/toolz-bridge/device.env` with owner-only permissions (chmod 600). The file must be owned by the Termux user, must not be a symlink, and must contain shell assignments for `BRIDGE_WS_URL` and `BRIDGE_DEVICE_TOKEN`. Never commit or paste tokens. Since this file is sourced as shell, only populate it with trusted literal assignments.

Run `bash android-personal-automator/bridge/termux-bridge-start-secure.sh` to start. After validation, run `bash android-personal-automator/bridge/install-termux-bridge-boot.sh` to install a boot hook. Termux:Boot must be installed and opened once. This hook starts the existing supervisor and does not modify backup hooks.

This is file-permission protection, not Android Keystore encryption. A compromised Termux process can read the token. Rotate any previously exposed tokens. Physical-device boot, reconnection, and log-redaction validation remain required.
