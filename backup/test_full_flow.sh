#!/usr/bin/env bash
# Comprehensive non-destructive regression gate for Tier-1/Tier-2 scripts.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.."
command -v python3 >/dev/null || { echo 'python3 required' >&2; exit 1; }
python3 -m pytest --version >/dev/null || { echo 'Install pytest: python3 -m pip install pytest' >&2; exit 1; }
for file in "$HERE"/*.sh; do
  test -f "$file" || { echo "Missing $file" >&2; exit 1; }
  bash -n "$file"
done
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -v -p no:cacheprovider backup/tests "$@"
echo 'PASS: isolated regression suite. Device-specific acceptance and shell branch coverage remain separate requirements.'
