"""Check exact GNU tar producer paths against Tier-2's canonical validator.

Creates a tiny fake Termux HOME; never snapshots or touches live Debian.
"""
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

from backup.tests.test_tier2_isolated_extractor import ROOT

VALIDATOR = Path(__file__).resolve().parents[1] / "validate_andronix2_archive.py"


@unittest.skipUnless(shutil.which("tar"), "tar required")
class ProductionTarFormatTests(unittest.TestCase):
    def test_exact_producer_member_arguments(self):
        with tempfile.TemporaryDirectory(prefix="tier2-tar-format-") as tmp:
            home = Path(tmp)
            root = home / ROOT
            root.mkdir(parents=True)
            (root / "etc").mkdir()
            (root / "etc" / "issue").write_text("synthetic Debian fixture\n")
            (home / "start-debian.sh").write_text("#!/bin/sh\n")
            cmd = [
                "tar", "-C", str(home), "-czpf", "-", "--one-file-system",
                "--exclude=.andronix/distros/debian/rootfs/sdcard",
                "--exclude=.andronix/distros/debian/rootfs/proc",
                "--exclude=.andronix/distros/debian/rootfs/sys",
                "--exclude=.andronix/distros/debian/rootfs/dev",
                "--exclude=.andronix/distros/debian/rootfs/tmp",
                "--exclude=.andronix/distros/debian/rootfs/run",
                "--exclude=.andronix/distros/debian/rootfs/var/cache/apt/archives",
                "--exclude=.andronix/distros/debian/rootfs/home/b/.gnupg/S.gpg-agent*",
                ROOT, "start-debian.sh",
            ]
            result = subprocess.run(cmd, capture_output=True, check=True, timeout=20)
            with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:gz") as archive:
                names = archive.getnames()
            self.assertIn(ROOT, names)
            self.assertIn("start-debian.sh", names)
            self.assertTrue(all(not name.startswith("./") for name in names), names)
            validated = subprocess.run(
                [sys.executable, str(VALIDATOR)],
                input=result.stdout, capture_output=True, timeout=20,
            )
            self.assertEqual(validated.returncode, 0,
                             validated.stderr.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main()
