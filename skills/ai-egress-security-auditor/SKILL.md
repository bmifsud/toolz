# ai-egress-security-auditor

## Purpose
Audit data sent from repository automation to external AI providers, preventing accidental secrets, PII and sensitive source disclosure.

## Trigger
Adding or changing AI adapters, provider API calls, prompt construction, agent tools, logging, or external data transfers.

## Procedure
1. Read repository security policy, existing skills, outbound adapters and issue #112. Inventory each egress sink and data source.
2. Trace inputs to network calls and logs; identify trust boundaries, credentials, private diffs, device logs, backup artifacts and personal content.
3. Require a strict source allowlist and fail-closed redaction/deny policy before transmission. Test synthetic secret and PII canaries, prompt injection and malformed inputs without using real sensitive material.
4. Verify least-privilege permissions, SHA-pinned trusted execution, bounded request size, timeouts, rate/quota/cost limits and redacted logs.
5. For live API tests require separate authorization, trusted default-branch/manual-only workflows, fixed non-sensitive synthetic payloads, and no PR-supplied code with secrets.
6. Keep Perplexity review advisory and Gemini documentation advisory read-only unless separately authorized and reviewed.
7. Produce findings with exact file/line and SHA, severity, reproduction, remediation and evidence; mark unavailable live tests NOT VERIFIED.

## Output
Data-flow inventory, security matrix, synthetic test results and blocking findings. Never expose keys or activate integrations.
