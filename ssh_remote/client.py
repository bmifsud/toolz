"""Hardened OpenSSH client execution wrapper."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Optional

try:
    from .security import (
        SecurityError,
        is_allowed_network_target,
        validate_key_permissions,
        validate_known_hosts_permissions,
        validate_port,
    )
except ImportError:
    from security import (
        SecurityError,
        is_allowed_network_target,
        validate_key_permissions,
        validate_known_hosts_permissions,
        validate_port,
    )


@dataclass(frozen=True)
class SSHClientConfig:
    host: str
    port: int
    user: str
    identity_file: Path
    known_hosts_file: Path
    connect_timeout: int = 10

    def __post_init__(self):
        if not is_allowed_network_target(self.host):
            raise SecurityError(
                f"Target host '{self.host}' is not localhost or private RFC1918 network. Operation denied."
            )
        validate_port(self.port)
        if not self.user or not self.user.isalnum():
            raise SecurityError(f"Invalid user name: '{self.user}'")
        validate_key_permissions(self.identity_file)
        validate_known_hosts_permissions(self.known_hosts_file)


class SecureSSHClient:
    """Client wrapper that strictly enforces secure OpenSSH parameters."""

    def __init__(self, config: SSHClientConfig):
        self.config = config

    def build_command(self, remote_command: Optional[List[str]] = None) -> List[str]:
        """Construct strictly hardened OpenSSH command list."""
        cmd = [
            "ssh",
            "-p", str(self.config.port),
            "-i", str(self.config.identity_file.resolve()),
            "-o", f"UserKnownHostsFile={self.config.known_hosts_file.resolve()}",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "PasswordAuthentication=no",
            "-o", "KbdInteractiveAuthentication=no",
            "-o", "ChallengeResponseAuthentication=no",
            "-o", "PubkeyAuthentication=yes",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={self.config.connect_timeout}",
            "-o", "IdentitiesOnly=yes",
            "-o", "ForwardAgent=no",
            "-o", "ForwardX11=no",
            f"{self.config.user}@{self.config.host}",
        ]
        if remote_command:
            cmd.extend(remote_command)
        return cmd

    def run_command(self, remote_command: List[str], timeout: Optional[int] = 30) -> subprocess.CompletedProcess:
        """Run a remote command fail-closed and return CompletedProcess."""
        if not remote_command:
            raise ValueError("remote_command must not be empty")
        cmd = self.build_command(remote_command)
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
