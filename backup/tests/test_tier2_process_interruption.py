"""Real subprocess interruption tests, restricted to synthetic temporary fixtures."""
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest

from backup.extract_andronix2_isolated_experimental import ROOT


class ProcessInterruptionTests(unittest.TestCase):
    def test_sigkill_during_synthetic_extraction_never_publishes(self):
        with tempfile.TemporaryDirectory(prefix="tier2-kill-test-") as tmp:
            base = Path(tmp)
            archive = base / "synthetic.tar.gz"
            dest = base / "published"
            # A sparse source payload is generated in a temp file, never rootfs.
            payload = base / "payload.bin"
            with payload.open("wb") as out:
                block = b"synthetic-test-only-" * 4096
                for _ in range(256):
                    out.write(block)
            with tarfile.open(archive, "w:gz", compresslevel=1) as tf:
                for name in (".andronix", ".andronix/distros",
                             ".andronix/distros/debian", ROOT):
                    info = tarfile.TarInfo(name)
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    tf.addfile(info)
                info = tarfile.TarInfo("start-debian.sh")
                info.size = 0
                tf.addfile(info, io.BytesIO())
                for i in range(24):
                    tf.add(payload, arcname=f"{ROOT}/tmp/fixture-{i}.bin", recursive=False)
            runner = (
                "import sys; "
                "from backup.recover_andronix2_transactional_experimental "
                "import recover_synthetic; "
                "recover_synthetic(sys.argv[1], sys.argv[2])"
            )
            proc = subprocess.Popen(
                [sys.executable, "-c", runner, str(archive), str(dest)],
                cwd=str(Path(__file__).resolve().parents[2]),
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 15
                started = False
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        stderr = proc.stderr.read().decode(errors="replace")
                        self.fail(f"recovery finished before interruption: {proc.returncode}: {stderr}")
                    stages = list(base.glob(".tier2-*.incomplete"))
                    if stages and any((stage / ROOT / "tmp").exists() for stage in stages):
                        started = True
                        break
                    time.sleep(0.01)
                self.assertTrue(started, "synthetic extraction did not start before timeout")
                proc.kill()
                proc.wait(timeout=10)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(dest.exists(), "terminated recovery was published")
                stages = list(base.glob(".tier2-*.incomplete"))
                self.assertEqual(len(stages), 1)
                self.assertFalse((stages[0] / ".tier2-recovery-complete").exists())
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
                proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
