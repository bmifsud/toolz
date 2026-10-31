import importlib.util
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jules_adapter", root / "jules_adapter.py")
jules_adapter = importlib.util.module_from_spec(spec)
sys.modules["jules_adapter"] = jules_adapter
spec.loader.exec_module(jules_adapter)

JulesConfig = jules_adapter.JulesConfig
JulesIntegration = jules_adapter.JulesIntegration
Plan = jules_adapter.Plan
PlanStep = jules_adapter.PlanStep
TaskStatus = jules_adapter.TaskStatus
redact_secrets = jules_adapter.redact_secrets
validate_plan = jules_adapter.validate_plan


class JulesAdapterTests(unittest.TestCase):
    def setUp(self):
        self.api_token = "jules_secret_token_1234567890_abc"
        self.config = JulesConfig(
            api_token=self.api_token,
            base_url="https://api.jules.ai/v1",
            max_concurrency=3,
            timeout_seconds=30,
            max_output_bytes=1024,
            max_retries=2,
            additional_secrets=["custom_db_password_999"],
        )
        self.adapter = JulesIntegration(self.config)

    def test_config_validation(self):
        # Valid config
        self.assertEqual(self.config.max_concurrency, 3)

        # Repr protects token
        self.assertNotIn(self.api_token, repr(self.config))

        # Invalid token (too short)
        with self.assertRaises(ValueError):
            JulesConfig(api_token="short")

        # Insecure non-loopback HTTP base_url
        with self.assertRaises(ValueError):
            JulesConfig(api_token=self.api_token, base_url="http://remote.jules.ai/v1")

        # Valid loopback HTTP base_url
        loopback_cfg = JulesConfig(api_token=self.api_token, base_url="http://127.0.0.1:8080/v1")
        self.assertEqual(loopback_cfg.base_url, "http://127.0.0.1:8080/v1")

        # Invalid max_concurrency
        with self.assertRaises(ValueError):
            JulesConfig(api_token=self.api_token, max_concurrency=0)

    def test_plan_proposal_and_validation(self):
        # Read-only safe plan
        plan = self.adapter.propose_plan(
            task_id="task_00000001",
            plan_id="plan_001",
            raw_steps=[
                {"step_id": "s1", "action": "inspect", "target_path": "README.md"},
                {"step_id": "s2", "action": "run_test", "command": "pytest tests/"},
            ],
        )
        val = validate_plan(plan)
        self.assertTrue(val.is_valid)
        self.assertFalse(val.requires_approval)

        # Path traversal plan -> Invalid
        bad_plan = self.adapter.propose_plan(
            task_id="task_00000002",
            plan_id="plan_002",
            raw_steps=[
                {"step_id": "s1", "action": "read", "target_path": "../../etc/passwd"},
            ],
        )
        val_bad = validate_plan(bad_plan)
        self.assertFalse(val_bad.is_valid)

        # Absolute target_path plan -> Invalid
        abs_target_plan = self.adapter.propose_plan(
            task_id="task_00000002b",
            plan_id="plan_002b",
            raw_steps=[
                {"step_id": "s1", "action": "read", "target_path": "/root/secret"},
            ],
        )
        val_abs = validate_plan(abs_target_plan)
        self.assertFalse(val_abs.is_valid)

        # Absolute command path plan -> Invalid
        abs_cmd_plan = self.adapter.propose_plan(
            task_id="task_00000002c",
            plan_id="plan_002c",
            raw_steps=[
                {"step_id": "s1", "action": "exec", "command": "cat /tmp/data"},
            ],
        )
        val_cmd_abs = validate_plan(abs_cmd_plan)
        self.assertFalse(val_cmd_abs.is_valid)

        # Mutating plan -> Requires approval
        mutating_plan = self.adapter.propose_plan(
            task_id="task_00000003",
            plan_id="plan_003",
            raw_steps=[
                {"step_id": "s1", "action": "install", "command": "npm install"},
                {"step_id": "s2", "action": "commit", "command": "git commit -m 'update'"},
            ],
        )
        val_mutating = validate_plan(mutating_plan)
        self.assertTrue(val_mutating.is_valid)
        self.assertTrue(val_mutating.requires_approval)

    def test_task_submission_and_approval(self):
        plan_safe = self.adapter.propose_plan(
            task_id="task_safe_01",
            plan_id="plan_safe",
            raw_steps=[{"step_id": "s1", "action": "check", "command": "ls"}],
        )

        # Unapproved safe task succeeds
        task = self.adapter.submit_task(
            task_id="task_safe_01",
            project_id="proj_100",
            description="Run diagnostic check",
            workspace_path="src/project",
            plan=plan_safe,
        )
        self.assertEqual(task.status, TaskStatus.PENDING)

        # Mutating plan without approval fails with PermissionError
        plan_mutating = self.adapter.propose_plan(
            task_id="task_mutating_01",
            plan_id="plan_mutating",
            raw_steps=[{"step_id": "s1", "action": "clean", "command": "rm -rf build/"}],
        )
        with self.assertRaises(PermissionError):
            self.adapter.submit_task(
                task_id="task_mutating_01",
                project_id="proj_100",
                description="Clean build",
                workspace_path="src/project",
                plan=plan_mutating,
                user_approved=False,
            )

        # Mutating plan with user_approved=True succeeds
        task_mut = self.adapter.submit_task(
            task_id="task_mutating_01",
            project_id="proj_100",
            description="Clean build",
            workspace_path="src/project",
            plan=plan_mutating,
            user_approved=True,
        )
        self.assertEqual(task_mut.status, TaskStatus.PENDING)

    def test_duplicate_task_id_and_replay_rejection(self):
        plan = self.adapter.propose_plan(
            task_id="task_replay_01",
            plan_id="plan_01",
            raw_steps=[{"step_id": "s1", "action": "check", "command": "echo hello"}],
        )
        self.adapter.submit_task(
            task_id="task_replay_01",
            project_id="proj_100",
            description="First submission",
            workspace_path="workspace",
            plan=plan,
        )

        # Replay/duplicate task ID
        with self.assertRaises(ValueError) as ctx:
            self.adapter.submit_task(
                task_id="task_replay_01",
                project_id="proj_100",
                description="Duplicate submission",
                workspace_path="workspace",
                plan=plan,
            )
        self.assertIn("Duplicate task ID", str(ctx.exception))

    def test_concurrency_limit(self):
        for i in range(1, 4):
            t_id = f"task_concurrent_{i:02d}"
            p = self.adapter.propose_plan(t_id, "p1", [{"step_id": "s1", "action": "noop"}])
            self.adapter.submit_task(t_id, "proj", "desc", "ws", p)

        # 4th task exceeds max_concurrency=3
        t_id_4 = "task_concurrent_04"
        p4 = self.adapter.propose_plan(t_id_4, "p1", [{"step_id": "s1", "action": "noop"}])
        with self.assertRaises(RuntimeError) as ctx:
            self.adapter.submit_task(t_id_4, "proj", "desc", "ws", p4)
        self.assertIn("Concurrency limit reached", str(ctx.exception))

    def test_secret_redaction_and_bounded_output(self):
        plan = self.adapter.propose_plan("task_secret_01", "p1", [{"step_id": "s1", "action": "echo"}])
        self.adapter.submit_task("task_secret_01", "proj", "desc", "ws", plan)

        # Record result containing API token and custom secret
        secret_out = f"API Token: {self.api_token}, Key: sk-abcdefghijklmnopqrstuvwxyz123456, DB: custom_db_password_999"
        self.adapter.record_execution_result("task_secret_01", exit_code=0, stdout=secret_out)

        retrieved = self.adapter.get_task_status("task_secret_01")
        self.assertNotIn(self.api_token, retrieved.stdout)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz123456", retrieved.stdout)
        self.assertNotIn("custom_db_password_999", retrieved.stdout)
        self.assertIn("[REDACTED]", retrieved.stdout)

        # Bounded stdout truncation test (> 1024 bytes)
        plan_big = self.adapter.propose_plan("task_bigout_01", "p1", [{"step_id": "s1", "action": "echo"}])
        self.adapter.submit_task("task_bigout_01", "proj", "desc", "ws", plan_big)
        big_stdout = "A" * 2000
        self.adapter.record_execution_result("task_bigout_01", exit_code=0, stdout=big_stdout)

        retrieved_big = self.adapter.get_task_status("task_bigout_01")
        self.assertIn("[STDOUT TRUNCATED: EXCEEDED SIZE LIMIT]", retrieved_big.stdout)
        self.assertLessEqual(len(retrieved_big.stdout.encode("utf-8")), self.config.max_output_bytes + 100)

        # Bounded stderr truncation test (> 1024 bytes)
        plan_big_err = self.adapter.propose_plan("task_bigerr_01", "p1", [{"step_id": "s1", "action": "echo"}])
        self.adapter.submit_task("task_bigerr_01", "proj", "desc", "ws", plan_big_err)
        big_stderr = "E" * 2000
        self.adapter.record_execution_result("task_bigerr_01", exit_code=1, stderr=big_stderr)

        retrieved_big_err = self.adapter.get_task_status("task_bigerr_01")
        self.assertIn("[STDERR TRUNCATED: EXCEEDED SIZE LIMIT]", retrieved_big_err.stderr)
        total_len = len(retrieved_big_err.stdout.encode("utf-8")) + len(retrieved_big_err.stderr.encode("utf-8"))
        self.assertLessEqual(total_len, self.config.max_output_bytes + 100)

    def test_cancellation_timeout_and_retry(self):
        # Cancellation
        p1 = self.adapter.propose_plan("task_cancel_01", "p1", [{"step_id": "s1", "action": "noop"}])
        self.adapter.submit_task("task_cancel_01", "proj", "desc", "ws", p1)
        canceled = self.adapter.cancel_task("task_cancel_01")
        self.assertEqual(canceled.status, TaskStatus.CANCELLED)

        # Timeout
        p2 = self.adapter.propose_plan("task_timeout_01", "p1", [{"step_id": "s1", "action": "noop"}])
        self.adapter.submit_task("task_timeout_01", "proj", "desc", "ws", p2)
        timed_out = self.adapter.handle_timeout("task_timeout_01")
        self.assertEqual(timed_out.status, TaskStatus.TIMED_OUT)

        # Retry
        retried = self.adapter.retry_task("task_timeout_01")
        self.assertEqual(retried.status, TaskStatus.PENDING)
        self.assertEqual(retried.retries_count, 1)

        # Retry budget depletion
        self.adapter.handle_timeout("task_timeout_01")
        self.adapter.retry_task("task_timeout_01")  # retry 2
        self.adapter.handle_timeout("task_timeout_01")
        with self.assertRaises(RuntimeError):
            self.adapter.retry_task("task_timeout_01")  # retry 3 -> exceeds max_retries=2

    def test_correlated_receipt_creation_and_verification(self):
        plan = self.adapter.propose_plan("task_receipt_01", "p1", [{"step_id": "s1", "action": "noop"}])
        self.adapter.submit_task("task_receipt_01", "proj", "desc", "ws", plan)

        # Pending task cannot issue receipt
        with self.assertRaises(ValueError):
            self.adapter.create_receipt("task_receipt_01", "req_12345678")

        # Execute task
        self.adapter.record_execution_result("task_receipt_01", exit_code=0, stdout="Task completed successfully")

        receipt = self.adapter.create_receipt("task_receipt_01", "req_12345678")
        self.assertEqual(receipt.task_id, "task_receipt_01")
        self.assertEqual(receipt.request_id, "req_12345678")
        self.assertEqual(receipt.status, "COMPLETED")
        self.assertEqual(len(receipt.output_sha256), 64)

        # Verify receipt
        self.assertTrue(self.adapter.verify_receipt(receipt, "task_receipt_01", "req_12345678"))

        # Mismatch task_id fails verification
        with self.assertRaises(ValueError):
            self.adapter.verify_receipt(receipt, "task_other_99", "req_12345678")

        # Mismatch request_id fails verification
        with self.assertRaises(ValueError):
            self.adapter.verify_receipt(receipt, "task_receipt_01", "req_wrong_id")


if __name__ == "__main__":
    unittest.main()
