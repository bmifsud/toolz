"""Private GPG homes independent of long pytest/Termux test paths."""
import os
from pathlib import Path
import subprocess
import tempfile

import pytest


@pytest.fixture
def short_gnupg_home():
    # tempfile honors TMPDIR on Termux and chooses a writable directory on Debian.
    # Do not put agent sockets beneath pytest's long per-test directory names.
    with tempfile.TemporaryDirectory(prefix='g-') as directory:
        home = Path(directory)
        home.chmod(0o700)
        if len(os.fsencode(str(home / 'S.gpg-agent.browser'))) >= 104:
            pytest.fail('GPG socket path too long: set TMPDIR to a short private writable directory')
        try:
            yield home
        finally:
            # Only stop agents belonging to this fixture, never the user's agent.
            subprocess.run(['gpgconf', '--homedir', str(home), '--kill', 'all'],
                           check=True, capture_output=True, timeout=15)
