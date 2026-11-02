# Replay guard recovery intent

- Owner: repository maintainer.
- Baseline: 9b0de145d737a80749543574dfdd097ffa02c611.
- Problem: no durable duplicate-request guard exists on main for future transport integration.
- Scope: recover replay_store.py and its 15 host-only tests byte-for-byte from 8a66e540d9ca7a25e3d325ca81269ed9e57fb3a2; include in maintained CI.
- Acceptance: duplicates remain denied after restart; concurrent identical claims have one winner; corruption, capacity and filesystem substitution fail closed.
- Plan: inspect source, recover isolated module/tests, run temporary-path tests and CI, document platform/atomicity limits.
- Exclusions: listener, relay, controller, executor, production state and device installation.
- Risks: Linux-specific descriptor semantics; pre-start same-UID replacement not detected; IDs are never pruned; a claimed request can remain denied after interruption without completed execution.
- Rollback: revert through review; no live state migrated.
- Release: existing required reviews/CI and device/backup gates remain mandatory.
- Evidence: [record](evidence.md).
