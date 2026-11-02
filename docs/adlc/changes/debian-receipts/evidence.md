# Debian receipt alignment evidence

Date: 2026-11-02. Baseline: dc91663886e8a1137f4279c350e600d823eddbc1.
32 offline bridge unit tests pass locally. ADLC structure/local-link checker passes.
New cases cover every planner diagnostic, malformed received/expected IDs and diagnostics,
combined multibyte output exactly at/above the byte limit, and unpaired surrogates.
Full CI and exact revision-bound results are recorded in the PR after execution.

No network, device, backup, restore or deployment operations were performed.
This verifies offline receipt shape/correlation, not authentication or device origin.

