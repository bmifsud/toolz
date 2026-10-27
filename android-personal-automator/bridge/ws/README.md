# Termux command bridge — deployment and verification

> **Status (2026-10-27):** Experimental. GitHub issue polling has executed `git-branch` on the tablet successfully. WebSocket transport is committed but **not yet connected to the tablet**. A separate Render service exists, but its first deployment **failed** because `BRIDGE_DEVICE_TOKEN` was absent. No production-ready remote shell exists.

## Components and boundaries

| Component | Path / location | Role |
| --- | --- | --- |
| Read-only command runner | `../readonly_runner.py` | Fixed subprocess arguments; 10-second timeout |
| GitHub issue worker | `../github_issue_worker.py` | Existing pull-based transport; queue issue #24 |
| WebSocket relay | `relay.py` | Routes authenticated request/result JSON; never executes shell |
| Termux device listener | `device.py` | Outbound WSS, visible stdout, reconnect, STOP file |
| Existing Render bridge | `android-personal-automator-bridge` | Separate legacy service; **do not modify** |
| New Render service | `toolz-termux-ws-relay` | Isolated experimental relay |

The relay is hosted at https://toolz-termux-ws-relay.onrender.com, dashboard https://dashboard.render.com/web/srv-dbgbgvo473hc73b11nug. It uses Frankfurt, free plan, feature branch `feat/termux-readonly-bridge-20261027`, with auto-deploy disabled. This endpoint is **not healthy until credentials are installed and deployment succeeds**.

## Security model

- Only `git-branch` is allowed through the WebSocket transport, even though the local runner supports other diagnostics.
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
5. Redeploy (auto-deploy is off), then inspect deploy status and application logs. Expect `Relay listening on 0.0.0.0:<PORT>`. If the process exits with `KeyError: 'BRIDGE_DEVICE_TOKEN'`, the device token is not configured. Confirm TLS/WSS endpoint before tablet testing.
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

## Verification checklist

| Check | Evidence / state |
| --- | --- |
| GitHub issue worker executes `git-branch` | **PASS**, issue #24 result `live-display-20261027-1432`, exit 0 |
| Previous bridge CI | **PASS** on earlier commits; latest commit must be rechecked |
| Render service creation | **PASS**, separate service ID `srv-dbgbgvo473hc73b11nug` |
| Render dependency build | **PASS**, `websockets-16.1.1` installed in build logs |
| First Render deployment | **FAIL**, missing `BRIDGE_DEVICE_TOKEN` |
| Render credentials / healthy deployment | **PENDING** |
| WebSocket auth rejection / routing integration tests | **PENDING** |
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
