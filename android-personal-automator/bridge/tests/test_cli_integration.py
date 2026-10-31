"""Offline tests for the Toolz CLI integration contract."""
import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location(
    "cli_integration",
    Path(__file__).resolve().parents[1] / "cli_integration.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CliIntegrationContractTests(unittest.TestCase):
    def setUp(self):
        self.registry = module.IntegrationRegistry()
        self.cline = module.IntegrationDescriptor(
            name="cline",
            version="1.0.0",
            capabilities=frozenset({"health", "run-task", "cancel-task"}),
            requires_approval=frozenset({"run-task"}),
        )
        self.registry.register(self.cline)

    def test_contract_version_is_pinned(self):
        self.assertEqual(module.CONTRACT_VERSION, 1)

    def test_descriptor_rejects_unknown_approval_capability(self):
        with self.assertRaises(module.IntegrationError):
            module.IntegrationDescriptor(
                name="bad",
                version="1",
                capabilities=frozenset({"health"}),
                requires_approval=frozenset({"missing"}),
            )

    def test_valid_request_is_reserved_once(self):
        request = module.TaskRequest(
            task_id="task-1",
            integration="cline",
            capability="run-task",
            request_id=module.new_request_id(),
            approval_token="approval-1",
        )
        descriptor = self.registry.reserve_task(request)
        self.assertEqual(descriptor.name, "cline")
        with self.assertRaises(module.DuplicateTaskError):
            self.registry.reserve_task(request)

    def test_approval_is_required_for_declared_capability(self):
        request = module.TaskRequest(
            task_id="task-2",
            integration="cline",
            capability="run-task",
            request_id=module.new_request_id(),
        )
        with self.assertRaises(module.ApprovalRequiredError):
            self.registry.validate_request(request)

    def test_unsupported_capability_is_rejected(self):
        request = module.TaskRequest(
            task_id="task-3",
            integration="cline",
            capability="unknown",
            request_id=module.new_request_id(),
            approval_token="approval-1",
        )
        with self.assertRaises(module.IntegrationError):
            self.registry.validate_request(request)

    def test_unknown_integration_is_rejected(self):
        request = module.TaskRequest(
            task_id="task-4",
            integration="missing",
            capability="health",
            request_id=module.new_request_id(),
        )
        with self.assertRaises(module.UnknownIntegrationError):
            self.registry.validate_request(request)

    def test_contract_version_must_match(self):
        with self.assertRaises(module.IntegrationError):
            module.TaskRequest(
                task_id="task-5",
                integration="cline",
                capability="health",
                request_id=module.new_request_id(),
                contract_version=2,
            )

    def test_path_traversal_and_shell_metacharacters_are_rejected(self):
        for bad in ("../task", "task;rm", "task|id", "task&id", "task\nx", ""):
            with self.assertRaises(module.IntegrationError):
                module.TaskRequest(
                    task_id=bad,
                    integration="cline",
                    capability="health",
                    request_id=module.new_request_id(),
                )

    def test_metadata_is_flat_and_bounded(self):
        self.assertEqual(module.validate_metadata(None), {})
        self.assertEqual(
            module.validate_metadata({"route": "omniroute"}),
            {"route": "omniroute"},
        )
        with self.assertRaises(module.IntegrationError):
            module.validate_metadata({"bad key": "value"})
        with self.assertRaises(module.IntegrationError):
            module.validate_metadata({"route": 123})

    def test_release_task_allows_reuse_after_release(self):
        request = module.TaskRequest(
            task_id="task-6",
            integration="cline",
            capability="health",
            request_id=module.new_request_id(),
        )
        self.registry.reserve_task(request)
        self.registry.release_task("task-6")
        self.registry.reserve_task(request)


if __name__ == "__main__":
    unittest.main()