#!/usr/bin/env bash
# Offline repository gate; not live deployment acceptance.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for tool in python3 gpg gpgconf sqlite3 tar gzip sha256sum; do
  command -v "$tool" >/dev/null || { echo "Missing prerequisite: $tool" >&2; exit 1; }
done
python3 -m pytest --version >/dev/null || { echo 'Missing prerequisite: pytest' >&2; exit 1; }
python3 scripts/check_adlc.py
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find backup tests -name '*.sh' -type f -print0)
python3 -m pytest tests/ backup/tests/ android-personal-automator/bridge/tests/ android-personal-automator/bridge/ws/test_replay_store.py -q
