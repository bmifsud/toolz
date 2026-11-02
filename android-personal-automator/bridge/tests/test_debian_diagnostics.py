import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
for name in ("request_router", "routing_adapter", "debian_diagnostics"):
    spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
from request_router import route
from routing_adapter import plan_execution
from debian_diagnostics import discover_launcher, diagnostic_spec

class DebianTests(unittest.TestCase):
    def test_explicit(self):
        self.assertEqual(route("@Debian check disk").destination, "debian")
    def test_auto(self):
        self.assertEqual(route("Check Andronix rootfs").destination, "debian")
    def test_ambiguous(self):
        self.assertEqual(route("Compare Debian and Termux").permission, "clarify")
    def test_disconnected(self):
        self.assertEqual(plan_execution(route("@Debian check disk"), "debian-disk").status, "bridge_disconnected")
    def test_allowlist(self):
        self.assertEqual(plan_execution(route("@Debian check disk"), "debian-disk", bridge_authenticated=True).status, "ready_for_executor")
        self.assertEqual(plan_execution(route("@Debian check disk"), "shell", bridge_authenticated=True).status, "denied")
    def test_mutation(self):
        d = route("@Debian delete rootfs")
        self.assertEqual(plan_execution(d, "debian-identity", bridge_authenticated=True, user_approved=True).status, "denied")
    def test_specs(self):
        self.assertEqual(diagnostic_spec("debian-identity").argv, ("cat", "/etc/os-release"))
        with self.assertRaises(ValueError):
            diagnostic_spec("bash")
    def test_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "start-debian.sh").write_text("#!/bin/sh\n")
            (p / "debian.sh").symlink_to(p / "start-debian.sh")
            self.assertEqual(discover_launcher(p), (p / "start-debian.sh",))

if __name__ == "__main__":
    unittest.main()
