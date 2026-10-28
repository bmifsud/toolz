---
name: toolz-collaboration
description: Safe, evidence-driven collaboration for bmifsud/toolz, Termux, Android, Cline/OmniRoute and backups.
---

# Toolz collaboration

## Purpose
Keep independent Toolz workstreams progressing with explicit evidence, without disrupting the Android tablet or backups. This repository skill is guidance for coding agents that load it; it is not a live connection, a ChatGPT memory store, or permission to execute arbitrary commands.

## Visibility
For each meaningful change, publish **STARTED / WORKING / VERIFIED (PASS, FAIL, BLOCKED) / FINISHED / NEXT** with links to relevant commits, PRs, CI runs or redacted receipts. Distinguish a passing mocked test from an emulator run and from a physical-device test. Do not claim background work is continuous when it runs on a schedule. If no safe work remains, report why.

## Independent workstreams
- **Termux relay/security:** PR #42, issue #41. Verify authentication before WebSocket accept; relay health checks or handshake logs alone never prove an authenticated device session.
- **Persistent controller:** PR #35; PR #34 is overlapping draft. Validate durability, leases, concurrency, cancellation and fail-closed recovery before integration.
- **Bounded executor:** PR #33 and read-only diagnostic runner #23. Keep explicit allowlists, argument-vector execution, output limits, timeouts and cancellation.
- **Emulator:** PR #37 and issue #36. Prove emulator/ADB readiness, then run a real authenticated end-to-end test with disposable credentials and receipts before asking for physical-device validation.
- **Backups:** issue #40, PRs #18, #19, #22. Tier-1 runs twice daily in Termux; Tier-2 runs Monday/Wednesday/Friday in Andronix Debian. Never change schedules without explicit authorization. Preserve encrypted archives until remote upload is independently verified; confirm restore in isolation, not by destructive live extraction.
- **Cline/OmniRoute:** Verify actual CLI and gateway availability on the intended host, not inferred from repository configuration. Use isolated checkouts for concurrent tasks; do not overlap edits to the same files.
- **Private universal CLI gateway:** Plan separately. Require authentication, per-command authorization, audit trails, safe defaults and explicit opt-in before broadening the executor.

## Integration gates
1. Inventory branches, diffs, dependencies and required CI.
2. Run isolated unit, regression and security checks; document limitations.
3. Integrate non-overlapping changes on a separate branch; resolve conflicts without overwriting existing work.
4. Run emulator end-to-end tests and save redacted receipts.
5. Request approval for production deployment, tablet execution, destructive operations, or irreversible changes.
6. Merge/close PRs only when evidence supports the action. Do not merge or close everything blindly.

## Device and security boundaries
- Never expose tokens, passphrases, device data or personal content in issues or logs.
- Do not bypass Android permissions, execute arbitrary scripts, delete backups, restore over live data, or enable broad shell access.
- Never claim Termux is connected until an authorized, authenticated request produces a correlated device receipt.
- Render relay may auto-deploy on checked commits; check live service configuration before changing the deployed branch.

## Evidence checklist
Record: exact commit SHA, workflow/job URL, test result, emulator/API/ABI where relevant, whether the tablet was involved, backup timestamp and encrypted archive identity (without secrets), remote integrity evidence, restore evidence, remaining blockers and next action.

## Continuous improvement
After meaningful incidents, add a narrowly scoped, reviewed improvement to this skill. Keep the skill short, actionable and version-controlled. Do not store sensitive user memory or secrets here.
