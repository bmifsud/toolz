# Shared ADLC skill library

Reusable, repository-agnostic skill instructions for Toolz, AM and adaptive-ai-tmux. These are initial instruction specifications, not installed or runtime-validated skills.

| Skill | Focus |
| --- | --- |
| adlc-compliance-auditor | ADLC evidence and gaps |
| release-readiness-gate | Merge/release blockers |
| agent-failure-recovery | Safe incident recovery |
| cross-repo-dependency-manager | Compatibility across repositories |
| test-coverage-gap-detector | Missing test scenarios |
| skill-effectiveness-evaluator | Skill quality and value |

Read each `skills/<name>/SKILL.md` for the procedure. Reuse existing Android/Termux testing skills rather than duplicating them. No automatic installation, workflow execution or repository modification is implied. The existing `docs/adlc/` and `AGENTS.md` remain authoritative. Validate these skills in isolated test tasks before adoption.
