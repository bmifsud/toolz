# Issue: Backup Test Decryption Fails Due to GPG Batch Mode / Passphrase

## Description
During `tests/test-backup.sh` execution, test decryption fails with:
`gpg: problem with the agent: Inappropriate ioctl for device`
`gpg: decryption failed: Bad session key`

## Impact
Automated backup verification test (`test-backup.sh`) fails during Test 3 restoration phase when running in non-interactive batch mode without proper GPG options (`--batch --passphrase`).

## Recommended Action
Update `backup/backup_cline_omniroute.sh` or `tests/test-backup.sh` to pass `--batch --yes --passphrase-fd` or environment variables for deterministic non-interactive GPG decryption during automated testing.
