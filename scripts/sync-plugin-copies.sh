#!/usr/bin/env bash
# Keep marketplace thin-plugin skill copies in sync with authoritative skills.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

changed=0
for src in "$repo_root"/skills/*/SKILL.md; do
  name="$(basename "$(dirname "$src")")"
  dst="$repo_root/plugins/usage-trace/skills/$name/SKILL.md"
  mkdir -p "$(dirname "$dst")"
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
    echo "skill copies in sync: $name"
    continue
  fi
  cp "$src" "$dst"
  echo "updated $dst"
  changed=1
done

[[ "$changed" -eq 0 ]] && echo "all skill copies already in sync"
exit 0
