"""Execute the real Tier-2 upload branch with synthetic inputs and fake rclone.

No real cloud operations. The copied script has only its Termux HOME/PREFIX
guards replaced so it can run against an isolated fixture.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "snapshot_andronix2_streaming.sh"
FAKE_RCLONE = r'''#!/usr/bin/env python3
import os, pathlib, shutil, sys
cmd, *args = sys.argv[1:]
immutable = "--immutable" in args
args = [arg for arg in args if arg != "--immutable"]
root = pathlib.Path(os.environ["FAKE_CLOUD"])
def path(remote):
    assert remote.startswith("fake:"), remote
    return root / remote[5:]
failure = os.environ.get("FAKE_FAILURE", "")
if cmd == "lsf":
    p = path(args[0])
    if failure == "list":
        sys.exit(17)
    if p.is_dir():
        for item in p.iterdir():
            if item.is_file():
                print(item.name)
    elif p.exists():
        print(p.name)
elif cmd == "copyto":
    if failure == "upload":
        sys.exit(19)
    target = path(args[1]); target.parent.mkdir(parents=True, exist_ok=True)
    if failure == "collision" or (immutable and target.exists()):\n        sys.exit(27)\n    shutil.copyfile(args[0], target)
    if failure == "interrupted":\n        target.write_bytes(b"incomplete upload")\n        sys.exit(28)\n    if failure == "staged_corrupt":
        target.write_bytes(b"corrupted staged object")
elif cmd == "cat":
    p = path(args[0])
    if failure == "final_corrupt" and not p.name.endswith(".uploading"):
        sys.stdout.buffer.write(b"corrupted published object")
    else:
        sys.stdout.buffer.write(p.read_bytes())
elif cmd == "moveto":
    if failure == "publish":
        sys.exit(23)
    source, target = path(args[0]), path(args[1])
    if failure == "publish_collision":\n        target.write_bytes(b"existing other device backup")\n    if immutable and target.exists():\n        sys.exit(29)\n    source.rename(target)
else:
    sys.exit(99)
'''


@unittest.skipUnless(all(shutil.which(x) for x in ("bash", "tar", "gpg", "sha256sum")), "requires bash, tar, gpg, sha256sum")
class MockCloudUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tier2-cloud-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        root = self.home / ".andronix/distros/debian/rootfs"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "issue").write_text("synthetic only\n")
        (self.home / "start-debian.sh").write_text("#!/bin/sh\n")
        self.snaps = self.base / "snapshots"
        self.cloud = self.base / "cloud"
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.key = self.base / "passphrase"
        self.key.write_text("synthetic-key-only\n")
        self.key.chmod(0o600)
        fake = self.bin / "rclone"
        fake.write_text(FAKE_RCLONE)
        fake.chmod(0o700)
        script = SOURCE.read_text()
        script = script.replace('[[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]]', '[[ -n "${FAKE_CLOUD:-}" ]]')
        self.assertIn('[[ "$ROOTFS_DIR" == "$HOME/.andronix/distros/debian/rootfs" ]]', script)
        self.script = self.base / "snapshot.sh"
        self.script.write_text(script)
        shutil.copyfile(SOURCE.parent / "validate_andronix2_archive.py",
                        self.base / "validate_andronix2_archive.py")

    def run_snapshot(self, failure=""):
        env = os.environ.copy()
        env.update(
            HOME=str(self.home), PREFIX="/data/data/com.termux/files/usr",
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            BACKUP_PASSPHRASE_FILE=str(self.key),
            SNAP_DIR=str(self.snaps), GDRIVE_SNAP_REMOTE="fake:backups",
            FAKE_CLOUD=str(self.cloud), FAKE_FAILURE=failure,
            TIER2_DELETE_LOCAL_AFTER_VERIFIED_UPLOAD="1",
        )
        return subprocess.run(["bash", str(self.script), "--gdrive"], env=env,
                              capture_output=True, text=True, timeout=40)

    def assert_retained(self, failure):
        result = self.run_snapshot(failure)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(self.snaps.glob("*.tar.gz.gpg"))), 1,
                         result.stdout + result.stderr)

    def test_listing_failure_retains_local(self):
        self.assert_retained("list")

    def test_interrupted_upload_retains_local(self):
        self.assert_retained("interrupted")

    def test_remote_staged_collision_retains_local(self):
        self.assert_retained("collision")

    def test_remote_publication_collision_retains_local(self):
        self.assert_retained("publish_collision")

    def test_upload_failure_retains_local(self):
        self.assert_retained("upload")

    def test_staged_checksum_failure_retains_local(self):
        self.assert_retained("staged_corrupt")

    def test_publication_failure_retains_local(self):
        self.assert_retained("publish")

    def test_published_checksum_failure_retains_local(self):
        self.assert_retained("final_corrupt")

    def test_success_removes_local_only_after_cloud_verification(self):
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(list(self.snaps.glob("*.tar.gz.gpg")))
        self.assertEqual(len(list(self.cloud.glob("backups/*.tar.gz.gpg"))), 1)


if __name__ == "__main__":
    unittest.main()
