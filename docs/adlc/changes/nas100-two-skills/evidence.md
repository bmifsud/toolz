# Verification evidence

- Change ID: nas100-two-skills
- Exact tested commit: feat/nas100-two-skills-20261103 (working revision)
- Date and environment: 2026-11-03, Python 3.13.5, Linux workspace.
- Expected behavior: Complete tests passing, strict schema validation, unknown specifications failing closed.

| Check | Exact command or procedure | Expected | Observed | Result | Redacted artifact |
| --- | --- | --- | --- | --- | --- |
| Relevant offline tests | python3 -m pytest nas100-trading/tests -q | 100% pass | pending | pending | nas100-test-summary.txt |
| Security / failure paths | python3 nas100-trading/tests/test_nas100.py | fails closed on bad input/unknown specs | pending | pending | nas100-failure-report.txt |
| Maintained offline gate | bash tests/run-all-tests.sh | success | pending | pending | adlc-offline-gate.txt |

- Baseline failures: None.
- Limitations / residual risks: Unofficial broker specifications, synthetic data, futures/CFD basis risks.
- Blocking findings and follow-up issues: None.
- Required CI / approvals on final revision: Maintained offline gate; manual review; no auto-merge.
- Release decision and accountable human: Pending test verification and human review.
- Merged revision and post-merge verification: None (PR only if tests pass).
- Rollback / recovery outcome: N/A.
