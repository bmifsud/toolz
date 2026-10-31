# Tier-1 AI configuration coverage (draft)

The existing Tier-1 backup remains unchanged by default. Set `TIER1_INCLUDE_AI_CONFIG=1` in the **Debian** process running `backup_cline_omniroute.sh` to include additional Debian AI configuration. Do not enable until testing and review complete.

## Additional archive contents
`ai-config/debian-home/` contains existing allowlisted Cline, Codex, shared agent, Gemini, uv tool, and shell configuration. `ai-config/manifest.txt` records included paths without dumping secrets. The helper skips missing paths and top-level symlinks. It does not enumerate all dynamically installed skills or guarantee every MCP server is recoverable.

## Security and recovery blockers
- The original Tier-1 implementation stages sensitive plaintext files before GPG encryption and uses a generic tar extraction restore path. Do not treat this new feature as a security audit or an approved restoration method.
- Outer Termux `~/.cline`, `~/.termux`, `~/.bashrc`, and `~/.config/toolz-backup` are **not included** by this Debian-only helper. They require a separate Termux-side, access-controlled capture and restore flow. Avoid recursively including passphrase files without reviewing threat model.
- The helper currently copies the uv tools tree; benchmark size and decide whether a lockfile plus install manifest is preferable.
- Avoid blindly restoring saved API credentials or overwriting existing configuration.
- Existing backup script's restore mode does **not** restore `ai-config/`; a safe selective restore procedure and tests are pending.
- Never print or commit contents of credential files.

## Acceptance gates
1. Synthetic fixture tests for absent directories, permissions, symlink boundaries, and exact inclusion manifest.
2. Confirm the Debian helper runs from the intended scheduled Tier-1 execution environment.
3. Produce an encrypted test archive and verify the manifest and file hashes **after decryption**, without logging secrets.
4. Implement and test safe isolated restoration of skills and MCP settings.
5. Verify backup upload to Google Drive and ensure the unchanged Tier-1 schedule still passes.
6. Independently design Termux-side coverage.

Keep this branch as a draft until all gates pass.
