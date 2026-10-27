# ChatGPT-to-Termux bridge: security and integration contract

## Verified today
- Authenticated controller-to-Render-to-Termux `git-branch` completed with exit code 0.
- The ASGI Render relay passed HTTP GET health checks.
- **This ChatGPT session does not have a callable, authenticated controller action.** GitHub and Render connectors cannot substitute for device execution.

## Integration contract for a future ChatGPT-facing connector
1. Expose one narrowly scoped action: `run_diagnostic(diagnostic: "git-branch" | "tier1-tests")`.
2. Store the controller credential only in the connector's secret store. Never place it in a repository, model prompt, URL query, log, or user-visible response.
3. Require explicit user opt-in to enable device diagnostics. Only connect over `wss://`; validate TLS.
4. Generate a unique unpredictable request ID and enforce a 30-second end-to-end timeout, 8192-byte message cap, and bounded outstanding requests.
5. Check the relay's authenticated response ID, type, diagnostic, exit code, and size; reject mismatches. A JSON receipt is **not** cryptographic evidence of device origin.
6. Return a redacted receipt with request ID, diagnostic, exit code, elapsed time, bounded stdout/stderr, and errors; never include secrets.
7. Keep mutations, arbitrary shell commands, and Tier-2 snapshot execution out of scope. Future writes need a separate user-approval and authorization design.
8. Device must be online and explicitly running the listener. Provide a clear offline/timeout error, not a fabricated result.
9. Add integration tests for unauthorized access, query-token rejection, replay IDs, disconnected device, malformed payloads, oversized responses, timeout, and concurrent requests.
10. Do not claim ChatGPT can execute Termux diagnostics until the connector action is actually registered and a live request succeeds from ChatGPT.

## Manual verification until connector is available

In one Termux session, export `BRIDGE_DEVICE_TOKEN` privately and start `device.py`. In another, export `BRIDGE_CONTROLLER_TOKEN` privately and run `controller.py git-branch` or `controller.py tier1-tests`. Never paste tokens into chat.
