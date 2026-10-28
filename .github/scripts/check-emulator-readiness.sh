#!/usr/bin/env bash
# The emulator-runner action executes each script line separately. Keep all
# compound shell logic in this file, invoked by one `script:` command.
set -euo pipefail

mkdir -p emulator-receipts
ready=0
for attempt in $(seq 1 12); do
  boot="$(timeout 15 adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [[ "$boot" == "1" ]]; then
    ready=1
    break
  fi
  sleep 5
done
if [[ "$ready" -ne 1 ]]; then
  timeout 15 adb devices -l > emulator-receipts/adb-failure.txt 2>&1 || true
  echo 'NOT_READY: ADB boot property unavailable after 12 bounded attempts; gateway end-to-end test not run' > emulator-receipts/result.txt
  exit 1
fi

timeout 30 adb -s emulator-5554 shell getprop ro.build.version.release > emulator-receipts/android-version.txt
timeout 30 adb -s emulator-5554 shell getprop ro.product.cpu.abi > emulator-receipts/device-abi.txt
timeout 30 adb devices -l > emulator-receipts/adb-devices.txt
echo 'PASS: emulator booted and ADB connected; readiness only; gateway end-to-end test not run' > emulator-receipts/result.txt
