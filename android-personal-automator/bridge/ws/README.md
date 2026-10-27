# Experimental push transport for Termux

This is a **prototype**, not a deployed service. It avoids GitHub comment polling by keeping an outbound WSS connection from Termux to a relay. Only the `git-branch` diagnostic is supported. Do not use this for arbitrary shell execution.

## Security constraints
- TLS (`wss://`) is mandatory on the device. Host relay behind a TLS-terminating service.
- Distinct, randomly generated 32+ character device and controller tokens are required. Do not commit them.
- Never put tokens in GitHub issues, command output, logs, or screenshots. Tokens are sent as Authorization bearer headers; configure proxy logging to redact Authorization headers.
- The relay is in-memory and single-device, without durable queue, token rotation, rate limiting, or per-request approval. It is not production ready.
- STOP file: `~/.local/state/toolz-termux-bridge/STOP`. Start the listener explicitly; Ctrl+C stops it.
- Do not run the earlier live-update supervisor against an unreviewed branch: it executes downloaded code.
- A ChatGPT GitHub connector cannot directly submit WebSocket messages. A separately authorized controller/connector is necessary.

## Local verification
`python -m pip install -r requirements.txt`
`python -m py_compile relay.py device.py`

## Termux
After provisioning a trusted TLS relay and environment variables `BRIDGE_WS_URL` and `BRIDGE_DEVICE_TOKEN`, run `python -u device.py`. Keep this foreground process visible to watch command execution.
