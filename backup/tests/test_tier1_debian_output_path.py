"""Regression coverage for the Tier-1 archive destination passed into Debian."""
from pathlib import Path
import subprocess

BACKUP = Path(__file__).resolve().parents[1]
LAUNCHER = BACKUP / "run_debian_noninteractive.sh"


def test_launcher_syntax():
    subprocess.run(["bash", "-n", str(LAUNCHER)], check=True)


def test_launcher_passes_explicit_output_to_debian():
    source = LAUNCHER.read_text()
    assert 'host_out="${TIER1_LOCAL_DIR:-' in source
    assert '"$ROOTFS"/*)' in source
    assert '/sdcard/*)' in source
    assert 'ANDROID_OUT="$debian_out"' in source
    assert 'Unsupported Tier-1 output path' in source


def test_producer_prefers_explicit_output():
    producer = (BACKUP / "backup_cline_omniroute.sh").read_text()
    assert 'if [ -n "${ANDROID_OUT:-}" ]; then' in producer
