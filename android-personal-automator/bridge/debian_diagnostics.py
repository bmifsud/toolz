"""Safe Debian launcher discovery and fixed diagnostic specifications.

No subprocess execution here. A future device-local executor must authenticate
requests, validate the launcher and implement timeout/output bounds.
"""
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class DiagnosticSpec:
    identifier: str
    argv: tuple[str, ...]
    timeout_seconds: int = 15

DIAGNOSTICS = {
    "debian-identity": DiagnosticSpec("debian-identity", ("cat", "/etc/os-release")),
    "debian-disk": DiagnosticSpec("debian-disk", ("df", "-h", "/")),
}

def discover_launcher(home: Path) -> tuple[Path, ...]:
    """Return existing candidate launchers; never execute or trust them automatically."""
    home = Path(home)
    candidates = (home / "start-debian.sh", home / "debian.sh", home / "start-andronix.sh")
    return tuple(p for p in candidates if p.is_file() and not p.is_symlink())

def diagnostic_spec(identifier: str) -> DiagnosticSpec:
    if identifier not in DIAGNOSTICS:
        raise ValueError("unsupported Debian diagnostic")
    return DIAGNOSTICS[identifier]
