#!/usr/bin/env bash
# ==============================================================================
# File:        tests/test-launch-ai-tmux.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Automated integration and unit test suite for toolz scripts:
#                - Bash syntax & executable permission checks
#                - CLI argument parsing (--help, invalid flags)
#                - Portrait orientation (even-vertical stacked panes)
#                - Landscape orientation (even-horizontal side-by-side panes)
#                - Dynamic screen rotation hooks (Portrait <-> Landscape)
#                - Android soft-keyboard resilience in portrait mode
#                - Full-screen pane zoom preservation across resizes
#                - Mouse mode, border headers, codex --no-daemon, and AI_WORKDIR
#
# Usage:
#   ./tests/test-launch-ai-tmux.sh
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCHER="${REPO_ROOT}/scripts/launch-ai-tmux.sh"
INSTALLER="${REPO_ROOT}/scripts/install-autostart.sh"

TEST_SESSION="ai-test-$$"
TEST_TMPDIR="$(mktemp -d "/tmp/toolz-test.XXXXXX")"
TEST_HOME="${TEST_TMPDIR}/home"
TEST_WORKDIR="${TEST_TMPDIR}/workspace"

PASSED=0
FAILED=0

cleanup() {
    tmux kill-session -t "$TEST_SESSION" 2>/dev/null || true
    rm -rf "$TEST_TMPDIR"
}
trap cleanup EXIT

pass() {
    PASSED=$((PASSED + 1))
    printf "  [PASS] %s\n" "$1"
}

fail() {
    FAILED=$((FAILED + 1))
    printf "  [FAIL] %s\n" "$1" >&2
}

assert_eq() {
    local actual="$1"
    local expected="$2"
    local msg="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass "$msg"
    else
        fail "$msg (expected '$expected', got '$actual')"
    fi
}

assert_true() {
    local expr="$1"
    local msg="$2"
    if eval "$expr"; then
        pass "$msg"
    else
        fail "$msg (expression failed: $expr)"
    fi
}

# ------------------------------------------------------------------------------
# Setup Isolated Mock Environment
# ------------------------------------------------------------------------------
mkdir -p "${TEST_HOME}/.local/bin" "$TEST_WORKDIR"

cat > "${TEST_HOME}/.local/bin/agy" <<EOF
#!/usr/bin/env bash
echo "\$*" > "${TEST_TMPDIR}/agy.args"
pwd > "${TEST_TMPDIR}/agy.pwd"
exec sleep 300
EOF

cat > "${TEST_HOME}/.local/bin/codex" <<EOF
#!/usr/bin/env bash
echo "\$*" > "${TEST_TMPDIR}/codex.args"
pwd > "${TEST_TMPDIR}/codex.pwd"
exec sleep 300
EOF

cat > "${TEST_HOME}/.local/bin/jules" <<EOF
#!/usr/bin/env bash
echo "\$*" > "${TEST_TMPDIR}/jules.args"
pwd > "${TEST_TMPDIR}/jules.pwd"
exec sleep 300
EOF

chmod +x "${TEST_HOME}/.local/bin/agy" "${TEST_HOME}/.local/bin/codex" "${TEST_HOME}/.local/bin/jules"

echo "================================================================================"
echo "Running toolz Test Suite"
echo "================================================================================"

# ------------------------------------------------------------------------------
# Test 1: Script Syntax & Permissions
# ------------------------------------------------------------------------------
echo "==> Test 1: Script syntax and executable permissions"
assert_true "bash -n '$LAUNCHER'" "scripts/launch-ai-tmux.sh has valid bash syntax"
assert_true "bash -n '$INSTALLER'" "scripts/install-autostart.sh has valid bash syntax"
assert_true "[[ -x '$LAUNCHER' ]]" "scripts/launch-ai-tmux.sh is executable"
assert_true "[[ -x '$INSTALLER' ]]" "scripts/install-autostart.sh is executable"

# ------------------------------------------------------------------------------
# Test 2: CLI Flags (--help and Invalid Flag Handling)
# ------------------------------------------------------------------------------
echo "==> Test 2: CLI argument parsing"
HELP_OUT="$("$LAUNCHER" --help)"
assert_true "[[ '$HELP_OUT' == *'--portrait'* && '$HELP_OUT' == *'--landscape'* ]]" "--help documents --portrait and --landscape flags"

if "$LAUNCHER" --unknown-invalid-flag >/dev/null 2>&1; then
    fail "Unknown flag should exit with non-zero status"
else
    pass "Unknown flag exits with non-zero status"
fi

