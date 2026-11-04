"""Unit and integration tests for secure OpenSSH alternative."""

import os
from pathlib import Path
import pytest
import subprocess

from ssh_remote.security import (
    SecurityError,
    is_allowed_network_target,
    validate_key_permissions,
    validate_known_hosts_permissions,
    validate_port,
)
from ssh_remote.config_generator import (
    TargetEnvironment,
    generate_sshd_config,
)
from ssh_remote.client import (
    SSHClientConfig,
    SecureSSHClient,
)


def test_allowed_network_targets():
    # Allowed
    assert is_allowed_network_target("localhost") is True
    assert is_allowed_network_target("127.0.0.1") is True
    assert is_allowed_network_target("::1") is True
    assert is_allowed_network_target("10.0.0.1") is True
    assert is_allowed_network_target("172.16.5.10") is True
    assert is_allowed_network_target("192.168.1.100") is True

    # Denied
    assert is_allowed_network_target("8.8.8.8") is False
    assert is_allowed_network_target("1.1.1.1") is False
    assert is_allowed_network_target("example.com") is False
    assert is_allowed_network_target("") is False
    assert is_allowed_network_target("   ") is False
    assert is_allowed_network_target("google.com") is False


def test_key_permissions(tmp_path):
    key_file = tmp_path / "id_ed25519"
    key_file.write_text("fake-private-key\\n")

    # Mode 0600 is valid
    os.chmod(key_file, 0o600)
    validate_key_permissions(key_file)

    # Mode 0400 is valid
    os.chmod(key_file, 0o400)
    validate_key_permissions(key_file)

    # Mode 0644 is insecure for private keys
    os.chmod(key_file, 0o644)
    with pytest.raises(SecurityError, match="Insecure private key file permissions"):
        validate_key_permissions(key_file)

    # Nonexistent file
    missing = tmp_path / "missing_key"
    with pytest.raises(SecurityError, match="does not exist"):
        validate_key_permissions(missing)


def test_known_hosts_permissions(tmp_path):
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("localhost ssh-ed25519 AAAA...\\n")

    # Safe modes
    os.chmod(known_hosts, 0o644)
    validate_known_hosts_permissions(known_hosts)

    os.chmod(known_hosts, 0o600)
    validate_known_hosts_permissions(known_hosts)

    # Insecure: group or world writable
    os.chmod(known_hosts, 0o666)
    with pytest.raises(SecurityError, match="Must not be group/other writable"):
        validate_known_hosts_permissions(known_hosts)


def test_port_validation():
    validate_port(22)
    validate_port(8022)
    validate_port(2222)
    validate_port(65535)

    with pytest.raises(SecurityError):
        validate_port(0)
    with pytest.raises(SecurityError):
        validate_port(-1)
    with pytest.raises(SecurityError):
        validate_port(65536)


def test_generate_sshd_config(tmp_path):
    host_key = tmp_path / "ssh_host_ed25519_key"
    auth_keys = tmp_path / "authorized_keys"

    # Termux config
    termux_cfg = generate_sshd_config(TargetEnvironment.TERMUX, host_key, auth_keys)
    assert "Port 8022" in termux_cfg
    assert "ListenAddress 127.0.0.1" in termux_cfg
    assert "PasswordAuthentication no" in termux_cfg
    assert "PubkeyAuthentication yes" in termux_cfg
    assert "StrictModes yes" in termux_cfg
    assert f"HostKey {host_key.resolve()}" in termux_cfg

    # Termux privileged port rejection
    with pytest.raises(SecurityError, match="Termux non-root sshd cannot bind privileged port"):
        generate_sshd_config(TargetEnvironment.TERMUX, host_key, auth_keys, port=22)

    # Debian config
    deb_cfg = generate_sshd_config(TargetEnvironment.DEBIAN, host_key, auth_keys, port=2222)
    assert "Port 2222" in deb_cfg

    # Public listen address rejection
    with pytest.raises(SecurityError, match="listen_address must be localhost or private network"):
        generate_sshd_config(TargetEnvironment.DEBIAN, host_key, auth_keys, listen_address="8.8.8.8")


def test_client_config_and_command_construction(tmp_path):
    key_file = tmp_path / "id_ed25519"
    key_file.write_text("key")
    os.chmod(key_file, 0o600)

    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("known")
    os.chmod(known_hosts, 0o600)

    # Denied public host
    with pytest.raises(SecurityError, match="not localhost or private RFC1918 network"):
        SSHClientConfig(
            host="example.com",
            port=22,
            user="b",
            identity_file=key_file,
            known_hosts_file=known_hosts,
        )

    # Valid config
    cfg = SSHClientConfig(
        host="127.0.0.1",
        port=8022,
        user="b",
        identity_file=key_file,
        known_hosts_file=known_hosts,
    )
    client = SecureSSHClient(cfg)
    cmd = client.build_command(["echo", "hello"])

    assert "StrictHostKeyChecking=yes" in cmd
    assert "PasswordAuthentication=no" in cmd
    assert "PubkeyAuthentication=yes" in cmd
    assert "-p" in cmd and "8022" in cmd
    assert f"UserKnownHostsFile={known_hosts.resolve()}" in cmd
    assert f"-i" in cmd and str(key_file.resolve()) in cmd
    assert "b@127.0.0.1" in cmd
    assert cmd[-2:] == ["echo", "hello"]
