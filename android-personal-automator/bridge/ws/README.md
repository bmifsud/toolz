# Termux command bridge — deployment and verification

> **Status (2026-10-27):** Experimental. Render WebSocket relay deployment `6e5b712` is Live (15:52:56 UTC). A user-run controller previously received a `git-branch` result from the tablet. This does not establish a current connection or ChatGPT-to-device execution. The `/healthz` endpoint has not been independently verified over the public URL. No production-ready remote shell exists.

## Components and boundaries

| Component | Path / location | Role |
| --- | --- | --- |
| Read-only command runner | `../readonly_runner.py` | Fixed subprocess arguments; 10-second timeout |
| GitHub issue worker | `../github_issue_worker.py` | Existing pull-based transport; queue issue #24 |
| WebSocket relay | `relay.py` | Routes authenticated request/result JSON; never executes shell |
| Termux device listener | `device.py` | Outbound WSS, visible stdout, reconnect, STOP file |
| Explicit controller | `controller.py` | Authenticated one-shot read-only `git-branch` request; not connected to ChatGPT |
| Existing Render bridge | `android-personal-automator-bridge` | Separate legacy service; **do not modify** |
| New Render service | `toolz-termux-ws-relay` | Isolated experimental relay |

The relay is hosted at https://toolz-termux-ws-relay.onrender.com, dashboard https://dashboard.render.com/web/srv-dbgbgvo473hc73b11nug. It uses Frankfurt, free plan, feature branch `feat/termux-readonly-bridge-20261027`, with auto-deploy disabled. The latest checked Render deployment is **Live**; actual authenticated connectivity still needs device verification.

## Security model

- Only `git-branch` and `tier1-tests` are allowed through the WebSocket transport; the device must have the updated client and runner for `tier1-tests`.
- No arbitrary shell, writes, APK installs, screenshots, backup operations or privileged Android commands.
- Device connects outward over `wss://`; controller must be separately authenticated.
- Distinct random secrets (minimum 32 characters): `BRIDGE_DEVICE_TOKEN` and `BRIDGE_CONTROLLER_TOKEN`. Set in Render environment, **never** commit, paste into issues, or expose in logs. Headers use `Authorization: Bearer ...`.
- Existing implementation has **no durable queue, rate limits, persistent replay ledger, token rotation, per-request user approval, or multiple-device isolation**. It is not production ready.
- Never enable the live-update supervisor on unreviewed commits: it executes fetched code.
- Termux STOP file: `~/.local/state/toolz-termux-bridge/STOP`. `Ctrl+C` also terminates the foreground listener.
- ChatGPT's current GitHub connector **cannot open a WebSocket**. A separately authenticated controller interface or integration is still needed.

## Render provisioning

1. Create a separate Python web service from `https://github.com/bmifsud/toolz` on branch `feat/termux-readonly-bridge-20261027`; the separate service above has already been created.
2. Build: `pip install -r android-personal-automator/bridge/ws/requirements.txt`.
3. Start: `python android-personal-automator/bridge/ws/relay.py`.
4. Set **both** private environment variables in Render:
   - `BRIDGE_DEVICE_TOKEN` — independently generated random secret, 32+ characters.
   - `BRIDGE_CONTROLLER_TOKEN` — different independently generated random secret, 32+ characters.
5. Configure Render's **Health Check Path** as `/healthz` in the service settings. This is a configuration change, not a WebSocket command; verify GET returns HTTP 200. The current service configuration was inspected and the health-check path is empty. Requests using HEAD against the WebSocket endpoint may still produce handshake tracebacks; do not mistake those for proof of a failed device connection. Redeploy (auto-deploy is off), then inspect deploy status and application logs. Expect `Relay listening on 0.0.0.0:<PORT>`. If the process exits with `KeyError: 'BRIDGE_DEVICE_TOKEN'`, the device token is not configured. Confirm TLS/WSS endpoint before tablet testing.
6. Render free services can sleep or restart; do not assume uninterrupted connectivity.

## Tablet installation (manual consent required)

Keep the existing backup checkout and branch unchanged. In Termux, explicitly fetch the reviewed feature branch files into a separate directory; do **not** merge or reset the backup branch.