# ------------------------------------------------------------------------------
# Test 3: Portrait Orientation (--portrait) Stacks Panes Vertically
# ------------------------------------------------------------------------------
echo "==> Test 3: Portrait orientation (--portrait) vertical pane stacking"
HOME="$TEST_HOME" AI_SESSION_NAME="$TEST_SESSION" AI_WORKDIR="$TEST_WORKDIR" \
    "$LAUNCHER" --portrait --no-attach

assert_true "tmux has-session -t '$TEST_SESSION' 2>/dev/null" "Creates tmux session '$TEST_SESSION'"

PANE_COUNT="$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" | wc -l | tr -d ' ')"
assert_eq "$PANE_COUNT" "3" "Creates exactly 3 panes in AI-Workspace"

# Wait briefly for mock CLIs to record their arguments and working directories
for _ in {1..20}; do
    if [[ -f "${TEST_TMPDIR}/agy.pwd" && -f "${TEST_TMPDIR}/codex.args" && -f "${TEST_TMPDIR}/jules.pwd" ]]; then
        break
    fi
    sleep 0.1
done

assert_eq "$(cat "${TEST_TMPDIR}/codex.args" 2>/dev/null || true)" "--no-daemon" "Launches codex with --no-daemon flag"
assert_eq "$(cat "${TEST_TMPDIR}/agy.pwd" 2>/dev/null || true)" "$TEST_WORKDIR" "Starts Pane 0 (Antigravity) in AI_WORKDIR"
assert_eq "$(cat "${TEST_TMPDIR}/codex.pwd" 2>/dev/null || true)" "$TEST_WORKDIR" "Starts Pane 1 (Codex) in AI_WORKDIR"
assert_eq "$(cat "${TEST_TMPDIR}/jules.pwd" 2>/dev/null || true)" "$TEST_WORKDIR" "Starts Pane 2 (Jules) in AI_WORKDIR"

# Verify titles and portrait vertical stacking geometry (even-vertical)
read -r P0_TITLE P0_W P0_H P0_L P0_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_title} #{pane_width} #{pane_height} #{pane_left} #{pane_top}' | sed -n '1p')"
read -r P1_TITLE P1_W P1_H P1_L P1_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_title} #{pane_width} #{pane_height} #{pane_left} #{pane_top}' | sed -n '2p')"
read -r P2_TITLE P2_W P2_H P2_L P2_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_title} #{pane_width} #{pane_height} #{pane_left} #{pane_top}' | sed -n '3p')"

assert_eq "$P0_TITLE" "Antigravity" "Pane 0 title is Antigravity"
assert_eq "$P1_TITLE" "Codex" "Pane 1 title is Codex"
assert_eq "$P2_TITLE" "Jules" "Pane 2 title is Jules"

assert_true "(( P0_L == 0 && P1_L == 0 && P2_L == 0 ))" "Portrait mode: all 3 panes align at left edge (pane_left == 0)"
assert_true "(( P0_W == P1_W && P1_W == P2_W ))" "Portrait mode: all 3 panes span the full terminal width equally"
assert_true "(( P0_T < P1_T && P1_T < P2_T ))" "Portrait mode: panes are stacked on top of each other (P0_top < P1_top < P2_top)"
assert_true "(( P0_T + P0_H <= P1_T && P1_T + P1_H <= P2_T ))" "Portrait mode: stacked panes do not overlap vertically"

# ------------------------------------------------------------------------------
# Test 4: Landscape Orientation (--landscape) Places Panes Side-by-Side
# ------------------------------------------------------------------------------
echo "==> Test 4: Landscape orientation (--landscape) side-by-side columns"
HOME="$TEST_HOME" AI_SESSION_NAME="$TEST_SESSION" AI_WORKDIR="$TEST_WORKDIR" \
    "$LAUNCHER" --landscape --no-attach

read -r L0_W L0_H L0_L L0_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_width} #{pane_height} #{pane_left} #{pane_top}' | sed -n '1p')"
read -r L1_W L1_H L1_L L1_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_width} #{pane_height} #{pane_left} #{pane_top}' | sed -n '2p')"
read -r L2_W L2_H L2_L L2_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_width} #{pane_height} #{pane_left} #{pane_top}' | sed -n '3p')"

assert_true "(( L0_T == L1_T && L1_T == L2_T ))" "Landscape mode: all 3 panes align at top edge (pane_top equal)"
assert_true "(( L0_H == L1_H && L1_H == L2_H ))" "Landscape mode: all 3 panes share the full window height"
assert_true "(( L0_L < L1_L && L1_L < L2_L ))" "Landscape mode: panes are arranged side-by-side (P0_left < P1_left < P2_left)"
assert_true "(( L0_L + L0_W <= L1_L && L1_L + L1_W <= L2_L ))" "Landscape mode: side-by-side panes do not overlap horizontally"

