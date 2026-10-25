# Issue: Tmux AI Workspace Tests Reference Missing Scripts

## Description
`tests/test-launch-ai-tmux.sh` and `tests/test-doc-coverage.sh` expect a `scripts/` directory containing `launch-ai-tmux.sh`, `start-debian.sh`, and related launcher scripts. However, these scripts are not present in the current `toolz` repository root, causing test suite failures.

## Impact
Master test runner (`tests/run-all-tests.sh`) fails on Suite 1.

## Recommended Action
Either integrate the missing launcher scripts into `scripts/` or refactor/remove obsolete test suites that depend on missing launcher scripts.
