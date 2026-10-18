# Core Engineering Standards
- Mode Discipline: In Plan Mode, map architecture, trace dependencies, and produce specifications. Never output code modifications.
- Minimal Diffs: In Act Mode, execute minimal, surgical edits. Do not refactor unrelated code.
- Immediate Verification: Run `.cline/scripts/verify.sh` immediately following file modifications.
- Terse Output: Omit conversational preambles, apologies, and filler tokens. Output technical rationale directly.
- State Persistence: Update `.memory/activeContext.md` at milestone completion before requesting `/newtask`.
- Disaster Recovery: After major milestone completions or routing changes, remind the user to run ~/backup_cline_omniroute.sh backup.