# ------------------------------------------------------------------------------
# Test 5: Dynamic Auto-Orientation (--auto) & Real-Time Screen Rotation Hooks
# ------------------------------------------------------------------------------
echo "==> Test 5: Dynamic rotation hooks (--auto: Landscape <-> Portrait <-> Soft Keyboard)"
HOME="$TEST_HOME" AI_SESSION_NAME="$TEST_SESSION" AI_WORKDIR="$TEST_WORKDIR" \
    "$LAUNCHER" --auto --no-attach

# 5a. Simulate Landscape rotation (180x45)
tmux resize-window -t "${TEST_SESSION}:AI-Workspace" -x 180 -y 45
sleep 0.2
read -r A0_L A0_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '1p')"
read -r A1_L A1_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '2p')"
read -r A2_L A2_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '3p')"
assert_true "(( A0_T == A1_T && A1_T == A2_T && A0_L < A1_L && A1_L < A2_L ))" "Auto-hook switches to side-by-side (even-horizontal) on 180x45 landscape resize"

# 5b. Simulate Portrait rotation (92x65)
tmux resize-window -t "${TEST_SESSION}:AI-Workspace" -x 92 -y 65
sleep 0.2
read -r B0_L B0_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '1p')"
read -r B1_L B1_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '2p')"
read -r B2_L B2_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '3p')"
assert_true "(( B0_L == 0 && B1_L == 0 && B2_L == 0 && B0_T < B1_T && B1_T < B2_T ))" "Auto-hook stacks panes on top of each other (even-vertical) on 92x65 portrait resize"

# 5c. Simulate Android soft keyboard opening in Portrait (92x32: height shrinks, width stays 92 < 115)
tmux resize-window -t "${TEST_SESSION}:AI-Workspace" -x 92 -y 32
sleep 0.2
read -r K0_L K0_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '1p')"
read -r K1_L K1_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '2p')"
read -r K2_L K2_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '3p')"
assert_true "(( K0_L == 0 && K1_L == 0 && K2_L == 0 && K0_T < K1_T && K1_T < K2_T ))" "Auto-hook keeps panes stacked vertically when soft keyboard opens in portrait (92x32)"

# 5d. Rotate back to Landscape (180x45)
tmux resize-window -t "${TEST_SESSION}:AI-Workspace" -x 180 -y 45
sleep 0.2
read -r C0_L C0_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '1p')"
read -r C1_L C1_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '2p')"
read -r C2_L C2_T <<<"$(tmux list-panes -t "${TEST_SESSION}:AI-Workspace" -F '#{pane_left} #{pane_top}' | sed -n '3p')"
assert_true "(( C0_T == C1_T && C1_T == C2_T && C0_L < C1_L && C1_L < C2_L ))" "Auto-hook switches back to side-by-side on return to 180x45 landscape"

# ------------------------------------------------------------------------------
# Test 6: Zoom Preservation Across Window Resizes
# ------------------------------------------------------------------------------
echo "==> Test 6: Full-screen pane zoom preservation during resize"
tmux resize-pane -Z -t "${TEST_SESSION}:AI-Workspace.0"
assert_eq "$(tmux display-message -t "${TEST_SESSION}:AI-Workspace" -p '#{window_zoomed_flag}')" "1" "Pane 0 is zoomed before resize"

tmux resize-window -t "${TEST_SESSION}:AI-Workspace" -x 92 -y 65
sleep 0.2
assert_eq "$(tmux display-message -t "${TEST_SESSION}:AI-Workspace" -p '#{window_zoomed_flag}')" "1" "Pane 0 remains zoomed after resize hook fires"
tmux resize-pane -Z -t "${TEST_SESSION}:AI-Workspace.0"

# ------------------------------------------------------------------------------
# Test 7: Session Options (Mouse Mode & Top Pane Border Headers)
# ------------------------------------------------------------------------------
echo "==> Test 7: tmux session configuration options"
MOUSE_OPT="$(tmux show-options -t "$TEST_SESSION" -gv mouse)"
BORDER_STATUS="$(tmux show-options -t "$TEST_SESSION" -gv pane-border-status)"
assert_eq "$MOUSE_OPT" "on" "tmux mouse mode is enabled"
assert_eq "$BORDER_STATUS" "top" "tmux pane-border-status is set to top"

echo "================================================================================"
printf "Test Summary: %d passed, %d failed\n" "$PASSED" "$FAILED"
echo "================================================================================"

if (( FAILED > 0 )); then
    exit 1
fi
exit 0
