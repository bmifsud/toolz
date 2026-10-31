# Toolz host readiness CLI (preview)

This dependency-free Python package inventories local executable availability. It does not invoke Cline, OmniRoute, SSH, PRoot, an emulator, or a device. It does not inspect credential values or configuration files. Found executable paths are omitted from output.

Install from a reviewed checkout using Python 3.10 or newer:

```sh
python -m pip install ./cli
toolz-readiness
toolz-readiness --json
```

The command exits successfully when the inventory is produced, even if tools are missing. It always reports integration verification as pending and device execution readiness as false. Executable presence does not establish version compatibility, service health, authorization, or an authenticated channel. The JSON schema begins at version 1.

To upgrade, install the reviewed new package revision with `python -m pip install --upgrade ./cli`. To uninstall, use `python -m pip uninstall toolz-cli`. Use a virtual environment where supported; no system installation is required.

## Integration order

1. Verify the existing Termux service through the reviewed WebSocket controller using a securely configured distinct controller credential. Require a matching bounded request/receipt, not relay health alone.
2. Start Debian only through a supported, explicitly authorized device lifecycle operation. Establish an authenticated Debian-side channel and verify its scope separately.
3. Verify the installed Cline version and actual interactive and noninteractive interfaces. Interactive use needs a console-carrying session; do not assume one-shot command support from executable presence.
4. Route scoped requests to Cline only after those checks. Verify OmniRoute configuration and service readiness without exposing tokens.

This package adds none of these remote operations. Existing diagnostic allowlists are unchanged. No arbitrary shell fallback or production backup changes are permitted by this inventory.

## Portability and limits

| Environment | Current support |
| --- | --- |
| Linux, macOS, Windows | Pure Python local inventory; workflow defines installation and command checks; remote results pending |
| Android Termux | Intended Python-compatible inventory; physical-device validation pending |
| Debian/Andronix | Run inside the selected environment to inventory that host; cloud Debian does not establish tablet Debian readiness |
| iOS | Only within a supported SSH/app environment providing Python; no unrestricted iOS shell access is claimed |

The `omniroute` executable may not be installed under that name when deployed as a service. Missing entries require investigation, not automatic installation. A service may be running without appearing on this host's PATH.

Run fixture tests after installation:

```sh
python -m unittest discover -s cli/tests -v
```

The package is an initial packaging step for the CLI workstream, not a released or connected gateway. Authenticated execution, signed release artifacts, OS-specific credential storage and lifecycle adapters remain pending.
