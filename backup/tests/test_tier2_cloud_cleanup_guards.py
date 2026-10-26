"""Static safety regressions for opt-in Tier-2 cloud publication.

These tests make no network requests and do not touch live backups.
Full mocked command failure-injection remains required before activation.
"""
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "snapshot_andronix2_streaming.sh"


class CloudCleanupSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text()
        cls.cloud = cls.script.split('if [[ "$MODE" == --gdrive ]]; then', 1)[1].split('\n    fi', 1)[0]

    def test_deletion_opt_in_is_disabled_by_default(self):
        self.assertIn('TIER2_DELETE_LOCAL_AFTER_VERIFIED_UPLOAD:-0', self.cloud)

    def test_staging_and_published_hash_verification_precede_deletion(self):
        stage = self.cloud.index('[[ "$local_hash" == "$remote_hash" ]]')
        publish = self.cloud.index('rclone moveto --immutable "$remote_partial" "$remote_final"')
        final = self.cloud.index('[[ "$local_hash" == "$final_hash" ]]')
        delete = self.cloud.index('rm -- "$out"')
        self.assertLess(stage, publish)
        self.assertLess(publish, final)
        self.assertLess(final, delete)

    def test_no_unconditional_local_deletion(self):
        self.assertEqual(self.cloud.count('rm -- "$out"'), 1)
        self.assertIn('if [[ "${TIER2_DELETE_LOCAL_AFTER_VERIFIED_UPLOAD:-0}" == 1 ]]; then', self.cloud)

    def test_upload_is_staged_before_publication(self):
        self.assertIn('remote_partial="$REMOTE/$name.uploading"', self.cloud)
        self.assertIn('rclone copyto --immutable "$out" "$remote_partial"', self.cloud)
        self.assertIn('rclone cat "$remote_final"', self.cloud)


if __name__ == "__main__":
    unittest.main()
