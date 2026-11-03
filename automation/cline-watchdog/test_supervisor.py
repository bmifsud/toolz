import fcntl
import hashlib
import json
import subprocess
import sys
from unittest.mock import patch

import pytest
from supervisor import tick


@pytest.fixture
def config(tmp_path):
    return {"state_dir": str(tmp_path / "state"), "tasks": [
        {"id": "existing-session", "cwd": str(tmp_path),
         "adapter": [sys.executable, "-c", "import sys; sys.exit(10)"]}]}


def state_path(config):
    from pathlib import Path
    key = hashlib.sha256(config["tasks"][0]["id"].encode()).hexdigest()
    return Path(config["state_dir"]) / (key + ".json")


def test_persistent_backoff_and_cap(config):
    now = 100
    for attempt in range(1, 10):
        result = tick(config, True, clock=lambda: now)["existing-session"]
        assert result["attempts"] == attempt
        assert result["next_at"] == now + min(3600, 60 * 2 ** min(attempt - 1, 6))
        assert tick(config, True, clock=lambda: now)["existing-session"] == "cooldown"
        now = result["next_at"]


@pytest.mark.parametrize("code,status,reason", [
    (0, "complete", "verified_completion"),
    (11, "retry", "incomplete_checkpoint"),
    (20, "blocked", "approval_required"),
    (21, "blocked", "authentication_or_configuration_required"),
    (22, "blocked", "runtime_repair_required"),
    (1, "blocked", "unknown_adapter_failure_inspect_locally")])
def test_outcomes(config, code, status, reason):
    config["tasks"][0]["adapter"][-1] = f"import sys; sys.exit({code})"
    result = tick(config, True)["existing-session"]
    assert (result["status"], result["reason"]) == (status, reason)
    if status != "retry":
        with patch("supervisor.subprocess.run") as run:
            tick(config, True, clock=lambda: 1e12)
            run.assert_not_called()


def test_dry_run(config):
    with patch("supervisor.subprocess.run") as run:
        assert tick(config)["existing-session"] == "observe_only"
        run.assert_not_called()
    assert not state_path(config).parent.exists()


def test_interrupted_attempt_never_replayed(config):
    with patch("supervisor.subprocess.run", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            tick(config, True)
    with patch("supervisor.subprocess.run") as run:
        result = tick(config, True)["existing-session"]
        assert result["reason"] == "interrupted_attempt_reconcile_ownership"
        run.assert_not_called()


def test_concurrency(config):
    def adapter(*args, **kwargs):
        assert tick(config, True)["existing-session"] == "already_running"
        return subprocess.CompletedProcess(args, 10)
    with patch("supervisor.subprocess.run", side_effect=adapter) as run:
        tick(config, True)
        assert run.call_count == 1


def test_independent_tasks(config):
    config["tasks"].append(dict(config["tasks"][0], id="second"))
    result = tick(config, True)
    assert set(result) == {"existing-session", "second"}
    assert all(value["attempts"] == 1 for value in result.values())


@pytest.mark.parametrize("failure,reason", [
    (OSError(), "adapter_launch_failed_repair_runtime"),
    (subprocess.TimeoutExpired("adapter", 1), "timeout_reconcile_child_ownership")])
def test_launch_failures(config, failure, reason):
    with patch("supervisor.subprocess.run", side_effect=failure):
        assert tick(config, True)["existing-session"]["reason"] == reason


def test_corruption_and_config_change(config):
    tick(config, True)
    config["tasks"][0]["adapter"].append("changed")
    assert "configuration_changed" in tick(config, True)["existing-session"]
    state_path(config).write_text("not json")
    assert "corrupt_state" in tick(config, True)["existing-session"]


def test_duplicates_rejected(config):
    config["tasks"] *= 2
    with pytest.raises(ValueError):
        tick(config, True)
