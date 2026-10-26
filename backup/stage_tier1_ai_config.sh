#!/usr/bin/env bash
# Stage additional Debian AI configuration inside the existing encrypted Tier-1 archive.
# Invoked by backup_cline_omniroute.sh before tar|gpg, never standalone restore.
set -euo pipefail
umask 077
[[ $# == 1 ]] || { echo 'Usage: stage_tier1_ai_config.sh STAGING_DIR' >&2; exit 2; }
stage=$1
[[ -d "$stage" && ! -L "$stage" ]] || exit 2
dest="$stage/ai-config/debian-home"
mkdir -p "$dest"
# Preserve installed skills and configuration, not reproducible caches or package trees.
paths=(
  .cline/skills
  .cline/docs/capability-stack/manifests
  .codex/skills
  .codex/config.toml
  .agents/skills
  .agents/.skill-lock.json
  .gemini/config
  .gemini/antigravity
  .gemini/antigravity-cli/builtin/skills
  .gemini/jetski/mcp_config.json
  .config/mcp
  .local/share/uv/tools
  .bashrc
)
manifest="$stage/ai-config/manifest.txt"
: > "$manifest"
for rel in "${paths[@]}"; do
  src="$HOME/$rel"
  [[ -e "$src" || -L "$src" ]] || continue
  # Do not traverse top-level symlinks into arbitrary locations.
  if [[ -L "$src" ]]; then
    echo "SKIPPED symlink: $rel" >> "$manifest"
    continue
  fi
  mkdir -p "$dest/$(dirname "$rel")"
  cp -a -- "$src" "$dest/$rel"
  echo "INCLUDED $rel" >> "$manifest"
done
chmod 600 "$manifest"
