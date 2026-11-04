# Current architecture and integration boundaries

This map reflects the source inventory inspected on 2026-11-04. Source presence is not deployment evidence.

| Component | Implemented source | Boundary |
| --- | --- | --- |
| Tier-1 | [Producer](../backup/backup_cline_omniroute.sh) | Encrypted archive and optional cloud copy; restore overwrites state |
| Scheduling | [Runner](../backup/run_scheduled_backup.sh), [cron installer](../backup/install_backup_cron.sh), [catch-up](../backup/check_missed_backups.sh) | Operational configuration and execution; device acceptance pending |
| Tier-2 | [Debian snapshot](../backup/snapshot_andronix_debian.sh), [streaming snapshot](../backup/snapshot_andronix2_streaming.sh), [layout](../backup/snapshot_andronix_layout.sh) | Consistency and isolated restoration require independent evidence |
| Preparation | [Preflight](../backup/check_tier2_preflight.sh), [cleanup](../backup/pre_snapshot_clean.sh) | Cleanup can stop services and change data |
| Retention | [Tier-1 retention](../backup/tier1_retention.sh) | Apply mode deletes archives; preserve existing policy |
| Advisory AI | [Perplexity](../scripts/perplexity_advisory.py), [Gemini](../scripts/gemini_docs_advisory.py) | Explicit CLI invocation calls external APIs; no publisher, executor or scheduled integration |
| ADLC | [Workflow](adlc/README.md), [checker](../scripts/check_adlc.py) | Repository consistency checks; not authorization or compliance certification |
| OpenSSH Alternative | [SSH Remote](../ssh_remote/README.md) | Parallel fail-closed transport; localhost/RFC1918 only; key-based auth and strict host verification |

Offline routing/receipt modules have been recovered from pinned branch source (see [recovery evidence](adlc/changes/offline-bridge-recovery/evidence.md)). They classify requests, construct plans and validate receipt shape/correlation only. Debian launcher discovery never executes candidate files. Permission/authentication booleans are caller-supplied planning inputs, not enforced authentication. Receipt digests do not prove device origin. Receipt validation shares the planner's fixed host/Debian diagnostic allowlists. Device plans target Remote Desktop Commander, which must independently verify the selected device and authorization. No direct device bridge is planned or connected; request tracking remains required.

Android app, proposal server, custom relay/controller/device, task queue and CLI adapters remain absent. The primary access path is Remote Desktop Commander, with a secure, fail-closed OpenSSH alternative available for isolated, localhost/private network communication in Termux and Debian environments. Any separate future capability requires its own scoped change and verification.

## Trust boundaries

Backup producers use local state and configured cloud tools. Scheduled execution, remote integrity and restored data must be verified on the target separately. Termux and Debian may use separate checkouts; updating one does not update the other. See [Tier-1 deployment acceptance](../backup/TIER1_DEPLOYMENT_ACCEPTANCE.md).

Advisory scripts accept input and return external model suggestions. Review/redact input before authorized invocation. Their output is untrusted and does not grant permission to execute commands, publish docs or merge.

## Release policy

Follow [ADLC](adlc/README.md) and [verification](verification.md). Authenticated emulator/tablet lifecycle and both backup tiers remain pending. Keep existing backup schedules and retention unchanged while collecting offline evidence.

Offline planning validates known destination/permission/action combinations and boolean flags; malformed states are denied, ambiguous requests require clarification, and all device environments route to Desktop Commander. Legacy direct Termux/Debian destination objects are denied. These checks still do not authenticate callers or execute plans.
