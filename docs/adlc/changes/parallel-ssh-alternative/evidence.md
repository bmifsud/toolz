# Verification evidence: parallel-ssh-alternative

- Change ID / issue / PR: parallel-ssh-alternative
- Exact tested commit: f545a0f0b9b6771fa3fc6d0ca76300cd8e5993f8
- Date and environment / tool versions: 2026-11-04, Debian 13 (aarch64 proot under Termux), Python 3.13.5, OpenSSH 9.9p1
- Expected behavior: Secure OpenSSH alternative operates strictly on localhost/private RFC1918 networks with key-only authentication and strict host verification.
- Reviewer and reviewed revision: Pending independent review.

| Check | Exact command or procedure | Expected | Observed | Result | Redacted artifact |
| --- | --- | --- | --- | --- | --- |
| Unit tests (ssh_remote) | `PYTHONPATH=. python3 -m pytest ssh_remote/tests/ -v` | 6 passed | 6 passed | pass | Local pytest output |
| Security / failure paths | Tested public IP rejection, permission checks, Termux privileged port denial | All fail closed | Verified in `test_ssh_remote.py` | pass | Local pytest output |
| ADLC link & structure | `python3 scripts/check_adlc.py` | PASS | PASS | pass | stdout |
| Offline test suite | `bash tests/run-all-tests.sh` | PASS | PASS | pass | Runner output |
| Emulator lifecycle | N/A - offline transport foundation | N/A | not run | not-applicable | Pure software module |
| Tablet lifecycle | N/A - offline transport foundation | N/A | not run | not-applicable | Pure software module |
| Tier-1 scheduled/upload/catch-up | N/A - backup schedules unchanged | N/A | not run | not-applicable | Backup scripts untouched |
| Tier-2 shutdown/snapshot/restore | N/A - backup scripts unchanged | N/A | not run | not-applicable | Backup scripts untouched |

- Baseline failures: None.
- Limitations / residual risks: Live SSH daemon binding requires Termux/Debian environment runtime execution.
- Blocking findings and follow-up issues: PR to be submitted without merge.
- Required CI / approvals on final revision: Pending GitHub Actions run and maintainer approval.
- Release decision and accountable human: Unmerged pending user/maintainer review.
- Merged revision and post-merge verification: Not merged.
- Rollback / recovery outcome: Safe branch isolation.
