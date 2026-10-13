#!/usr/bin/env bash
# Link the skills of this repo into Claude Code (~/.claude/skills) and/or OpenCode
# (${XDG_CONFIG_HOME:-~/.config}/opencode/skills). Never replaces an existing entry.
set -euo pipefail

usage() {
  echo "usage: install.sh [--claude] [--opencode]" >&2
  exit 2
}

claude=0
opencode=0
[ $# -gt 0 ] || usage
for arg in "$@"; do
  case "$arg" in
    --claude) claude=1 ;;
    --opencode) opencode=1 ;;
    *) usage ;;
  esac
done

repo="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
claude_dir="$HOME/.claude/skills"
opencode_dir="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills"
status=0

# Print the physical path of a directory, or nothing if it does not resolve.
resolve() { (cd -P "$1" 2>/dev/null && pwd -P) || true; }

# link <skill dir> <target dir>
link() {
  local skill="$1" dest="$2/$(basename "$1")"
  if [ -L "$dest" ] || [ -e "$dest" ]; then
    if [ "$(resolve "$dest")" = "$skill" ]; then
      echo "already linked: $dest"
    elif [ -L "$dest" ] && [ ! -e "$dest" ]; then
      echo "dangling link, not replaced: $dest" >&2
      status=1
    else
      echo "exists, not replaced: $dest" >&2
      status=1
    fi
    return
  fi
  mkdir -p "$2"
  ln -s "$skill" "$dest"
  echo "linked: $dest -> $skill"
}

found=0
for skill in "$repo"/skills/*/; do
  skill="$(resolve "$skill")"
  [ -f "$skill/SKILL.md" ] || continue
  found=$((found + 1))
  name="$(basename "$skill")"
  if [ "$claude" = 1 ]; then
    link "$skill" "$claude_dir"
  fi
  if [ "$opencode" = 1 ]; then
    # OpenCode also reads ~/.claude/skills; a second link would list the skill twice.
    if [ "$(resolve "$claude_dir/$name")" = "$skill" ]; then
      echo "skipped: $opencode_dir/$name (OpenCode reads $claude_dir/$name)"
      if [ "$(resolve "$opencode_dir/$name")" = "$skill" ]; then
        echo "duplicate: OpenCode lists $name twice; remove $opencode_dir/$name" >&2
      fi
    else
      link "$skill" "$opencode_dir"
    fi
  fi
done

if [ "$found" = 0 ]; then
  echo "no skills found under $repo/skills; run install.sh from its clone, not through a link" >&2
  exit 1
fi
exit "$status"
