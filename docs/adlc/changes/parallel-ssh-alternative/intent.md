# Change intent: parallel-ssh-alternative

- Change ID / issue: parallel-ssh-alternative
- Owner: Cline
- Baseline revision: 356d3c12750882c5520d909c912f9efba86cfaa0
- Problem and expected behavior:
  - Problem: Relying exclusively on Remote Desktop Commander (RDC) or ad-hoc transports lacks an isolated, fail-closed command transport for Android Termux and Debian environments.
  - Expected behavior: Provide a secure OpenSSH alternative client and server configuration generator for Android Termux and Debian that operates parallel to RDC. Enforces key-only auth, strict host key checking, and localhost / private network RFC1918 boundaries fail-closed.
- Scope / exclusions:
  - In scope: Hardened client configuration and command builder (`ssh_remote/client.py`), fail-closed security validators (`ssh_remote/security.py`), sshd config generator for Termux & Debian (`ssh_remote/config_generator.py`), test suite, and ADLC tracking.
  - Out of scope: Live external network bridging, modifying existing RDC daemon/tokens, public listening sockets, or modifying production backup schedules.
- Acceptance criteria (observable, independent of implementation):
  - Strict rejection of public IP addresses and non-local domains.
  - Strict enforcement of private key permissions (`0600`/`0400`) and known_hosts permissions.
  - Server config enforces `PasswordAuthentication no`, `PubkeyAuthentication yes`, `StrictModes yes`, and rejects Termux privileged port bindings (< 1024).
  - All unit/integration tests pass cleanly offline.
- Risk: low; additive module with fail-closed security checks and no destructive side effects.
- Data, secrets, device, backup and permission implications:
  - No secrets or credentials are hardcoded or tracked in git.
  - RDC daemon and configuration remain untouched.
- Affected source paths and dependencies:
  - `ssh_remote/`
  - `docs/adlc/changes/parallel-ssh-alternative/`
  - `docs/architecture.md`
  - `docs/adlc/status.md`
  - `tests/run-all-tests.sh`
- Assumptions / unresolved decisions:
  - OpenSSH client binary `ssh` is available in runtime environment.
- Implementation steps:
  1. Create `ssh_remote` package with security validations, config generation, and client wrapper.
  2. Implement unit tests in `ssh_remote/tests/`.
  3. Wire test execution into repository test runner.
  4. Complete ADLC intent and evidence documentation.
- Validation commands and environments:
  - `PYTHONPATH=. pytest ssh_remote/tests/`
  - `python3 scripts/check_adlc.py`
  - `bash tests/run-all-tests.sh`
- Failure and denied-action cases:
  - Public IPs fail with `SecurityError`.
  - Insecure file permissions fail with `SecurityError`.
  - Malformed ports fail with `SecurityError`.
- Rollback / recovery:
  - Remove `ssh_remote/` directory and documentation changes.
- Required reviewer / approvals:
  - Independent maintainer review prior to merge.
- Evidence record:
  - `docs/adlc/changes/parallel-ssh-alternative/evidence.md`
