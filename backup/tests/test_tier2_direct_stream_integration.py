"""Synthetic direct-stream integration tests. No actual cloud access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "snapshot_andronix2_direct_stream_experimental.sh"
FAKE = """#!/usr/bin/env python3
import os, sys
from pathlib import Path
cmd, *args = sys.argv[1:]
immutable = "--immutable" in args
args = [x for x in args if x != "--immutable"]
base = Path(os.environ["FAKE_CLOUD"])
failure = os.environ.get("FAKE_FAILURE", "")
def path(name):
    assert name.startswith("fake:")
    return base / name[5:]
if cmd == "lsf":
    if failure == "listing": sys.exit(31)
    folder = path(args[0])
    if folder.is_dir():
        for item in folder.iterdir():
            if item.is_file(): print(item.name)
elif cmd == "rcat":
    dest = path(args[0]); dest.parent.mkdir(parents=True, exist_ok=True)
    if immutable and dest.exists(): sys.exit(32)
    if failure == "upload":
        dest.write_bytes(sys.stdin.buffer.read(10)); sys.exit(33)
    data = sys.stdin.buffer.read()
    dest.write_bytes(b"corrupted" if failure == "staged_corrupt" else data)
elif cmd == "cat":
    src = path(args[0])
    if failure == "final_corrupt" and not src.name.endswith(".uploading"):
        sys.stdout.buffer.write(b"corrupted")
    else: sys.stdout.buffer.write(src.read_bytes())
elif cmd == "moveto":
    if failure == "publication": sys.exit(34)
    src, dest = path(args[0]), path(args[1])
    if failure == "collision": dest.write_bytes(b"existing")
    if immutable and dest.exists(): sys.exit(35)
    src.rename(dest)
elif cmd == "about": print("Free: 1 TiB")
else: sys.exit(99)
"""

@unittest.skipUnless(all(shutil.which(x) for x in ("bash", "tar", "gpg", "flock")),
                     "requires shell tools")
class DirectStreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tier2-stream-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "home"
        root = self.home / ".andronix/distros/debian/rootfs"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "issue").write_text("synthetic only")
        (root / "etc" / "passwd").write_text("root:x:0:0:root:/root:/bin/sh")
        (root / "etc" / "os-release").write_text("ID=debian")
        (self.home / "start-debian.sh").write_text("#!/bin/sh")
        self.key = self.base / "passphrase"
        self.key.write_text("synthetic secret")
        self.key.chmod(0o600)
        self.cloud = self.base / "cloud"
        bin_dir = self.base / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "rclone"
        fake.write_text(FAKE)
        fake.chmod(0o700)
        self.path = str(bin_dir) + os.pathsep + os.environ["PATH"]
        # Model process state, not the host's running Debian session.
        self.pgrep = bin_dir / "pgrep"
        self.pgrep.write_text("#!/bin/sh\nexit 1\n")
        self.pgrep.chmod(0o700)
        self.flock = bin_dir / "flock"
        self.flock.write_text("#!/bin/sh\nexit 0\n")
        self.flock.chmod(0o700)
        self.gnupg = self.base / "gnupg"
        self.gnupg.mkdir(mode=0o700)
        script = SOURCE.read_text()
        guard = '[[ "' + chr(36) + '{PREFIX:-}" == /data/data/com.termux/files/usr ]]'
        replacement = '[[ -n "' + chr(36) + '{FAKE_CLOUD:-}" ]]'
        self.assertIn(guard, script)
        self.script = self.base / "stream.sh"
        self.script.write_text(script.replace(guard, replacement))
        shutil.copyfile(SOURCE.parent / "validate_andronix2_archive.py",
                        self.base / "validate_andronix2_archive.py")

    def run_case(self, failure="", overrides=None):
        env = {"PATH": os.environ["PATH"], "GNUPGHOME": str(self.gnupg)}
        env.update(HOME=str(self.home), PATH=self.path,
                   PREFIX="/data/data/com.termux/files/usr",
                   BACKUP_PASSPHRASE_FILE=str(self.key),
                   GDRIVE_SNAP_REMOTE="fake:backups",
                   FAKE_CLOUD=str(self.cloud), FAKE_FAILURE=failure,
                   TIER2_EXPERIMENTAL_STREAM_CONFIRM="I_UNDERSTAND_EXPERIMENTAL")
        if overrides: env.update(overrides)
        return subprocess.run(["bash", str(self.script), "--gdrive-stream"],
                              env=env, capture_output=True, text=True, timeout=45)

    def assert_no_published_archive(self, failure="", overrides=None):
        result = self.run_case(failure, overrides)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(list(self.cloud.glob("backups/*.tar.gz.gpg")))
        self.assertFalse(list(self.home.rglob("*.tar.gz.gpg")))

    def test_upload_failure(self):
        self.assert_no_published_archive("upload")

    def test_staged_corruption(self):
        self.assert_no_published_archive("staged_corrupt")

    def test_listing_failure(self):
        self.assert_no_published_archive("listing")

    def test_publication_failure(self):
        self.assert_no_published_archive("publication")

    def test_collision(self):
        result = self.run_case("collision")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        existing = list(self.cloud.glob("backups/*.tar.gz.gpg"))
        self.assertEqual(len(existing), 1)
        self.assertEqual(existing[0].read_bytes(), b"existing")
        self.assertNotIn("PASS: Encrypted stream", result.stdout)
        self.assertFalse(list(self.home.rglob("*.tar.gz.gpg")))

    def test_missing_passphrase(self):
        self.assert_no_published_archive(overrides={"BACKUP_PASSPHRASE_FILE": str(self.base / "missing")})

    def test_confirmation_required(self):
        self.assert_no_published_archive(overrides={"TIER2_EXPERIMENTAL_STREAM_CONFIRM": ""})

    def test_lock_denial_blocks_publication(self):
        self.flock.write_text("#!/bin/sh\nexit 1\n")
        result = self.run_case()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Another direct-stream backup is running", result.stderr)
        self.assertFalse(self.cloud.exists())
        self.assertFalse(list(self.base.rglob("*.tar.gz.gpg")))

    def test_running_debian_blocks_before_any_output(self):
        self.pgrep.write_text("#!/bin/sh\nexit 0\n")
        result = self.run_case()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stop Debian", result.stderr)
        self.assertFalse(self.cloud.exists())
        self.assertFalse(list(self.base.rglob("*.tar.gz.gpg")))

    def test_success(self):
        result = self.run_case()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(self.cloud.glob("backups/*.tar.gz.gpg"))), 1)
        self.assertFalse(list(self.home.rglob("*.tar.gz.gpg")))
        self.assertIn("PASS: Encrypted stream", result.stdout)

    def test_final_corruption_detected(self):
        result = self.run_case("final_corrupt")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS: Encrypted stream", result.stdout)


if __name__ == "__main__":
    unittest.main()
