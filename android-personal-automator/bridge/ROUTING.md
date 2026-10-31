# Hybrid request routing (design and security boundary)

This module is a pure classifier, **not** a ChatGPT tool registration, remote shell, or automatic bridge connection.

Routing: `@ChatGPT`, `@GitHub`, and `@Termux` explicitly override classification. Without a prefix, one unambiguous target routes to its destination; mixed targets require clarification. No target or ambiguous language defaults to ChatGPT.

Permissions: ChatGPT answers locally. GitHub read requests require a scoped connector; GitHub writes require explicit approval. Termux diagnostics must map to a separately enforced allowlist; mutating requests are proposals only and require explicit approval. The router never accepts shell commands, tokens, or URLs as executable instructions. The existing bridge must separately authenticate its controller and device. A router decision is **not authorization**.

Audit: `audit_event` returns structured JSONL with UTC timestamp, opaque request ID, SHA-256 prompt fingerprint, destination, permission, action and reason. It does not log raw prompt text or secrets. An integrating application must persist these records securely with retention and access controls and add execution receipts separately.

Tests: `python -m unittest discover -s android-personal-automator/bridge/tests -p 'test_request_router.py' -v`.

Deployment is intentionally not wired to a live Termux device. Do not describe a diagnostic as executed unless an authenticated connector returns its result.
