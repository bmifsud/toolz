"""Static regression checks for the Andronix 2.0 Tier-2 runner wiring."""
from pathlib import Path
import subprocess

BACKUP = Path(__file__).resolve().parents[1]
RUNNER = BACKUP / "run_scheduled_backup.sh"
STREAMING = BACKUP / "snapshot_andronix2_streaming.sh"

def test_scripts_have_valid_bash_syntax():
    for path in (RUNNER, STREAMING):
        subprocess.run(["bash", "-n", str(path)], check=True)

def test_tier2_uses_streaming_snapshot():
    text = RUNNER.read_text()
    assert '"$HERE/snapshot_andronix2_streaming.sh" --gdrive' in text
    assert '"$HERE/snapshot_andronix_debian.sh" --gdrive' not in text

def test_tier2_verifies_current_run_and_cloud():
    text = RUNNER.read_text()
    assert 'export BACKUP_PASSPHRASE_FILE' in text
    assert "s/^Locally verified: //p" in text
    assert '"$HERE/snapshot_andronix2_streaming.sh" --verify-archive "$latest"' in text
    assert 'verify "$latest" "$GDRIVE_SNAP_REMOTE"' in text
    assert 'rm -f "$marker"' in text

def test_tier1_path_remains_separate():
    text = RUNNER.read_text()
    assert 'if [[ "$MODE" == tier1 ]]; then' in text
    assert 'run_debian_noninteractive.sh' in text
