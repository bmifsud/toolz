"""Synthetic Tier-2 GPG AES256 roundtrip tests. Never use real backup keys.

Run from repository root:
python3 -m unittest backup.tests.test_tier2_encrypted_roundtrip -v
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from backup.recover_andronix2_transactional_experimental import (
    COMPLETION_MARKER, recover_synthetic,
)
from backup.tests.test_tier2_isolated_extractor import fixture, ROOT


@unittest.skipUnless(shutil.which("gpg"), "GnuPG is required")
class EncryptedSyntheticRoundtrip(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tier2-gpg-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.gnupg = self.base / "gnupg"
        self.gnupg.mkdir(mode=0o700)
        self.plain = self.base / "fixture.tar.gz"
        self.encrypted = self.base / "fixture.tar.gz.gpg"
        self.decrypted = self.base / "decrypted.tar.gz"
        self.passfile = self.base / "synthetic-passphrase"
        self.passfile.write_text("synthetic-only-not-a-real-backup-key\n")
        self.passfile.chmod(0o600)
        self.destination = self.base / "published"
        fixture(self.plain)

    def gpg(self, *args):
        return subprocess.run(
            ["gpg", "--homedir", str(self.gnupg), "--batch", "--yes", "--no-tty", "--pinentry-mode", "loopback",
             "--passphrase-file", str(self.passfile), *map(str, args)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
        )

    def encrypt(self):
        result = self.gpg("--symmetric", "--cipher-algo", "AES256",
                          "--output", self.encrypted, self.plain)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_encrypt_decrypt_restore_and_hash(self):
        self.encrypt()
        self.assertTrue(self.encrypted.stat().st_size > 0)
        result = self.gpg("--decrypt", "--output", self.decrypted, self.encrypted)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(digest(self.plain), digest(self.decrypted))
        self.assertEqual(recover_synthetic(self.decrypted, self.destination), 5)
        self.assertTrue((self.destination / ROOT).is_dir())
        self.assertTrue((self.destination / COMPLETION_MARKER).is_file())

    def test_wrong_passphrase_never_publishes(self):
        self.encrypt()
        self.passfile.write_text("incorrect-synthetic-passphrase\n")
        result = self.gpg("--decrypt", "--output", self.decrypted, self.encrypted)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())

    def test_corrupted_ciphertext_never_publishes(self):
        self.encrypt()
        data = self.encrypted.read_bytes()
        self.encrypted.write_bytes(data[:max(10, len(data) // 2)])
        result = self.gpg("--decrypt", "--output", self.decrypted, self.encrypted)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
