from pathlib import Path

ROOT = Path(__file__).parent

def test_secure_loader_checks_permissions_and_owner():
    script = (ROOT / "termux-bridge-start-secure.sh").read_text()
    assert 'stat -c %a' in script
    assert 'stat -c %u' in script
    assert '! -L "$CONFIG"' in script
    assert 'BRIDGE_DEVICE_TOKEN' in script
    assert 'exec bash' in script

def test_boot_hook_does_not_touch_backup_hooks():
    script = (ROOT / "install-termux-bridge-boot.sh").read_text()
    assert '30-toolz-bridge' in script
    assert 'chmod 700 "$HOOK"' in script
    assert '20-toolz-backup' not in script
