# Offline bridge recovery evidence

Date: 2026-11-02. Baseline: 656758095e66fa09cb8728e763205eed0957e4a8.
Source branch: fix/bridge-ci-bounded-ws-tests-20261030.
Pinned source commit: 8a66e540d9ca7a25e3d325ca81269ed9e57fb3a2.

Four modules and their four tests are recovered byte-for-byte from that commit.
Source was inspected: no network/subprocess execution; launcher discovery checks candidate files
without executing them. The planner's authentication/approval inputs are not security enforcement.

Local commands:
- Python unittest discovery under android-personal-automator/bridge/tests: 28 passed.
- ADLC structure/local-link checker: passed.
- Maintained shell runner syntax: passed.

Full CI on the new revision is pending; record exact commit/run in the PR once available.
No device connection, emulator lifecycle, cloud upload/readback or live restore was performed.
Android app, transport/executor and Debian receipt integration remain separate pending work.
