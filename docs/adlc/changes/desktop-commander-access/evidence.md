# Desktop Commander access evidence

- Baseline revision: 9b0de145d737a80749543574dfdd097ffa02c611.
- Exact tested source commit: 2f217ae486f799dc17a80c50dcdfcc8150c60789. This follow-up changes only this evidence record.
- Date/environment: 2026-11-02, Andronix Debian aarch64, accessed exclusively with Remote Desktop Commander.
- Expected behavior: all device requests target Desktop Commander; legacy direct destinations and unsafe plans are denied; no executor or permissions added.

| Check | Command / procedure | Observed | Result |
| --- | --- | --- | --- |
| Maintained offline gate | `env -i HOME="$test_home" GNUPGHOME="$test_home/gnupg" RCLONE_CONFIG=/dev/null PATH=/usr/bin:/bin LC_ALL=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 bash tests/run-all-tests.sh` with private `mktemp -d /tmp/tzdc.XXXXXX` HOME and mode-700 gnupg | ADLC structure/local links, shell syntax and 119 pytest tests passed in 88.25 seconds | pass |
| Focused router/planner/receipt checks | `python3 -m pytest -p no:cacheprovider android-personal-automator/bridge/tests/ -q` before final additional regression cases | 38 passed; final additional cases included in maintained gate above | pass |
| Security and failure paths | Maintained gate includes unavailable Commander, nonboolean flags, arbitrary diagnostics, legacy direct destinations and mutation denial | All passed; no execution performed | pass |
| Whitespace | `git diff --check` | No errors | pass |
| Android build/instrumentation | Android app is absent from current main | Not applicable to this change | not-applicable |
| Live lifecycle and both backup tiers' operational acceptance | No live producers, restores or bridge lifecycle tests invoked for this PR | Standing evidence remains pending | pending |

No provider calls, live archives or production remotes were used by tests. Original tablet checkout and its pre-existing backup edits were preserved in a separate worktree. Legacy environment labels are compatibility hints only; the planner does not call Desktop Commander and a boolean flag does not prove authentication.

Independent review and required CI apply to final PR HEAD. The documentation-only evidence commit follows the tested source commit; CI must validate final HEAD. No merge, deployment, branch-protection change or waiver of existing release gates is authorized or claimed.

Rollback: revert this PR. No runtime installation or configuration migration was performed.
