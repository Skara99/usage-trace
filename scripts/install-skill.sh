#!/usr/bin/env bash
# Install usage-trace skill for Codex / Claude Code / Cursor, and install the CLI.
# Default: symlink skill into agent skill dirs so repo updates apply immediately.
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  install-skill.sh [--symlink|--copy] [--skip-cli] user              # all user-level skill dirs (Recommended)
  install-skill.sh [--symlink|--copy] [--skip-cli] project [dir]     # all project-level skill dirs
  install-skill.sh [--symlink|--copy] [--skip-cli] codex-user        # only ~/.codex/skills (or $CODEX_HOME)
  install-skill.sh [--symlink|--copy] [--skip-cli] claude-user       # only ~/.claude/skills
  install-skill.sh [--symlink|--copy] [--skip-cli] cursor-user       # only ~/.cursor/skills
  install-skill.sh [--symlink|--copy] [--skip-cli] all               # alias of user

Installs skills/usage-trace for coding agents and (by default) the local usage-trace CLI.

Link mode:
  --symlink   ln -sfn repo skills/usage-trace into each dest (default)
  --copy      copy SKILL.md into each dest
  USAGE_TRACE_SKILL_INSTALL=symlink|copy overrides the default

CLI:
  By default also runs: python3 -m pip install -e <repo>
  --skip-cli  install skill only (no pip)

Skill load paths (Agent Skills standard):
  Claude Code  ~/.claude/skills/  or  <project>/.claude/skills/
  Cursor       ~/.cursor/skills/  or  <project>/.cursor/skills/
               also reads ~/.agents/skills/ and .agents/skills/
  Codex        ~/.codex/skills/   or  plugin marketplace
               also reads ~/.agents/skills/

Examples:
  install-skill.sh user
  install-skill.sh --copy user
  install-skill.sh project .
  install-skill.sh codex-user
USAGE
}

link_mode="${USAGE_TRACE_SKILL_INSTALL:-symlink}"
skip_cli=0
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --symlink)
      link_mode="symlink"
      shift
      ;;
    --copy)
      link_mode="copy"
      shift
      ;;
    --skip-cli)
      skip_cli=1
      shift
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    --)
      shift
      args+=("$@")
      break
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done
set -- "${args[@]:-}"

mode="${1:-user}"
target="${2:-}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
skill_src_root="$repo_root/skills"
skill_src_dir="$repo_root/skills/usage-trace"
skill_src="$skill_src_dir/SKILL.md"

if [[ ! -f "$skill_src" ]]; then
  echo "Skill definition not found: $skill_src" >&2
  exit 1
fi

# All shipped skills (usage-trace, field-regression, ...) install side by side.
skill_names=()
for d in "$skill_src_root"/*/; do
  name="$(basename "$d")"
  [[ -f "$d/SKILL.md" ]] && skill_names+=("$name")
done
if [[ ${#skill_names[@]} -eq 0 ]]; then
  echo "No skill definitions found under $skill_src_root" >&2
  exit 1
fi

if [[ "$link_mode" != "symlink" && "$link_mode" != "copy" ]]; then
  echo "Invalid link mode: $link_mode (use symlink|copy)" >&2
  exit 2
fi

install_one() {
  local dest="$1"
  local skill_name
  local parent
  skill_name="$(basename "$dest")"
  local src_dir="$skill_src_root/$skill_name"
  parent="$(dirname "$dest")"
  mkdir -p "$parent"

  if [[ "$link_mode" == "symlink" ]]; then
    if [[ -L "$dest" || -e "$dest" ]]; then
      rm -rf "$dest"
    fi
    ln -sfn "$src_dir" "$dest"
    echo "  $dest -> $src_dir"
  else
    mkdir -p "$dest"
    install -m 0644 "$src_dir/SKILL.md" "$dest/SKILL.md"
    echo "  $dest/SKILL.md (copy)"
  fi
}

install_cli() {
  echo "Installing CLI (editable) from $repo_root ..."
  python3 -m pip install -e "$repo_root"
  if command -v usage-trace >/dev/null 2>&1; then
    echo "  usage-trace -> $(command -v usage-trace)"
  else
    echo "  note: usage-trace not on PATH yet; open a new shell or check pip bin dir." >&2
  fi
}

dest_parents=()

case "$mode" in
  user|all)
    dest_parents+=(
      "${HOME}/.claude/skills"
      "${HOME}/.cursor/skills"
      "${HOME}/.agents/skills"
      "${CODEX_HOME:-$HOME/.codex}/skills"
    )
    ;;
  project)
    project_dir="${target:-$PWD}"
    project_dir="$(cd "$project_dir" && pwd)"
    dest_parents+=(
      "$project_dir/.claude/skills"
      "$project_dir/.cursor/skills"
      "$project_dir/.agents/skills"
    )
    ;;
  codex-user)
    dest_parents+=("${CODEX_HOME:-$HOME/.codex}/skills")
    ;;
  claude-user)
    dest_parents+=("${HOME}/.claude/skills")
    ;;
  cursor-user)
    dest_parents+=("${HOME}/.cursor/skills")
    ;;
  "")
    usage >&2
    exit 2
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

echo "Installed usage-trace skills ($link_mode): ${skill_names[*]}"
for parent in "${dest_parents[@]}"; do
  for name in "${skill_names[@]}"; do
    install_one "$parent/$name"
  done
done

if [[ "$skip_cli" -eq 0 ]]; then
  install_cli
else
  echo "Skipped CLI install (--skip-cli)."
fi

cat <<EOF

Ask your coding agent (examples):

  查找 orderId 字段项目使用情况
  Trace storeNo call chain and database tables in the current project
  给 storeNo 生成回归用例并打通上线SQL   (field-regression pipeline)

The agent should load this skill and run:

  usage-trace --keyword orderId --root . --profile auto --depth 4

Platform notes:
  - Claude Code: ~/.claude/skills or <project>/.claude/skills
  - Cursor:      ~/.cursor/skills or <project>/.cursor/skills
                  (also loads .agents/skills and Claude/Codex skill dirs)
  - Codex:       plugin marketplace, or ~/.codex/skills / install-skill.sh codex-user
EOF