# Single-user AI proposal bridge

Python 3.10+, standard library only. Returns proposals; cannot call the tablet,
tap, read screens, execute arbitrary URLs, or write to GitHub. The Android app
connects only on Send and requires a separate local approval.

## Run on a server/workstation

Configure environment variables using your host's secret manager or private shell
session. Never commit their values:

- `OPENAI_API_KEY`: your provider API key, kept only on this server.
- `OPENAI_MODEL`: a Responses API text model available to your account.
- `BRIDGE_TOKEN`: independent random token. Generate one with
  `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
- `PORT`: optional, defaults to `8080`.
- `BRIDGE_HOST`: defaults to `127.0.0.1`. Only change for private ingress or a
  TLS-terminating platform proxy. Never expose the plain HTTP port directly.

From this directory:

```sh
python3 -m unittest -v
python3 server.py
```

Put a reverse proxy with a valid HTTPS certificate in front of the loopback server.
Example Caddy configuration on the same host, with DNS pointing at the host:

```caddyfile
bridge.your-domain.example {
    request_body {
        max_size 8KB
    }
    reverse_proxy 127.0.0.1:8080
}
```

Replace the domain with your actual domain. Configure proxy connection/rate limits
and provider spending limits. This is a single-user prototype. It admits one provider
call at a time and one call per five seconds per process; use one process if relying
on that limit. Do not enable proxy logging of headers, request bodies or tokens.
Rotate the bridge token if exposed.

In the app enter `https://YOUR_ACTUAL_DOMAIN/proposal`, the **bridge token**, and a task.
The app does not save the token. Local approval applies only to the fixed PR URL.

## Protocol

Authenticated `POST /proposal`, `Authorization: Bearer <BRIDGE_TOKEN>`, JSON:

```json
{"version":1,"task":"Open the demo PR"}
```

Only a bounded JSON object with exactly these fields is accepted:

```json
{"action":"OPEN_DEMO","explanation":"Open the supported demo PR for your review."}
```

`NONE` means no supported action. Both server and app validate output. Failures
return generic 400/401/404/429/502 responses without provider details. No queues,
push commands, screen uploads or execution acknowledgments are implemented.
The local audit reports intent dispatch, which does not prove a page loaded.

## Data and validation

Typed tasks go to this server and OpenAI. Responses requests set `store: false`;
this is not a claim of zero provider retention. No task/token logging or persistence
is implemented here. Check infrastructure and provider policies. API usage is separate
from your ChatGPT subscription.

Tests use a fake provider and loopback HTTP; no billable calls or credentials.
Live HTTPS, model access and real-device behavior must be verified after hosting.
Based on the official [Responses API quickstart](https://developers.openai.com/api/docs/quickstart).
