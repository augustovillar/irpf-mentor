#!/usr/bin/env bash
# Install the irpf-mentor Claude Code skills into your personal skills directory.
#
#   ./scripts/install_skills.sh            # copy into ~/.claude/skills/
#   ./scripts/install_skills.sh --link     # symlink instead (stays in sync with the repo)
#   CLAUDE_SKILLS_DIR=/path ./scripts/install_skills.sh
#
# Skills are plain files; Claude Code discovers them from the skills directory.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/integrations/claude_skills"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mode="copy"
[ "${1:-}" = "--link" ] && mode="link"

mkdir -p "$dest"
for skill in "$src"/*/; do
    name="$(basename "$skill")"
    target="$dest/$name"
    rm -rf "$target"
    if [ "$mode" = "link" ]; then
        ln -s "${skill%/}" "$target"
        echo "linked  $name -> $target"
    else
        cp -r "${skill%/}" "$target"
        echo "copied  $name -> $target"
    fi
done
echo "Done. Installed $(ls -1d "$src"/*/ | wc -l | tr -d ' ') skills into $dest"
