#!/usr/bin/env bash
# ==============================================================================
# File:        tests/run-all-tests.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Unified test runner that executes all test suites in toolz:
#                1. Tmux AI Workspace & Orientation Tests (test-launch-ai-tmux.sh)
#                2. Backup, AES-256 Encryption & Restore Tests (test-backup.sh)
#                3. Android Chrome Subscriptions Provider Sync (test_suite.py)
#                4. Self-Healing Documentation & Feature Coverage (test-doc-coverage.sh)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TOTAL_SUITES=4
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
chmod +x "${REPO_ROOT}/scripts"/*.sh \
         "${REPO_ROOT}/backup"/*.sh \
         "${REPO_ROOT}/tests"/*.sh \
         "${REPO_ROOT}/tests"/*.py \
         "${REPO_ROOT}/android-chrome-subscriptions"/*.py 2>/dev/null || true

# 1. Tmux AI Workspace suite
run_suite "Tmux Multi-Session Workspace & Orientation" "${SCRIPT_DIR}/test-launch-ai-tmux.sh"

# 2. Backup & Restore suite
run_suite "OmniRoute & Cline CLI Backup, AES-256 & Restore" "${SCRIPT_DIR}/test-backup.sh"

# 3. Android Chrome Subscriptions suite
run_suite "Android Chrome Subscriptions Provider Sync" python3 "${REPO_ROOT}/android-chrome-subscriptions/test_suite.py"

# 4. Documentation Coverage Self-Healing suite
run_suite "Documentation Coverage Engine (Self-Healing)" "${SCRIPT_DIR}/test-doc-coverage.sh"

echo ""
echo "================================================================================"
echo "ALL TEST SUITES PASSED! (${PASSED_SUITES}/${TOTAL_SUITES})"
echo "Documentation coverage dynamically updated in docs/TEST_COVERAGE.md"
echo "================================================================================"
exit 0
