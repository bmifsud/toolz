# ADLC alignment evidence

Date: 2026-11-02. Environment: managed Linux workspace, Python 3.12.3 system interpreter.
Source baseline: 24ca10df53ca75672a20b838b4ecaa400bee5c41. Results apply to the alignment working tree;
final commit is identified by the PR head and must receive CI on that revision.

| Check | Procedure | Observed | Result |
| --- | --- | --- | --- |
| ADLC consistency | `python3 scripts/check_adlc.py` | No missing required records or broken local links | Pass |
| Offline unit tests | `/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v` | 13 passed, external HTTP mocked | Pass |
| Negative gate cases | Included in unit discovery | Broken/missing/escaping links and incomplete records detected | Pass |
| Shell syntax | `bash -n` on every shell file under backup/tests | No syntax errors | Pass |
| Full backup pytest | `bash tests/run-all-tests.sh` | Missing sqlite3 and pytest in local environment | Pending |
| GitHub workflow | Read-only token, immutable checkout pin, dependency installation, bounded job | Added; remote run pending | Pending |
| Device and cloud gates | No live commands executed | Emulator/tablet, Tier-1 and Tier-2 acceptance unverified | Pending |

No claim of full ADLC compliance, coverage, restored data integrity or release readiness.
Branch protection and CI-required status are administration tasks, not established by YAML.
Existing expected failures and any newly exposed failures must be triaged before release.
