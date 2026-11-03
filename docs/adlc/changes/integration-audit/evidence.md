# Integration audit evidence

Baseline: 9ebcecaf2f18406358ab35f6f658ff796ab85ea9. Date: 2026-11-02.
Worktree: /home/b/toolz-adlc-audit; branch audit/adlc-integration-20261102.
The worktree was clean at entry. No command writes to the original checkout.

## Applicability and findings

| Requirement | Finding / control | Remaining gate |
| --- | --- | --- |
| Intent and plan | Scoped intent precedes implementation; independent observable criteria | Human review pending |
| Small isolated branch | Only validation, CI, tests and documentation changed | No merge authorized |
| Required documentation | Expanded required-file checks; reject empty/comment-only/example-only records | Content quality/truth requires review; no schema retrofitted to historical prose |
| Negative validation | Missing files, incomplete/empty pairs, traversal/symlink links and malformed provenance tested | Markdown parser is deliberately limited; not a complete Markdown/security scanner |
| Fixture isolation | Existing fixtures isolate HOME, GPG and cloud/service mocks; CI now clears inherited environment and uses temporary HOME/TMPDIR | Not an OS/network sandbox; tests must remain reviewed |
| Evidence provenance | SHA/outcome validation retained; event allowlist and positive ASCII identifiers added | Receipts are unsigned, not independent approval |
| CI evidence | Pinned actions, read-only token, always-upload receipt/JUnit already present | Remote execution, artifact retrieval and required-check configuration unverified |
| AI evaluation/inventory | No delivered AI behavior/model/prompt/tool permission changed | Existing advisory mock tests do not establish live provider compatibility |
| Release and learning | Standing hold retained; reviewed revert is rollback | No deployment, rollback exercise, merge or post-merge verification |

## Validation

Executed on 2026-11-03 through Remote Desktop Commander in this audit worktree:
- ADLC structure/local-link check and git diff --check passed.
- Focused validator/receipt tests: 10 passed after the review correction.
- Full maintained offline gate: 125 passed in 68.16 seconds, exit 0.
- The full gate used env -i, PATH=/usr/bin:/bin and disposable HOME/TMPDIR/GNUPGHOME,
  with cloud/service fixtures. Final JUnit: /tmp/adlc-finish.rcm2Dl/tests-final-retry.xml.
- An earlier pre-correction run passed 124 tests; a later terminal-attached attempt
  was interrupted without an exit record and was not counted as passing. The final
  detached retry above is the completed run.

Cline text-only review identified an unfinished HTML comment being accepted as
record content. That specific recommendation was applied: comments now strip through
EOF; regressions reject comment-only records and preserve visible preceding text.
Cline did not claim tests were run. Interactive Cline crashed under PRoot, and a later
code-generation retry failed when the gateway API was unavailable. No blanket
approval or --yolo was used. This working-tree result is not mislabeled as testing
an unchanged commit. Final source/CI identities are recorded in the draft PR.
Fetched main 0b49f4aa30a496b727e8befc01b42c21df369000 had no overlapping changes
in the five modified CI/validator/test files before reconciliation.

## Unverified operational gates

- Independent maintainer review and required CI/approvals on final revision.
- Branch-protection enforcement: unverified, neither queried nor changed.
- Commander architecture applicability plus authenticated connect/reconnect/cancel/restart and denial/security paths, emulator first and tablet second. No emulator/tablet lifecycle actions were performed.
- Tier-1 scheduled execution, encrypted upload/readback/integrity and missed-run catch-up.
- Tier-2 safe OmniRoute shutdown/WAL handling, encrypted snapshot/upload and isolated restore/integrity.
- Deployment, accountable human release decision, rollback and post-merge verification.

All operational gates remain pending and release remains blocked. Historical evidence
and fixture success cannot waive them. No secrets, schedules, retention, backup source,
permissions, remote settings changed by the repository patch. Cline review used its existing configured model route. A stopped local gateway was launched for review retries, but API readiness remained unverified; no provider settings or credentials were changed.
