#!/usr/bin/env bash
# ==============================================================================
# File:        tests/test-doc-coverage.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Automated test & verification of repository documentation coverage.
#              Invokes doc_coverage_engine.py to self-heal and update docs/TEST_COVERAGE.md
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "Running Documentation & Test Coverage Engine (Self-Healing)"
echo "================================================================================"

python3 "${SCRIPT_DIR}/doc_coverage_engine.py"

echo "  [PASS] Documentation-to-test coverage verified and synchronized"
exit 0
