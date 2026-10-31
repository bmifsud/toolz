# Debian/Andronix integration staging

The hybrid router supports explicit `@Debian` and conservative Debian auto-detection.
The execution adapter recognizes only `debian-identity` and `debian-disk`.
Neither diagnostic is remotely executable yet.

## Device onboarding

1. Inspect actual launcher location and behavior on the tablet without executing unknown scripts.
2. Confirm Andronix Debian 13 starts safely via the existing Termux/PRoot installation.
3. Establish authenticated Termux bridge and per-request authorization, with request correlation.
4. Implement a device-local adapter that invokes a reviewed launcher with fixed diagnostic arguments, timeout and bounded output.
5. Return authenticated receipts; validate request ID, target, diagnostic, exit status and output size.
6. Verify denial, timeout, disconnection, launcher absence, and no public Debian listener.
7. Enable Tier-2 *read-only* verification only after the above checks.

The discovery helper lists candidate launcher files but deliberately does not execute them.
Never send Debian credentials, GPG passphrases, or rootfs archives through the relay.
