import importlib.util
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
for name in ("request_router", "routing_adapter"):
    spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

from request_router import route
from routing_adapter import plan_execution

class IntegrationBoundaryTests(unittest.TestCase):
    def test_bridge_absent(self):
        self.assertEqual(plan_execution(route("@Termux check cron"), "git-branch").status, "bridge_disconnected")
    def test_no_arbitrary_command(self):
        self.assertEqual(plan_execution(route("@Termux check cron"), "rm -rf /", bridge_authenticated=True).status, "denied")
    def test_allowlisted_only_when_authenticated(self):
        p = plan_execution(route("@Termux run pytest"), "tier1-tests", bridge_authenticated=True)
        self.assertEqual((p.status, p.operation), ("ready_for_executor", "tier1-tests"))
    def test_mutation_never_executes(self):
        d = route("@Termux delete backups")
        self.assertEqual(plan_execution(d, "git-branch", bridge_authenticated=True).status, "approval_required")
        self.assertEqual(plan_execution(d, "git-branch", bridge_authenticated=True, user_approved=True).status, "denied")
    def test_github_connector_required(self):
        self.assertEqual(plan_execution(route("@GitHub check branch")).status, "connector_required")
    def test_local_only(self):
        self.assertEqual(plan_execution(route("Explain backups")).status, "local_only")

if __name__ == "__main__":
    unittest.main()
