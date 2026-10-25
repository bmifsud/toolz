#!/usr/bin/env bash
# =============================================================================
# File:        tests/run-all-tests.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Unified test runner that executes active test suites in toolz:
#                1. Backup, AES-256 Encryption & Restore Tests (test-backup.sh)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TOTAL_SUITES=1
PASSED_SUITES=0

run_suite() {
    local name="$1"
    shift
    echo ""
    echo "================================================================================"
    echo ">>> Running Suite: $name"
    echo "================================================================================"
    if "$@"; then
        PASSED_SUITES=$((PASSED_SUITES + 1))
        printf "\n>>> Suite SUCCESS: %s\n" "$name"
    else
        printf "\n>>> Suite FAILED: %s\n" "$name" >&2
        exit 1
    fi
}

# Ensure all scripts are executable
chmod +x "${REPO_ROOT}/backup"/*.sh \
         "${REPO_ROOT}/tests"/*.sh 2>/dev/null || true

# 1. Backup & Restore suite
run_suite "OmniRoute & Cline CLI Backup, AES-256 & Restore" "${SCRIPT_DIR}/test-backup.sh"

echo ""
echo "================================================================================"
echo "ALL TEST SUITES PASSED! (${PASSED_SUITES}/${TOTAL_SUITES})"
echo "================================================================================"
exit 0
