# Restore regression gates evidence

Date: 2026-11-02. Baseline: 88f0f18cc77ec7e82aa134fd240e45c68a0a811c.

The baseline's [main CI](https://github.com/bmifsud/toolz/actions/runs/41449263942) passed
75 tests and unexpectedly passed both marked restore tests. Source inspection confirms the
restore path now supplies batch/loopback GPG input when BACKUP_PASSPHRASE is configured.

The new change removes those stale exemptions and checks that a wrong passphrase cannot
change existing secret/database bytes, create the target workspace or invoke systemctl.
All paths and services are disposable fixtures.

Local ADLC/link checks and 13 unittest tests pass; Python source compilation passes.
Full fixture suite on this new revision is pending remote CI (local pytest/sqlite3 unavailable).
The exact tested revision and CI result must be read from the PR checks before review.
No live devices, cloud uploads, production restore, schedules or retention were changed.
