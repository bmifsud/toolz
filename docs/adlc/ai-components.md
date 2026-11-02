# AI component inventory

Inspected 2026-11-02 at source baseline 24ca10df53ca75672a20b838b4ecaa400bee5c41.
Owner: repository maintainer. Development advisory tooling only; no deployed AI product established.

| Component | Model and endpoint declared in source | Permissions / data | Verification |
| --- | --- | --- | --- |
| Perplexity advisory | `sonar`, `api.perplexity.ai/chat/completions` | Explicit review CLI sends supplied text; key via PERPLEXITY_API_KEY; no GitHub writes | Mocked HTTP unit tests only |
| Gemini docs advisory | `gemini-2.5-flash`, Google generateContent API | Explicit docs CLI sends supplied text; key via GEMINI_API_KEY; no publishing | Mocked HTTP unit tests only |

Provider aliases are not immutable model versions. Weight hashes, training lineage, provider
retention terms, deployed configuration and live API compatibility are unknown/unverified.
Review those with the maintainer before activation. No API request was made during alignment.
Both clients bound input/output and use 30-second HTTP timeouts; provider billing limits are
not enforced locally. Do not send private device data or credentials. Model suggestions are
untrusted and require source-based review. Prompts and tool code are versioned under scripts/.
This is a manual inventory, not a generated standards-compliant AIBOM/SBOM.

## Offline device planning update (2026-11-02)

The deterministic router/planner has no model or external API. Device requests now target Remote Desktop Commander exclusively; legacy Termux/Debian labels are environment hints. No tool permission or executor is added. Caller availability booleans are not authentication. See [intent](changes/desktop-commander-access/intent.md) and [evidence](changes/desktop-commander-access/evidence.md).
