#!/usr/bin/env bash
# ==============================================================================
# File:        tests/test-backup.sh
# Repository:  https://github.com/bmifsud/toolz
# Description: Automated test suite for backup_cline_omniroute.sh
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_SCRIPT="${REPO_ROOT}/backup/backup_cline_omniroute.sh"

TEST_TMPDIR="$(mktemp -d "/tmp/toolz-backup-test.XXXXXX")"
MOCK_HOME="${TEST_TMPDIR}/home"
MOCK_WORKSPACE="${TEST_TMPDIR}/workspace"

PASSED=0
FAILED=0

cleanup() {
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

assert_true() {
    local expr="$1"
    local msg="$2"
    if eval "$expr"; then
        pass "$msg"
    else
        fail "$msg (expression failed: $expr)"
    fi
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

echo "================================================================================"
echo "Running Backup & Restore Test Suite"
echo "================================================================================"

echo "==> Test 1: Backup script syntax and executable permissions"
assert_true "bash -n '$BACKUP_SCRIPT'" "backup_cline_omniroute.sh has valid bash syntax"
assert_true "[[ -x '$BACKUP_SCRIPT' ]]" "backup_cline_omniroute.sh is executable"

# Setup Mock Environment
mkdir -p "${MOCK_HOME}/.omniroute" \
         "${MOCK_HOME}/.config/systemd/user" \
         "${MOCK_HOME}/.cline/data/settings" \
         "${MOCK_HOME}/ClineOmniRouteBackups" \
         "${MOCK_WORKSPACE}/.clinerules" \
         "${MOCK_WORKSPACE}/.memory" \
         "${MOCK_WORKSPACE}/.cline/scripts"

sqlite3 "${MOCK_HOME}/.omniroute/storage.sqlite" "PRAGMA journal_mode=WAL; CREATE TABLE providers (id TEXT PRIMARY KEY, name TEXT); INSERT INTO providers VALUES ('p1', 'OpenAI');"
echo "STORAGE_KEY=test-secret-key-12345" > "${MOCK_HOME}/.omniroute/.env"
chmod 600 "${MOCK_HOME}/.omniroute/.env"

echo "[Service]" > "${MOCK_HOME}/.config/systemd/user/omniroute.service"
echo '{"lastSession": "sess-42"}' > "${MOCK_HOME}/.cline/data/globalState.json"
echo '{"apiKey": "sk-cline-test"}' > "${MOCK_HOME}/.cline/data/secrets.json"
chmod 600 "${MOCK_HOME}/.cline/data/secrets.json"
echo '{"customTheme": "dark"}' > "${MOCK_HOME}/.cline/data/settings/theme.json"

echo "rule 1: minimal diffs" > "${MOCK_WORKSPACE}/.clinerules/rules.txt"
echo "# Active Context" > "${MOCK_WORKSPACE}/.memory/activeContext.md"
cat > "${MOCK_WORKSPACE}/.cline/scripts/verify.sh" << 'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "${MOCK_WORKSPACE}/.cline/scripts/verify.sh"

export BACKUP_PASSPHRASE="test-passphrase-2026"
export SKIP_GDRIVE_SYNC=1
echo "==> Test 2: Executing backup routine in isolated environment"
BACKUP_OUTPUT=$(HOME="$MOCK_HOME" "$BACKUP_SCRIPT" backup "$MOCK_WORKSPACE")

assert_true "[[ -d '${MOCK_HOME}/ClineOmniRouteBackups' ]]" "Backup output directory created"
ARCHIVES=(${MOCK_HOME}/ClineOmniRouteBackups/cline_omniroute_backup_*.tar.gz.gpg)
assert_true "[[ -f '${ARCHIVES[0]}' ]]" "Encrypted backup archive created (.tar.gz.gpg)"

GPG_PACKET_INFO=$(gpg --list-packets "${ARCHIVES[0]}" 2>/dev/null | head -n 10 || true)
assert_true "[[ '$GPG_PACKET_INFO' == *'encrypted'* || '$GPG_PACKET_INFO' == *'symkey'* ]]" "Archive is verified AES/symmetric encrypted"

echo "==> Test 3: Local restoration of all backed up components"
RESTORE_WORKSPACE="${TEST_TMPDIR}/restored_workspace"
mkdir -p "$RESTORE_WORKSPACE"

rm -f "${MOCK_HOME}/.omniroute/storage.sqlite"
echo "CORRUPTED" > "${MOCK_HOME}/.omniroute/.env"
rm -f "${MOCK_HOME}/.cline/data/secrets.json"
rm -f "${MOCK_HOME}/.cline/data/settings/theme.json"

HOME="$MOCK_HOME" "$BACKUP_SCRIPT" --restore "${ARCHIVES[0]}" "$RESTORE_WORKSPACE"

RESTORED_PROVIDER=$(sqlite3 "${MOCK_HOME}/.omniroute/storage.sqlite" "SELECT name FROM providers WHERE id='p1';")
assert_eq "$RESTORED_PROVIDER" "OpenAI" "Restored SQLite database contains expected records"

RESTORED_ENV_CONTENT=$(cat "${MOCK_HOME}/.omniroute/.env")
assert_true "[[ '$RESTORED_ENV_CONTENT' == *'STORAGE_KEY=test-secret-key-12345'* ]]" "Restored .env matches original configuration"
ENV_PERMS=$(stat -c "%a" "${MOCK_HOME}/.omniroute/.env")
assert_eq "$ENV_PERMS" "600" "Restored .env has restricted chmod 600 permissions"

SECRETS_CONTENT=$(cat "${MOCK_HOME}/.cline/data/secrets.json")
assert_true "[[ '$SECRETS_CONTENT' == *'sk-cline-test'* ]]" "Restored Cline secrets.json content is intact"
SECRETS_PERMS=$(stat -c "%a" "${MOCK_HOME}/.cline/data/secrets.json")
assert_eq "$SECRETS_PERMS" "600" "Restored Cline secrets.json has restricted chmod 600 permissions"

THEME_CONTENT=$(cat "${MOCK_HOME}/.cline/data/settings/theme.json")
assert_true "[[ '$THEME_CONTENT' == *'dark'* ]]" "Restored Cline settings/theme.json is intact"

assert_true "[[ -f '${RESTORE_WORKSPACE}/.memory/activeContext.md' ]]" "Workspace .memory restored"
assert_true "[[ -f '${RESTORE_WORKSPACE}/.clinerules/rules.txt' ]]" "Workspace .clinerules restored"
assert_true "[[ -x '${RESTORE_WORKSPACE}/.cline/scripts/verify.sh' ]]" "Workspace verify.sh restored and executable"

echo "==> Test 4: Backup retention policy pruning"
for i in {1..7}; do
    touch "${MOCK_HOME}/ClineOmniRouteBackups/cline_omniroute_backup_20260101_00000${i}.tar.gz.gpg"
done

HOME="$MOCK_HOME" "$BACKUP_SCRIPT" backup "$MOCK_WORKSPACE" >/dev/null 2>&1
COUNT=$(ls -1 "${MOCK_HOME}/ClineOmniRouteBackups"/cline_omniroute_backup_*.tar.gz.gpg | wc -l | tr -d ' ')
assert_eq "$COUNT" "5" "Retention policy keeps exactly 5 most recent backups"

echo "==> Test 5: Google Drive restore flow (--restore-gdrive)"
MOCK_BIN="${TEST_TMPDIR}/bin"
mkdir -p "$MOCK_BIN"
MOCK_GDRIVE_DIR="${TEST_TMPDIR}/mock_gdrive"
mkdir -p "$MOCK_GDRIVE_DIR"
LATEST_ARCHIVE=$(ls -1t "${MOCK_HOME}/ClineOmniRouteBackups"/cline_omniroute_backup_*.tar.gz.gpg | head -n 1)
cp "${LATEST_ARCHIVE}" "${MOCK_GDRIVE_DIR}/"
LATEST_BASENAME="$(basename "${LATEST_ARCHIVE}")"

cat > "${MOCK_BIN}/rclone" << EOF
#!/usr/bin/env bash
if [[ "\$1" == "lsf" ]]; then
    echo "$LATEST_BASENAME"
elif [[ "\$1" == "copy" ]]; then
    cp "${MOCK_GDRIVE_DIR}/$LATEST_BASENAME" "\$3/"
fi
EOF
chmod +x "${MOCK_BIN}/rclone"

RESTORE_GDRIVE_WORKSPACE="${TEST_TMPDIR}/restored_gdrive_workspace"
mkdir -p "$RESTORE_GDRIVE_WORKSPACE"
rm -f "${MOCK_HOME}/.omniroute/storage.sqlite"

PATH="${MOCK_BIN}:${PATH}" HOME="$MOCK_HOME" "$BACKUP_SCRIPT" --restore-gdrive "$RESTORE_GDRIVE_WORKSPACE"
assert_true "[[ -f '${MOCK_HOME}/.omniroute/storage.sqlite' ]]" "Remote --restore-gdrive successfully restores SQLite database"
assert_true "[[ -f '${RESTORE_GDRIVE_WORKSPACE}/.clinerules/rules.txt' ]]" "Remote --restore-gdrive successfully restores workspace"

echo "==> Test 6: Error handling"
if HOME="$MOCK_HOME" "$BACKUP_SCRIPT" --restore "${TEST_TMPDIR}/nonexistent.gpg" >/dev/null 2>&1; then
    fail "Restoring nonexistent file should exit with non-zero status"
else
    pass "Restoring nonexistent file exits with non-zero status"
fi

echo "================================================================================"
printf "Backup Test Summary: %d passed, %d failed\n" "$PASSED" "$FAILED"
echo "================================================================================"

if (( FAILED > 0 )); then
    exit 1
fi
exit 0

