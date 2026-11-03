# Change intent

- Change ID: nas100-two-skills; requested by repository owner.
- Baseline: origin/main 92b12c4; isolated feat/nas100-two-skills-20261103.
- Scope: new top-level nas100-trading only plus these ADLC records; preserve existing files.
- Behavior: two paper-only skills, shared chronological NQ CSV research, optional TimesFM forecasts, explicit broker and dataset limitations.
- Acceptance: strict schema and chronological validation; causal fold selection; same-period baseline comparison; EUR 500; unknown costs/specifications block money simulation; no execution or credentials; offline regression tests pass before PR.
- Risk: medium, misleading investment conclusions. Mitigation: proxy warnings, conservative fills, fail-closed specification checks, no claims of improvement without OOS evidence.
- Dependencies: Python standard library; existing pytest for tests. Optional model artifacts only, no model/network runtime dependency.
- No device, backup, permission, credential or live trading changes.
- Assumptions: user CSV absent; Blueberry account-specific contract and cost inputs unknown. Synthetic tests do not establish profitability.
- Steps: implement validation and engine; docs/attribution; tests; offline gate; review; push/PR only on pass.
- Validation: python3 -m pytest nas100-trading/tests -q; bash tests/run-all-tests.sh.
- Denied cases: malformed/unsorted/mixed-symbol data, future forecast metadata, missing specifications, excessive risk, minimum lot infeasibility.
- Rollback: revert new-file commit; no runtime deployment.
- Approval: human review and existing standing release gates remain required; do not merge.
- Evidence: [evidence](evidence.md).