```bash
cd ~/toolz-tier1-test
git fetch origin feat/termux-readonly-bridge-20261027
mkdir -p "$HOME/toolz-ws-bridge"
for name in device.py requirements.txt; do
  git show "FETCH_HEAD:android-personal-automator/bridge/ws/$name" > "$HOME/toolz-ws-bridge/$name"
done
git show "FETCH_HEAD:android-personal-automator/bridge/readonly_runner.py" > "$HOME/readonly_runner.py"
python -m pip install -r "$HOME/toolz-ws-bridge/requirements.txt"
python -m py_compile "$HOME/toolz-ws-bridge/device.py" "$HOME/readonly_runner.py"
```

**Important:** `device.py` imports `readonly_runner` from its parent directory. With the above layout it finds `$HOME/readonly_runner.py`. Review the downloaded scripts before running them. To connect:

```bash
export BRIDGE_WS_URL="wss://toolz-termux-ws-relay.onrender.com"
# Obtain BRIDGE_DEVICE_TOKEN securely from the same private secret configured in Render.
# Do not echo it or save it in shell history.
read -r -s -p 'Device token: ' BRIDGE_DEVICE_TOKEN; echo
export BRIDGE_DEVICE_TOKEN
rm -f "$HOME/.local/state/toolz-termux-bridge/STOP"
cd ~/toolz-tier1-test
python -u "$HOME/toolz-ws-bridge/device.py"
```

The `read` prompt requires interactive Bash; `Ctrl+C` stops the client. Never post tokens to GitHub. Use an approved authenticated controller to submit `{"id":"unique-id-123","diagnostic":"git-branch"}` to `/controller`. Expected response type is `result`, with the same ID and runner result.

## One-shot controller test (separate authorized terminal)

Install the same `requirements.txt` and copy `controller.py` to a trusted host or a separate Termux session. Use the distinct private **controller** token (not the device token):

```bash
export BRIDGE_WS_URL='wss://toolz-termux-ws-relay.onrender.com'
read -r -s -p 'Controller token: ' BRIDGE_CONTROLLER_TOKEN; echo
export BRIDGE_CONTROLLER_TOKEN
python -u controller.py
unset BRIDGE_CONTROLLER_TOKEN
```

Only run this after the device listener reports `Connected; waiting for authorized requests`. The controller prints the submitted diagnostic and the response; the device listener prints the actual command and output. The controller is an explicit CLI, **not** a ChatGPT connector. Never paste tokens into chat, logs, or issues.

## Verification checklist

| Check | Evidence / state |
| --- | --- |
| GitHub issue worker executes `git-branch` | **PASS**, issue #24 result `live-display-20261027-1432`, exit 0 |
| Previous bridge CI | **PASS** on earlier commits; latest commit must be rechecked |
| Render service creation | **PASS**, separate service ID `srv-dbgbgvo473hc73b11nug` |
| Render dependency build | **PASS**, `websockets-16.1.1` installed in build logs |
| First Render deployment | **FAIL**, missing `BRIDGE_DEVICE_TOKEN` |
| Render credentials / deployment | **PASS** deployment `dep-dbgbprh42hec73e5vlrg` Live; endpoint check pending |
| WebSocket health and authentication unit tests | **PASS** GitHub Actions on commit `9ba544e`; end-to-end routing pending |
| Device connected over WSS | **PENDING** |
| Controller-to-device-to-controller live roundtrip | **PENDING** |
| STOP, reconnect, replay, offline behavior | **PENDING** |

## Troubleshooting and rollback

- If startup reports a missing environment variable, configure it privately in Render and redeploy.
- If `ModuleNotFoundError: websockets`, install requirements in the Termux Python environment.
- If `ModuleNotFoundError: readonly_runner`, verify the parent-directory file arrangement above.
- If the listener prints disconnected/retrying, inspect TLS, service health, token matching, and Render logs.
- To stop locally, press `Ctrl+C` or create `~/.local/state/toolz-termux-bridge/STOP`; to stop the public relay, suspend the separate Render service. Do not suspend the existing `android-personal-automator-bridge`.
- The GitHub issue transport remains available independently; it polls issue #24. Its duplicate result observed for an earlier request motivated request-ID deduplication.

## Links

- [Bridge PR #23](https://github.com/bmifsud/toolz/pull/23)
- [GitHub queue issue #24](https://github.com/bmifsud/toolz/issues/24)
- [Verified tablet result](https://github.com/bmifsud/toolz/issues/24#issuecomment-6444748104)
- [Render service dashboard](https://dashboard.render.com/web/srv-dbgbgvo473hc73b11nug)
