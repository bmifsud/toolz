# Secure OpenSSH Alternative (Termux & Debian)

This module provides a secure, fail-closed OpenSSH client transport and server configuration generator for Android Termux and Debian environments, running parallel to Remote Desktop Commander (RDC).

## Security Principles & Constraints

1. **Localhost & Private Network Only:**
   - Client and server configurations strictly refuse public internet addresses.
   - Allowed destinations: `127.0.0.1`, `::1`, `localhost`, and RFC1918 private IPv4 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
   - Any attempt to target public or unresolvable IP addresses is rejected fail-closed.

2. **Key-Based Authentication Only:**
   - Password authentication, challenge-response, keyboard-interactive, and PAM are explicitly disabled (`PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes`).
   - Client connections require a valid private key path with strict filesystem permissions (`0600` or `0400`).

3. **Strict Host Key Verification:**
   - Host key verification is strictly enforced (`StrictHostKeyChecking yes`).
   - Insecure flags (`StrictHostKeyChecking=no`, `UserKnownHostsFile=/dev/null`) are explicitly forbidden and rejected.
   - Known hosts file must exist and have secure file permissions (`0600` or `0644`).

4. **Environment Isolation (Android Termux vs Debian):**
   - **Termux:** Default sshd port `8022` (unprivileged non-root), runtime paths under `$PREFIX` (`/data/data/com.termux/files/usr`).
   - **Debian:** Default sshd port `2222` or `22`, paths under standard `/etc/ssh` or isolated user directory.
   - Config generators validate ownership and refuse execution if directory or key permissions are loose.

5. **Parallel to RDC (Non-Interference):**
   - Operates independently without altering Remote Desktop Commander daemon, ports, or credentials.
   - Preserves all existing configurations, environment variables, and active sessions.
