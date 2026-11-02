# backup-recovery-verifier

## Purpose
Produce reproducible, independently reviewable Tier-1 and Tier-2 backup integrity and isolated recovery evidence. Never infer recovery from upload progress or archive listing alone.

## Trigger
Backup creation, upload, restore, deletion, catch-up, schedule changes, failed checks, or release gates involving backups.

## Procedure
1. Read backup scripts, runbooks, issues #105 and #40, and relevant existing skills. Establish exact revision, device/environment, authorized scope and preconditions.
2. Run non-destructive preflight checks. Do not stop Debian/OmniRoute, use passphrases, delete backups, alter cron, or run device commands without explicit authorization for the operation.
3. For each tier separately record archive identity, timestamp, size, local SHA-256, remote path/object identity, and full remote ciphertext readback SHA-256.
4. In a fresh isolated destination, decrypt using authorized credentials and validate archive safety (path traversal, links, permissions), contents, SQLite quick_check and application data. Tier-2 requires documented clean OmniRoute stop and WAL handling.
5. Exercise expected failures with synthetic fixtures where safe. Never replace live rootfs or follow restored links outside isolation.
6. Record exact command, source SHA, environment, expected/observed result, redacted logs, receipts and unresolved checks.
7. Label every gate PASS, FAIL or NOT RUN; distinguish structural validity, extraction and usable recovery. Do not approve merge or deletion based on incomplete evidence.

## Output
Separate Tier-1 and Tier-2 evidence tables, blockers, risks and safe next steps. No production changes by default.
