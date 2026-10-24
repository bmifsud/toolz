# Issue #10: integration baseline and verification ledger

Audit date: 2026-10-24. This is a partial implementation ledger, not a device
acceptance certificate. Issue: https://github.com/bmifsud/toolz/issues/10.

## Architecture and boundaries

Android Personal Automator currently sends user-entered tasks to local OmniRoute
(port 20128) or the existing HTTPS proposal bridge. Local policy permits only the
fixed demo action after approval. Saved connections use Android Keystore encryption.
This is not yet an arbitrary development-task dispatcher. OmniRoute may forward
requests upstream; loopback transport does not imply on-device inference.

AM provides role/path ownership validation, dependency scheduling, session budgets,
checkpoint patches and recovery branches, PR scope checks and explicit acceptance.
Ownership checks are not an OS sandbox. Use one controller per repository. Unpublished
changes in destroyed agent environments cannot be recovered without durable artifacts.
The tmux launcher is a separate component, not a durable task coordinator.

The existing Termux diagnostic script publishes a bounded health report to GitHub
only after confirmation. It is not authenticated local Android-to-Termux command IPC.
Do not replace it with automatic execution of model output.

Tier-1 protects application state; Tier-2 protects Andronix rootfs data. Never run
rootfs restoration against the active environment. No schedules, backup retention,
installed launchers, permissions, or APKs were changed during this audit.

## Baseline and preservation

- toolz baseline: `e12963b4af9223d434211461817727f483f17f56` (merged PR #6).
- AM PRs #1 and #2 are merged; new recovery work is separate in
  https://github.com/bmifsud/AM/pull/3.
- adaptive-ai-tmux baseline: `b8dddcb27681621638be74c5e31b8afbea08a915`.
- Existing toolz checkout has untracked tests/documentation; preserved untouched.
- Existing `feat/android-consented-tools` worktree contains uncommitted capture
  classes and accessibility-service edits. Preserved; not claimed as delivered.
- Work uses a separate `feat/issue10-verification` worktree, not main.

## Executed evidence

| Check | Observed result |
| --- | --- |
| Proposal bridge: `python3 -m unittest -v` in its directory | 11 tests, OK, 5.735s; fake providers, no inference |
| Backups: `python3 -m pytest -q backup/tests` | 40 passed, 1 xfailed, 1 xpassed in 52.40s; exit 0 |
| AM baseline: `python3 -m unittest discover -s tests -v` | 29 tests; 2 Git fixture setup errors |
| New HTTP 408 regression before correction | Failed: 3 create payloads rather than 1 after restart |
| AM controller/plan suite after correction | 24 tests, OK, 0.722s |
| AM full suite after correction (local) | 30 tests; 2 existing Git fixture setup errors, 2.191s |
| AM PR #3 Ubuntu CI | 30 tests, OK, 0.342s: https://github.com/bmifsud/AM/actions/runs/40128283185 |
| Standalone disposable Git push | Reproduces `bad pack` independently of AM code |
| tmux: `bash tests/run.sh` | Exit 1: refusal to remove a running pane; not a pass |
| ADB discovery | No attached device |
| Generic verification script | PASS; does not discover these suites automatically |

Backup tests are isolated fixture evidence, not proof of real cloud upload, actual
schedule execution, reboot catch-up, or a bootable restored tablet. The unexpected
XPASS requires investigation; it must not be silently counted as full acceptance.
The initial foreground backup invocation timed out; the recorded completed run above
was executed separately with a captured exit status.

Upstream CI inspected before changes:
- Android: https://github.com/bmifsud/toolz/actions/runs/40122234279 (success).
- Backup regression: https://github.com/bmifsud/toolz/actions/runs/39977621623 (success).
- tmux: https://github.com/bmifsud/adaptive-ai-tmux/actions/runs/39387674996 (success).
These receipts apply to their recorded commits, not future implementations.

## Security review and outstanding gates

1. Capture: fresh MediaProjection consent, foreground-service lifecycle, visible stop,
   protected-screen handling, private storage cleanup and per-transmission approval
   still require implementation review and Android 14/15/16 device evidence.
2. Command bridge: authenticated local IPC, exact-action approval, expiry, cancellation,
   timeout, output bounds and redaction are not yet delivered. Arbitrary shell access
   must remain disabled.
3. AM HTTP 408 creation ambiguity is fixed in PR #3: retain the attempt, block launches,
   reconcile after restart. No live Jules invocation was used to test this.
4. AM ownership is validated after results, not enforced inside a remote agent sandbox.
   Cross-controller ownership and filesystem durability need further review.
5. Modern Tier-2 documentation reports symlink rejection in restore validation. Real
   rootfs compatibility and restore integrity must be reproduced in disposable storage.
6. Physical Android testing and local APK compilation are blocked: no attached device
   and no Java executable found on PATH. CI is not a substitute for device acceptance.

## Remaining dependency-aware work

- Review preserved capture drafts, then implement Phase A on its own branch.
- Implement Phase B separately, with one owner for shared Android manifests/UI.
- Continue AM recovery/security review; await complete offline CI and human PR review.
- Audit installed schedules and notifications read-only; run disposable restore tests.
- Only then exercise request -> isolated modification -> tests -> receipt -> PR ->
  human review, with permission loss, invalid credentials, restart and concurrent-task
  scenarios. Human approval/merge must never be fabricated or automated.

Final device acceptance remains **blocked**, not complete. No APK was installed,
no permission was granted, no screenshot was transmitted and no PR was merged.
