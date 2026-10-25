import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location("fetch_apk", Path(__file__).with_name("fetch_apk.py"))
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.run = dict(id=fetch.RUN, head_sha=fetch.COMMIT, head_branch="main", event="push",
                        status="completed", conclusion="success", path=".github/workflows/android.yml",
                        repository={"full_name": fetch.REPO}, head_repository={"full_name": fetch.REPO})
        self.artifact = dict(id=fetch.ARTIFACT, name="android-debug-apk", expired=False,
                             digest=f"sha256:{fetch.ZIP_SHA}",
                             workflow_run={"id": fetch.RUN, "head_sha": fetch.COMMIT})

    def test_expected_provenance(self):
        fetch.validate_run(self.run)
        fetch.validate_artifact(self.artifact)

    def test_untrusted_sources_and_failed_or_incomplete_runs_rejected(self):
        for key, value in [("id", 1), ("head_sha", "different"), ("head_branch", "feature"),
                           ("event", "pull_request"), ("status", "in_progress"),
                           ("conclusion", "failure"), ("path", "other.yml"),
                           ("repository", {"full_name": "attacker/toolz"}),
                           ("head_repository", {"full_name": "attacker/toolz"})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                fetch.validate_run({**self.run, key: value})

    def test_expired_wrong_artifact_or_digest_rejected(self):
        for key, value in [("id", 1), ("name", "other"), ("expired", True), ("digest", "bad"),
                           ("workflow_run", {"id": 1, "head_sha": fetch.COMMIT}),
                           ("workflow_run", {"id": fetch.RUN, "head_sha": "bad"})]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                fetch.validate_artifact({**self.artifact, key: value})

    def test_tampered_archive_rejected(self):
        with self.assertRaisesRegex(ValueError, "ZIP checksum"):
            fetch.unpack(b"tampered")

    def test_apk_hash_and_archive_member_checks(self):
        def archive(name, payload):
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w") as package:
                package.writestr(name, payload)
            return output.getvalue()
        data = archive("app-debug.apk", b"test APK bytes")
        with patch.object(fetch, "ZIP_SHA", hashlib.sha256(data).hexdigest()):
            with self.assertRaisesRegex(ValueError, "APK checksum"):
                fetch.unpack(data)
            with patch.object(fetch, "APK_SHA", hashlib.sha256(b"test APK bytes").hexdigest()):
                self.assertEqual(fetch.unpack(data), b"test APK bytes")
        data = archive("../app-debug.apk", b"test APK bytes")
        with patch.object(fetch, "ZIP_SHA", hashlib.sha256(data).hexdigest()):
            with self.assertRaisesRegex(ValueError, "contents"):
                fetch.unpack(data)


class ChecklistTests(unittest.TestCase):
    def test_initializer_keeps_every_device_test_pending_and_preserves_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.json"
            command = [sys.executable, str(Path(__file__).with_name("checklist.py")),
                       "--initialize", "--output", str(output)]
            subprocess.run(command, check=True, capture_output=True)
            original = output.read_bytes()
            report = json.loads(original)
            self.assertEqual(len(report["tests"]), 13)
            self.assertTrue(all(case["status"] == "pending" for case in report["tests"]))
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), original)

    def test_interruption_does_not_mark_unobserved_cases_passed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.json"
            subprocess.run([sys.executable, str(Path(__file__).with_name("checklist.py")),
                            "--output", str(output)], input="Android 16\nbuild ID\n",
                           text=True, check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertTrue(all(case["status"] == "pending" for case in report["tests"]))


if __name__ == "__main__":
    unittest.main()
