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
    def test_desktop_commander_absent(self):
        self.assertEqual(plan_execution(route("@Termux check cron"), "git-branch").status, "desktop_commander_unavailable")
    def test_no_arbitrary_command(self):
        self.assertEqual(plan_execution(route("@Termux check cron"), "rm -rf /", desktop_commander_available=True).status, "denied")
    def test_allowlisted_only_when_available(self):
        p = plan_execution(route("@Termux run pytest"), "tier1-tests", desktop_commander_available=True)
        self.assertEqual((p.status, p.operation), ("ready_for_commander", "tier1-tests"))
    def test_mutation_never_executes(self):
        d = route("@Termux delete backups")
        self.assertEqual(plan_execution(d, "git-branch", desktop_commander_available=True).status, "approval_required")
        self.assertEqual(plan_execution(d, "git-branch", desktop_commander_available=True, user_approved=True).status, "denied")
    def test_github_connector_required(self):
        self.assertEqual(plan_execution(route("@GitHub check branch")).status, "connector_required")
    def test_local_only(self):
        self.assertEqual(plan_execution(route("Explain backups")).status, "local_only")

class FailClosedPlanningTests(unittest.TestCase):
    def test_ambiguous_request_requires_clarification(self):
        self.assertEqual(plan_execution(route("Compare GitHub and Termux")).status, "clarification_required")

    def test_commander_destination_preserved(self):
        decision = route("@Debian check disk")
        for authenticated in (False, True):
            plan = plan_execution(decision, "debian-disk", desktop_commander_available=authenticated)
            self.assertEqual(plan.destination, "desktop_commander")

    def test_unknown_permission_or_action_denied(self):
        from request_router import Decision
        for permission, action in (("unknown", "propose_diagnostic"), ("allowlisted_only", "execute"),
                                   ("connector_scoped", "propose_connector")):
            decision = Decision("desktop_commander", permission, action, "fixture")
            plan = plan_execution(decision, "git-branch", desktop_commander_available=True)
            self.assertEqual((plan.status, plan.operation), ("denied", None))

    def test_truthy_nonboolean_flags_denied(self):
        for value in ("false", 1, [], None):
            with self.subTest(value=value):
                for flags in ({"desktop_commander_available": value}, {"user_approved": value}):
                    self.assertEqual(plan_execution(route("@Termux check cron"), "git-branch", **flags).status, "denied")

    def test_malformed_inputs_denied(self):
        for decision in (None, {}, object()):
            self.assertEqual(plan_execution(decision).status, "denied")
        self.assertEqual(plan_execution(route("@Termux check cron"), [], desktop_commander_available=True).status, "denied")

    def test_legacy_direct_destinations_are_denied(self):
        from request_router import Decision
        for target in ("termux", "debian"):
            for available in (False, True):
                plan = plan_execution(Decision(target, "allowlisted_only", "propose_diagnostic", "legacy"),
                                      "git-branch", desktop_commander_available=available)
                self.assertEqual((plan.status, plan.operation), ("denied", None))

    def test_unknown_destination_denied(self):
        from request_router import Decision
        self.assertEqual(plan_execution(Decision("shell", "none", "answer", "fixture")).status, "denied")

if __name__ == "__main__":
    unittest.main()
