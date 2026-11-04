"""Security validators and policy definitions for secure OpenSSH alternative."""

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
import re
from typing import Optional, Set


class SecurityError(Exception):
    """Raised when an SSH operation violates security policies."""
    pass


ALLOWED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})


def is_allowed_network_target(host: str) -> bool:
    """Validate that the target host is strictly localhost or private network (RFC 1918)."""
    if not isinstance(host, str) or not host.strip():
        return False
    host = host.strip().lower()

    if host in ALLOWED_HOSTNAMES:
        return True

    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        # Hostnames that are not IP addresses must match local-only patterns or be rejected
        # To fail closed and prevent DNS rebinding / public egress, only explicitly approved local names are permitted.
        return False


def validate_key_permissions(key_path: Path) -> None:
    """Validate that the SSH private key file exists and has strict permissions (0600 or 0400)."""
    if not key_path.is_file():
        raise SecurityError(f"Private key file does not exist or is not a regular file: {key_path}")

    mode = stat_mode = os.stat(key_path).st_mode & 0o777
    if stat_mode not in (0o600, 0o400):
        raise SecurityError(
            f"Insecure private key file permissions on {key_path}: {oct(stat_mode)}. Must be 0600 or 0400."
        )


def validate_known_hosts_permissions(known_hosts_path: Path) -> None:
    """Validate that the known_hosts file exists and has safe permissions (not group/world writable)."""
    if not known_hosts_path.is_file():
        raise SecurityError(f"known_hosts file does not exist or is not a regular file: {known_hosts_path}")

    stat_mode = os.stat(known_hosts_path).st_mode & 0o777
    if stat_mode & 0o022:  # group-writable or other-writable
        raise SecurityError(
            f"Insecure known_hosts file permissions on {known_hosts_path}: {oct(stat_mode)}. Must not be group/other writable."
        )


def validate_port(port: int) -> None:
    """Validate that port is within valid range (1 - 65535)."""
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise SecurityError(f"Invalid port number: {port}. Must be an integer between 1 and 65535.")
