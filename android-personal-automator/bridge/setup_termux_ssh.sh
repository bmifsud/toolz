#!/data/data/com.termux/files/usr/bin/bash
# Explicit, local-only SSH setup for Termux. No credentials are transmitted.
set -euo pipefail

if [[ "${PREFIX:-}" != "/data/data/com.termux/files/usr" ]]; then
  echo "Run inside the official Termux environment." >&2
  exit 2
fi
if ! command -v pkg >/dev/null 2>&1; then
  echo "Termux pkg is required." >&2
  exit 2
fi

echo "This will install OpenSSH and start sshd on the tablet."
echo "Termux sshd normally listens on TCP 8022; protect access using a private network."
read -r -p "Proceed locally? [y/N] " answer
[[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "Cancelled"; exit 0; }

pkg install -y openssh
if ! command -v sshd >/dev/null 2>&1; then
  echo "OpenSSH installation failed." >&2
  exit 1
fi

echo "Account: $(whoami)"
echo "Configure SSH authentication separately. Never paste passwords or private keys into chat."
echo "Starting sshd..."
sshd
if pgrep -x sshd >/dev/null; then
  echo "sshd process detected; confirm TCP port 8022 using: ss -ltn"
else
  echo "Could not confirm sshd process." >&2
  exit 1
fi
echo "This does not grant ChatGPT remote shell access; an authorized connector is still required."
