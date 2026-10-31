# Current architecture and integration boundaries

This map describes source on `main` at revision `64be9874f64b1f3eeb60877b93beddef1f5d4094`. It records implemented components, not a verified device installation. Draft branches can contain additional code; inspect their exact revision before using them. The [verification guide](verification.md) separates offline checks from operational changes.

## Repository map

| Component | Responsibility on this revision | Boundary / evidence still needed |
| --- | --- | --- |
| [Android app](../android-personal-automator/app/src/main/java/org/aief/personalautomator/) | Kotlin activity, session/capture lifecycle, provider endpoint validation, connection vault and supervised proposal handling | Android permissions, user consent and session state remain device concerns; a successful app build does not prove Termux/Cline connectivity |
| [Proposal server](../android-personal-automator/bridge/server.py) | Authenticated HTTP `/proposal` endpoint, bounded request/provider response, rate/concurrency checks, strict proposal schema; supports Responses and chat-completions providers | Produces proposals only; it does not control a device. Provider configuration and deployment are separate operational steps |
| [Request router](../android-personal-automator/bridge/request_router.py) and [routing adapter](../android-personal-automator/bridge/routing_adapter.py) | Classify destinations and produce fail-closed execution plans | A route or `ready_for_executor` plan is not a connector call, authorization or evidence of execution |
| [Receipt validator](../android-personal-automator/bridge/routing_receipts.py) | Check diagnostic allowlist, request correlation, exit code and combined UTF-8 output bound; produce a content digest | Caller must authenticate transport and track requests. A digest does not authenticate device origin |
| [Bounded executor](../android-personal-automator/bridge/bounded_executor.py) | Invoke a separately supplied controller through a fixed argument vector with timeout and output checks | Prototype requires configured credentials and verified controller `--diagnostic` compatibility. Post-execution output checks are not a streaming memory cap |
| [Debian diagnostics](../android-personal-automator/bridge/debian_diagnostics.py) | Discover candidate launcher files and define fixed identity/disk diagnostic arguments | Discovery never executes or trusts a launcher. There is no remotely executable Debian adapter in this revision |
| [Supervisor and boot helpers](../android-personal-automator/bridge/termux-bridge-supervisor.sh) | Opt-in listener supervision, locking, stop/restart and secure-start/boot setup helpers | Depend on a separately supplied listener, protected credentials and device setup; presence of helpers does not establish installation or persistence |
| [Tier-1 producer](../backup/backup_cline_omniroute.sh) | Stage Cline state/settings, OmniRoute SQLite/environment/service configuration and workspace files; create encrypted archive; optional cloud copy; restore modes | Restore overwrites state and can invoke user-service operations. Producer cloud copy is not the scheduler's full remote readback verification |
| [Scheduled runner](../backup/run_scheduled_backup.sh) and [retention](../backup/tier1_retention.sh) | Load local configuration, lock runs, invoke configured producer/snapshot, verify local decryption and remote SHA-256 readback, report status and apply Tier-1 retention | These are operational scripts, not diagnostics. Configured command/launcher paths are operator-controlled; review them before execution |
| [Tier-2 streaming snapshot](../backup/snapshot_andronix2_streaming.sh) | Create/verify encrypted Andronix archives, with optional cloud upload | Rootfs consistency, real-device compatibility and isolated recovery require separate acceptance; no production restore authorization follows from archive validation |
| [Snapshot alternatives](../backup/snapshot_andronix_debian.sh), [layout helper](../backup/snapshot_andronix_layout.sh), [preflight](../backup/check_tier2_preflight.sh) and [cleanup](../backup/pre_snapshot_clean.sh) | Alternative snapshot/layout and pre-snapshot operational helpers | Inspect each entry point. In particular, cleanup and snapshots may stop services or create/delete data; they are not interchangeable read-only health checks |
| [Cron installer](../backup/install_backup_cron.sh), [catch-up checker](../backup/check_missed_backups.sh) and [catch-up installer](../backup/install_catchup.sh) | Provision schedules and missed-run/boot handling | Installation and catch-up can modify configuration or start work. Source does not establish that a device schedule ran |

## Data and trust flow

The app requests a proposal from the authenticated proposal server, which calls a configured provider and validates the returned proposal. Device consent and app-side policy remain separate from that server response. The router/adapter separately describe where a request could go; they do not connect the app to a remote shell.

A future integrated diagnostic flow needs an authenticated controller-to-relay-to-device transport, per-request authorization, fixed diagnostic selection, bounded execution and a correlated receipt. The receipt validator is one validation component of that flow, not the whole transport. The supervisor can manage an installed listener, but the WebSocket relay/controller/device implementations are absent from this `main` revision.

The Termux scheduled runner and Debian producer can live in different checkouts. Updating outer Termux does not update the Debian copy. Read [Tier-1 deployment acceptance](../backup/TIER1_DEPLOYMENT_ACCEPTANCE.md) for the documented split; its deployment commands change the installation and are not part of offline verification.

## Main versus draft work

The following are workstreams under review, not capabilities established by this revision:

- WebSocket relay/controller/device, HTTP diagnostic gateway and their transport/security tests.
- Persistent SQLite task queue/controller and an integrated execution worker.
- Dedicated Android emulator readiness evidence and full gateway/controller lifecycle testing.
- Installable host-readiness CLI, Cline collaboration guidance and cross-platform gateway packaging.
- Expanded coverage reporting, receipt hardening and backup/restore test improvements submitted independently of this baseline.

Check open pull requests and their base branches rather than treating their titles or green checks as merged behavior. Some relay branches are associated with auto-deployment; merging into them can be an operational deployment. Overlapping drafts require source comparison before disposition. Backups remain a separate workstream.

## Required connection and Cline sequence

1. Verify an actual authenticated Termux WebSocket diagnostic round trip through an approved controller path. Require matching request/receipt identifiers, bounded output and current device evidence. Relay health, a socket acceptance log and local executable presence are insufficient.
2. Inspect the installed Debian launcher and start Debian only through a supported, explicitly authorized lifecycle operation. Establish and scope an authenticated Debian-side channel separately. A cloud Linux shell is not evidence of the tablet's Debian environment.
3. Verify the installed Cline version and its actual interfaces. Interactive use requires a console-carrying session; noninteractive invocation must be verified independently rather than inferred from a binary name. Verify OmniRoute configuration/service readiness without exposing credentials.
4. Integrate scoped execution only after these gates and the applicable emulator/security checks pass. Keep timeout, cancellation, reconnect, restart, replay and output-bound evidence distinct from the successful happy path.

This sequence remains pending. It grants no arbitrary script fallback. Any proposed full-script feature requires its explicit opt-in, authenticated authorization and consent; it is not supplied by the current routing plan.

## Backup scheduling status

The cron installer source specifies Tier-1 at 09:00 and 21:00 daily and Tier-2 at 03:00 on Monday, Wednesday and Friday, according to the cron environment's timezone. Treat these as planned schedules until verified on the target device, including missed-run behavior, upload integrity, retention and recovery. Do not enable or change production schedules while collecting offline evidence.

The existing acceptance document records a historical, user-reported Tier-1 device check. It is not a fresh end-to-end result for every later revision or proof of automatic scheduling. Tier-2 and production recovery gates remain independent.
