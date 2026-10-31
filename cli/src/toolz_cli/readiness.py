"""Inventory executable availability without invoking tools or inspecting secrets."""
import argparse
import json
import platform
import shutil
from typing import Callable

TOOLS = ("git", "ssh", "cline", "omniroute", "proot", "adb", "emulator")


def inventory(find: Callable[[str], str | None] = shutil.which,
              system: str | None = None) -> dict:
    """Return presence only: paths, versions, tokens and configuration are excluded."""
    return {
        "schema_version": 1,
        "host_system": system if system is not None else platform.system(),
        "tools": {name: {"available": find(name) is not None} for name in TOOLS},
        "verification": {
            "termux_authenticated_roundtrip": "pending",
            "debian_authenticated_channel": "pending",
            "cline_interactive_interface": "pending",
            "cline_noninteractive_interface": "pending",
        },
        "ready_for_device_execution": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the versioned JSON inventory")
    args = parser.parse_args(argv)
    result = inventory()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("Toolz local capability inventory")
        print("Host: " + result["host_system"])
        for name, tool in result["tools"].items():
            print(name + ": " + ("available" if tool["available"] else "missing"))
        print("Termux, Debian and Cline integration verification: pending")
        print("Executable availability does not establish a connection or CLI compatibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
