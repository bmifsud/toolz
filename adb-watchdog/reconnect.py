#!/usr/bin/env python3
"""Opt-in, read-only ADB connection recovery for already paired devices."""
import argparse
import re
import subprocess
import sys

SERVICE = re.compile(r'(?P<address>(?:\d{1,3}\.){3}\d{1,3}):(?P<port>\d{2,5})')

def discover(output):
    # Android's adb mdns lists _adb-tls-connect services and IP:port pairs.
    return list(dict.fromkeys(m.group(0) for line in output.splitlines()
        if '_adb-tls-connect' in line for m in SERVICE.finditer(line)))

def run(adb='adb', dry_run=False):
    devices = subprocess.run([adb, 'devices'], capture_output=True, text=True, timeout=12, check=True).stdout
    if any(line.endswith('\tdevice') for line in devices.splitlines()[1:]):
        return 'CONNECTED'
    services = subprocess.run([adb, 'mdns', 'services'], capture_output=True, text=True, timeout=12, check=True).stdout
    candidates = discover(services)
    if len(candidates) != 1:
        return 'UNAVAILABLE: require exactly one discovered paired ADB TLS endpoint'
    if dry_run:
        return 'DISCOVERED: '+candidates[0]
    subprocess.run([adb, 'connect', candidates[0]], capture_output=True, text=True, timeout=12, check=True)
    devices = subprocess.run([adb, 'devices'], capture_output=True, text=True, timeout=12, check=True).stdout
    return 'CONNECTED' if any(line.endswith('\tdevice') for line in devices.splitlines()[1:]) else 'UNAVAILABLE: pairing or authorization required'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = run(dry_run=args.dry_run)
        print(result)
        sys.exit(0 if result == 'CONNECTED' or result.startswith('DISCOVERED:') else 2)
    except (OSError, subprocess.SubprocessError) as exc:
        print('UNAVAILABLE: '+str(exc))
        sys.exit(2)
