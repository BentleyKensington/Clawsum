#!/usr/bin/env bash
# Copy deploy/skills/<name> onto OpenClaw + Hermes filesystem trees.
# Paperclip openclaw_gateway adapter does not sync skills.
set -euo pipefail
ROOT="${CLAWSUM_ROOT:-/docker/clawsum}"
SKILLS_SRC="$ROOT/skills"
OC="$ROOT/data/.openclaw/workspace/skills"
HERMES="$ROOT/paperclip-data/.hermes/skills/integrations"

install_one() {
  local name="$1"
  local src="$SKILLS_SRC/$name"
  if [[ ! -f "$src/SKILL.md" ]]; then
    echo "MISS $src/SKILL.md" >&2
    return 1
  fi
  mkdir -p "$OC/$name" "$HERMES/$name"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$src/" "$OC/$name/"
    rsync -a "$src/" "$HERMES/$name/"
  else
    cp -a "$src/." "$OC/$name/"
    cp -a "$src/." "$HERMES/$name/"
  fi
  echo "installed $name → $OC/$name"
}

if [[ "${1:-}" == "--all" ]]; then
  for d in "$SKILLS_SRC"/*/SKILL.md; do
    [[ -f "$d" ]] || continue
    name=$(basename "$(dirname "$d")")
    [[ "$name" == _* ]] && continue
    install_one "$name"
  done
elif [[ $# -ge 1 ]]; then
  for name in "$@"; do
    install_one "$name"
  done
else
  echo "usage: $0 --all | skill-name [skill-name...]" >&2
  exit 2
fi

# Keep CloseBot helper executable
chmod +x "$OC/closebot-api-operator/scripts/closebot_request.py" 2>/dev/null || true
echo "Note: gateway must mount workspace/skills (already the OpenClaw volume)."
